"""
Test suite for frame buffer management - TDD approach.

Tests cover:
- Circular buffer overflow/underflow handling
- Thread safety for concurrent access
- Zero-copy operations
- Performance benchmarks
"""

import asyncio
import threading
import time

import numpy as np
import pytest

# Import będzie dodany po implementacji
# from src.frame_buffer import CircularFrameBuffer, FrameBufferError


class TestFrameBufferBasics:
    """Basic frame buffer functionality tests."""

    @pytest.fixture
    def buffer(self):
        """Create a buffer with capacity for 10 frames."""
        from src.frame_buffer import CircularFrameBuffer

        return CircularFrameBuffer(capacity=10)

    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame (1920x1080 RGB)."""
        return np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

    def test_buffer_initialization(self):
        """Test buffer initializes with correct capacity."""
        from src.frame_buffer import CircularFrameBuffer

        buffer = CircularFrameBuffer(capacity=100)
        assert buffer.capacity == 100
        assert buffer.size == 0
        assert buffer.is_empty()
        assert not buffer.is_full()

    def test_buffer_put_and_get(self, buffer, sample_frame):
        """Test basic put and get operations."""
        # Put frame
        frame_id = "frame_001"
        timestamp = time.time()
        buffer.put(frame_id, sample_frame, timestamp)

        assert buffer.size == 1
        assert not buffer.is_empty()

        # Get frame
        retrieved_id, retrieved_frame, retrieved_ts = buffer.get()
        assert retrieved_id == frame_id
        assert np.array_equal(retrieved_frame, sample_frame)
        assert retrieved_ts == timestamp
        assert buffer.is_empty()

    def test_buffer_overflow_handling(self, buffer, sample_frame):
        """Test buffer behavior when full (circular overwrite)."""
        # Fill buffer beyond capacity
        frame_ids = []
        for i in range(15):  # Buffer capacity is 10
            frame_id = f"frame_{i:03d}"
            frame_ids.append(frame_id)
            buffer.put(frame_id, sample_frame, time.time())

        assert buffer.size == 10  # Should maintain max capacity
        assert buffer.is_full()

        # Oldest frames should be overwritten
        # Should get frame_005 (frames 0-4 were overwritten)
        first_id, _, _ = buffer.get()
        assert first_id == "frame_005"

    def test_buffer_underflow_handling(self, buffer):
        """Test buffer behavior when empty."""
        from src.frame_buffer import FrameBufferError

        assert buffer.is_empty()

        # Should raise or return None on empty buffer
        with pytest.raises(FrameBufferError, match="Buffer is empty"):
            buffer.get()

    def test_buffer_peek_without_remove(self, buffer, sample_frame):
        """Test peeking at frames without removing them."""
        buffer.put("frame_001", sample_frame, time.time())

        # Peek should not remove frame
        frame_id, frame, _ = buffer.peek()
        assert frame_id == "frame_001"
        assert buffer.size == 1  # Still in buffer

        # Can still get the frame
        retrieved_id, _, _ = buffer.get()
        assert retrieved_id == "frame_001"
        assert buffer.is_empty()

    def test_buffer_clear(self, buffer, sample_frame):
        """Test clearing the buffer."""
        # Add multiple frames
        for i in range(5):
            buffer.put(f"frame_{i}", sample_frame, time.time())

        assert buffer.size == 5

        # Clear buffer
        buffer.clear()
        assert buffer.size == 0
        assert buffer.is_empty()

    def test_buffer_statistics(self, buffer, sample_frame):
        """Test buffer statistics tracking."""
        stats_before = buffer.get_statistics()
        assert stats_before["total_frames_added"] == 0
        assert stats_before["total_frames_dropped"] == 0

        # Add frames to cause overflow
        for i in range(15):
            buffer.put(f"frame_{i}", sample_frame, time.time())

        stats_after = buffer.get_statistics()
        assert stats_after["total_frames_added"] == 15
        assert stats_after["total_frames_dropped"] == 5  # 15 - 10 capacity
        assert stats_after["current_size"] == 10


class TestFrameBufferThreadSafety:
    """Thread safety tests for concurrent access."""

    @pytest.fixture
    def buffer(self):
        """Create a buffer with capacity for 100 frames."""
        from src.frame_buffer import CircularFrameBuffer

        return CircularFrameBuffer(capacity=100)

    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame (480x640 RGB)."""
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    def test_concurrent_put_operations(self, buffer, sample_frame):
        """Test multiple threads putting frames concurrently."""
        num_threads = 10
        frames_per_thread = 20

        def producer(thread_id):
            for i in range(frames_per_thread):
                frame_id = f"thread_{thread_id}_frame_{i}"
                buffer.put(frame_id, sample_frame.copy(), time.time())
                time.sleep(0.001)  # Small delay

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=producer, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have exactly 100 frames (buffer capacity)
        assert buffer.size == 100
        assert buffer.is_full()

    def test_concurrent_get_operations(self, buffer, sample_frame):
        """Test multiple threads getting frames concurrently."""
        # Fill buffer first
        for i in range(100):
            buffer.put(f"frame_{i}", sample_frame, time.time())

        retrieved_frames = []
        lock = threading.Lock()

        def consumer():
            while not buffer.is_empty():
                try:
                    frame_id, _, _ = buffer.get()
                    with lock:
                        retrieved_frames.append(frame_id)
                except Exception:
                    break

        # Multiple consumers
        threads = []
        for _ in range(5):
            t = threading.Thread(target=consumer)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All frames should be retrieved exactly once
        assert len(retrieved_frames) == 100
        assert len(set(retrieved_frames)) == 100  # All unique
        assert buffer.is_empty()

    def test_concurrent_put_get_operations(self, buffer, sample_frame):
        """Test simultaneous put and get operations."""
        stop_event = threading.Event()
        frames_produced = []
        frames_consumed = []
        lock = threading.Lock()

        def producer():
            i = 0
            while not stop_event.is_set():
                frame_id = f"frame_{i}"
                buffer.put(frame_id, sample_frame, time.time())
                with lock:
                    frames_produced.append(frame_id)
                i += 1
                time.sleep(0.001)

        def consumer():
            while not stop_event.is_set() or not buffer.is_empty():
                try:
                    frame_id, _, _ = buffer.get()
                    with lock:
                        frames_consumed.append(frame_id)
                except Exception:
                    time.sleep(0.001)

        # Start producers and consumers
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)

        producer_thread.start()
        consumer_thread.start()

        # Run for a short time
        time.sleep(0.5)
        stop_event.set()

        producer_thread.join()
        consumer_thread.join()

        # Verify data integrity
        assert len(frames_produced) > 0
        assert len(frames_consumed) > 0
        # All consumed frames should have been produced
        for frame_id in frames_consumed:
            assert frame_id in frames_produced


