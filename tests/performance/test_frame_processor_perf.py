"""Performance and benchmark tests for frame processor."""

import asyncio
import statistics
import time
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock

import pytest

from src.examples.frame_processor import FrameProcessor
from src.shared.kernel.domain import Frame


@pytest.mark.benchmark
class TestFrameProcessorPerformance:
    """Performance tests for frame processor."""

    @pytest.fixture
    def fast_processor(self):
        """Create processor with fast mocked dependencies."""
        # Ultra-fast mocks for performance testing
        fast_detector = AsyncMock(return_value=[{"confidence": 0.9}])
        fast_repo = AsyncMock()
        fast_publisher = AsyncMock()

        return FrameProcessor(
            face_detector=type("MockDetector", (), {"detect": fast_detector})(),
            object_detector=type("MockDetector", (), {"detect": fast_detector})(),
            frame_repository=type("MockRepo", (), {"save": fast_repo})(),
            event_publisher=type("MockPublisher", (), {"publish": fast_publisher})(),
        )

    def test_single_frame_processing_time(self, benchmark, fast_processor):
        """Benchmark single frame processing time."""
        frame = Frame.create(camera_id="perf_test", timestamp=datetime.now())

        async def process():
            return await fast_processor.process_frame(frame)

        # Run benchmark
        result = benchmark.pedantic(
            lambda: asyncio.run(process()), rounds=100, iterations=5
        )

        # Verify result
        assert result.success is True

        # Performance assertions
        assert benchmark.stats["mean"] < 0.01  # Less than 10ms average
        assert benchmark.stats["max"] < 0.05  # Less than 50ms worst case

    def test_concurrent_processing_throughput(self, benchmark, fast_processor):
        """Benchmark concurrent frame processing throughput."""
        frames = [
            Frame.create(camera_id=f"perf_{i}", timestamp=datetime.now())
            for i in range(100)
        ]

        async def process_batch():
            return await asyncio.gather(
                *[fast_processor.process_frame(f) for f in frames]
            )

        # Run benchmark
        benchmark.pedantic(lambda: asyncio.run(process_batch()), rounds=5, iterations=1)

        # Calculate throughput
        total_frames = 100
        avg_time = benchmark.stats["mean"]
        throughput = total_frames / avg_time

        print(f"\nThroughput: {throughput:.2f} frames/second")

        # Should handle at least 1000 frames/second with mocked deps
        assert throughput > 1000

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, fast_processor):
        """Test memory usage doesn't grow excessively."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process many frames
        for batch in range(10):
            frames = [
                Frame.create(camera_id=f"mem_test_{i}", timestamp=datetime.now())
                for i in range(100)
            ]

            await asyncio.gather(*[fast_processor.process_frame(f) for f in frames])

            # Small delay between batches
            await asyncio.sleep(0.1)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        print(f"\nMemory growth: {memory_growth:.2f} MB")

        # Memory growth should be reasonable (less than 50MB)
        assert memory_growth < 50

    @pytest.mark.asyncio
    async def test_latency_percentiles(self, fast_processor):
        """Test latency percentiles for frame processing."""
        latencies: List[float] = []

        # Process 1000 frames sequentially to measure latency
        for i in range(1000):
            frame = Frame.create(
                camera_id=f"latency_test_{i}", timestamp=datetime.now()
            )

            start = time.time()
            await fast_processor.process_frame(frame)
            latency = (time.time() - start) * 1000  # ms
            latencies.append(latency)

        # Calculate percentiles
        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.50)]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        print(f"\nLatency percentiles (ms):")
        print(f"  p50: {p50:.2f}")
        print(f"  p95: {p95:.2f}")
        print(f"  p99: {p99:.2f}")

        # Performance requirements
        assert p50 < 5  # 50th percentile under 5ms
        assert p95 < 10  # 95th percentile under 10ms
        assert p99 < 20  # 99th percentile under 20ms

    def test_cpu_efficiency(self, benchmark, fast_processor):
        """Test CPU efficiency of frame processing."""
        import multiprocessing

        cpu_count = multiprocessing.cpu_count()
        frames_per_batch = cpu_count * 10

        frames = [
            Frame.create(camera_id=f"cpu_test_{i}", timestamp=datetime.now())
            for i in range(frames_per_batch)
        ]

        async def process_with_concurrency():
            # Process frames with concurrency matching CPU count
            semaphore = asyncio.Semaphore(cpu_count)

            async def process_with_limit(frame):
                async with semaphore:
                    return await fast_processor.process_frame(frame)

            return await asyncio.gather(*[process_with_limit(f) for f in frames])

        result = benchmark(lambda: asyncio.run(process_with_concurrency()))

        # All frames should be processed successfully
        assert len(result) == frames_per_batch
        assert all(r.success for r in result)

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_load(self, fast_processor):
        """Test sustained load handling."""
        duration_seconds = 10
        frames_per_second = 100

        start_time = time.time()
        total_processed = 0
        errors = 0

        while time.time() - start_time < duration_seconds:
            # Create batch of frames
            frames = [
                Frame.create(camera_id=f"sustained_{i}", timestamp=datetime.now())
                for i in range(frames_per_second)
            ]

            # Process batch
            results = await asyncio.gather(
                *[fast_processor.process_frame(f) for f in frames],
                return_exceptions=True,
            )

            # Count results
            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                else:
                    total_processed += 1

            # Wait for next second
            elapsed = time.time() - start_time
            sleep_time = max(0, 1.0 - (elapsed % 1.0))
            await asyncio.sleep(sleep_time)

        actual_fps = total_processed / duration_seconds
        error_rate = (
            errors / (total_processed + errors) if (total_processed + errors) > 0 else 0
        )

        print(f"\nSustained load test:")
        print(f"  Target FPS: {frames_per_second}")
        print(f"  Actual FPS: {actual_fps:.2f}")
        print(f"  Error rate: {error_rate:.2%}")

        # Should maintain at least 90% of target FPS
        assert actual_fps >= frames_per_second * 0.9
        # Error rate should be very low
        assert error_rate < 0.01
