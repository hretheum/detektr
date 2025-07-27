"""Frame distributor - routes frames to appropriate processors."""

import logging
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

import redis.asyncio as aioredis

from src.models import FrameReadyEvent
from src.orchestrator.processor_registry import ProcessorInfo, ProcessorRegistry

logger = logging.getLogger(__name__)


class FrameDistributor:
    """Distributes frames to processors based on capabilities and load."""

    DEFAULT_QUEUE_MAXLEN = 10000  # Increased default queue size

    def __init__(
        self, registry: ProcessorRegistry, redis_client: Optional[aioredis.Redis] = None
    ):
        """Initialize distributor with registry and optional Redis client."""
        self.registry = registry
        self.redis = redis_client
        self.processor_failures = defaultdict(list)
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = timedelta(minutes=5)

    def is_processor_available(self, processor_id: str) -> bool:
        """Check if processor circuit breaker is open."""
        failures = self.processor_failures[processor_id]
        if len(failures) < self.circuit_breaker_threshold:
            return True

        # Check if timeout has passed since last failure
        last_failure = failures[-1]
        if datetime.now() - last_failure > self.circuit_breaker_timeout:
            # Reset circuit breaker
            self.processor_failures[processor_id] = []
            return True

        return False

    async def get_eligible_processors(
        self, frame: FrameReadyEvent
    ) -> List[ProcessorInfo]:
        """Get processors that can handle this frame."""
        # Extract required capability from frame metadata
        detection_type = frame.metadata.get("detection_type")
        if not detection_type:
            logger.warning(f"Frame {frame.frame_id} missing detection_type metadata")
            return []

        # Find processors with this capability
        processors = await self.registry.find_by_capability(detection_type)

        # Filter out processors with open circuit breakers
        available = [p for p in processors if self.is_processor_available(p.id)]

        return available

    async def get_queue_length(self, queue_name: str) -> int:
        """Get current length of a processor queue."""
        if not self.redis:
            return 0
        return await self.redis.xlen(queue_name)

    async def select_processor(self, frame: FrameReadyEvent) -> Optional[ProcessorInfo]:
        """Select best processor for the frame based on capabilities and load."""
        eligible = await self.get_eligible_processors(frame)
        if not eligible:
            return None

        # If we have Redis, check queue lengths for load balancing
        if self.redis:
            # Get queue lengths for all eligible processors
            processor_loads = []
            for proc in eligible:
                queue_len = await self.get_queue_length(proc.queue)
                # Calculate load percentage
                load_pct = (
                    (queue_len / proc.capacity) * 100 if proc.capacity > 0 else 100
                )
                processor_loads.append((proc, load_pct, queue_len))

            # Sort by load percentage (ascending)
            processor_loads.sort(key=lambda x: x[1])

            # Filter out overloaded processors (>90% capacity)
            available = [p for p in processor_loads if p[1] < 90]

            if available:
                # Among least loaded processors, pick randomly for better distribution
                # Take processors within 10% load of the least loaded
                min_load = available[0][1]
                similar_load = [p for p in available if p[1] <= min_load + 10]
                selected = random.choice(similar_load)
                return selected[0]
            else:
                # All processors are overloaded, pick least loaded
                if processor_loads:
                    return processor_loads[0][0]

        # No Redis or no load info - pick randomly
        return random.choice(eligible) if eligible else None

    async def dispatch_to_processor(
        self, processor: ProcessorInfo, frame: FrameReadyEvent
    ) -> str:
        """Dispatch frame to processor's queue."""
        if not self.redis:
            raise RuntimeError("Redis client required for dispatch")

        # Convert frame to Redis Stream format
        frame_data = frame.to_json()

        # Get configurable maxlen or use default
        maxlen = processor.metadata.get("queue_maxlen", self.DEFAULT_QUEUE_MAXLEN)

        # Add to processor's queue
        msg_id = await self.redis.xadd(processor.queue, frame_data, maxlen=maxlen)
        return msg_id

    async def distribute_frame(self, frame: FrameReadyEvent) -> bool:
        """Distribute a frame to appropriate processor."""
        try:
            processor = await self.select_processor(frame)
            if not processor:
                logger.warning(
                    f"No processor available for frame {frame.frame_id} "
                    f"with capability {frame.metadata.get('detection_type')}"
                )
                return False

            msg_id = await self.dispatch_to_processor(processor, frame)
            logger.debug(
                f"Dispatched frame {frame.frame_id} to processor {processor.id} "
                f"(queue: {processor.queue}, msg_id: {msg_id})"
            )

            # TODO: Update metrics when metrics system is implemented
            # self.metrics.frames_distributed.inc(
            #     processor_id=processor.id,
            #     camera_id=frame.camera_id
            # )

            return True

        except Exception as e:
            logger.error(
                f"Failed to distribute frame {frame.frame_id}: {e}", exc_info=True
            )
            # Record failure for circuit breaker
            if hasattr(e, "processor_id"):
                self.processor_failures[e.processor_id].append(datetime.now())
            return False
