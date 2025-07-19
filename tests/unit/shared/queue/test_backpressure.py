"""
TDD tests for backpressure handling in frame queue.

Test scenarios:
- No frame loss under high load
- Adaptive buffer sizing
- Circuit breaker activation
- Graceful degradation
"""
import asyncio
import time
from datetime import datetime

import pytest

from src.shared.kernel.domain.frame_data import FrameData
from src.shared.queue.backpressure import (
    AdaptiveBuffer,
    BackpressureConfig,
    BackpressureHandler,
    BackpressureState,
    CircuitBreaker,
    CircuitBreakerState,
)


class TestBackpressureHandler:
    """Test cases for backpressure handling."""

    @pytest.fixture
    def config(self):
        """Create default backpressure configuration."""
        return BackpressureConfig(
            min_buffer_size=100,
            max_buffer_size=10000,
            high_watermark=0.8,  # 80% full triggers backpressure
            low_watermark=0.3,  # 30% full releases backpressure
            circuit_breaker_threshold=5,  # 5 consecutive failures
            circuit_breaker_timeout=30,  # 30 seconds
            adaptive_increase_factor=2.0,
            adaptive_decrease_factor=0.5,
        )

    @pytest.fixture
    def handler(self, config):
        """Create backpressure handler instance."""
        return BackpressureHandler(config)

    @pytest.fixture
    def sample_frame(self):
        """Create sample frame for testing."""
        return FrameData(
            id="test_frame_001",
            timestamp=datetime.now(),
            camera_id="camera_01",
            sequence_number=1,
            image_data=None,  # No image data for unit tests
            metadata={"test": True},
        )

    @pytest.mark.asyncio
    async def test_no_frame_loss_under_pressure(self, handler, sample_frame):
        """Test that no frames are lost even under high pressure."""
        frames_sent = []
        frames_received = []

        # Producer coroutine - sends frames rapidly
        async def producer():
            for i in range(1000):
                frame = FrameData(
                    id=f"frame_{i}",
                    timestamp=datetime.now(),
                    camera_id="camera_01",
                    sequence_number=i,
                    image_data=None,
                    metadata={"index": i},
                )
                frames_sent.append(frame)

                # Apply backpressure
                await handler.send(frame)

                # Simulate varying production rate
                if i % 100 == 0:
                    await asyncio.sleep(0.001)

        # Consumer coroutine - processes frames slowly
        async def consumer():
            while len(frames_received) < 1000:
                frame = await handler.receive()
                if frame:
                    frames_received.append(frame)
                    # Simulate slow processing
                    await asyncio.sleep(0.005)

        # Run producer and consumer concurrently
        await asyncio.gather(producer(), consumer())

        # Verify no frame loss
        assert len(frames_received) == len(frames_sent)
        assert all(f.id in [r.id for r in frames_received] for f in frames_sent)

    @pytest.mark.asyncio
    async def test_backpressure_activates_at_high_watermark(self, handler, config):
        """Test that backpressure activates when buffer reaches high watermark."""
        # Fill buffer to just below high watermark
        fill_level = int(config.min_buffer_size * config.high_watermark - 1)
        for i in range(fill_level):
            frame = FrameData(
                id=f"frame_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            await handler.send(frame)

        # Should not be under backpressure yet
        assert handler.state == BackpressureState.NORMAL

        # Add one more frame to cross high watermark
        await handler.send(
            FrameData(
                id="trigger_frame",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=fill_level,
                image_data=None,
                metadata={},
            )
        )

        # Should now be under backpressure
        assert handler.state == BackpressureState.BACKPRESSURE

    @pytest.mark.asyncio
    async def test_backpressure_releases_at_low_watermark(self, handler, config):
        """Test that backpressure releases when buffer drops to low watermark."""
        # Fill buffer above high watermark
        fill_level = int(config.min_buffer_size * 0.9)
        for i in range(fill_level):
            frame = FrameData(
                id=f"frame_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            await handler.send(frame)

        # Should be under backpressure
        assert handler.state == BackpressureState.BACKPRESSURE

        # Drain buffer to low watermark
        drain_to = int(config.min_buffer_size * config.low_watermark)
        frames_to_drain = fill_level - drain_to

        for _ in range(frames_to_drain):
            await handler.receive()

        # Should no longer be under backpressure
        assert handler.state == BackpressureState.NORMAL

    @pytest.mark.asyncio
    async def test_send_blocks_during_backpressure(self, handler, config):
        """Test that send operations block when under backpressure."""
        # Fill buffer to trigger backpressure
        for i in range(int(config.min_buffer_size * 0.9)):
            await handler.send(
                FrameData(
                    id=f"frame_{i}",
                    timestamp=datetime.now(),
                    camera_id="camera_01",
                    sequence_number=i,
                    image_data=None,
                    metadata={},
                )
            )

        # Try to send while under backpressure
        start_time = time.time()
        send_task = asyncio.create_task(
            handler.send(
                FrameData(
                    id="blocked_frame",
                    timestamp=datetime.now(),
                    camera_id="camera_01",
                    sequence_number=999,
                    image_data=None,
                    metadata={},
                )
            )
        )

        # Should still be blocked after short wait
        await asyncio.sleep(0.1)
        assert not send_task.done()

        # Drain some frames to release backpressure
        for _ in range(int(config.min_buffer_size * 0.7)):
            await handler.receive()

        # Send should now complete
        await send_task
        elapsed = time.time() - start_time
        assert elapsed > 0.1  # Was blocked for at least 0.1 seconds

    def test_metrics_tracking(self, handler, sample_frame):
        """Test that metrics are properly tracked."""
        metrics = handler.get_metrics()

        assert metrics.frames_sent == 0
        assert metrics.frames_received == 0
        assert metrics.frames_dropped == 0
        assert metrics.backpressure_activations == 0

        # Send some frames
        asyncio.run(handler.send(sample_frame))
        asyncio.run(handler.send(sample_frame))

        # Receive one frame
        asyncio.run(handler.receive())

        metrics = handler.get_metrics()
        assert metrics.frames_sent == 2
        assert metrics.frames_received == 1
        assert metrics.current_buffer_size == 1


class TestAdaptiveBuffer:
    """Test cases for adaptive buffer sizing."""

    @pytest.fixture
    def adaptive_buffer(self):
        """Create adaptive buffer instance."""
        return AdaptiveBuffer(
            min_size=100, max_size=10000, increase_factor=2.0, decrease_factor=0.5
        )

    def test_buffer_increases_on_pressure(self, adaptive_buffer):
        """Test that buffer size increases when under pressure."""
        initial_size = adaptive_buffer.current_size

        # Simulate sustained high load
        for _ in range(10):
            adaptive_buffer.record_pressure_event()

        adaptive_buffer.adjust_size()

        assert adaptive_buffer.current_size > initial_size
        assert adaptive_buffer.current_size <= adaptive_buffer.max_size

    def test_buffer_decreases_when_idle(self, adaptive_buffer):
        """Test that buffer size decreases during low activity."""
        # First increase the buffer
        adaptive_buffer.current_size = 1000

        # Simulate low activity
        for _ in range(20):
            adaptive_buffer.record_idle_event()

        adaptive_buffer.adjust_size()

        assert adaptive_buffer.current_size < 1000
        assert adaptive_buffer.current_size >= adaptive_buffer.min_size

    def test_buffer_respects_min_max_limits(self, adaptive_buffer):
        """Test that buffer size stays within min/max limits."""
        # Try to decrease below minimum
        adaptive_buffer.current_size = adaptive_buffer.min_size
        for _ in range(100):
            adaptive_buffer.record_idle_event()
        adaptive_buffer.adjust_size()

        assert adaptive_buffer.current_size == adaptive_buffer.min_size

        # Try to increase above maximum
        adaptive_buffer.current_size = adaptive_buffer.max_size
        for _ in range(100):
            adaptive_buffer.record_pressure_event()
        adaptive_buffer.adjust_size()

        assert adaptive_buffer.current_size == adaptive_buffer.max_size

    def test_adaptive_sizing_hysteresis(self, adaptive_buffer):
        """Test that adaptive sizing has hysteresis to prevent oscillation."""
        # Set buffer to middle size
        adaptive_buffer.current_size = 1000
        sizes = []

        # Simulate mixed load (not purely alternating)
        patterns = [
            (8, 2),  # High pressure
            (6, 4),  # Moderate pressure
            (4, 6),  # Moderate idle
            (2, 8),  # High idle
            (5, 5),  # Balanced
            (7, 3),  # High pressure
            (3, 7),  # High idle
            (5, 5),  # Balanced
        ]

        for pressure_events, idle_events in patterns:
            for _ in range(pressure_events):
                adaptive_buffer.record_pressure_event()
            for _ in range(idle_events):
                adaptive_buffer.record_idle_event()

            adaptive_buffer.adjust_size()
            sizes.append(adaptive_buffer.current_size)

        # Check that buffer doesn't change too drastically
        # Calculate standard deviation of sizes
        avg_size = sum(sizes) / len(sizes)
        variance = sum((size - avg_size) ** 2 for size in sizes) / len(sizes)
        std_dev = variance**0.5

        # Standard deviation should be reasonable (not oscillating wildly)
        assert std_dev < avg_size * 0.4  # Less than 40% of average


class TestCircuitBreaker:
    """Test cases for circuit breaker pattern."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker instance."""
        return CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=1.0,  # 1 second for testing
            half_open_max_calls=3,
        )

    def test_circuit_opens_after_threshold_failures(self, circuit_breaker):
        """Test that circuit opens after consecutive failures."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

        # Record failures up to threshold
        for i in range(5):
            circuit_breaker.record_failure()
            if i < 4:
                assert circuit_breaker.state == CircuitBreakerState.CLOSED

        # Should now be open
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_blocks_calls_when_open(self, circuit_breaker):
        """Test that calls are blocked when circuit is open."""
        # Open the circuit
        for _ in range(5):
            circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Should not allow calls
        assert not circuit_breaker.can_execute()

    def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Test that circuit transitions to half-open after timeout."""
        # Open the circuit
        for _ in range(5):
            circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # Should now be half-open
        assert circuit_breaker.can_execute()
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    def test_circuit_closes_on_success_in_half_open(self, circuit_breaker):
        """Test that circuit closes after successful calls in half-open state."""
        # Open the circuit
        for _ in range(5):
            circuit_breaker.record_failure()

        # Wait for half-open
        time.sleep(1.1)
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

        # Record successful calls
        for _ in range(3):
            assert circuit_breaker.can_execute()
            circuit_breaker.record_success()

        # Should now be closed
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_reopens_on_failure_in_half_open(self, circuit_breaker):
        """Test that circuit reopens on failure in half-open state."""
        # Open the circuit
        for _ in range(5):
            circuit_breaker.record_failure()

        # Wait for half-open
        time.sleep(1.1)
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

        # Record a failure
        circuit_breaker.record_failure()

        # Should be open again
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_success_resets_failure_count(self, circuit_breaker):
        """Test that success resets the failure count."""
        # Record some failures
        for _ in range(3):
            circuit_breaker.record_failure()

        # Record a success
        circuit_breaker.record_success()

        # Should reset failure count
        assert circuit_breaker._consecutive_failures == 0

        # Can still record more failures without opening
        for _ in range(4):
            circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED


class TestIntegratedBackpressure:
    """Integration tests for complete backpressure system."""

    @pytest.mark.asyncio
    async def test_stress_test_with_slow_consumer(self):
        """Stress test with fast producer and slow consumer."""
        config = BackpressureConfig(
            min_buffer_size=100,
            max_buffer_size=1000,
            high_watermark=0.8,
            low_watermark=0.3,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=30,
            adaptive_increase_factor=2.0,
            adaptive_decrease_factor=0.5,
        )

        handler = BackpressureHandler(config)
        frames_produced = 0
        frames_consumed = 0

        async def fast_producer():
            nonlocal frames_produced
            for i in range(500):
                frame = FrameData(
                    id=f"stress_frame_{i}",
                    timestamp=datetime.now(),
                    camera_id="camera_01",
                    sequence_number=i,
                    image_data=None,
                    metadata={"stress_test": True},
                )
                await handler.send(frame)
                frames_produced += 1
                # Very fast production
                if i % 50 == 0:
                    await asyncio.sleep(0.001)

        async def slow_consumer():
            nonlocal frames_consumed
            while frames_consumed < 500:
                frame = await handler.receive()
                if frame:
                    frames_consumed += 1
                    # Slow consumption
                    await asyncio.sleep(0.01)

        # Run test
        await asyncio.gather(fast_producer(), slow_consumer())

        # Verify results
        assert frames_produced == 500
        assert frames_consumed == 500

        metrics = handler.get_metrics()
        assert metrics.frames_dropped == 0
        assert (
            metrics.backpressure_activations > 0
        )  # Should have triggered backpressure

        # Buffer should have adapted
        assert handler.adaptive_buffer.current_size > config.min_buffer_size

    @pytest.mark.asyncio
    async def test_graceful_degradation_under_extreme_load(self):
        """Test graceful degradation when system is overwhelmed."""
        config = BackpressureConfig(
            min_buffer_size=10,  # Very small buffer
            max_buffer_size=50,
            high_watermark=0.8,
            low_watermark=0.3,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=1,
            adaptive_increase_factor=1.5,
            adaptive_decrease_factor=0.7,
        )

        handler = BackpressureHandler(config, enable_dropping=True)

        # Overwhelm the system
        send_tasks = []
        for i in range(100):
            frame = FrameData(
                id=f"overwhelm_frame_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            task = asyncio.create_task(handler.send(frame, timeout=0.1))
            send_tasks.append(task)

        # Wait for all sends to complete or timeout
        await asyncio.gather(*send_tasks, return_exceptions=True)

        # Some frames should have been dropped gracefully
        metrics = handler.get_metrics()
        assert metrics.frames_dropped > 0
        assert metrics.frames_sent + metrics.frames_dropped == 100

        # Circuit breaker should have activated
        assert handler.circuit_breaker.state == CircuitBreakerState.OPEN