class TestFrameBufferPerformance:
    """Performance and zero-copy operation tests."""

    @pytest.fixture
    def buffer(self):
        """Create a buffer with capacity for 1000 frames."""
        from src.frame_buffer import CircularFrameBuffer

        return CircularFrameBuffer(capacity=1000)

    @pytest.fixture
    def sample_frame(self):
        """Create a 4K sample frame for performance testing."""
        # 4K frame for performance testing
        return np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)

    def test_zero_copy_operations(self, buffer, sample_frame):
        """Test that frames are not copied unnecessarily."""
        frame_id = "test_frame"

        # Put frame and verify it's the same object (zero-copy)
        buffer.put(frame_id, sample_frame, time.time())
        _, retrieved_frame, _ = buffer.get()

        # Should be the same memory location (zero-copy)
        assert retrieved_frame.data == sample_frame.data

        # Modifying retrieved frame should modify original
        # (This tests zero-copy but might not be desired behavior)
        retrieved_frame[0, 0, 0] = 255
        assert sample_frame[0, 0, 0] == 255

    @pytest.mark.benchmark(group="frame_buffer")
    def test_throughput_performance(self, buffer, benchmark):
        """Benchmark frame buffer throughput."""
        from src.frame_buffer import CircularFrameBuffer

        # Smaller frame for throughput test
        frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        buffer = CircularFrameBuffer(capacity=1000)

        def run_operations():
            # Put and get 1000 frames
            for i in range(1000):
                buffer.put(f"frame_{i}", frame, time.time())
                if i >= 100:  # Keep buffer partially full
                    buffer.get()

        # Benchmark should show >1000 FPS throughput
        benchmark(run_operations)

        # Get statistics from benchmark
        stats = benchmark.stats
        mean_time = stats["mean"]  # Mean time per run in seconds

        # Calculate operations per second
        operations_per_run = 1900  # 1000 put + 900 get operations
        operations_per_second = operations_per_run / mean_time

        # Print performance info
        print(f"\nThroughput: {operations_per_second:.1f} ops/s")
        print(f"Mean time per run: {mean_time*1000:.2f} ms")

        assert (
            operations_per_second > 1000
        ), f"Throughput {operations_per_second:.1f} ops/s is below 1000 FPS requirement"

    def test_memory_efficiency(self, buffer):
        """Test memory usage doesn't grow with repeated operations."""
        import gc

        import psutil

        process = psutil.Process()
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

        # Baseline memory
        gc.collect()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Perform many operations
        for i in range(10000):
            buffer.put(f"frame_{i}", frame, time.time())
            if i > 100:
                buffer.get()

        gc.collect()
        memory_after = process.memory_info().rss / 1024 / 1024  # MB

        # Memory growth should be minimal (<50MB)
        memory_growth = memory_after - memory_before
        assert memory_growth < 50, f"Memory grew by {memory_growth:.1f}MB"


