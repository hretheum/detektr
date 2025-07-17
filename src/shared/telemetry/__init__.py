"""
OpenTelemetry telemetry setup module.

Provides centralized configuration for traces, metrics, and logs.
"""

from .config import setup_telemetry
from .decorators import traced, traced_frame, traced_method
from .instrumentation import instrument_app, setup_auto_instrumentation
from .metrics import (
    DetektorMetrics,
    get_metrics,
    increment_detections,
    increment_errors,
    increment_frames_processed,
    record_processing_time,
)

__all__ = [
    "setup_telemetry",
    "setup_auto_instrumentation",
    "instrument_app",
    "traced",
    "traced_method",
    "traced_frame",
    "DetektorMetrics",
    "get_metrics",
    "increment_frames_processed",
    "increment_detections",
    "record_processing_time",
    "increment_errors",
]
