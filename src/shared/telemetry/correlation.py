"""Correlation utilities for logs, metrics, and traces."""

import logging
import sys
from typing import Any, Dict, Optional

import structlog
from opentelemetry import trace
from opentelemetry.trace import Span
from prometheus_client import Counter, Histogram

from .frame_tracking import get_camera_id, get_frame_id

# Frame processing metrics with labels
frame_processing_counter = Counter(
    "frame_processing_total",
    "Total number of frames processed",
    ["camera_id", "stage", "status"],
)

frame_processing_duration = Histogram(
    "frame_processing_duration_seconds",
    "Frame processing duration",
    ["camera_id", "stage"],
)

frame_errors_counter = Counter(
    "frame_processing_errors_total",
    "Total number of frame processing errors",
    ["camera_id", "stage", "error_type"],
)


def add_correlation_info(event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Structlog processor to add correlation info.

    Adds trace_id, span_id, and frame_id to all log entries.

    Args:
        event_dict: Log event dictionary

    Returns:
        Enhanced event dictionary with correlation info
    """
    # Get current span
    span = trace.get_current_span()
    if span and span.is_recording():
        span_context = span.get_span_context()
        if span_context.trace_id:
            event_dict["trace_id"] = format(span_context.trace_id, "032x")
        if span_context.span_id:
            event_dict["span_id"] = format(span_context.span_id, "016x")

    # Add frame context
    frame_id = get_frame_id()
    if frame_id:
        event_dict["frame_id"] = frame_id

    camera_id = get_camera_id()
    if camera_id:
        event_dict["camera_id"] = camera_id

    return event_dict


def configure_correlated_logging() -> None:
    """Configure structlog with correlation processors."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_correlation_info,  # Add correlation info
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_correlated_logger(name: str) -> Any:
    """Get a logger with correlation support.

    Args:
        name: Logger name

    Returns:
        Structlog logger with correlation
    """
    return structlog.get_logger(name)


class CorrelatedMetrics:
    """Helper for recording metrics with frame correlation."""

    @staticmethod
    def increment_processed(stage: str = "unknown", status: str = "success") -> None:
        """Increment frames processed counter with correlation.

        Args:
            stage: Processing stage name
            status: Processing status (success/failure)
        """
        camera_id = get_camera_id() or "unknown"
        frame_processing_counter.labels(
            camera_id=camera_id, stage=stage, status=status
        ).inc()

    @staticmethod
    def observe_duration(duration_seconds: float, stage: str = "unknown") -> None:
        """Observe processing duration with correlation.

        Args:
            duration_seconds: Processing duration in seconds
            stage: Processing stage name
        """
        camera_id = get_camera_id() or "unknown"
        frame_processing_duration.labels(camera_id=camera_id, stage=stage).observe(
            duration_seconds
        )

    @staticmethod
    def increment_errors(stage: str = "unknown", error_type: str = "unknown") -> None:
        """Increment error counter with correlation.

        Args:
            stage: Processing stage where error occurred
            error_type: Type of error
        """
        camera_id = get_camera_id() or "unknown"
        frame_errors_counter.labels(
            camera_id=camera_id, stage=stage, error_type=error_type
        ).inc()


def span_to_exemplar(span: Optional[Span] = None) -> Dict[str, str]:
    """Convert span to Prometheus exemplar format.

    Args:
        span: Span to convert (uses current if None)

    Returns:
        Exemplar labels dict
    """
    if span is None:
        span = trace.get_current_span()

    if not span or not span.is_recording():
        return {}

    span_context = span.get_span_context()
    exemplar = {
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
    }

    # Add frame ID if available
    frame_id = get_frame_id()
    if frame_id:
        exemplar["frame_id"] = frame_id

    return exemplar


class FrameContextFilter(logging.Filter):
    """Logging filter to add frame context to standard logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add frame context to log record.

        Args:
            record: Log record to enhance

        Returns:
            True (always passes the record)
        """
        # Add trace context
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            setattr(record, "trace_id", format(span_context.trace_id, "032x"))
            setattr(record, "span_id", format(span_context.span_id, "016x"))
        else:
            setattr(record, "trace_id", "")
            setattr(record, "span_id", "")

        # Add frame context
        setattr(record, "frame_id", get_frame_id() or "")
        setattr(record, "camera_id", get_camera_id() or "")

        return True


def configure_stdlib_correlation() -> None:
    """Configure standard library logging with correlation."""
    # Create formatter with correlation fields
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - "
        "[trace_id=%(trace_id)s span_id=%(span_id)s "
        "frame_id=%(frame_id)s camera_id=%(camera_id)s] - "
        "%(message)s"
    )

    # Configure root logger
    root_logger = logging.getLogger()

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handler with correlation
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(FrameContextFilter())
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
