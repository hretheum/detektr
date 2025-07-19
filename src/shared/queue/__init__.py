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

__all__ = [
    "BackpressureHandler",
    "BackpressureConfig",
    "BackpressureState",
    "BackpressureMetrics",
    "AdaptiveBuffer",
    "CircuitBreaker",
    "CircuitBreakerState",
]
