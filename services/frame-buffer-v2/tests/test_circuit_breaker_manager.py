"""Tests for circuit breaker manager."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.circuit_breaker import CircuitOpenError
from src.circuit_breaker_manager import CircuitBreakerManager


@pytest.mark.asyncio
async def test_circuit_breaker_manager_creation():
    """Test circuit breaker manager creates breakers on demand."""
    manager = CircuitBreakerManager(
        failure_threshold=3, recovery_timeout=10.0, success_threshold=2
    )

    # No breakers initially
    assert len(manager.breakers) == 0

    # Get breaker creates it
    breaker = manager.get_breaker("proc1")
    assert breaker is not None
    assert breaker.name == "processor_proc1"
    assert breaker.failure_threshold == 3

    # Getting again returns same instance
    breaker2 = manager.get_breaker("proc1")
    assert breaker2 is breaker

    # Different processor gets different breaker
    breaker3 = manager.get_breaker("proc2")
    assert breaker3 is not breaker
    assert len(manager.breakers) == 2


@pytest.mark.asyncio
async def test_call_processor_through_breaker():
    """Test calling processor functions through circuit breaker."""
    manager = CircuitBreakerManager(failure_threshold=2)

    # Successful call
    async def success_func():
        return "success"

    result = await manager.call_processor("proc1", success_func)
    assert result == "success"

    # Failed calls
    async def fail_func():
        raise RuntimeError("fail")

    # First failure
    with pytest.raises(RuntimeError):
        await manager.call_processor("proc1", fail_func)

    # Second failure opens circuit
    with pytest.raises(RuntimeError):
        await manager.call_processor("proc1", fail_func)

    # Circuit should be open
    with pytest.raises(CircuitOpenError):
        await manager.call_processor("proc1", success_func)


@pytest.mark.asyncio
async def test_processor_availability_check():
    """Test checking processor availability."""
    manager = CircuitBreakerManager(failure_threshold=2)

    # Initially all processors are available
    assert manager.is_processor_available("proc1")
    assert manager.is_processor_available("proc2")

    # Open circuit for proc1
    async def fail_func():
        raise RuntimeError("fail")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await manager.call_processor("proc1", fail_func)

    # proc1 should be unavailable, proc2 still available
    assert not manager.is_processor_available("proc1")
    assert manager.is_processor_available("proc2")


@pytest.mark.asyncio
async def test_get_available_processors():
    """Test filtering available processors."""
    manager = CircuitBreakerManager(failure_threshold=1)

    processor_ids = ["proc1", "proc2", "proc3"]

    # All initially available
    available = manager.get_available_processors(processor_ids)
    assert available == processor_ids

    # Fail proc2
    async def fail_func():
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        await manager.call_processor("proc2", fail_func)

    # Only proc1 and proc3 available
    available = manager.get_available_processors(processor_ids)
    assert available == ["proc1", "proc3"]


@pytest.mark.asyncio
async def test_circuit_breaker_metrics():
    """Test getting metrics from all breakers."""
    manager = CircuitBreakerManager()

    # Make some calls
    await manager.call_processor("proc1", lambda: "success")
    await manager.call_processor("proc2", lambda: "success")

    with pytest.raises(Exception):
        await manager.call_processor("proc1", lambda: exec("raise Exception()"))

    # Get metrics
    metrics = manager.get_all_metrics()

    assert "proc1" in metrics
    assert "proc2" in metrics
    assert metrics["proc1"]["successful_calls"] == 1
    assert metrics["proc1"]["failed_calls"] == 1
    assert metrics["proc2"]["successful_calls"] == 1
    assert metrics["proc2"]["failed_calls"] == 0


@pytest.mark.asyncio
async def test_reset_functionality():
    """Test resetting circuit breakers."""
    manager = CircuitBreakerManager(failure_threshold=1)

    # Open circuit
    async def fail_func():
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        await manager.call_processor("proc1", fail_func)

    assert not manager.is_processor_available("proc1")

    # Reset specific processor
    manager.reset_processor("proc1")
    assert manager.is_processor_available("proc1")

    # Open multiple circuits
    for proc in ["proc1", "proc2"]:
        with pytest.raises(RuntimeError):
            await manager.call_processor(proc, fail_func)

    assert not manager.is_processor_available("proc1")
    assert not manager.is_processor_available("proc2")

    # Reset all
    manager.reset_all()
    assert manager.is_processor_available("proc1")
    assert manager.is_processor_available("proc2")


@pytest.mark.asyncio
async def test_fallback_handling():
    """Test fallback function handling."""
    manager = CircuitBreakerManager(failure_threshold=1)

    # Open circuit
    async def fail_func():
        raise RuntimeError("fail")

    async def fallback_func():
        return "fallback_result"

    with pytest.raises(RuntimeError):
        await manager.call_processor("proc1", fail_func)

    # Use fallback when circuit is open
    result = await manager.call_processor(
        "proc1", lambda: "normal", fallback=fallback_func
    )
    assert result == "fallback_result"
