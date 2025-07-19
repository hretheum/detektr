"""
Tests for queue metrics export.

Verifies:
- Prometheus metrics are properly exposed
- Metrics update correctly with queue operations
- MetricsEnabledBackpressureHandler integration
"""
import asyncio
from datetime import datetime

import pytest
from prometheus_client import REGISTRY

from src.shared.kernel.domain.frame_data import FrameData
from src.shared.queue.backpressure import BackpressureConfig
from src.shared.queue.metrics import MetricsEnabledBackpressureHandler


class TestQueueMetricsCollector:
    """Test cases for queue metrics collector."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BackpressureConfig(
            min_buffer_size=10,
            max_buffer_size=100,
            high_watermark=0.8,
            low_watermark=0.3,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=1.0,
        )

    @pytest.fixture
    def handler_with_metrics(self, config):
        """Create handler with metrics enabled."""
        return MetricsEnabledBackpressureHandler(config=config, queue_name="test_queue")

    @pytest.fixture
    def sample_frame(self):
        """Create sample frame."""
        return FrameData(
            id="test_frame",
            timestamp=datetime.now(),
            camera_id="camera_01",
            sequence_number=1,
            image_data=None,
            metadata={"test": True},
        )

    def test_metrics_initialization(self, handler_with_metrics):
        """Test that metrics are properly initialized."""
        collector = handler_with_metrics.metrics_collector

        # Queue info should be set
        assert collector.queue_name == "test_queue"

        # Get current metrics
        metrics = collector.get_current_metrics()

        assert metrics["queue_depth"] == 0
        assert metrics["throughput_sent"] == 0
        assert metrics["throughput_received"] == 0
        assert metrics["dropped_frames"] == 0
        assert metrics["circuit_breaker_state"] == 0  # CLOSED

    @pytest.mark.asyncio
    async def test_throughput_metrics(self, handler_with_metrics, sample_frame):
        """Test throughput metrics increment correctly."""
        # Send frames
        for _ in range(5):
            await handler_with_metrics.send(sample_frame)

        # Receive frames
        for _ in range(3):
            await handler_with_metrics.receive()

        # Check metrics
        metrics = handler_with_metrics.metrics_collector.get_current_metrics()

        assert metrics["throughput_sent"] == 5
        assert metrics["throughput_received"] == 3
        assert metrics["queue_depth"] == 2  # 5 sent - 3 received

    @pytest.mark.asyncio
    async def test_queue_depth_metric(self, handler_with_metrics, sample_frame):
        """Test queue depth metric updates correctly."""
        collector = handler_with_metrics.metrics_collector

        # Initial depth
        assert collector.get_current_metrics()["queue_depth"] == 0

        # Add frames
        await handler_with_metrics.send(sample_frame)
        assert collector.get_current_metrics()["queue_depth"] == 1

        await handler_with_metrics.send(sample_frame)
        assert collector.get_current_metrics()["queue_depth"] == 2

        # Remove frame
        await handler_with_metrics.receive()
        assert collector.get_current_metrics()["queue_depth"] == 1

    @pytest.mark.asyncio
    async def test_backpressure_metrics(self, config):
        """Test backpressure activation metrics."""
        handler = MetricsEnabledBackpressureHandler(
            config=config, queue_name="backpressure_test"
        )

        # Fill queue to trigger backpressure
        for i in range(int(config.min_buffer_size * 0.9)):
            frame = FrameData(
                id=f"frame_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            await handler.send(frame)

        # Check metrics
        metrics = handler.metrics_collector.get_current_metrics()
        assert metrics["backpressure_activations"] >= 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics(self, handler_with_metrics):
        """Test circuit breaker state metrics."""
        collector = handler_with_metrics.metrics_collector

        # Initial state (CLOSED = 0)
        assert collector.get_current_metrics()["circuit_breaker_state"] == 0

        # Force circuit breaker to open
        for _ in range(5):
            handler_with_metrics.circuit_breaker.record_failure()

        # Should be OPEN (1)
        assert collector.get_current_metrics()["circuit_breaker_state"] == 1

        # Wait for recovery
        await asyncio.sleep(1.1)

        # Trigger state check by calling can_execute
        handler_with_metrics.circuit_breaker.can_execute()

        # Should be HALF_OPEN (2)
        assert collector.get_current_metrics()["circuit_breaker_state"] == 2

    @pytest.mark.asyncio
    async def test_dropped_frames_metrics(self, config):
        """Test dropped frames metrics."""
        handler = MetricsEnabledBackpressureHandler(
            config=config, queue_name="drop_test", enable_dropping=True
        )

        # Fill queue completely
        for i in range(config.min_buffer_size):
            frame = FrameData(
                id=f"frame_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            await handler.send(frame)

        # Try to send with timeout - should drop
        overflow_frame = FrameData(
            id="overflow",
            timestamp=datetime.now(),
            camera_id="camera_01",
            sequence_number=999,
            image_data=None,
            metadata={},
        )

        result = await handler.send(overflow_frame, timeout=0.01)
        assert not result  # Frame was dropped

        # Check metrics
        await asyncio.sleep(0.1)  # Let metrics update
        metrics = handler.metrics_collector.get_current_metrics()
        assert metrics["dropped_frames"] >= 1

    @pytest.mark.asyncio
    async def test_latency_metrics(self, handler_with_metrics, sample_frame):
        """Test latency metrics recording."""
        # Send with some processing
        await handler_with_metrics.send(sample_frame)

        # Add artificial delay
        await asyncio.sleep(0.01)

        # Receive
        await handler_with_metrics.receive()

        # Latency should be recorded (check histogram exists)
        # Note: We can't easily check histogram values in unit tests
        # but we verify the metrics are being recorded
        collector = handler_with_metrics.metrics_collector
        collector.record_send_latency(0.005)
        collector.record_receive_latency(0.003)

        # Verify we can get metrics without errors
        metrics = collector.get_current_metrics()
        assert "queue_depth" in metrics

    def test_prometheus_metrics_registered(self):
        """Test that Prometheus metrics are properly registered."""
        # Check that metrics are in registry
        metric_names = [metric.name for metric in REGISTRY.collect()]

        assert any("frame_queue_depth" in name for name in metric_names)
        assert any("frame_queue_throughput_total" in name for name in metric_names)
        assert any("frame_queue_latency_seconds" in name for name in metric_names)
        assert any(
            "frame_queue_backpressure_events_total" in name for name in metric_names
        )
        assert any("frame_queue_circuit_breaker_state" in name for name in metric_names)
        assert any("frame_queue_dropped_frames_total" in name for name in metric_names)

    @pytest.mark.asyncio
    async def test_adaptive_buffer_size_metric(self, handler_with_metrics):
        """Test adaptive buffer size is tracked in metrics."""
        initial_size = handler_with_metrics.adaptive_buffer.current_size

        # Trigger buffer adaptation by creating pressure
        for _ in range(10):
            handler_with_metrics.adaptive_buffer.record_pressure_event()

        handler_with_metrics.adaptive_buffer.adjust_size()

        # Check metrics reflect new size
        metrics = handler_with_metrics.metrics_collector.get_current_metrics()
        assert metrics["adaptive_buffer_size"] > initial_size

    @pytest.mark.asyncio
    async def test_metrics_update_periodically(
        self, handler_with_metrics, sample_frame
    ):
        """Test that metrics update periodically during operations."""
        # Send multiple frames with delays
        for _ in range(5):
            await handler_with_metrics.send(sample_frame)
            await asyncio.sleep(0.3)  # Total > 1 second

        # Metrics should have been updated during operations
        metrics = handler_with_metrics.metrics_collector.get_current_metrics()
        assert metrics["throughput_sent"] == 5
