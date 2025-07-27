"""Circuit breaker manager for processor-specific breakers."""

import logging
from typing import Dict, Optional

from .circuit_breaker import CircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)


class CircuitBreakerManager:
    """Manages circuit breakers for different processors."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
    ):
        """Initialize circuit breaker manager.

        Args:
            failure_threshold: Default failures before opening circuit
            recovery_timeout: Default seconds before attempting recovery
            success_threshold: Default successes needed to close from half-open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, processor_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for processor.

        Args:
            processor_id: Processor identifier

        Returns:
            Circuit breaker instance
        """
        if processor_id not in self.breakers:
            self.breakers[processor_id] = CircuitBreaker(
                name=f"processor_{processor_id}",
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
                success_threshold=self.success_threshold,
            )
            logger.info(f"Created circuit breaker for processor {processor_id}")

        return self.breakers[processor_id]

    async def call_processor(self, processor_id: str, func, fallback=None):
        """Call processor function through circuit breaker.

        Args:
            processor_id: Processor identifier
            func: Function to call
            fallback: Optional fallback function

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open and no fallback
        """
        breaker = self.get_breaker(processor_id)
        return await breaker.call(func, fallback)

    def is_processor_available(self, processor_id: str) -> bool:
        """Check if processor is available (circuit not open).

        Args:
            processor_id: Processor identifier

        Returns:
            True if processor is available
        """
        if processor_id not in self.breakers:
            return True  # No breaker means no failures yet

        return self.breakers[processor_id].state.value != "open"

    def get_available_processors(self, processor_ids: list) -> list:
        """Filter list of processors to only available ones.

        Args:
            processor_ids: List of processor IDs to check

        Returns:
            List of available processor IDs
        """
        return [pid for pid in processor_ids if self.is_processor_available(pid)]

    def get_all_metrics(self) -> Dict[str, dict]:
        """Get metrics for all circuit breakers.

        Returns:
            Dictionary mapping processor_id to metrics
        """
        return {
            processor_id: breaker.get_metrics()
            for processor_id, breaker in self.breakers.items()
        }

    def reset_processor(self, processor_id: str):
        """Reset circuit breaker for specific processor.

        Args:
            processor_id: Processor identifier
        """
        if processor_id in self.breakers:
            self.breakers[processor_id].reset()
            logger.info(f"Reset circuit breaker for processor {processor_id}")

    def reset_all(self):
        """Reset all circuit breakers."""
        for processor_id, breaker in self.breakers.items():
            breaker.reset()
        logger.info("Reset all circuit breakers")
