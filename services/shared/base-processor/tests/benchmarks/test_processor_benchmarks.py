"""Performance benchmarks for base processor framework."""
import asyncio
import time
from typing import Any, Dict

import numpy as np
import pytest
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


class ComputeProcessor(BaseProcessor):
    """Processor with simulated compute load."""

    def __init__(self, compute_ms: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.compute_ms = compute_ms

    async def setup(self):
        """No setup needed."""
        pass

    async def validate_frame(self, frame: np.ndarray, metadata: Dict[str, Any]):
        """Standard validation."""
        if frame is None or frame.size == 0:
            raise ProcessingError("Invalid frame")

    async def process_frame(
        self, frame: np.ndarray, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate compute workload."""
        # Simulate CPU work
        start = time.time()
        while (time.time() - start) < (self.compute_ms / 1000):
            # Busy wait to simulate CPU usage
            _ = np.sum(frame)

        return {
            "shape": frame.shape,
            "mean": float(np.mean(frame)),
            "compute_ms": self.compute_ms,
        }

    async def cleanup(self):
        """No cleanup needed."""
        pass


class TestProcessorBenchmarks:
    """Benchmark tests for processor performance."""

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

    @pytest.mark.benchmark(group="overhead")
    def test_minimal_processor_overhead(self, benchmark, test_frame, test_metadata):
        """Benchmark minimal processor overhead."""
        processor = MinimalProcessor(name="benchmark_minimal")

        async def process():
            await processor.initialize()
            result = await processor.process(test_frame, test_metadata)
            await processor.shutdown()
            return result

        result = benchmark(lambda: asyncio.run(process()))
        assert result["shape"] == test_frame.shape

    @pytest.mark.benchmark(group="overhead")
    def test_tracing_overhead(self, benchmark, test_frame, test_metadata):
        """Benchmark overhead with tracing enabled."""
        processor = MinimalProcessor(name="benchmark_traced", enable_tracing=True)

        async def process():
            await processor.initialize()
            result = await processor.process(test_frame, test_metadata)
            await processor.shutdown()
            return result

        result = benchmark(lambda: asyncio.run(process()))
        assert result["shape"] == test_frame.shape

    @pytest.mark.benchmark(group="overhead")
    def test_metrics_overhead(self, benchmark, test_frame, test_metadata):
        """Benchmark overhead with metrics enabled."""
        processor = MinimalProcessor(name="benchmark_metrics", enable_metrics=True)

        async def process():
            await processor.initialize()
            result = await processor.process(test_frame, test_metadata)
            await processor.shutdown()
            return result

        result = benchmark(lambda: asyncio.run(process()))
        assert result["shape"] == test_frame.shape

    @pytest.mark.benchmark(group="throughput")
    @pytest.mark.parametrize("batch_size", [1, 10, 32, 100])
    def test_batch_throughput(self, benchmark, batch_size, test_frame, test_metadata):
        """Benchmark batch processing throughput."""
        processor = MinimalProcessor(name="benchmark_batch")

        # Create batch
        frames = [test_frame.copy() for _ in range(batch_size)]
        metadata_list = [test_metadata.copy() for _ in range(batch_size)]

        async def process_batch():
            await processor.initialize()
            results = []
            for frame, meta in zip(frames, metadata_list):
                result = await processor.process(frame, meta)
                results.append(result)
            await processor.shutdown()
            return results

        results = benchmark(lambda: asyncio.run(process_batch()))
        assert len(results) == batch_size

    @pytest.mark.benchmark(group="compute")
    @pytest.mark.parametrize("compute_ms", [0, 10, 50, 100])
    def test_compute_scaling(self, benchmark, compute_ms, test_frame, test_metadata):
        """Benchmark with different compute loads."""
        processor = ComputeProcessor(
            name="benchmark_compute",
            compute_ms=compute_ms,
        )

        async def process():
            await processor.initialize()
            result = await processor.process(test_frame, test_metadata)
            await processor.shutdown()
            return result

        result = benchmark(lambda: asyncio.run(process()))
        assert result["compute_ms"] == compute_ms

    @pytest.mark.benchmark(group="memory")
    @pytest.mark.parametrize(
        "frame_size", [(240, 320), (480, 640), (1080, 1920), (2160, 3840)]
    )
    def test_memory_scaling(self, benchmark, frame_size, test_metadata):
        """Benchmark with different frame sizes."""
        height, width = frame_size
        frame = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        processor = MinimalProcessor(name="benchmark_memory")

        async def process():
            await processor.initialize()
            result = await processor.process(frame, test_metadata)
            await processor.shutdown()
            return result

        result = benchmark(lambda: asyncio.run(process()))
        assert result["shape"] == (height, width, 3)

    @pytest.mark.benchmark(group="lifecycle")
    def test_initialization_overhead(self, benchmark):
        """Benchmark initialization overhead."""

        def init_and_shutdown():
            processor = MinimalProcessor(name="benchmark_init")
            asyncio.run(processor.initialize())
            asyncio.run(processor.shutdown())

        benchmark(init_and_shutdown)

    @pytest.mark.benchmark(group="concurrent")
    @pytest.mark.parametrize("concurrency", [1, 5, 10, 20])
    def test_concurrent_processing(
        self, benchmark, concurrency, test_frame, test_metadata
    ):
        """Benchmark concurrent frame processing."""
        processor = MinimalProcessor(name="benchmark_concurrent")

        async def process_concurrent():
            await processor.initialize()

            # Create concurrent tasks
            tasks = []
            for i in range(concurrency):
                meta = test_metadata.copy()
                meta["frame_id"] = f"concurrent_{i}"
                task = processor.process(test_frame.copy(), meta)
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            await processor.shutdown()
            return results

        results = benchmark(lambda: asyncio.run(process_concurrent()))
        assert len(results) == concurrency


class TestBatchProcessingBenchmarks:
    """Benchmarks specifically for batch processing."""

    @pytest.fixture
    def batch_processor(self):
        """Processor with batch support."""
        from base_processor.batch_processor import BatchProcessorMixin

        class BatchMinimalProcessor(BatchProcessorMixin, MinimalProcessor):
            pass

        return BatchMinimalProcessor(
            name="benchmark_batch_proc",
            batch_size=32,
            max_concurrent_batches=2,
        )

    @pytest.mark.benchmark(group="batch")
    @pytest.mark.parametrize("num_frames", [10, 50, 100, 500])
    async def test_batch_processing_performance(
        self, benchmark, batch_processor, num_frames
    ):
        """Benchmark batch processing performance."""
        frames = [
            np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
            for _ in range(num_frames)
        ]
        metadata_list = [
            {"frame_id": f"batch_{i}", "timestamp": f"2024-01-01T00:00:{i:02d}"}
            for i in range(num_frames)
        ]

        await batch_processor.initialize()

        async def process_batch():
            results = await batch_processor.process_frames_in_batches(
                frames, metadata_list
            )
            return results

        results = benchmark(lambda: asyncio.run(process_batch()))

        # Verify all frames processed
        total_processed = sum(r.successful for r in results)
        assert total_processed == num_frames

        await batch_processor.shutdown()


class TestResourceBenchmarks:
    """Benchmarks for resource management."""

    @pytest.fixture
    def resource_processor(self):
        """Processor with resource management."""
        from base_processor.resource_manager import ResourceManagerMixin

        class ResourceMinimalProcessor(ResourceManagerMixin, MinimalProcessor):
            pass

        return ResourceMinimalProcessor(
            name="benchmark_resource",
            cpu_cores=2,
            memory_limit_mb=512,
        )

    @pytest.mark.benchmark(group="resource")
    async def test_resource_allocation_overhead(
        self, benchmark, resource_processor, test_frame, test_metadata
    ):
        """Benchmark resource allocation overhead."""
        await resource_processor.initialize()

        async def process_with_resources():
            async with resource_processor.with_resources(test_metadata["frame_id"]):
                result = await resource_processor.process(test_frame, test_metadata)
            return result

        result = benchmark(lambda: asyncio.run(process_with_resources()))
        assert result["shape"] == test_frame.shape

        await resource_processor.shutdown()


# Benchmark result analysis utilities
def analyze_benchmark_results(benchmark_stats):
    """Analyze benchmark results for performance validation.

    Args:
        benchmark_stats: pytest-benchmark statistics

    Returns:
        Dict with analysis results
    """
    analysis = {
        "overhead_ms": None,
        "throughput_fps": None,
        "memory_efficiency": None,
        "scaling_factor": None,
    }

    # Calculate base overhead
    if "overhead" in benchmark_stats:
        minimal = benchmark_stats["overhead"]["minimal_processor"]
        analysis["overhead_ms"] = minimal["mean"] * 1000  # Convert to ms

    # Calculate throughput
    if "throughput" in benchmark_stats:
        batch_100 = benchmark_stats["throughput"]["batch_100"]
        time_per_frame = batch_100["mean"] / 100
        analysis["throughput_fps"] = 1.0 / time_per_frame if time_per_frame > 0 else 0

    return analysis


# Performance regression detector
class PerformanceRegression:
    """Detect performance regressions."""

    THRESHOLDS = {
        "overhead_ms": 1.0,  # Max 1ms overhead
        "throughput_fps": 1000,  # Min 1000 fps for minimal processor
        "memory_mb_per_frame": 10,  # Max 10MB per frame overhead
    }

    @classmethod
    def check_regression(cls, current_stats, baseline_stats=None):
        """Check for performance regression.

        Args:
            current_stats: Current benchmark results
            baseline_stats: Optional baseline to compare against

        Returns:
            Dict with regression detection results
        """
        regressions = []

        # Check absolute thresholds
        current_analysis = analyze_benchmark_results(current_stats)

        if (
            current_analysis["overhead_ms"]
            and current_analysis["overhead_ms"] > cls.THRESHOLDS["overhead_ms"]
        ):
            regressions.append(
                {
                    "metric": "overhead_ms",
                    "current": current_analysis["overhead_ms"],
                    "threshold": cls.THRESHOLDS["overhead_ms"],
                    "severity": "high",
                }
            )

        if (
            current_analysis["throughput_fps"]
            and current_analysis["throughput_fps"] < cls.THRESHOLDS["throughput_fps"]
        ):
            regressions.append(
                {
                    "metric": "throughput_fps",
                    "current": current_analysis["throughput_fps"],
                    "threshold": cls.THRESHOLDS["throughput_fps"],
                    "severity": "medium",
                }
            )

        # Check against baseline if provided
        if baseline_stats:
            baseline_analysis = analyze_benchmark_results(baseline_stats)

            # 10% regression threshold
            for metric in ["overhead_ms", "throughput_fps"]:
                if current_analysis[metric] and baseline_analysis[metric]:
                    if metric == "overhead_ms":
                        regression_pct = (
                            current_analysis[metric] - baseline_analysis[metric]
                        ) / baseline_analysis[metric]
                    else:  # throughput - lower is worse
                        regression_pct = (
                            baseline_analysis[metric] - current_analysis[metric]
                        ) / baseline_analysis[metric]

                    if regression_pct > 0.1:  # 10% regression
                        regressions.append(
                            {
                                "metric": metric,
                                "current": current_analysis[metric],
                                "baseline": baseline_analysis[metric],
                                "regression_pct": regression_pct * 100,
                                "severity": "high"
                                if regression_pct > 0.2
                                else "medium",
                            }
                        )

        return {
            "has_regression": len(regressions) > 0,
            "regressions": regressions,
            "analysis": current_analysis,
        }
