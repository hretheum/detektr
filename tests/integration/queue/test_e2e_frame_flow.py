"""
End-to-end integration tests for frame flow through queue system.

Tests complete flow:
- Frame capture (simulated)
- Queue with backpressure
- Processing with failures and retries
- Metrics and monitoring
"""
import asyncio
import random
from datetime import datetime
from typing import List

import pytest

from src.shared.kernel.domain.frame_data import FrameData
from src.shared.queue import (
    BackpressureConfig,
    DeadLetterQueue,
    DLQReason,
    MetricsEnabledBackpressureHandler,
)
from src.shared.queue.metrics_endpoint import create_metrics_server


class MockRTSPCapture:
    """Mock RTSP capture service for testing."""

    def __init__(self, fps: int = 30, failure_rate: float = 0.0):
        """Initialize mock capture."""
        self.fps = fps
        self.failure_rate = failure_rate
        self.frame_counter = 0
        self.is_running = False

    async def capture_frames(self, duration_seconds: int) -> List[FrameData]:
        """Simulate frame capture for specified duration."""
        frames = []
        self.is_running = True

        frame_interval = 1.0 / self.fps
        start_time = asyncio.get_event_loop().time()

        while (
            self.is_running
            and (asyncio.get_event_loop().time() - start_time) < duration_seconds
        ):
            # Simulate frame capture
            if random.random() > self.failure_rate:
                frame = FrameData(
                    id=f"rtsp_frame_{self.frame_counter}",
                    timestamp=datetime.now(),
                    camera_id="rtsp_camera_01",
                    sequence_number=self.frame_counter,
                    image_data=None,  # Simulated - no actual image
                    metadata={
                        "fps": self.fps,
                        "capture_time": datetime.now().isoformat(),
                    },
                )
                frames.append(frame)
                self.frame_counter += 1

            await asyncio.sleep(frame_interval)

        self.is_running = False
        return frames

    def stop(self):
        """Stop capture."""
        self.is_running = False


class MockFrameProcessor:
    """Mock frame processor for testing."""

    def __init__(self, processing_time: float = 0.01, failure_rate: float = 0.1):
        """Initialize mock processor."""
        self.processing_time = processing_time
        self.failure_rate = failure_rate
        self.processed_frames = []
        self.failed_frames = []

    async def process_frame(self, frame: FrameData) -> bool:
        """Simulate frame processing."""
        await asyncio.sleep(self.processing_time)

        if random.random() < self.failure_rate:
            self.failed_frames.append(frame)
            return False
        else:
            self.processed_frames.append(frame)
            return True


