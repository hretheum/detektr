"""Performance regression detection"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .baseline import BaselineManager, PerformanceBaseline


@dataclass
class RegressionResult:
    """Result of regression detection"""

    operation: str
    status: str  # "ok", "warning", "critical"
    degradations: Dict[str, Dict[str, float]]
    recommendations: List[str]
    timestamp: datetime


class RegressionDetector:
    """Detect performance regressions against baselines"""

    def __init__(
        self,
        baseline_manager: BaselineManager,
        warning_threshold: float = 10.0,  # 10% degradation = warning
        critical_threshold: float = 20.0,  # 20% degradation = critical
    ):
        self.baseline_manager = baseline_manager
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def check_regression(
        self, operation: str, current: PerformanceBaseline
    ) -> RegressionResult:
        """Check for performance regression"""
        comparison = self.baseline_manager.compare_with_baseline(
            operation, current, self.warning_threshold
        )

        if comparison["status"] == "no_baseline":
            return RegressionResult(
                operation=operation,
                status="ok",
                degradations={},
                recommendations=["Baseline established for future comparisons"],
                timestamp=datetime.now(),
            )

        if comparison["status"] == "ok":
            return RegressionResult(
                operation=operation,
                status="ok",
                degradations={},
                recommendations=[],
                timestamp=datetime.now(),
            )

        # Analyze degradations
        degradations = comparison["degradations"]
        max_degradation = max(d["degradation_percent"] for d in degradations.values())

        if max_degradation >= self.critical_threshold:
            status = "critical"
        else:
            status = "warning"

        recommendations = self._generate_recommendations(operation, degradations)

        return RegressionResult(
            operation=operation,
            status=status,
            degradations=degradations,
            recommendations=recommendations,
            timestamp=datetime.now(),
        )

    def _generate_recommendations(
        self, operation: str, degradations: Dict[str, Dict[str, float]]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Latency degradation
        if "p99_ms" in degradations:
            recommendations.append(
                f"P99 latency degraded by {degradations['p99_ms']['degradation_percent']}%. "
                "Check for: blocking I/O, increased load, or algorithm changes."
            )

        if "p95_ms" in degradations:
            recommendations.append(
                f"P95 latency degraded by {degradations['p95_ms']['degradation_percent']}%. "
                "Consider: caching, connection pooling, or async optimization."
            )

        # Throughput degradation
        if "throughput_rps" in degradations:
            recommendations.append(
                f"Throughput degraded by {degradations['throughput_rps']['degradation_percent']}%. "
                "Review: concurrency settings, resource limits, or bottlenecks."
            )

        # General recommendations
        recommendations.extend(
            [
                f"Run profiler on {operation} to identify hotspots",
                "Compare git diff since baseline was established",
                "Check system resources (CPU, memory, I/O) during test",
            ]
        )

        return recommendations

    def generate_regression_report(
        self, results: List[RegressionResult]
    ) -> Dict[str, Any]:
        """Generate regression report for multiple operations"""
        critical_count = sum(1 for r in results if r.status == "critical")
        warning_count = sum(1 for r in results if r.status == "warning")
        ok_count = sum(1 for r in results if r.status == "ok")

        return {
            "summary": {
                "total_operations": len(results),
                "critical": critical_count,
                "warning": warning_count,
                "ok": ok_count,
                "overall_status": "critical"
                if critical_count > 0
                else "warning"
                if warning_count > 0
                else "ok",
            },
            "details": [
                {
                    "operation": r.operation,
                    "status": r.status,
                    "degradations": r.degradations,
                    "recommendations": r.recommendations,
                }
                for r in results
                if r.status != "ok"
            ],
            "timestamp": datetime.now().isoformat(),
        }
