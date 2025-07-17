"""OpenTelemetry metrics helpers for easy custom metrics creation.

Provides simple interfaces for common metric types used in detektor.
"""

from typing import Any, Dict, Optional

from opentelemetry import metrics, trace
from opentelemetry.metrics import Counter, Histogram, UpDownCounter
from opentelemetry.trace import format_span_id, format_trace_id


class DetektorMetrics:
    """Helper class for creating and managing detektor-specific metrics."""

    def __init__(self, service_name: str):
        """Initialize metrics for a service.

        Args:
            service_name: Name of the service (used as prefix for metrics)
        """
        self.service_name = service_name
        self.meter = metrics.get_meter(__name__)

        # Cache for created metrics to avoid recreation
        self._counters: Dict[str, Counter] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._updown_counters: Dict[str, UpDownCounter] = {}

    def _get_trace_attributes(self) -> Dict[str, Any]:
        """Get current trace context attributes for exemplar support.

        Returns:
            Dict with trace_id and span_id if available
        """
        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            if ctx.is_valid:
                return {
                    "trace_id": format_trace_id(ctx.trace_id),
                    "span_id": format_span_id(ctx.span_id),
                }
        return {}

    def _add_trace_attributes(
        self, attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add trace attributes to provided attributes for exemplar support.

        Args:
            attributes: Existing attributes

        Returns:
            Combined attributes with trace context
        """
        trace_attrs = self._get_trace_attributes()
        if attributes:
            return {**attributes, **trace_attrs}
        return trace_attrs

    def get_counter(self, name: str, description: str = "", unit: str = "1") -> Counter:
        """Get or create a counter metric.

        Args:
            name: Metric name (will be prefixed with service name)
            description: Human-readable description
            unit: Unit of measurement

        Returns:
            Counter metric instance
        """
        full_name = f"detektor_{self.service_name}_{name}"

        if full_name not in self._counters:
            self._counters[full_name] = self.meter.create_counter(
                name=full_name,
                description=description or f"{name} counter for {self.service_name}",
                unit=unit,
            )

        return self._counters[full_name]

    def get_histogram(
        self, name: str, description: str = "", unit: str = "1"
    ) -> Histogram:
        """Get or create a histogram metric.

        Args:
            name: Metric name (will be prefixed with service name)
            description: Human-readable description
            unit: Unit of measurement

        Returns:
            Histogram metric instance
        """
        full_name = f"detektor_{self.service_name}_{name}"

        if full_name not in self._histograms:
            self._histograms[full_name] = self.meter.create_histogram(
                name=full_name,
                description=description or f"{name} histogram for {self.service_name}",
                unit=unit,
            )

        return self._histograms[full_name]

    def get_updown_counter(
        self, name: str, description: str = "", unit: str = "1"
    ) -> UpDownCounter:
        """Get or create an up-down counter metric.

        Args:
            name: Metric name (will be prefixed with service name)
            description: Human-readable description
            unit: Unit of measurement

        Returns:
            UpDownCounter metric instance
        """
        full_name = f"detektor_{self.service_name}_{name}"

        if full_name not in self._updown_counters:
            self._updown_counters[full_name] = self.meter.create_up_down_counter(
                name=full_name,
                description=description
                or f"{name} up-down counter for {self.service_name}",
                unit=unit,
            )

        return self._updown_counters[full_name]

    # Convenience methods for common detektor metrics

    def increment_frames_processed(
        self, count: int = 1, attributes: Optional[Dict[str, Any]] = None
    ):
        """Increment frames processed counter."""
        counter = self.get_counter("frames_processed", "Total frames processed")
        attrs = self._add_trace_attributes(attributes)
        counter.add(count, attrs)

    def increment_detections(
        self,
        detection_type: str,
        count: int = 1,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Increment detection counter for specific type."""
        counter = self.get_counter("detections_total", "Total detections by type")
        attrs = {"detection_type": detection_type}
        if attributes:
            attrs.update(attributes)
        attrs = self._add_trace_attributes(attrs)
        counter.add(count, attrs)

    def record_processing_time(
        self, stage: str, duration: float, attributes: Optional[Dict[str, Any]] = None
    ):
        """Record processing time for a stage."""
        histogram = self.get_histogram(
            "processing_duration_seconds", "Processing duration by stage", "s"
        )
        attrs = {"stage": stage}
        if attributes:
            attrs.update(attributes)
        attrs = self._add_trace_attributes(attrs)
        histogram.record(duration, attrs)

    def record_frame_size(
        self, width: int, height: int, attributes: Optional[Dict[str, Any]] = None
    ):
        """Record frame size as histogram."""
        histogram = self.get_histogram(
            "frame_size_pixels", "Frame size in pixels", "pixel"
        )
        attrs = {"dimension": "area"}
        if attributes:
            attrs.update(attributes)
        attrs = self._add_trace_attributes(attrs)
        histogram.record(width * height, attrs)

    def set_active_cameras(
        self, count: int, attributes: Optional[Dict[str, Any]] = None
    ):
        """Set number of active cameras."""
        counter = self.get_updown_counter("active_cameras", "Number of active cameras")
        # For UpDownCounter, we need to track the delta
        # In a real implementation, you'd track the previous value
        attrs = self._add_trace_attributes(attributes)
        counter.add(count, attrs)

    def increment_errors(
        self, error_type: str, attributes: Optional[Dict[str, Any]] = None
    ):
        """Increment error counter."""
        counter = self.get_counter("errors_total", "Total errors by type")
        attrs = {"error_type": error_type}
        if attributes:
            attrs.update(attributes)
        attrs = self._add_trace_attributes(attrs)
        counter.add(1, attrs)

    def record_queue_size(
        self, queue_name: str, size: int, attributes: Optional[Dict[str, Any]] = None
    ):
        """Record queue size."""
        histogram = self.get_histogram("queue_size", "Queue size by name", "items")
        attrs = {"queue_name": queue_name}
        if attributes:
            attrs.update(attributes)
        attrs = self._add_trace_attributes(attrs)
        histogram.record(size, attrs)

    def record_memory_usage(
        self, memory_mb: float, attributes: Optional[Dict[str, Any]] = None
    ):
        """Record memory usage."""
        histogram = self.get_histogram("memory_usage_mb", "Memory usage in MB", "MB")
        attrs = self._add_trace_attributes(attributes)
        histogram.record(memory_mb, attrs)

    def record_gpu_utilization(
        self,
        utilization_percent: float,
        gpu_id: str = "0",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Record GPU utilization."""
        histogram = self.get_histogram(
            "gpu_utilization_percent", "GPU utilization percentage", "%"
        )
        attrs = {"gpu_id": gpu_id}
        if attributes:
            attrs.update(attributes)
        attrs = self._add_trace_attributes(attrs)
        histogram.record(utilization_percent, attrs)


# Global metrics instances for common services
_metrics_instances: Dict[str, DetektorMetrics] = {}


def get_metrics(service_name: str) -> DetektorMetrics:
    """Get metrics instance for a service.

    Args:
        service_name: Name of the service

    Returns:
        DetektorMetrics instance for the service
    """
    if service_name not in _metrics_instances:
        _metrics_instances[service_name] = DetektorMetrics(service_name)

    return _metrics_instances[service_name]


# Convenience functions for common metrics
def increment_frames_processed(service_name: str, count: int = 1, **attributes):
    """Convenience function to increment frames processed."""
    get_metrics(service_name).increment_frames_processed(count, attributes)


def increment_detections(
    service_name: str, detection_type: str, count: int = 1, **attributes
):
    """Convenience function to increment detections."""
    get_metrics(service_name).increment_detections(detection_type, count, attributes)


def record_processing_time(
    service_name: str, stage: str, duration: float, **attributes
):
    """Convenience function to record processing time."""
    get_metrics(service_name).record_processing_time(stage, duration, attributes)


def increment_errors(service_name: str, error_type: str, **attributes):
    """Convenience function to increment errors."""
    get_metrics(service_name).increment_errors(error_type, attributes)
