"""Trace context management for frame tracking."""

import contextvars
from contextlib import contextmanager
from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from .metadata import FrameMetadata

# Context variable to store current trace context
_trace_context_var: contextvars.ContextVar[
    Optional["TraceContext"]
] = contextvars.ContextVar("trace_context", default=None)


class TraceContext:
    """Manages trace context for frame processing."""

    def __init__(self, frame_id: str, trace_id: str, span_id: str, span: Any):
        """
        Initialize trace context.

        Args:
            frame_id: Frame identifier
            trace_id: Trace ID from OpenTelemetry
            span_id: Span ID from OpenTelemetry
            span: Current span object
        """
        self.frame_id = frame_id
        self.trace_id = trace_id
        self.span_id = span_id
        self._span = span
        self._propagator = TraceContextTextMapPropagator()

    @classmethod
    @contextmanager
    def inject(cls, frame_id: str, metadata: Optional[FrameMetadata] = None):
        """
        Inject trace context for frame processing.

        Args:
            frame_id: Frame identifier
            metadata: Optional frame metadata to enrich

        Yields:
            TraceContext instance
        """
        tracer = trace.get_tracer("frame-tracking")

        # Start root span for frame
        with tracer.start_as_current_span(
            "frame.process", attributes={"frame.id": frame_id}
        ) as span:
            # Get span context
            span_context = span.get_span_context()
            trace_id = format(span_context.trace_id, "032x")
            span_id = format(span_context.span_id, "016x")

            # Create context
            ctx = cls(frame_id, trace_id, span_id, span)

            # Add metadata attributes if provided
            if metadata:
                span.set_attributes(metadata.to_trace_attributes())
                ctx.apply_to_metadata(metadata)

            # Set in context var
            token = _trace_context_var.set(ctx)

            try:
                yield ctx
            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            finally:
                # Reset context
                _trace_context_var.reset(token)

    def apply_to_metadata(self, metadata: FrameMetadata):
        """Apply trace context to frame metadata."""
        metadata.trace_id = self.trace_id
        metadata.span_id = self.span_id

        # Get parent span if in nested context
        parent_context = trace.get_current_span().parent
        if parent_context:
            metadata.parent_span_id = format(parent_context.span_id, "016x")

    @contextmanager
    def span(self, name: str, **attributes):
        """
        Create a child span within current trace.

        Args:
            name: Span name
            **attributes: Span attributes

        Yields:
            Span object
        """
        tracer = trace.get_tracer("frame-tracking")

        # Add frame ID to attributes
        attributes["frame.id"] = self.frame_id

        with tracer.start_as_current_span(name, attributes=attributes) as span:
            yield span

    def inject_to_carrier(self, carrier: Dict[str, str]):
        """
        Inject trace context into carrier for propagation.

        Args:
            carrier: Dictionary to inject context into
        """
        self._propagator.inject(carrier)

    @classmethod
    def extract_from_carrier(cls, carrier: Dict[str, str]) -> Optional[Any]:
        """
        Extract trace context from carrier.

        Args:
            carrier: Dictionary containing trace context

        Returns:
            Extracted context or None
        """
        propagator = TraceContextTextMapPropagator()
        return propagator.extract(carrier)

    @classmethod
    def get_current(cls) -> Optional["TraceContext"]:
        """Get current trace context from context var."""
        return _trace_context_var.get()

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to current span."""
        if self._span:
            self._span.add_event(name, attributes or {})

    def set_attribute(self, key: str, value: Any):
        """Set attribute on current span."""
        if self._span:
            self._span.set_attribute(key, value)
