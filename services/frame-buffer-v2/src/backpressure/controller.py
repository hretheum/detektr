"""Backpressure controller for managing system load."""

import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from typing import Dict, Optional

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


class PressureLevel(IntEnum):
    """Backpressure severity levels."""

    NORMAL = 0
    LOW = 1
    HIGH = 2
    CRITICAL = 3


# Metrics (module level to avoid duplication)
backpressure_level = Gauge(
    "frame_buffer_backpressure_level",
    "Current backpressure level (0=normal, 1=low, 2=high, 3=critical)",
)

consumption_rate = Gauge(
    "frame_buffer_consumption_rate", "Current consumption rate multiplier (0.0-1.0)"
)

queue_utilization = Gauge(
    "frame_buffer_queue_utilization", "Queue utilization percentage", ["processor_id"]
)

backpressure_events = Counter(
    "frame_buffer_backpressure_events_total", "Total backpressure events", ["level"]
)

throttle_duration = Histogram(
    "frame_buffer_throttle_duration_seconds", "Duration of throttling periods"
)


class BackpressureController:
    """Controls system behavior based on queue pressure."""

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        check_interval: float = 5.0,
        adaptive: bool = False,
    ):
        """Initialize backpressure controller.

        Args:
            thresholds: Pressure thresholds (low, high, critical)
            check_interval: How often to check pressure (seconds)
            adaptive: Enable adaptive threshold adjustment
        """
        self.thresholds = thresholds or {
            "low": 0.6,  # 60% utilization
            "high": 0.8,  # 80% utilization
            "critical": 0.95,  # 95% utilization
        }
        self.check_interval = check_interval
        self.adaptive = adaptive

        # State
        self.is_paused = False
        self.consumption_rate = 1.0  # 1.0 = normal, 0.5 = 50% speed
        self.current_level = PressureLevel.NORMAL
        self.throttle_start_time: Optional[datetime] = None

        # History for adaptive adjustment
        self.pressure_history = deque(maxlen=100)
        self.last_adjustment = datetime.now()

        # Alert tracking
        self.last_alert_time: Optional[datetime] = None
        self.alert_cooldown = timedelta(minutes=5)

    async def get_queue_stats(self) -> Dict[str, Dict]:
        """Get current queue statistics.

        Returns:
            Dict mapping processor_id to stats (size, capacity, priority)
        """
        # This should be implemented to fetch actual queue stats
        # from Redis or queue manager
        raise NotImplementedError("Subclass must implement get_queue_stats")

    async def check_pressure(self) -> PressureLevel:
        """Check current system pressure level.

        Returns:
            Current pressure level
        """
        stats = await self.get_queue_stats()

        if not stats:
            return PressureLevel.NORMAL

        # Calculate maximum utilization across all queues
        max_utilization = 0.0
        total_size = 0
        total_capacity = 0

        for proc_id, proc_stats in stats.items():
            size = proc_stats.get("size", 0)
            capacity = proc_stats.get("capacity", 100)

            if capacity > 0:
                utilization = size / capacity
                max_utilization = max(max_utilization, utilization)

                # Update per-queue metric
                queue_utilization.labels(processor_id=proc_id).set(utilization * 100)

            total_size += size
            total_capacity += capacity

        # Determine pressure level
        if max_utilization >= self.thresholds["critical"]:
            level = PressureLevel.CRITICAL
        elif max_utilization >= self.thresholds["high"]:
            level = PressureLevel.HIGH
        elif max_utilization >= self.thresholds["low"]:
            level = PressureLevel.LOW
        else:
            level = PressureLevel.NORMAL

        # Track history
        self.pressure_history.append(level)

        logger.debug(
            f"Pressure check: max_utilization={max_utilization:.2%}, "
            f"level={level.name}, queues={len(stats)}"
        )

        return level

    async def apply_backpressure(self, level: PressureLevel):
        """Apply appropriate backpressure response.

        Args:
            level: Current pressure level
        """
        previous_level = self.current_level
        self.current_level = level

        # Record level change
        if level != previous_level:
            backpressure_events.labels(level=level.name).inc()
            logger.info(
                f"Backpressure level changed: {previous_level.name} → {level.name}"
            )

        # Start throttle timing if entering pressure state
        if level > PressureLevel.NORMAL and self.throttle_start_time is None:
            self.throttle_start_time = datetime.now()

        # Apply appropriate response
        if level == PressureLevel.CRITICAL:
            # Pause consumption
            self.is_paused = True
            self.consumption_rate = 0.0
            logger.warning("CRITICAL pressure: Pausing frame consumption")

        elif level == PressureLevel.HIGH:
            # Severe throttling
            self.is_paused = False
            self.consumption_rate = 0.5  # 50% speed
            logger.warning("HIGH pressure: Throttling to 50% consumption rate")

        elif level == PressureLevel.LOW:
            # Mild throttling
            self.is_paused = False
            self.consumption_rate = 0.8  # 80% speed
            logger.info("LOW pressure: Throttling to 80% consumption rate")

        else:  # NORMAL
            # Resume normal operation
            self.is_paused = False
            self.consumption_rate = 1.0

            # Record throttle duration if we were throttling
            if self.throttle_start_time:
                duration = (datetime.now() - self.throttle_start_time).total_seconds()
                throttle_duration.observe(duration)
                self.throttle_start_time = None

            logger.info("NORMAL pressure: Resuming full consumption rate")

        # Update metrics
        await self.update_metrics(level)

        # Adaptive threshold adjustment
        if self.adaptive and level != previous_level:
            await self.adjust_thresholds()

    async def update_metrics(self, level: PressureLevel):
        """Update Prometheus metrics.

        Args:
            level: Current pressure level
        """
        backpressure_level.set(level.value)
        consumption_rate.set(self.consumption_rate)

    def adjust_thresholds(self):
        """Adaptively adjust thresholds based on history."""
        if len(self.pressure_history) < 50:
            return

        # Only adjust once per minute
        if datetime.now() - self.last_adjustment < timedelta(minutes=1):
            return

        # Count recent pressure levels
        recent = list(self.pressure_history)[-50:]
        high_count = sum(1 for l in recent if l >= PressureLevel.HIGH)
        critical_count = sum(1 for l in recent if l == PressureLevel.CRITICAL)

        # If sustaining high pressure, lower thresholds
        if high_count > 30:  # >60% of time in high pressure
            self.thresholds["high"] *= 0.95
            self.thresholds["critical"] *= 0.97
            logger.info(f"Adjusted thresholds down: {self.thresholds}")

        # If rarely hitting pressure, raise thresholds
        elif high_count < 5:  # <10% of time in pressure
            self.thresholds["high"] = min(0.85, self.thresholds["high"] * 1.05)
            self.thresholds["critical"] = min(0.98, self.thresholds["critical"] * 1.02)
            logger.info(f"Adjusted thresholds up: {self.thresholds}")

        self.last_adjustment = datetime.now()

    async def get_throttle_decisions(self) -> Dict[str, Dict]:
        """Get per-processor throttling decisions.

        Returns:
            Dict mapping processor_id to throttle decision
        """
        stats = await self.get_queue_stats()
        decisions = {}

        for proc_id, proc_stats in stats.items():
            size = proc_stats.get("size", 0)
            capacity = proc_stats.get("capacity", 100)
            priority = proc_stats.get("priority", 1)

            utilization = size / capacity if capacity > 0 else 0

            # Higher priority queues get less throttling
            priority_factor = 1.0 / max(1, priority)

            # Calculate throttle amount
            if utilization > self.thresholds["critical"]:
                throttle = 0.9 * priority_factor  # 90% throttle
            elif utilization > self.thresholds["high"]:
                throttle = 0.5 * priority_factor  # 50% throttle
            elif utilization > self.thresholds["low"]:
                throttle = 0.2 * priority_factor  # 20% throttle
            else:
                throttle = 0.0

            decisions[proc_id] = {
                "throttle": throttle,
                "utilization": utilization,
                "priority": priority,
            }

        return decisions

    async def send_alert(self, message: str, **kwargs):
        """Send alert for critical conditions.

        Args:
            message: Alert message
            **kwargs: Additional context
        """
        # Check cooldown
        if self.last_alert_time:
            if datetime.now() - self.last_alert_time < self.alert_cooldown:
                return

        # This should be implemented to send actual alerts
        # (e.g., webhook, email, PagerDuty)
        logger.critical(f"ALERT: {message}", extra=kwargs)
        self.last_alert_time = datetime.now()

    async def monitor_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                level = await self.check_pressure()
                await self.apply_backpressure(level)

                # Alert if critical
                if level == PressureLevel.CRITICAL:
                    await self.send_alert(
                        "Critical backpressure detected",
                        queue_stats=await self.get_queue_stats(),
                    )

            except Exception as e:
                logger.error(f"Backpressure monitoring error: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval)

    async def get_status(self) -> Dict:
        """Get current backpressure status.

        Returns:
            Status dictionary
        """
        return {
            "level": self.current_level.name,
            "consumption_rate": self.consumption_rate,
            "is_paused": self.is_paused,
            "thresholds": self.thresholds,
            "adaptive": self.adaptive,
            "history": {
                "last_10": [l.name for l in list(self.pressure_history)[-10:]],
                "average": sum(self.pressure_history) / len(self.pressure_history)
                if self.pressure_history
                else 0,
            },
        }
