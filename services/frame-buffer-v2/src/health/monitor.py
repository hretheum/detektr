"""Health monitoring system for processors."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ProcessorHealthStatus:
    """Detailed health status for a processor."""

    processor_id: str
    status: str  # healthy, unhealthy, degraded
    last_check: datetime
    consecutive_failures: int
    capacity_used: float = 0.0
    frames_processed: int = 0
    avg_processing_time_ms: float = 0.0
    errors_last_minute: int = 0


class CircuitBreaker:
    """Circuit breaker for processor health checks."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 300):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.is_open = False
        self._lock = asyncio.Lock()

    async def record_success(self):
        """Record successful check."""
        async with self._lock:
            self.failure_count = 0
            self.is_open = False

    async def record_failure(self):
        """Record failed check."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now(timezone.utc)

            if self.failure_count >= self.failure_threshold:
                self.is_open = True

    def can_attempt(self) -> bool:
        """Check if we can attempt a health check."""
        if not self.is_open:
            return True

        # Check if recovery timeout has passed
        if self.last_failure_time:
            if (
                datetime.now(timezone.utc) - self.last_failure_time
                > self.recovery_timeout
            ):
                # Try to recover
                self.is_open = False
                self.failure_count = 0
                return True

        return False


class HealthMonitor:
    """Monitors health of registered processors."""

    def __init__(
        self,
        check_interval: float = 10.0,
        timeout: float = 5.0,
        failure_threshold: int = 5,
        recovery_timeout: float = 300,
        on_status_change: Optional[Callable] = None,
    ):
        """Initialize health monitor."""
        self.check_interval = check_interval
        self.timeout = timeout
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.on_status_change = on_status_change

        self.processors: Dict[str, str] = {}  # processor_id -> health_endpoint
        self.health_status: Dict[str, ProcessorHealthStatus] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.http_client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def add_processor(self, processor_id: str, health_endpoint: str) -> None:
        """Add processor to monitoring."""
        # Validate endpoint
        if not health_endpoint.startswith(("http://", "https://")):
            raise ValueError(f"Invalid health endpoint URL: {health_endpoint}")

        self.processors[processor_id] = health_endpoint
        self.circuit_breakers[processor_id] = CircuitBreaker(
            self.failure_threshold, self.recovery_timeout
        )
        logger.info(f"Added processor {processor_id} to health monitoring")

    async def remove_processor(self, processor_id: str):
        """Remove processor from monitoring."""
        self.processors.pop(processor_id, None)
        self.health_status.pop(processor_id, None)
        self.circuit_breakers.pop(processor_id, None)
        logger.info(f"Removed processor {processor_id} from health monitoring")

    async def get_status(self, processor_id: str) -> Optional[str]:
        """Get current status of a processor."""
        if processor_id in self.health_status:
            return self.health_status[processor_id].status
        return None

    async def get_health_details(
        self, processor_id: str
    ) -> Optional[ProcessorHealthStatus]:
        """Get detailed health information."""
        return self.health_status.get(processor_id)

    async def is_circuit_open(self, processor_id: str) -> bool:
        """Check if circuit breaker is open for processor."""
        breaker = self.circuit_breakers.get(processor_id)
        return breaker.is_open if breaker else False

    async def check_processor_health(self, processor_id: str):
        """Check health of a single processor."""
        endpoint = self.processors.get(processor_id)
        if not endpoint:
            return

        breaker = self.circuit_breakers[processor_id]
        if not breaker.can_attempt():
            logger.debug(f"Circuit breaker open for {processor_id}, skipping check")
            return

        old_status = self.health_status.get(processor_id)
        old_status_str = old_status.status if old_status else None

        try:
            response = await self.http_client.get(endpoint)

            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "healthy")

                # Update health status
                health = ProcessorHealthStatus(
                    processor_id=processor_id,
                    status=status,
                    last_check=datetime.now(timezone.utc),
                    consecutive_failures=0,
                    capacity_used=data.get("capacity_used", 0.0),
                    frames_processed=data.get("frames_processed", 0),
                    avg_processing_time_ms=data.get("avg_processing_time_ms", 0.0),
                    errors_last_minute=data.get("errors_last_minute", 0),
                )

                self.health_status[processor_id] = health
                await breaker.record_success()

                # Notify status change
                if old_status_str != status and self.on_status_change:
                    await self.on_status_change(processor_id, old_status_str, status)

                logger.debug(f"Processor {processor_id} is {status}")

            else:
                await self._mark_unhealthy(processor_id, f"HTTP {response.status_code}")
                await breaker.record_failure()

        except asyncio.TimeoutError:
            await self._mark_unhealthy(processor_id, "Timeout")
            await breaker.record_failure()
        except httpx.HTTPError as e:
            await self._mark_unhealthy(processor_id, f"HTTP error: {e}")
            await breaker.record_failure()
        except Exception as e:
            await self._mark_unhealthy(processor_id, f"Unexpected error: {e}")
            await breaker.record_failure()
            logger.exception(f"Unexpected error in health check for {processor_id}")

    async def _mark_unhealthy(self, processor_id: str, reason: str) -> None:
        """Mark processor as unhealthy."""
        old_status = self.health_status.get(processor_id)
        old_status_str = old_status.status if old_status else None
        consecutive_failures = (
            (old_status.consecutive_failures + 1) if old_status else 1
        )

        health = ProcessorHealthStatus(
            processor_id=processor_id,
            status="unhealthy",
            last_check=datetime.now(timezone.utc),
            consecutive_failures=consecutive_failures,
        )

        self.health_status[processor_id] = health

        # Notify status change
        if old_status_str != "unhealthy" and self.on_status_change:
            try:
                await self.on_status_change(processor_id, old_status_str, "unhealthy")
            except Exception as e:
                logger.error(f"Error in status change callback: {e}")

        logger.warning(f"Processor {processor_id} marked unhealthy: {reason}")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            tasks = []
            for processor_id in list(self.processors.keys()):
                task = asyncio.create_task(self.check_processor_health(processor_id))
                tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            await asyncio.sleep(self.check_interval)

    async def start(self):
        """Start health monitoring."""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitoring started")

    async def stop(self):
        """Stop health monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        await self.http_client.aclose()
        logger.info("Health monitoring stopped")

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()
