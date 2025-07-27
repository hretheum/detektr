"""Circuit breaker implementation for failure isolation."""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, Set, Type, Union

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitOpenError(Exception):
    """Exception raised when circuit is open."""

    pass


# Metrics
circuit_state_gauge = Gauge(
    "frame_buffer_circuit_breaker_state",
    "Current circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["name"],
)

circuit_calls_total = Counter(
    "frame_buffer_circuit_breaker_calls_total",
    "Total circuit breaker calls",
    ["name", "result"],
)

circuit_state_changes = Counter(
    "frame_buffer_circuit_breaker_state_changes_total",
    "Circuit breaker state changes",
    ["name", "from_state", "to_state"],
)

call_duration = Histogram(
    "frame_buffer_circuit_breaker_call_duration_seconds",
    "Duration of calls through circuit breaker",
    ["name"],
)


class CircuitBreaker:
    """Circuit breaker for automatic failure isolation."""

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
        timeout: Optional[float] = None,
        excluded_exceptions: Optional[Set[Type[Exception]]] = None,
    ):
        """Initialize circuit breaker.

        Args:
            name: Circuit breaker name for identification
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Successes needed to close from half-open
            timeout: Optional timeout for calls (seconds)
            excluded_exceptions: Exceptions that don't count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.excluded_exceptions = excluded_exceptions or set()

        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change = datetime.now()

        # Metrics
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.circuit_open_count = 0

        # Update state metric
        self._update_state_metric()

    def _update_state_metric(self):
        """Update Prometheus state metric."""
        state_value = {
            CircuitState.CLOSED: 0,
            CircuitState.HALF_OPEN: 1,
            CircuitState.OPEN: 2,
        }[self.state]
        circuit_state_gauge.labels(name=self.name).set(state_value)

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from open state."""
        if self.last_failure_time is None:
            return True

        return datetime.now() - self.last_failure_time > timedelta(
            seconds=self.recovery_timeout
        )

    def _change_state(self, new_state: CircuitState):
        """Change circuit state and update metrics."""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            self.last_state_change = datetime.now()

            # Update metrics
            circuit_state_changes.labels(
                name=self.name, from_state=old_state.value, to_state=new_state.value
            ).inc()
            self._update_state_metric()

            # Log state change
            logger.info(
                f"Circuit breaker '{self.name}' state changed: "
                f"{old_state.value} → {new_state.value}"
            )

            if new_state == CircuitState.OPEN:
                self.circuit_open_count += 1

    def _on_success(self):
        """Handle successful call."""
        self.successful_calls += 1
        circuit_calls_total.labels(name=self.name, result="success").inc()

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._change_state(CircuitState.CLOSED)
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failed_calls += 1
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        circuit_calls_total.labels(name=self.name, result="failure").inc()

        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._change_state(CircuitState.OPEN)
        elif self.state == CircuitState.HALF_OPEN:
            # Single failure in half-open reopens circuit
            self._change_state(CircuitState.OPEN)
            self.success_count = 0

    async def call(self, func: Callable, fallback: Optional[Callable] = None) -> Any:
        """Execute function through circuit breaker.

        Args:
            func: Function to execute (sync or async)
            fallback: Optional fallback function if circuit is open

        Returns:
            Function result or fallback result

        Raises:
            CircuitOpenError: If circuit is open and no fallback provided
            Exception: Original exception from function
        """
        self.total_calls += 1

        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._change_state(CircuitState.HALF_OPEN)
                self.failure_count = 0
                self.success_count = 0
            else:
                circuit_calls_total.labels(name=self.name, result="rejected").inc()
                if fallback:
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback()
                    return fallback()
                raise CircuitOpenError(f"Circuit breaker '{self.name}' is open")

        # Execute function with timeout if specified
        try:
            with call_duration.labels(name=self.name).time():
                if self.timeout:
                    if asyncio.iscoroutinefunction(func):
                        result = await asyncio.wait_for(func(), timeout=self.timeout)
                    else:
                        # For sync functions with timeout, run in executor
                        loop = asyncio.get_event_loop()
                        result = await asyncio.wait_for(
                            loop.run_in_executor(None, func), timeout=self.timeout
                        )
                else:
                    if asyncio.iscoroutinefunction(func):
                        result = await func()
                    else:
                        result = func()

            self._on_success()
            return result

        except asyncio.TimeoutError:
            self._on_failure()
            raise

        except Exception as e:
            # Check if exception should be excluded
            if type(e) in self.excluded_exceptions:
                # Don't count as failure
                circuit_calls_total.labels(name=self.name, result="excluded").inc()
                raise

            self._on_failure()
            raise

    def get_metrics(self) -> dict:
        """Get circuit breaker metrics.

        Returns:
            Dictionary of metrics
        """
        success_rate = (
            self.successful_calls / self.total_calls if self.total_calls > 0 else 0
        )

        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "circuit_open_count": self.circuit_open_count,
            "success_rate": success_rate,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat()
            if self.last_failure_time
            else None,
            "last_state_change": self.last_state_change.isoformat(),
        }

    def reset(self):
        """Manually reset circuit breaker to closed state."""
        self._change_state(CircuitState.CLOSED)
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' manually reset")

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name='{self.name}', state={self.state.value}, "
            f"failures={self.failure_count}/{self.failure_threshold})"
        )
