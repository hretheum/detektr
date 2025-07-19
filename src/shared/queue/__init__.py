"""Queue abstraction layer with backpressure support."""
from .backpressure import (
    AdaptiveBuffer,
    BackpressureConfig,
    BackpressureHandler,
    BackpressureMetrics,
    BackpressureState,
    CircuitBreaker,
    CircuitBreakerState,
)
from .dlq import DeadLetterQueue, DLQEntry, DLQReason
from .metrics import MetricsEnabledBackpressureHandler, QueueMetricsCollector

__all__ = [
    "BackpressureHandler",
    "BackpressureConfig",
    "BackpressureState",
    "BackpressureMetrics",
    "AdaptiveBuffer",
    "CircuitBreaker",
    "CircuitBreakerState",
    "DeadLetterQueue",
    "DLQEntry",
    "DLQReason",
    "MetricsEnabledBackpressureHandler",
    "QueueMetricsCollector",
]
