"""Unit tests for retry and error handling."""
import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest
from base_processor.exceptions import ProcessingError
from base_processor.retry import CircuitBreaker, ErrorHandler, RetryPolicy, with_retry


class TestRetryPolicy:
    """Test retry policy functionality."""

    def test_default_policy(self):
        """Test default retry policy settings."""
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.exponential_base == 2.0
        assert policy.jitter is True

    def test_calculate_delay_exponential(self):
        """Test exponential backoff calculation."""
        policy = RetryPolicy(base_delay=1.0, jitter=False)

        assert policy.calculate_delay(0) == 1.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 4.0
        assert policy.calculate_delay(3) == 8.0

    def test_calculate_delay_with_max(self):
        """Test delay calculation respects max_delay."""
        policy = RetryPolicy(base_delay=10.0, max_delay=30.0, jitter=False)

        assert policy.calculate_delay(0) == 10.0
        assert policy.calculate_delay(1) == 20.0
        assert policy.calculate_delay(2) == 30.0  # Capped at max
        assert policy.calculate_delay(3) == 30.0  # Still capped

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        policy = RetryPolicy(base_delay=10.0, jitter=True)

        # With jitter, delay should be between 50% and 100% of base
        for i in range(10):
            delay = policy.calculate_delay(1)
            assert 10.0 <= delay <= 20.0  # 50% to 100% of 20.0

    def test_should_retry(self):
        """Test retry decision based on exception type."""
        policy = RetryPolicy(retryable_exceptions=(ValueError, ProcessingError))

        assert policy.should_retry(ValueError("test"))
        assert policy.should_retry(ProcessingError("test"))
        assert not policy.should_retry(TypeError("test"))


class TestRetryDecorator:
    """Test retry decorator functionality."""

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test decorator with successful function call."""
        call_count = 0

        @with_retry(RetryPolicy(max_attempts=3))
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry on failure."""
        call_count = 0

        @with_retry(RetryPolicy(max_attempts=3, base_delay=0.1, jitter=False))
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = await failing_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test failure when max attempts exceeded."""
        call_count = 0

        @with_retry(RetryPolicy(max_attempts=3, base_delay=0.1))
        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await always_failing_func()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test non-retryable exception is raised immediately."""
        call_count = 0

        @with_retry(RetryPolicy(retryable_exceptions=(ValueError,)))
        async def func_with_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Non-retryable")

        with pytest.raises(TypeError, match="Non-retryable"):
            await func_with_type_error()

        assert call_count == 1  # No retry


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_initial_state(self):
        """Test circuit breaker starts closed."""
        cb = CircuitBreaker()
        assert cb.state == "closed"

    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self):
        """Test circuit opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        @cb.call
        async def failing_func():
            raise ValueError("Failure")

        # First failures
        for i in range(3):
            with pytest.raises(ValueError):
                await failing_func()

        # Circuit should be open now
        assert cb.state == "open"

        # Next call should fail immediately
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await failing_func()

    @pytest.mark.asyncio
    async def test_circuit_recovery(self):
        """Test circuit breaker recovery to half-open state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        @cb.call
        async def sometimes_failing_func():
            if cb._failure_count >= 2:
                return "success"
            raise ValueError("Failure")

        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await sometimes_failing_func()

        assert cb.state == "open"

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Should be half-open now
        assert cb.state == "half-open"

    @pytest.mark.asyncio
    async def test_successful_reset(self):
        """Test successful call resets circuit."""
        cb = CircuitBreaker()

        success_count = 0

        @cb.call
        async def func():
            nonlocal success_count
            success_count += 1
            return "success"

        # Successful calls
        for i in range(5):
            result = await func()
            assert result == "success"

        assert cb._failure_count == 0
        assert cb.state == "closed"


class TestErrorHandler:
    """Test error handler functionality."""

    @pytest.mark.asyncio
    async def test_recovery_strategy(self):
        """Test recovery strategy execution."""
        handler = ErrorHandler()

        async def recover_from_value_error(exc, context):
            return {"recovered": True, "original_error": str(exc)}

        handler.register_recovery(ValueError, recover_from_value_error)

        result = await handler.handle_error(ValueError("test error"), {})
        assert result["recovered"] is True
        assert result["original_error"] == "test error"

    @pytest.mark.asyncio
    async def test_fallback_handler(self):
        """Test fallback handler when recovery fails."""
        handler = ErrorHandler()

        async def failing_recovery(exc, context):
            raise Exception("Recovery failed")

        async def fallback(exc, context):
            return {"fallback": True}

        handler.register_recovery(ValueError, failing_recovery)
        handler.register_fallback(ValueError, fallback)

        result = await handler.handle_error(ValueError("test"), {})
        assert result["fallback"] is True

    @pytest.mark.asyncio
    async def test_no_handler_reraises(self):
        """Test exception is re-raised when no handler found."""
        handler = ErrorHandler()

        with pytest.raises(TypeError, match="Unhandled"):
            await handler.handle_error(TypeError("Unhandled"), {})
