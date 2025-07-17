"""
OpenTelemetry telemetry setup module.

Provides centralized configuration for traces, metrics, and logs.
"""

from .config import setup_telemetry
from .correlation import (
    CorrelatedMetrics,
    configure_correlated_logging,
    configure_stdlib_correlation,
    get_correlated_logger,
)
from .decorators import traced, traced_frame, traced_method
from .frame_decorators import (
    FrameProcessor,
    traced_frame_operation,
    traced_processing_stage,
)
from .frame_tracking import (
    FrameTracer,
    clear_frame_context,
    get_camera_id,
    get_frame_id,
    set_frame_context,
    with_frame_context,
)
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
    # Core setup
    "setup_telemetry",
    "setup_auto_instrumentation",
    "instrument_app",
    # Basic decorators
    "traced",
    "traced_method",
    "traced_frame",
    # Metrics
    "DetektorMetrics",
    "get_metrics",
    "increment_frames_processed",
    "increment_detections",
    "record_processing_time",
    "increment_errors",
    # Frame tracking
    "set_frame_context",
    "get_frame_id",
    "get_camera_id",
    "clear_frame_context",
    "with_frame_context",
    "FrameTracer",
    # Frame decorators
    "traced_frame_operation",
    "traced_processing_stage",
    "FrameProcessor",
    # Correlation
    "configure_correlated_logging",
    "get_correlated_logger",
    "CorrelatedMetrics",
    "configure_stdlib_correlation",
]
