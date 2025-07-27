"""Smart routing algorithms for intelligent frame distribution."""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set

from prometheus_client import Counter, Histogram

from src.models import FrameReadyEvent

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Available routing strategies."""

    ROUND_ROBIN = "round_robin"
    LOAD_BALANCED = "load_balanced"
    AFFINITY = "affinity"
    CAPABILITY_AWARE = "capability_aware"
    PRIORITY_AWARE = "priority_aware"
    ADAPTIVE = "adaptive"


# Metrics
routing_decisions = Counter(
    "frame_buffer_routing_decisions_total",
    "Total routing decisions made",
    ["strategy", "processor_id"],
)

routing_latency = Histogram(
    "frame_buffer_routing_latency_seconds", "Time to make routing decision"
)


class BaseRouter(ABC):
    """Base class for routing algorithms."""

    def __init__(self):
        self.processors: Dict[str, Dict] = {}
        self.failed_processors: Set[str] = set()
        self.performance_history: Dict[str, Dict] = {}

    async def register_processor(self, processor_id: str, metadata: Dict):
        """Register a processor with its metadata."""
        self.processors[processor_id] = metadata
        logger.info(f"Registered processor {processor_id} with metadata: {metadata}")

    async def unregister_processor(self, processor_id: str):
        """Unregister a processor."""
        self.processors.pop(processor_id, None)
        self.failed_processors.discard(processor_id)
        logger.info(f"Unregistered processor {processor_id}")

    def mark_processor_failed(self, processor_id: str):
        """Mark processor as failed."""
        self.failed_processors.add(processor_id)
        logger.warning(f"Marked processor {processor_id} as failed")

    def mark_processor_recovered(self, processor_id: str):
        """Mark processor as recovered."""
        self.failed_processors.discard(processor_id)
        logger.info(f"Marked processor {processor_id} as recovered")

    def get_active_processors(self) -> List[str]:
        """Get list of active (non-failed) processors."""
        return [
            proc_id
            for proc_id in self.processors
            if proc_id not in self.failed_processors
        ]

    @abstractmethod
    async def route_frame(self, frame: FrameReadyEvent) -> Optional[str]:
        """Route frame to appropriate processor."""
        pass


class RoundRobinRouter(BaseRouter):
    """Simple round-robin routing."""

    def __init__(self):
        super().__init__()
        self.current_index = 0

    async def route_frame(self, frame: FrameReadyEvent) -> Optional[str]:
        """Route using round-robin algorithm."""
        active = self.get_active_processors()
        if not active:
            return None

        processor = active[self.current_index % len(active)]
        self.current_index += 1

        return processor


class AffinityRouter(BaseRouter):
    """Route based on camera-processor affinity."""

    def __init__(self):
        super().__init__()
        self.camera_assignments: Dict[str, str] = {}

    async def route_frame(self, frame: FrameReadyEvent) -> Optional[str]:
        """Route based on camera affinity."""
        # Check if camera has assigned processor
        if frame.camera_id in self.camera_assignments:
            assigned = self.camera_assignments[frame.camera_id]
            if assigned in self.get_active_processors():
                return assigned

        # Find processors with this camera assigned
        for proc_id, metadata in self.processors.items():
            if proc_id in self.failed_processors:
                continue

            assigned_cameras = metadata.get("assigned_cameras", [])
            if frame.camera_id in assigned_cameras:
                self.camera_assignments[frame.camera_id] = proc_id
                return proc_id

        # Fallback to processor with no specific assignments
        for proc_id, metadata in self.processors.items():
            if proc_id in self.failed_processors:
                continue

            assigned_cameras = metadata.get("assigned_cameras", [])
            if not assigned_cameras:  # Generic processor
                return proc_id

        # Last resort: any active processor
        active = self.get_active_processors()
        return active[0] if active else None


class LoadBalancedRouter(BaseRouter):
    """Route based on processor load."""

    def __init__(self):
        super().__init__()
        self.load_cache: Dict[str, Dict] = {}
        self.cache_expiry = timedelta(seconds=5)
        self.last_cache_update = datetime.now()

    async def get_processor_loads(self) -> Dict[str, Dict]:
        """Get current load for all processors."""
        # This would be implemented to fetch actual load metrics
        # For now, return cached values
        return self.load_cache

    async def route_frame(self, frame: FrameReadyEvent) -> Optional[str]:
        """Route to least loaded processor."""
        loads = await self.get_processor_loads()

        best_processor = None
        min_load_ratio = float("inf")

        for proc_id in self.get_active_processors():
            load_info = loads.get(proc_id, {"current_load": 0, "capacity": 100})
            load_ratio = load_info["current_load"] / max(1, load_info["capacity"])

            if load_ratio < min_load_ratio:
                min_load_ratio = load_ratio
                best_processor = proc_id

        return best_processor


class SmartRouter(BaseRouter):
    """Intelligent routing with multiple strategies."""

    def __init__(self, strategy: str = "adaptive"):
        super().__init__()
        self.strategy = RoutingStrategy(strategy)

        # Strategy-specific routers
        self.round_robin = RoundRobinRouter()
        self.affinity = AffinityRouter()
        self.load_balanced = LoadBalancedRouter()

        # Adaptive routing state
        self.routing_history = deque(maxlen=1000)
        self.performance_window = timedelta(minutes=5)

        # Copy processor state to sub-routers
        self.round_robin.processors = self.processors
        self.affinity.processors = self.processors
        self.load_balanced.processors = self.processors

    async def register_processor(self, processor_id: str, metadata: Dict):
        """Register processor in all sub-routers."""
        await super().register_processor(processor_id, metadata)

        # Update sub-routers
        self.round_robin.processors = self.processors
        self.affinity.processors = self.processors
        self.load_balanced.processors = self.processors

    async def get_capable_processors(self, frame: FrameReadyEvent) -> List[str]:
        """Get processors capable of handling the frame."""
        detection_type = frame.metadata.get("detection_type")
        if not detection_type:
            return self.get_active_processors()

        capable = []
        for proc_id, metadata in self.processors.items():
            if proc_id in self.failed_processors:
                continue

            capabilities = metadata.get("capabilities", [])
            if detection_type in capabilities:
                capable.append(proc_id)

        return capable

    async def route_frame(self, frame: FrameReadyEvent) -> Optional[str]:
        """Route frame using selected strategy."""
        with routing_latency.time():
            # Filter by capability first
            capable = await self.get_capable_processors(frame)
            if not capable:
                logger.warning(
                    f"No processor capable of {frame.metadata.get('detection_type')}"
                )
                return None

            # Apply routing strategy
            if self.strategy == RoutingStrategy.ROUND_ROBIN:
                processor = await self._route_round_robin(capable)

            elif self.strategy == RoutingStrategy.LOAD_BALANCED:
                processor = await self._route_load_balanced(capable)

            elif self.strategy == RoutingStrategy.AFFINITY:
                processor = await self._route_affinity(frame, capable)

            elif self.strategy == RoutingStrategy.CAPABILITY_AWARE:
                processor = await self._route_capability_aware(frame, capable)

            elif self.strategy == RoutingStrategy.PRIORITY_AWARE:
                processor = await self._route_priority_aware(frame, capable)

            elif self.strategy == RoutingStrategy.ADAPTIVE:
                processor = await self._route_adaptive(frame, capable)

            else:
                # Fallback to round-robin
                processor = capable[0] if capable else None

            if processor:
                routing_decisions.labels(
                    strategy=self.strategy.value, processor_id=processor
                ).inc()

                # Track routing decision
                self.routing_history.append(
                    {
                        "timestamp": datetime.now(),
                        "frame_id": frame.frame_id,
                        "processor": processor,
                        "strategy": self.strategy.value,
                    }
                )

            return processor

    async def _route_round_robin(self, processors: List[str]) -> Optional[str]:
        """Simple round-robin among capable processors."""
        if not processors:
            return None

        # Use hash of processor list to maintain consistency
        index = hash(tuple(sorted(processors))) % len(processors)
        return processors[index]

    async def _route_load_balanced(self, processors: List[str]) -> Optional[str]:
        """Route to least loaded among capable processors."""
        loads = await self.load_balanced.get_processor_loads()

        best = None
        min_load = float("inf")

        for proc in processors:
            load_info = loads.get(proc, {"current_load": 0, "capacity": 100})
            load = load_info["current_load"]

            if load < min_load:
                min_load = load
                best = proc

        return best

    async def _route_affinity(
        self, frame: FrameReadyEvent, processors: List[str]
    ) -> Optional[str]:
        """Route based on camera affinity."""
        # Check camera assignments
        for proc in processors:
            assigned_cameras = self.processors[proc].get("assigned_cameras", [])
            if frame.camera_id in assigned_cameras:
                return proc

        # Fallback to least assigned
        min_cameras = float("inf")
        best = None

        for proc in processors:
            assigned_cameras = self.processors[proc].get("assigned_cameras", [])
            if len(assigned_cameras) < min_cameras:
                min_cameras = len(assigned_cameras)
                best = proc

        return best

    async def _route_capability_aware(
        self, frame: FrameReadyEvent, processors: List[str]
    ) -> Optional[str]:
        """Route based on best capability match."""
        detection_type = frame.metadata.get("detection_type")

        # Prefer specialists over generalists
        specialists = []
        generalists = []

        for proc in processors:
            capabilities = self.processors[proc].get("capabilities", [])
            if len(capabilities) == 1 and detection_type in capabilities:
                specialists.append(proc)
            else:
                generalists.append(proc)

        # Prefer specialists
        if specialists:
            return random.choice(specialists)

        return random.choice(generalists) if generalists else None

    async def _route_priority_aware(
        self, frame: FrameReadyEvent, processors: List[str]
    ) -> Optional[str]:
        """Route high-priority frames to high-priority processors."""
        frame_priority = frame.priority

        # Find processor with matching priority
        best_match = None
        min_diff = float("inf")

        for proc in processors:
            proc_priority = self.processors[proc].get("priority", 5)
            diff = abs(frame_priority - proc_priority)

            if diff < min_diff:
                min_diff = diff
                best_match = proc

        return best_match

    async def _route_adaptive(
        self, frame: FrameReadyEvent, processors: List[str]
    ) -> Optional[str]:
        """Adaptive routing based on performance history."""
        # Score each processor
        scores = {}

        for proc in processors:
            perf = self.performance_history.get(proc, {})

            # Default scores
            latency_score = 100
            success_score = 0.5

            if perf:
                # Lower latency is better
                latency_score = 1000 / max(1, perf.get("avg_latency", 100))
                # Higher success rate is better
                success_score = perf.get("success_rate", 0.95)

            # Combined score
            scores[proc] = latency_score * success_score

        # Weighted random selection based on scores
        if not scores:
            return None

        total_score = sum(scores.values())
        if total_score == 0:
            return random.choice(list(scores.keys()))

        # Weighted selection
        rand = random.uniform(0, total_score)
        cumulative = 0

        for proc, score in scores.items():
            cumulative += score
            if rand <= cumulative:
                return proc

        return list(scores.keys())[-1]

    def update_performance(self, processor_id: str, latency: float, success: bool):
        """Update processor performance metrics."""
        if processor_id not in self.performance_history:
            self.performance_history[processor_id] = {
                "latencies": deque(maxlen=100),
                "successes": deque(maxlen=100),
            }

        perf = self.performance_history[processor_id]
        perf["latencies"].append(latency)
        perf["successes"].append(1 if success else 0)

        # Calculate rolling averages
        perf["avg_latency"] = sum(perf["latencies"]) / len(perf["latencies"])
        perf["success_rate"] = sum(perf["successes"]) / len(perf["successes"])
