"""Retry and error handling utilities."""
import asyncio
import random
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, Type, TypeVar, Union

T = TypeVar("T")


class RetryPolicy:
    """Configurable retry policy."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ):
        """Initialize retry policy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Tuple of exceptions to retry on
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (Exception,)

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        # Exponential backoff
        delay = min(
            self.base_delay * (self.exponential_base**attempt), self.max_delay
        )

        # Add jitter if enabled
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def should_retry(self, exception: Exception) -> bool:
        """Check if exception is retryable."""
        return isinstance(exception, self.retryable_exceptions)


def with_retry(policy: Optional[RetryPolicy] = None):
    """Decorator for adding retry logic to async functions.

    Args:
        policy: Retry policy to use, defaults to standard policy
    """
    if policy is None:
        policy = RetryPolicy()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(policy.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not policy.should_retry(e) or attempt == policy.max_attempts - 1:
                        raise

                    delay = policy.calculate_delay(attempt)
                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time in seconds before attempting to close circuit
            expected_exception: Exception type to count as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half-open

    @property
    def state(self) -> str:
        """Get current circuit state."""
        if self._state == "open":
            # Check if we should transition to half-open
            if (
                self._last_failure_time
                and time.time() - self._last_failure_time >= self.recovery_timeout
            ):
                self._state = "half-open"
        return self._state

    def call(self, func: Callable):
        """Decorator to protect function calls with circuit breaker."""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                raise Exception("Circuit breaker is OPEN")

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise

        return wrapper

    def _on_success(self):
        """Handle successful call."""
        if self._state == "half-open":
            self._state = "closed"
        self._failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"


class ErrorHandler:
    """Centralized error handling with recovery strategies."""

    def __init__(self):
        self.recovery_strategies = {}
        self.fallback_handlers = {}

    def register_recovery(
        self, exception_type: Type[Exception], recovery_func: Callable
    ):
        """Register a recovery strategy for specific exception type."""
        self.recovery_strategies[exception_type] = recovery_func

    def register_fallback(
        self, exception_type: Type[Exception], fallback_func: Callable
    ):
        """Register a fallback handler for specific exception type."""
        self.fallback_handlers[exception_type] = fallback_func

    async def handle_error(self, exception: Exception, context: Dict) -> Any:
        """Handle an error with registered strategies.

        Args:
            exception: The exception that occurred
            context: Context information for recovery

        Returns:
            Recovery result or re-raises exception
        """
        # Try recovery strategy first
        for exc_type, recovery_func in self.recovery_strategies.items():
            if isinstance(exception, exc_type):
                try:
                    return await recovery_func(exception, context)
                except Exception:
                    # Recovery failed, continue to fallback
                    pass

        # Try fallback handler
        for exc_type, fallback_func in self.fallback_handlers.items():
            if isinstance(exception, exc_type):
                return await fallback_func(exception, context)

        # No handler found, re-raise
        raise exception
