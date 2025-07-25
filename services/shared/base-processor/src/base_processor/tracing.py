"""OpenTelemetry tracing integration for processors."""
import asyncio
import functools
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.utils import http_status_to_status_code
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode


class TracingMixin:
    """Mixin to add automatic tracing to processors."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracer = trace.get_tracer(
            self.__class__.__module__, self.__class__.__name__
        )

    def traced_method(
        self,
        span_name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        record_exception: bool = True,
    ):
        """Decorator to add tracing to methods.

        Args:
            span_name: Custom span name, defaults to method name
            attributes: Additional span attributes
            record_exception: Whether to record exceptions
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                name = span_name or f"{self.__class__.__name__}.{func.__name__}"

                with self.tracer.start_as_current_span(name) as span:
                    # Add default attributes
                    span.set_attribute("processor.name", self.name)
                    span.set_attribute("processor.method", func.__name__)

                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                    try:
                        # Execute the method
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result

                    except Exception as e:
                        if record_exception:
                            span.record_exception(e)
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                name = span_name or f"{self.__class__.__name__}.{func.__name__}"

                with self.tracer.start_as_current_span(name) as span:
                    # Add default attributes
                    span.set_attribute("processor.name", self.name)
                    span.set_attribute("processor.method", func.__name__)

                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                    try:
                        # Execute the method
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result

                    except Exception as e:
                        if record_exception:
                            span.record_exception(e)
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator


def setup_tracing(
    service_name: str,
    otlp_endpoint: Optional[str] = None,
    resource_attributes: Optional[Dict[str, str]] = None,
) -> TracerProvider:
    """Setup OpenTelemetry tracing with OTLP exporter.

    Args:
        service_name: Name of the service
        otlp_endpoint: OTLP endpoint URL
        resource_attributes: Additional resource attributes

    Returns:
        Configured TracerProvider
    """
    # Create resource
    attributes = {
        "service.name": service_name,
        "service.version": "1.0.0",
    }
    if resource_attributes:
        attributes.update(resource_attributes)

    resource = Resource.create(attributes)

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter if endpoint provided
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)

        # Add batch processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)

    # Set as global provider
    trace.set_tracer_provider(provider)

    return provider


class ProcessorSpan:
    """Context manager for processor-specific spans."""

    def __init__(
        self,
        tracer: trace.Tracer,
        name: str,
        processor_name: str,
        frame_id: Optional[str] = None,
    ):
        self.tracer = tracer
        self.name = name
        self.processor_name = processor_name
        self.frame_id = frame_id
        self.span: Optional[Span] = None

    def __enter__(self) -> Span:
        """Enter span context."""
        self.span = self.tracer.start_span(self.name)
        self.span.set_attribute("processor.name", self.processor_name)

        if self.frame_id:
            self.span.set_attribute("frame.id", self.frame_id)

        # Make span current
        self.token = trace.use_span(self.span, end_on_exit=False)
        self.token.__enter__()

        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit span context."""
        if self.span:
            if exc_type is not None:
                self.span.record_exception(exc_val)
                self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            else:
                self.span.set_status(Status(StatusCode.OK))

            # Exit token context
            self.token.__exit__(exc_type, exc_val, exc_tb)

            # End span
            self.span.end()


def extract_trace_context(metadata: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Extract trace context from metadata.

    Args:
        metadata: Frame metadata that may contain trace context

    Returns:
        Trace context dictionary or None
    """
    trace_context = {}

    # Look for standard trace headers
    for key in ["traceparent", "tracestate"]:
        if key in metadata:
            trace_context[key] = metadata[key]

    return trace_context if trace_context else None


def inject_trace_context(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Inject current trace context into metadata.

    Args:
        metadata: Frame metadata to inject context into

    Returns:
        Updated metadata with trace context
    """
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        span_context = current_span.get_span_context()

        # Format traceparent header
        metadata[
            "traceparent"
        ] = f"00-{format(span_context.trace_id, '032x')}-{format(span_context.span_id, '016x')}-{'01' if span_context.trace_flags else '00'}"

        # Add tracestate if present
        if span_context.trace_state:
            metadata["tracestate"] = str(span_context.trace_state)

    return metadata