class TestFrameBufferIntegration:
    """Integration tests with async operations."""

    @pytest.fixture
    def buffer(self):
        """Create a buffer with capacity for 50 frames."""
        from src.frame_buffer import CircularFrameBuffer

        return CircularFrameBuffer(capacity=50)

    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame (480x640 RGB)."""
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    @pytest.mark.asyncio
    async def test_async_producer_consumer(self, buffer, sample_frame):
        """Test async producer/consumer pattern."""

        async def producer(buffer, num_frames):
            for i in range(num_frames):
                buffer.put(f"frame_{i}", sample_frame, time.time())
                await asyncio.sleep(0.01)  # Simulate frame capture delay

        async def consumer(buffer, results):
            while True:
                try:
                    frame_id, _, _ = buffer.get()
                    results.append(frame_id)
                    await asyncio.sleep(0.005)  # Simulate processing
                except Exception:
                    await asyncio.sleep(0.01)
                    if buffer.is_empty():
                        break

        results = []

        # Run producer and consumer concurrently
        await asyncio.gather(producer(buffer, 100), consumer(buffer, results))

        # Should have processed all frames
        assert len(results) > 0
        assert all(f"frame_{i}" in results for i in range(min(50, len(results))))

    def test_buffer_with_different_frame_sizes(self, buffer):
        """Test buffer handles different frame sizes correctly."""
        # Different resolutions
        frames = [
            ("small", np.zeros((240, 320, 3), dtype=np.uint8)),
            ("medium", np.zeros((720, 1280, 3), dtype=np.uint8)),
            ("large", np.zeros((1080, 1920, 3), dtype=np.uint8)),
            ("4k", np.zeros((2160, 3840, 3), dtype=np.uint8)),
        ]

        # Add different sized frames
        for frame_id, frame in frames:
            buffer.put(frame_id, frame, time.time())

        # Retrieve and verify
        for expected_id, expected_frame in frames:
            frame_id, frame, _ = buffer.get()
            assert frame_id == expected_id
            assert frame.shape == expected_frame.shape


@pytest.mark.parametrize("capacity", [10, 100, 1000])
def test_buffer_capacity_variations(capacity):
    """Test buffer with different capacities."""
    from src.frame_buffer import CircularFrameBuffer

    buffer = CircularFrameBuffer(capacity=capacity)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Fill beyond capacity
    for i in range(capacity * 2):
        buffer.put(f"frame_{i}", frame, time.time())

    assert buffer.size == capacity
    assert buffer.is_full()

    # First frame should be at index capacity
    first_id, _, _ = buffer.get()
    assert first_id == f"frame_{capacity}"
