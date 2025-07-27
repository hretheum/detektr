"""Tests for health monitoring system."""

import asyncio

import pytest
from aioresponses import aioresponses

from src.health.monitor import HealthMonitor


@pytest.mark.asyncio
async def test_health_monitoring():
    """Test health check system."""
    monitor = HealthMonitor(check_interval=0.1)  # 100ms for tests

    # Register processor
    await monitor.add_processor("proc1", "http://proc1:8080/health")

    # Mock healthy response
    with aioresponses() as m:
        m.get("http://proc1:8080/health", payload={"status": "healthy"})

        # Start monitoring
        monitoring_task = asyncio.create_task(monitor.start())

        # Give it time to check
        await asyncio.sleep(0.2)

        # Check health status
        status = await monitor.get_status("proc1")
        assert status == "healthy"

        # Stop monitoring
        await monitor.stop()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_failure_detection():
    """Test failure detection."""
    monitor = HealthMonitor(check_interval=0.1)

    await monitor.add_processor("proc1", "http://proc1:8080/health")

    # Test failure detection
    with aioresponses() as m:
        # First check fails
        m.get("http://proc1:8080/health", status=500)

        monitoring_task = asyncio.create_task(monitor.start())
        await asyncio.sleep(0.2)

        status = await monitor.get_status("proc1")
        assert status == "unhealthy"

        await monitor.stop()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_circuit_breaker():
    """Test circuit breaker functionality."""
    monitor = HealthMonitor(
        check_interval=0.1, failure_threshold=3, recovery_timeout=0.5
    )

    await monitor.add_processor("proc1", "http://proc1:8080/health")

    with aioresponses() as m:
        # Multiple failures
        for _ in range(5):
            m.get("http://proc1:8080/health", status=500)

        monitoring_task = asyncio.create_task(monitor.start())
        await asyncio.sleep(0.4)  # Time for multiple checks

        # Circuit should be open
        assert await monitor.is_circuit_open("proc1") is True

        # Now return healthy responses
        for _ in range(10):
            m.get("http://proc1:8080/health", payload={"status": "healthy"})

        # Wait for recovery timeout
        await asyncio.sleep(0.6)

        # Circuit should be closed again
        assert await monitor.is_circuit_open("proc1") is False

        await monitor.stop()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_multiple_processors():
    """Test monitoring multiple processors."""
    monitor = HealthMonitor(check_interval=0.1)

    # Add multiple processors
    processors = {
        "proc1": "http://proc1:8080/health",
        "proc2": "http://proc2:8080/health",
        "proc3": "http://proc3:8080/health",
    }

    for proc_id, url in processors.items():
        await monitor.add_processor(proc_id, url)

    with aioresponses() as m:
        # Different statuses
        m.get("http://proc1:8080/health", payload={"status": "healthy"})
        m.get("http://proc2:8080/health", status=500)
        m.get("http://proc3:8080/health", payload={"status": "degraded"})

        monitoring_task = asyncio.create_task(monitor.start())
        await asyncio.sleep(0.2)

        # Check all statuses
        assert await monitor.get_status("proc1") == "healthy"
        assert await monitor.get_status("proc2") == "unhealthy"
        assert await monitor.get_status("proc3") == "degraded"

        await monitor.stop()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_processor_removal():
    """Test removing processor from monitoring."""
    monitor = HealthMonitor(check_interval=0.1)

    await monitor.add_processor("proc1", "http://proc1:8080/health")
    await monitor.add_processor("proc2", "http://proc2:8080/health")

    # Remove one processor
    await monitor.remove_processor("proc1")

    # Should only monitor proc2
    with aioresponses() as m:
        m.get("http://proc2:8080/health", payload={"status": "healthy"})

        monitoring_task = asyncio.create_task(monitor.start())
        await asyncio.sleep(0.2)

        # proc1 should not have status
        assert await monitor.get_status("proc1") is None
        assert await monitor.get_status("proc2") == "healthy"

        await monitor.stop()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_health_metrics():
    """Test health metrics collection."""
    monitor = HealthMonitor(check_interval=0.1)

    await monitor.add_processor("proc1", "http://proc1:8080/health")

    with aioresponses() as m:
        # Return metrics in health response
        m.get(
            "http://proc1:8080/health",
            payload={
                "status": "healthy",
                "capacity_used": 0.75,
                "frames_processed": 1000,
                "avg_processing_time_ms": 42.5,
                "errors_last_minute": 2,
            },
        )

        monitoring_task = asyncio.create_task(monitor.start())
        await asyncio.sleep(0.2)

        # Get detailed health
        health = await monitor.get_health_details("proc1")
        assert health is not None
        assert health.status == "healthy"
        assert health.capacity_used == 0.75
        assert health.frames_processed == 1000
        assert health.avg_processing_time_ms == 42.5
        assert health.errors_last_minute == 2

        await monitor.stop()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test timeout handling during health checks."""
    monitor = HealthMonitor(check_interval=0.1, timeout=0.05)  # 50ms timeout

    await monitor.add_processor("proc1", "http://proc1:8080/health")

    with aioresponses() as m:
        # Simulate timeout by not responding
        async def timeout_response(url, **kwargs):
            await asyncio.sleep(0.1)  # Longer than timeout
            return {"status": 200, "payload": {"status": "healthy"}}

        m.get("http://proc1:8080/health", callback=timeout_response)

        monitoring_task = asyncio.create_task(monitor.start())
        await asyncio.sleep(0.2)

        # Should be marked as unhealthy due to timeout
        status = await monitor.get_status("proc1")
        assert status == "unhealthy"

        await monitor.stop()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_callbacks():
    """Test status change callbacks."""
    status_changes = []

    async def on_status_change(processor_id: str, old_status: str, new_status: str):
        status_changes.append((processor_id, old_status, new_status))

    monitor = HealthMonitor(check_interval=0.1, on_status_change=on_status_change)

    await monitor.add_processor("proc1", "http://proc1:8080/health")

    with aioresponses() as m:
        # First check - healthy
        m.get("http://proc1:8080/health", payload={"status": "healthy"})
        # Second check - unhealthy
        m.get("http://proc1:8080/health", status=500)
        # Third check - healthy again
        m.get("http://proc1:8080/health", payload={"status": "healthy"})

        monitoring_task = asyncio.create_task(monitor.start())
        await asyncio.sleep(0.4)  # Time for multiple checks

        await monitor.stop()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

    # Should have status changes recorded
    assert len(status_changes) >= 2
    # First change: None -> healthy
    assert status_changes[0] == ("proc1", None, "healthy")
    # Second change: healthy -> unhealthy
    assert any(change == ("proc1", "healthy", "unhealthy") for change in status_changes)