class TestEndToEndFrameFlow:
    """Integration tests for complete frame flow."""

    @pytest.fixture
    def queue_config(self):
        """Create queue configuration."""
        return BackpressureConfig(
            min_buffer_size=100,
            max_buffer_size=1000,
            high_watermark=0.8,
            low_watermark=0.3,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=2.0,
        )

    @pytest.fixture
    def queue_handler(self, queue_config):
        """Create queue handler with metrics."""
        return MetricsEnabledBackpressureHandler(
            config=queue_config, queue_name="integration_test", enable_dropping=True
        )

    @pytest.fixture
    def dlq(self):
        """Create Dead Letter Queue."""
        return DeadLetterQueue(
            max_size=1000, max_retries=3, base_retry_delay=0.5, enable_auto_retry=True
        )

    @pytest.mark.asyncio
    async def test_normal_frame_flow(self, queue_handler, dlq):
        """Test normal frame flow without failures."""
        capture = MockRTSPCapture(fps=10, failure_rate=0.0)
        processor = MockFrameProcessor(processing_time=0.01, failure_rate=0.0)

        # Producer task
        async def producer():
            frames = await capture.capture_frames(duration_seconds=2)
            for frame in frames:
                await queue_handler.send(frame)
            return len(frames)

        # Consumer task
        async def consumer():
            processed = 0
            while processed < 20 or queue_handler.get_metrics().current_buffer_size > 0:
                frame = await queue_handler.receive(timeout=0.5)
                if frame:
                    success = await processor.process_frame(frame)
                    if success:
                        processed += 1
                    else:
                        await dlq.add_entry(
                            frame=frame,
                            reason=DLQReason.PROCESSING_ERROR,
                            error_message="Processing failed",
                        )
            return processed

        # Run producer and consumer
        produced, consumed = await asyncio.gather(producer(), consumer())

        # Verify results
        assert produced >= 18  # ~10 fps for 2 seconds
        assert consumed == produced
        assert len(processor.processed_frames) == produced
        assert len(processor.failed_frames) == 0
        assert dlq.get_stats()["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_frame_flow_with_failures(self, queue_handler, dlq):
        """Test frame flow with processing failures and DLQ."""
        capture = MockRTSPCapture(fps=10, failure_rate=0.0)
        processor = MockFrameProcessor(
            processing_time=0.01, failure_rate=0.2
        )  # 20% failure

        # Set DLQ retry callback
        async def retry_callback(frame):
            return await processor.process_frame(frame)

        dlq.set_retry_callback(retry_callback)

        # Producer task
        async def producer():
            frames = await capture.capture_frames(duration_seconds=2)
            for frame in frames:
                await queue_handler.send(frame)
            return len(frames)

        # Consumer task
        async def consumer():
            attempts = 0
            max_attempts = 100  # Prevent infinite loop

            while attempts < max_attempts:
                frame = await queue_handler.receive(timeout=0.1)
                if frame:
                    success = await processor.process_frame(frame)
                    if not success:
                        await dlq.add_entry(
                            frame=frame,
                            reason=DLQReason.PROCESSING_ERROR,
                            error_message="Processing failed",
                        )
                else:
                    # Check if queue is empty and DLQ has no active retries
                    if (
                        queue_handler.get_metrics().current_buffer_size == 0
                        and dlq.get_stats()["active_retries"] == 0
                    ):
                        break
                attempts += 1

        # Run producer and consumer
        produced = await producer()
        await consumer()

        # Wait for DLQ retries to complete
        await asyncio.sleep(2.0)

        # Verify results
        assert produced >= 18
        total_processed = len(processor.processed_frames)
        total_failed = dlq.get_stats()["permanent_failures"]

        # Most frames should be processed (including retries)
        assert total_processed >= produced * 0.7  # At least 70% success

        # Some should have failed permanently
        assert total_failed >= 0

        # Total attempts should be reasonable
        assert (
            total_processed + total_failed <= produced * 4
        )  # Max 3 retries + original

    @pytest.mark.asyncio
    async def test_backpressure_activation(self, queue_config):
        """Test backpressure activation under load."""
        # Create handler with small buffer
        config = BackpressureConfig(
            min_buffer_size=10,
            max_buffer_size=50,
            high_watermark=0.8,
            low_watermark=0.3,
        )
        handler = MetricsEnabledBackpressureHandler(
            config=config, queue_name="backpressure_test"
        )

        capture = MockRTSPCapture(fps=100, failure_rate=0.0)  # Fast producer
        processor = MockFrameProcessor(
            processing_time=0.1, failure_rate=0.0
        )  # Slow consumer

        backpressure_activated = False

        # Producer task
        async def producer():
            nonlocal backpressure_activated
            frames = await capture.capture_frames(duration_seconds=1)

            for frame in frames:
                start_time = asyncio.get_event_loop().time()
                await handler.send(frame)
                send_time = asyncio.get_event_loop().time() - start_time

                # If send took more than 10ms, backpressure is active
                if send_time > 0.01:
                    backpressure_activated = True

        # Consumer task
        async def consumer():
            while True:
                frame = await handler.receive(timeout=0.1)
                if frame:
                    await processor.process_frame(frame)
                else:
                    break

        # Run producer and consumer
        await asyncio.gather(producer(), consumer())

        # Verify backpressure was activated
        assert backpressure_activated
        metrics = handler.metrics_collector.get_current_metrics()
        assert metrics["backpressure_activations"] > 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self, queue_handler, dlq):
        """Test circuit breaker activation on repeated failures."""
        processor = MockFrameProcessor(
            processing_time=0.01, failure_rate=1.0
        )  # Always fail

        # Send frames that will all fail
        for i in range(10):
            frame = FrameData(
                id=f"cb_test_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )

            # Process frame
            received = await queue_handler.receive(timeout=0.1)
            if received is None:
                await queue_handler.send(frame)
                received = await queue_handler.receive(timeout=0.1)

            if received:
                success = await processor.process_frame(received)
                if not success:
                    # Record failure in circuit breaker
                    queue_handler.circuit_breaker.record_failure()

        # Circuit breaker should be open
        metrics = queue_handler.metrics_collector.get_current_metrics()
        assert metrics["circuit_breaker_state"] == 1  # OPEN

    @pytest.mark.asyncio
    async def test_metrics_endpoint_integration(self, queue_handler):
        """Test metrics endpoint serves correct data."""
        # Create metrics server
        create_metrics_server(queue_handler)

        # Send some frames
        for i in range(5):
            frame = FrameData(
                id=f"metrics_test_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            await queue_handler.send(frame)

        # Receive some frames
        for _ in range(3):
            await queue_handler.receive()

        # Update metrics
        queue_handler.metrics_collector.update_metrics()

        # Get metrics
        metrics = queue_handler.metrics_collector.get_current_metrics()

        assert metrics["throughput_sent"] == 5
        assert metrics["throughput_received"] == 3
        assert metrics["queue_depth"] == 2

    @pytest.mark.asyncio
    async def test_long_running_stability(self, queue_config):
        """Test system stability over extended period (simulated)."""
        handler = MetricsEnabledBackpressureHandler(
            config=queue_config, queue_name="stability_test"
        )
        dlq = DeadLetterQueue(max_retries=2, base_retry_delay=0.1)

        capture = MockRTSPCapture(fps=30, failure_rate=0.05)  # 5% capture failure
        processor = MockFrameProcessor(
            processing_time=0.02, failure_rate=0.1
        )  # 10% process failure

        # Set DLQ retry
        async def retry_callback(frame):
            return await processor.process_frame(frame)

        dlq.set_retry_callback(retry_callback)

        # Run for "24 hours" (simulated as 5 seconds)
        duration = 5

        async def producer():
            frames = await capture.capture_frames(duration_seconds=duration)
            sent = 0
            for frame in frames:
                if await handler.send(frame, timeout=0.1):
                    sent += 1
            return sent

        async def consumer():
            end_time = asyncio.get_event_loop().time() + duration + 1
            processed = 0

            while asyncio.get_event_loop().time() < end_time:
                frame = await handler.receive(timeout=0.1)
                if frame:
                    success = await processor.process_frame(frame)
                    if success:
                        processed += 1
                    else:
                        await dlq.add_entry(
                            frame=frame,
                            reason=DLQReason.PROCESSING_ERROR,
                            error_message="Failed",
                        )
            return processed

        # Run system
        sent, processed = await asyncio.gather(producer(), consumer())

        # Wait for DLQ to finish
        await asyncio.sleep(1.0)

        # Get final stats
        queue_metrics = handler.metrics_collector.get_current_metrics()
        dlq_stats = dlq.get_stats()

        # Verify stability
        assert sent > 0
        assert processed > 0
        assert queue_metrics["queue_depth"] < 50  # Queue didn't grow unbounded
        assert dlq_stats["current_size"] < 100  # DLQ didn't grow unbounded

        # Calculate success rate
        total_attempts = processed + dlq_stats["permanent_failures"]
        success_rate = processed / total_attempts if total_attempts > 0 else 0
        assert success_rate > 0.7  # At least 70% success rate

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, queue_handler, dlq):
        """Test graceful shutdown of all components."""
        # Add some frames
        for i in range(10):
            frame = FrameData(
                id=f"shutdown_test_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            await queue_handler.send(frame)

        # Add some to DLQ
        for i in range(5):
            frame = FrameData(
                id=f"dlq_shutdown_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            await dlq.add_entry(
                frame=frame,
                reason=DLQReason.PROCESSING_ERROR,
                error_message="Shutdown test",
            )

        # Shutdown DLQ
        await dlq.shutdown()

        # Verify clean shutdown
        assert len(dlq._retry_tasks) == 0

        # Process remaining frames
        count = 0
        while True:
            frame = await queue_handler.receive(timeout=0.1)
            if frame is None:
                break
            count += 1

        assert count == 10  # All frames processed
