"""Tests for circuit breaker implementation."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from src.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


@pytest.mark.asyncio
async def test_circuit_breaker_states():
    """Test circuit breaker state transitions."""
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=1.0,  # 1 second for tests
        success_threshold=2,
    )

    # Initial state is closed
    assert breaker.state == CircuitState.CLOSED
    assert await breaker.call(lambda: "success") == "success"

    # Simulate failures
    for _ in range(3):
        with pytest.raises(Exception):
            await breaker.call(lambda: exec('raise Exception("fail")'))

    # Should be open after threshold
    assert breaker.state == CircuitState.OPEN

    # Calls should fail fast when open
    with pytest.raises(CircuitOpenError):
        await breaker.call(lambda: "success")

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # Circuit should still be open, but next call should transition to half-open
    assert breaker.state == CircuitState.OPEN

    # This call should transition to half-open and succeed
    result = await breaker.call(lambda: "recovery_test")
    assert result == "recovery_test"
    assert breaker.state == CircuitState.HALF_OPEN

    # Success should close circuit
    await breaker.call(lambda: "success")
    await breaker.call(lambda: "success")
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_async_functions():
    """Test circuit breaker with async functions."""
    breaker = CircuitBreaker(failure_threshold=2)

    async def async_success():
        await asyncio.sleep(0.01)
        return "async_success"

    async def async_failure():
        await asyncio.sleep(0.01)
        raise ValueError("async_fail")

    # Test successful async call
    result = await breaker.call(async_success)
    assert result == "async_success"

    # Test failed async calls
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(async_failure)

    # Circuit should be open
    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_half_open_state_handling():
    """Test half-open state transitions."""
    breaker = CircuitBreaker(
        failure_threshold=2, recovery_timeout=0.1, success_threshold=2
    )

    # Open the circuit
    for _ in range(2):
        with pytest.raises(Exception):
            await breaker.call(lambda: exec("raise Exception()"))

    assert breaker.state == CircuitState.OPEN

    # Wait for recovery
    await asyncio.sleep(0.15)

    # First call should move to half-open
    result = await breaker.call(lambda: "test1")
    assert result == "test1"
    assert breaker.state == CircuitState.HALF_OPEN

    # Another success should close
    result = await breaker.call(lambda: "test2")
    assert result == "test2"
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_half_open_failure_reopens():
    """Test that failure in half-open state reopens circuit."""
    breaker = CircuitBreaker(
        failure_threshold=2, recovery_timeout=0.1, success_threshold=2
    )

    # Open the circuit
    for _ in range(2):
        with pytest.raises(Exception):
            await breaker.call(lambda: exec("raise Exception()"))

    # Wait for recovery
    await asyncio.sleep(0.15)

    # Failure in half-open should reopen
    with pytest.raises(Exception):
        await breaker.call(lambda: exec("raise Exception()"))

    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_metrics():
    """Test circuit breaker metrics collection."""
    breaker = CircuitBreaker(failure_threshold=3)

    # Initial metrics
    metrics = breaker.get_metrics()
    assert metrics["total_calls"] == 0
    assert metrics["successful_calls"] == 0
    assert metrics["failed_calls"] == 0
    assert metrics["circuit_open_count"] == 0

    # Make some calls
    await breaker.call(lambda: "success")
    await breaker.call(lambda: "success")

    with pytest.raises(Exception):
        await breaker.call(lambda: exec("raise Exception()"))

    metrics = breaker.get_metrics()
    assert metrics["total_calls"] == 3
    assert metrics["successful_calls"] == 2
    assert metrics["failed_calls"] == 1
    assert metrics["success_rate"] == 2 / 3


@pytest.mark.asyncio
async def test_circuit_breaker_with_different_exceptions():
    """Test circuit breaker handles different exception types."""
    breaker = CircuitBreaker(failure_threshold=3, excluded_exceptions=(ValueError,))

    # ValueError should not count as failure
    for _ in range(5):
        with pytest.raises(ValueError):
            await breaker.call(lambda: exec("raise ValueError()"))

    assert breaker.state == CircuitState.CLOSED

    # Other exceptions should count
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(lambda: exec("raise RuntimeError()"))

    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_fallback():
    """Test circuit breaker with fallback function."""
    breaker = CircuitBreaker(failure_threshold=2)

    async def fallback():
        return "fallback_value"

    # Normal operation
    result = await breaker.call(lambda: "normal", fallback=fallback)
    assert result == "normal"

    # Open circuit
    for _ in range(2):
        with pytest.raises(Exception):
            await breaker.call(lambda: exec("raise Exception()"))

    # Should use fallback when open
    result = await breaker.call(lambda: "normal", fallback=fallback)
    assert result == "fallback_value"


@pytest.mark.asyncio
async def test_circuit_breaker_timeout():
    """Test circuit breaker with call timeout."""
    breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)

    async def slow_function():
        await asyncio.sleep(0.5)
        return "should_timeout"

    # Timeout should be treated as failure
    with pytest.raises(asyncio.TimeoutError):
        await breaker.call(slow_function)

    with pytest.raises(asyncio.TimeoutError):
        await breaker.call(slow_function)

    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_name_tracking():
    """Test circuit breaker tracks names for monitoring."""
    breaker = CircuitBreaker(name="test_breaker", failure_threshold=2)

    assert breaker.name == "test_breaker"

    # Test with multiple named breakers
    breaker1 = CircuitBreaker(name="api_breaker")
    breaker2 = CircuitBreaker(name="db_breaker")

    assert breaker1.name == "api_breaker"
    assert breaker2.name == "db_breaker"
