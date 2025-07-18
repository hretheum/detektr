"""Performance baseline management for regression detection"""
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np


@dataclass
class PerformanceBaseline:
    """Performance baseline for a specific operation"""

    operation: str
    p50_ms: float
    p95_ms: float
    p99_ms: float
    throughput_rps: float
    timestamp: datetime
    iterations: int
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceBaseline":
        """Create from dictionary"""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class BaselineManager:
    """Manage performance baselines for operations"""

    def __init__(self, baseline_file: str = "baselines.json"):
        self.baseline_file = Path(baseline_file)
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self._load_baselines()

    def _load_baselines(self) -> None:
        """Load existing baselines from file"""
        if self.baseline_file.exists():
            with open(self.baseline_file) as f:
                data = json.load(f)
                for op, baseline_data in data.items():
                    self.baselines[op] = PerformanceBaseline.from_dict(baseline_data)

    def save_baselines(self) -> None:
        """Save baselines to file"""
        data = {op: baseline.to_dict() for op, baseline in self.baselines.items()}
        with open(self.baseline_file, "w") as f:
            json.dump(data, f, indent=2)

    async def measure_operation(
        self,
        name: str,
        operation: Callable,
        iterations: int = 1000,
        warmup: int = 10,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PerformanceBaseline:
        """
        Measure performance baseline for an operation

        Args:
            name: Operation name
            operation: Async callable to benchmark
            iterations: Number of iterations to run
            warmup: Number of warmup iterations
            metadata: Additional metadata to store

        Returns:
            PerformanceBaseline with measurements
        """
        # Warmup
        for _ in range(warmup):
            await operation()

        # Measure
        latencies = []
        start_time = time.time()

        for _ in range(iterations):
            op_start = time.perf_counter()
            await operation()
            latencies.append((time.perf_counter() - op_start) * 1000)  # Convert to ms

        total_time = time.time() - start_time
        latencies_sorted = sorted(latencies)

        baseline = PerformanceBaseline(
            operation=name,
            p50_ms=np.percentile(latencies_sorted, 50),
            p95_ms=np.percentile(latencies_sorted, 95),
            p99_ms=np.percentile(latencies_sorted, 99),
            throughput_rps=iterations / total_time,
            timestamp=datetime.now(),
            iterations=iterations,
            metadata=metadata,
        )

        self.baselines[name] = baseline
        return baseline

    def get_baseline(self, operation: str) -> Optional[PerformanceBaseline]:
        """Get baseline for an operation"""
        return self.baselines.get(operation)

    def compare_with_baseline(
        self,
        operation: str,
        current: PerformanceBaseline,
        threshold_percent: float = 20.0,
    ) -> Dict[str, Any]:
        """
        Compare current performance with baseline

        Args:
            operation: Operation name
            current: Current performance measurements
            threshold_percent: Degradation threshold percentage

        Returns:
            Comparison results with any degradations
        """
        baseline = self.get_baseline(operation)
        if not baseline:
            return {
                "status": "no_baseline",
                "message": f"No baseline found for {operation}",
            }

        degradations = {}

        # Compare percentiles
        for metric in ["p50_ms", "p95_ms", "p99_ms"]:
            baseline_value = getattr(baseline, metric)
            current_value = getattr(current, metric)

            if baseline_value > 0:
                change_percent = (
                    (current_value - baseline_value) / baseline_value
                ) * 100
                if change_percent > threshold_percent:
                    degradations[metric] = {
                        "baseline": baseline_value,
                        "current": current_value,
                        "degradation_percent": round(change_percent, 1),
                    }

        # Compare throughput (lower is worse)
        if baseline.throughput_rps > 0:
            throughput_change = (
                (baseline.throughput_rps - current.throughput_rps)
                / baseline.throughput_rps
            ) * 100
            if throughput_change > threshold_percent:
                degradations["throughput_rps"] = {
                    "baseline": baseline.throughput_rps,
                    "current": current.throughput_rps,
                    "degradation_percent": round(throughput_change, 1),
                }

        if degradations:
            return {
                "status": "degraded",
                "degradations": degradations,
                "baseline_timestamp": baseline.timestamp.isoformat(),
                "current_timestamp": current.timestamp.isoformat(),
            }

        return {"status": "ok", "message": "Performance within acceptable range"}

    def generate_report(self) -> Dict[str, Any]:
        """Generate performance baseline report"""
        return {
            "baselines": {
                op: {
                    "p50_ms": round(baseline.p50_ms, 2),
                    "p95_ms": round(baseline.p95_ms, 2),
                    "p99_ms": round(baseline.p99_ms, 2),
                    "throughput_rps": round(baseline.throughput_rps, 2),
                    "timestamp": baseline.timestamp.isoformat(),
                    "iterations": baseline.iterations,
                }
                for op, baseline in self.baselines.items()
            },
            "total_operations": len(self.baselines),
            "report_generated": datetime.now().isoformat(),
        }
