"""Performance baseline tests"""
import asyncio
import json
from pathlib import Path

import pytest

from src.examples.frame_processor import FrameProcessor
from src.shared.benchmarks import BaselineManager, RegressionDetector
from src.shared.kernel.domain.frame import Frame


@pytest.fixture
def baseline_manager(tmp_path):
    """Create baseline manager with temp file"""
    baseline_file = tmp_path / "test_baselines.json"
    return BaselineManager(str(baseline_file))


@pytest.fixture
async def frame_processor():
    """Create frame processor for testing"""
    processor = FrameProcessor()
    yield processor
    await processor.shutdown()


@pytest.fixture
def test_frame():
    """Create test frame"""
    return Frame.create(
        camera_id="test_cam",
        image_data=b"fake_image_data" * 1000,  # ~15KB
        width=1920,
        height=1080,
        format="RGB24",
    )


@pytest.mark.benchmark
async def test_frame_processing_baseline(baseline_manager, frame_processor, test_frame):
    """Establish frame processing baseline"""
    # Measure baseline
    baseline = await baseline_manager.measure_operation(
        "frame_processing",
        lambda: frame_processor.process_frame(test_frame),
        iterations=100,
        warmup=10,
        metadata={"frame_size": "1920x1080", "format": "RGB24"},
    )

    # Assertions on baseline quality
    assert baseline.p95_ms < 100  # 95th percentile under 100ms
    assert baseline.p99_ms < 150  # 99th percentile under 150ms
    assert baseline.throughput_rps > 10  # At least 10 frames/second

    # Save baseline
    baseline_manager.save_baselines()

    # Verify saved
    assert Path(baseline_manager.baseline_file).exists()
    with open(baseline_manager.baseline_file) as f:
        data = json.load(f)
        assert "frame_processing" in data


@pytest.mark.benchmark
async def test_regression_detection(baseline_manager, frame_processor, test_frame):
    """Test regression detection against baseline"""
    # Establish baseline
    baseline = await baseline_manager.measure_operation(
        "frame_processing",
        lambda: frame_processor.process_frame(test_frame),
        iterations=50,
    )

    # Simulate degraded performance (add artificial delay)
    async def degraded_operation():
        await asyncio.sleep(0.02)  # Add 20ms delay
        return await frame_processor.process_frame(test_frame)

    # Measure degraded performance
    degraded = await baseline_manager.measure_operation(
        "frame_processing_degraded", degraded_operation, iterations=50
    )

    # Use regression detector
    detector = RegressionDetector(baseline_manager)
    result = detector.check_regression("frame_processing", degraded)

    # Should detect regression
    assert result.status in ["warning", "critical"]
    assert len(result.degradations) > 0
    assert len(result.recommendations) > 0


@pytest.mark.benchmark
async def test_multiple_operations_baseline(baseline_manager):
    """Test baselines for multiple operations"""

    # Define test operations
    async def fast_operation():
        await asyncio.sleep(0.001)  # 1ms

    async def medium_operation():
        await asyncio.sleep(0.01)  # 10ms

    async def slow_operation():
        await asyncio.sleep(0.05)  # 50ms

    # Measure all operations
    operations = [
        ("fast_op", fast_operation, {"expected_ms": 1}),
        ("medium_op", medium_operation, {"expected_ms": 10}),
        ("slow_op", slow_operation, {"expected_ms": 50}),
    ]

    for name, op, metadata in operations:
        baseline = await baseline_manager.measure_operation(
            name, op, iterations=20, metadata=metadata
        )

        # Verify measurements are reasonable
        expected_ms = metadata["expected_ms"]
        assert baseline.p50_ms >= expected_ms * 0.8  # Within 20% of expected
        assert baseline.p50_ms <= expected_ms * 1.5  # Not too slow

    # Generate report
    report = baseline_manager.generate_report()
    assert report["total_operations"] == 3
    assert all(op in report["baselines"] for op, _, _ in operations)


@pytest.mark.benchmark
async def test_baseline_persistence(tmp_path):
    """Test baseline persistence across runs"""
    baseline_file = tmp_path / "persist_baselines.json"

    # First run - establish baseline
    manager1 = BaselineManager(str(baseline_file))

    async def test_op():
        await asyncio.sleep(0.005)

    baseline1 = await manager1.measure_operation("test_op", test_op, iterations=10)
    manager1.save_baselines()

    # Second run - load and compare
    manager2 = BaselineManager(str(baseline_file))
    loaded_baseline = manager2.get_baseline("test_op")

    assert loaded_baseline is not None
    assert loaded_baseline.p50_ms == baseline1.p50_ms
    assert loaded_baseline.operation == "test_op"


@pytest.mark.benchmark
async def test_regression_report_generation(baseline_manager):
    """Test regression report for multiple operations"""
    detector = RegressionDetector(baseline_manager)

    # Create some test results
    from datetime import datetime

    from src.shared.benchmarks.regression import RegressionResult

    results = [
        RegressionResult(
            operation="op1",
            status="ok",
            degradations={},
            recommendations=[],
            timestamp=datetime.now(),
        ),
        RegressionResult(
            operation="op2",
            status="warning",
            degradations={"p95_ms": {"degradation_percent": 15}},
            recommendations=["Check for blocking I/O"],
            timestamp=datetime.now(),
        ),
        RegressionResult(
            operation="op3",
            status="critical",
            degradations={"p99_ms": {"degradation_percent": 25}},
            recommendations=["Immediate investigation required"],
            timestamp=datetime.now(),
        ),
    ]

    report = detector.generate_regression_report(results)

    assert report["summary"]["total_operations"] == 3
    assert report["summary"]["critical"] == 1
    assert report["summary"]["warning"] == 1
    assert report["summary"]["ok"] == 1
    assert report["summary"]["overall_status"] == "critical"
    assert len(report["details"]) == 2  # Only non-ok results
