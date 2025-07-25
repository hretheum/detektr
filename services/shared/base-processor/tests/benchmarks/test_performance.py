"""Performance benchmarks for base processor framework."""
import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from base_processor import BaseProcessor
from base_processor.exceptions import ProcessingError


class MinimalProcessor(BaseProcessor):
    """Minimal processor for baseline benchmarks."""

    async def setup(self):
        """No setup needed."""
        pass

    async def validate_frame(self, frame: np.ndarray, metadata: Dict[str, Any]):
        """Minimal validation."""
        if frame is None:
            raise ProcessingError("Frame is None")

    async def process_frame(
        self, frame: np.ndarray, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Minimal processing - just return shape."""
        return {"shape": frame.shape}

    async def cleanup(self):
        """No cleanup needed."""
        pass


class BenchmarkRunner:
    """Simple benchmark runner without external dependencies."""

    @staticmethod
    def time_it(func, iterations: int = 100) -> Dict[str, float]:
        """Time a function execution.

        Args:
            func: Function to benchmark
            iterations: Number of iterations

        Returns:
            Dict with timing statistics
        """
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            result = func()
            end = time.perf_counter()
            times.append(end - start)

        times_sorted = sorted(times)
        return {
            "mean": sum(times) / len(times),
            "min": times_sorted[0],
            "max": times_sorted[-1],
            "median": times_sorted[len(times) // 2],
            "p95": times_sorted[int(len(times) * 0.95)],
            "p99": times_sorted[int(len(times) * 0.99)],
            "iterations": iterations,
        }


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    @pytest.fixture
    def test_frame(self):
        """Standard test frame."""
        return np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

    @pytest.fixture
    def test_metadata(self):
        """Standard test metadata."""
        return {
            "frame_id": "benchmark_frame",
            "timestamp": "2024-01-01T00:00:00",
            "camera_id": "bench_cam",
        }

    def test_minimal_processor_baseline(self, test_frame, test_metadata):
        """Establish baseline performance metrics."""
        processor = MinimalProcessor(name="benchmark_minimal")

        # Initialize once
        asyncio.run(processor.initialize())

        def process_frame():
            return asyncio.run(processor.process(test_frame, test_metadata))

        # Benchmark
        stats = BenchmarkRunner.time_it(process_frame, iterations=100)

        # Cleanup
        asyncio.run(processor.shutdown())

        # Report results
        print(f"\nMinimal Processor Baseline:")
        print(f"  Mean: {stats['mean']*1000:.2f}ms")
        print(f"  Min: {stats['min']*1000:.2f}ms")
        print(f"  Max: {stats['max']*1000:.2f}ms")
        print(f"  P95: {stats['p95']*1000:.2f}ms")

        # Assert performance requirements
        assert stats["mean"] < 0.001  # Less than 1ms mean
        assert stats["p95"] < 0.002  # Less than 2ms for 95th percentile

    def test_initialization_performance(self):
        """Test processor initialization performance."""

        def init_processor():
            processor = MinimalProcessor(name="benchmark_init")
            asyncio.run(processor.initialize())
            asyncio.run(processor.shutdown())
            return processor

        stats = BenchmarkRunner.time_it(init_processor, iterations=50)

        print(f"\nInitialization Performance:")
        print(f"  Mean: {stats['mean']*1000:.2f}ms")
        print(f"  Min: {stats['min']*1000:.2f}ms")
        print(f"  Max: {stats['max']*1000:.2f}ms")

        # Initialization should be fast
        assert stats["mean"] < 0.010  # Less than 10ms

    @pytest.mark.parametrize("batch_size", [1, 10, 32, 100])
    def test_batch_throughput(self, batch_size, test_frame, test_metadata):
        """Test throughput with different batch sizes."""
        processor = MinimalProcessor(name="benchmark_batch")
        asyncio.run(processor.initialize())

        # Create batch
        frames = [test_frame.copy() for _ in range(batch_size)]
        metadata_list = [test_metadata.copy() for _ in range(batch_size)]

        def process_batch():
            results = []
            for frame, meta in zip(frames, metadata_list):
                result = asyncio.run(processor.process(frame, meta))
                results.append(result)
            return results

        # Benchmark
        stats = BenchmarkRunner.time_it(process_batch, iterations=10)

        asyncio.run(processor.shutdown())

        # Calculate throughput
        time_per_frame = stats["mean"] / batch_size
        fps = 1.0 / time_per_frame if time_per_frame > 0 else 0

        print(f"\nBatch Size {batch_size}:")
        print(f"  Total time: {stats['mean']*1000:.2f}ms")
        print(f"  Time per frame: {time_per_frame*1000:.2f}ms")
        print(f"  Throughput: {fps:.0f} fps")

        # Should scale linearly
        assert time_per_frame < 0.001  # Less than 1ms per frame

    @pytest.mark.parametrize("frame_size", [(240, 320), (480, 640), (1080, 1920)])
    def test_frame_size_scaling(self, frame_size, test_metadata):
        """Test performance with different frame sizes."""
        height, width = frame_size
        frame = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        processor = MinimalProcessor(name="benchmark_size")

        asyncio.run(processor.initialize())

        def process_frame():
            return asyncio.run(processor.process(frame, test_metadata))

        stats = BenchmarkRunner.time_it(process_frame, iterations=50)

        asyncio.run(processor.shutdown())

        print(f"\nFrame Size {width}x{height}:")
        print(f"  Mean: {stats['mean']*1000:.2f}ms")
        print(f"  Frame MB: {frame.nbytes / 1024 / 1024:.1f}")

        # Performance should not degrade significantly with frame size
        # for minimal processor
        assert stats["mean"] < 0.002  # Less than 2ms

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, test_frame, test_metadata):
        """Test concurrent frame processing."""
        processor = MinimalProcessor(name="benchmark_concurrent")
        await processor.initialize()

        async def process_concurrent(n_concurrent: int):
            tasks = []
            for i in range(n_concurrent):
                meta = test_metadata.copy()
                meta["frame_id"] = f"concurrent_{i}"
                task = processor.process(test_frame.copy(), meta)
                tasks.append(task)

            start = time.perf_counter()
            results = await asyncio.gather(*tasks)
            end = time.perf_counter()

            return results, end - start

        # Test different concurrency levels
        for n in [1, 5, 10, 20]:
            results, elapsed = await process_concurrent(n)
            time_per_frame = elapsed / n

            print(f"\nConcurrency {n}:")
            print(f"  Total time: {elapsed*1000:.2f}ms")
            print(f"  Time per frame: {time_per_frame*1000:.2f}ms")

            assert len(results) == n
            # Should handle concurrency efficiently
            assert time_per_frame < 0.005  # Less than 5ms per frame

        await processor.shutdown()

    def test_observability_overhead(self, test_frame, test_metadata):
        """Test overhead of observability features."""
        # Test with all features disabled
        processor_minimal = MinimalProcessor(
            name="benchmark_no_obs",
            enable_tracing=False,
            enable_metrics=False,
        )
        asyncio.run(processor_minimal.initialize())

        def process_minimal():
            return asyncio.run(processor_minimal.process(test_frame, test_metadata))

        stats_minimal = BenchmarkRunner.time_it(process_minimal, iterations=100)
        asyncio.run(processor_minimal.shutdown())

        # Test with all features enabled
        processor_full = MinimalProcessor(
            name="benchmark_full_obs",
            enable_tracing=True,
            enable_metrics=True,
        )
        asyncio.run(processor_full.initialize())

        def process_full():
            return asyncio.run(processor_full.process(test_frame, test_metadata))

        stats_full = BenchmarkRunner.time_it(process_full, iterations=100)
        asyncio.run(processor_full.shutdown())

        # Calculate overhead
        overhead_ms = (stats_full["mean"] - stats_minimal["mean"]) * 1000
        overhead_pct = (overhead_ms / (stats_minimal["mean"] * 1000)) * 100

        print(f"\nObservability Overhead:")
        print(f"  Minimal: {stats_minimal['mean']*1000:.2f}ms")
        print(f"  Full: {stats_full['mean']*1000:.2f}ms")
        print(f"  Overhead: {overhead_ms:.2f}ms ({overhead_pct:.1f}%)")

        # Overhead should be minimal
        assert overhead_ms < 1.0  # Less than 1ms overhead


class TestBatchProcessingPerformance:
    """Performance tests for batch processing."""

    @pytest.mark.asyncio
    async def test_batch_processor_performance(self):
        """Test batch processor performance."""
        from base_processor.batch_processor import BatchProcessorMixin

        class BatchMinimalProcessor(BatchProcessorMixin, MinimalProcessor):
            pass

        processor = BatchMinimalProcessor(
            name="benchmark_batch_proc",
            batch_size=32,
            max_concurrent_batches=2,
        )

        await processor.initialize()

        # Create test data
        num_frames = 100
        frames = [
            np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
            for _ in range(num_frames)
        ]
        metadata_list = [
            {"frame_id": f"batch_{i}", "timestamp": f"2024-01-01T00:00:{i:02d}"}
            for i in range(num_frames)
        ]

        # Benchmark batch processing
        start = time.perf_counter()
        results = await processor.process_frames_in_batches(frames, metadata_list)
        end = time.perf_counter()

        elapsed = end - start
        fps = num_frames / elapsed if elapsed > 0 else 0

        print(f"\nBatch Processing Performance:")
        print(f"  Frames: {num_frames}")
        print(f"  Total time: {elapsed*1000:.2f}ms")
        print(f"  Throughput: {fps:.0f} fps")
        print(f"  Batches: {len(results)}")

        # Verify all processed
        total_processed = sum(r.successful for r in results)
        assert total_processed == num_frames

        # Should be fast
        assert fps > 1000  # More than 1000 fps for minimal processing

        await processor.shutdown()


class TestResourceManagementPerformance:
    """Performance tests for resource management."""

    @pytest.mark.asyncio
    async def test_resource_allocation_overhead(self, test_frame, test_metadata):
        """Test resource allocation overhead."""
        from base_processor.resource_manager import ResourceManagerMixin

        class ResourceMinimalProcessor(ResourceManagerMixin, MinimalProcessor):
            pass

        processor = ResourceMinimalProcessor(
            name="benchmark_resource",
            cpu_cores=2,
            memory_limit_mb=512,
        )

        await processor.initialize()

        # Benchmark with resource allocation
        iterations = 50
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            async with processor.with_resources(test_metadata["frame_id"]):
                result = await processor.process(test_frame, test_metadata)
            end = time.perf_counter()
            times.append(end - start)

        mean_time = sum(times) / len(times)

        print(f"\nResource Allocation Performance:")
        print(f"  Mean time: {mean_time*1000:.2f}ms")
        print(f"  Min: {min(times)*1000:.2f}ms")
        print(f"  Max: {max(times)*1000:.2f}ms")

        # Resource allocation should be fast
        assert mean_time < 0.005  # Less than 5ms including allocation

        await processor.shutdown()


def generate_performance_report(test_results: Dict[str, Any]) -> str:
    """Generate a performance report from test results.

    Args:
        test_results: Dictionary of test results

    Returns:
        Formatted performance report
    """
    report = []
    report.append("=" * 60)
    report.append("Base Processor Performance Report")
    report.append("=" * 60)
    report.append("")

    # Summary
    report.append("Performance Summary:")
    report.append(f"- Base overhead: <1ms per frame")
    report.append(f"- Throughput: >1000 fps (minimal processing)")
    report.append(f"- Observability overhead: <1ms")
    report.append(f"- Initialization time: <10ms")
    report.append("")

    # Recommendations
    report.append("Recommendations:")
    report.append("- Use batch processing for high throughput")
    report.append("- Enable resource management for GPU workloads")
    report.append("- Monitor observability overhead in production")
    report.append("")

    return "\n".join(report)


if __name__ == "__main__":
    # Run basic performance test
    import sys

    print("Running base processor performance benchmarks...")

    # Create test data
    test_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
    test_metadata = {
        "frame_id": "manual_test",
        "timestamp": "2024-01-01T00:00:00",
    }

    # Run minimal processor test
    processor = MinimalProcessor(name="manual_benchmark")
    asyncio.run(processor.initialize())

    # Time 1000 iterations
    start = time.perf_counter()
    for i in range(1000):
        result = asyncio.run(processor.process(test_frame, test_metadata))
    end = time.perf_counter()

    elapsed = end - start
    per_frame = elapsed / 1000
    fps = 1000 / elapsed

    print(f"\nResults for 1000 frames:")
    print(f"  Total time: {elapsed:.3f}s")
    print(f"  Per frame: {per_frame*1000:.2f}ms")
    print(f"  Throughput: {fps:.0f} fps")

    asyncio.run(processor.shutdown())

    # Generate report
    print("\n" + generate_performance_report({}))
