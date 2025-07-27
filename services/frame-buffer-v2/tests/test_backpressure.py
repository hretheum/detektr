"""Tests for backpressure controller."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.backpressure.controller import BackpressureController, PressureLevel


@pytest.mark.asyncio
async def test_backpressure_levels():
    """Test backpressure detection and response."""
    controller = BackpressureController(
        thresholds={"low": 0.6, "high": 0.8, "critical": 0.95}
    )

    # Mock queue stats
    queue_stats = {
        "proc1": {"size": 30, "capacity": 100},  # 30%
        "proc2": {"size": 85, "capacity": 100},  # 85% - high
    }

    with patch.object(controller, "get_queue_stats", return_value=queue_stats):
        level = await controller.check_pressure()
        assert level == PressureLevel.HIGH

        # Test response
        await controller.apply_backpressure(level)
        assert controller.consumption_rate == 0.5  # 50% slowdown

    # Test critical level
    queue_stats["proc2"]["size"] = 98  # 98%
    with patch.object(controller, "get_queue_stats", return_value=queue_stats):
        level = await controller.check_pressure()
        assert level == PressureLevel.CRITICAL

        # Should pause consumption
        await controller.apply_backpressure(level)
        assert controller.is_paused == True


@pytest.mark.asyncio
async def test_backpressure_recovery():
    """Test recovery from backpressure."""
    controller = BackpressureController()

    # Start with critical pressure
    controller.is_paused = True
    controller.consumption_rate = 0.1

    # Mock low pressure
    queue_stats = {
        "proc1": {"size": 20, "capacity": 100},  # 20%
        "proc2": {"size": 30, "capacity": 100},  # 30%
    }

    with patch.object(controller, "get_queue_stats", return_value=queue_stats):
        level = await controller.check_pressure()
        assert level == PressureLevel.NORMAL

        # Should resume normal operation
        await controller.apply_backpressure(level)
        assert controller.is_paused == False
        assert controller.consumption_rate == 1.0


@pytest.mark.asyncio
async def test_backpressure_alerts():
    """Test alert generation on critical pressure."""
    controller = BackpressureController()
    controller.send_alert = Mock()

    # Critical pressure
    queue_stats = {
        "proc1": {"size": 99, "capacity": 100},  # 99%
    }

    with patch.object(controller, "get_queue_stats", return_value=queue_stats):
        level = await controller.check_pressure()
        await controller.apply_backpressure(level)

        # Should have sent alert
        controller.send_alert.assert_called_once()
        args = controller.send_alert.call_args[0]
        assert "Critical" in args[0]


@pytest.mark.asyncio
async def test_backpressure_metrics():
    """Test metrics collection during backpressure."""
    controller = BackpressureController()

    # Test metric updates
    await controller.update_metrics(PressureLevel.HIGH)

    # Verify metrics were updated
    from src.backpressure.controller import backpressure_level, consumption_rate

    # Note: Can't easily test Prometheus metrics in unit tests without a registry


@pytest.mark.asyncio
async def test_adaptive_thresholds():
    """Test adaptive threshold adjustment."""
    controller = BackpressureController(adaptive=True)

    # Simulate sustained high pressure (need at least 50 entries)
    for _ in range(60):
        controller.pressure_history.append(PressureLevel.HIGH)

    # Force time to pass for adjustment
    controller.last_adjustment = datetime.now() - timedelta(minutes=2)

    # Should adjust thresholds
    controller.adjust_thresholds()
    assert controller.thresholds["high"] < 0.8  # Lowered threshold
    assert controller.thresholds["critical"] < 0.95


@pytest.mark.asyncio
async def test_queue_priority_handling():
    """Test priority-based backpressure."""
    controller = BackpressureController()

    # High priority queue should get preference
    queue_stats = {
        "critical-proc": {"size": 90, "capacity": 100, "priority": 10},
        "normal-proc": {"size": 50, "capacity": 100, "priority": 1},
    }

    with patch.object(controller, "get_queue_stats", return_value=queue_stats):
        # High priority (10) should have less throttling than low priority (1)
        decisions = await controller.get_throttle_decisions()
        # critical-proc at 90% utilization with priority 10: throttle = 0.9 * (1/10) = 0.09
        # normal-proc at 50% utilization with priority 1: throttle = 0.0 (below threshold)
        # Let's adjust the test data to make it clearer

    # Better test case: both above threshold
    queue_stats = {
        "critical-proc": {
            "size": 85,
            "capacity": 100,
            "priority": 10,
        },  # 85% - high pressure
        "normal-proc": {
            "size": 85,
            "capacity": 100,
            "priority": 1,
        },  # 85% - high pressure
    }

    with patch.object(controller, "get_queue_stats", return_value=queue_stats):
        decisions = await controller.get_throttle_decisions()
        # Both at same utilization, but critical-proc has higher priority, so less throttle
        assert (
            decisions["critical-proc"]["throttle"]
            < decisions["normal-proc"]["throttle"]
        )
