"""
Observability module for RTSP capture service.

Provides OpenTelemetry tracing and Prometheus metrics for monitoring
frame processing pipeline performance and reliability.
"""

import functools
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from prometheus_client import Counter, Gauge, Histogram

from .frame_buffer import CircularFrameBuffer


# Initialize tracer - will use global provider
def _get_tracer():
    """Get tracer from current provider."""
    return trace.get_tracer(__name__)


# Global tracer reference (updated when provider changes)
tracer = _get_tracer()

# Prometheus metrics - lazy initialization to avoid duplicates
_metrics_initialized = False
frame_counter = None
frame_processing_time = None
frame_drops_counter = None
active_connections_gauge = None
buffer_size_gauge = None
redis_queue_size_gauge = None


def _init_metrics_once():
    """Initialize metrics only once to avoid duplicates in tests."""
    global _metrics_initialized
    global frame_counter, frame_processing_time, frame_drops_counter
    global active_connections_gauge, buffer_size_gauge, redis_queue_size_gauge

    if _metrics_initialized:
        return

    try:
        frame_counter = Counter(
            "frames_processed_total",
            "Total number of frames processed",
            ["camera_id", "status"],
        )

        frame_processing_time = Histogram(
            "frame_processing_duration_seconds",
            "Time spent processing frames",
            ["camera_id", "operation"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )

        frame_drops_counter = Counter(
            "frame_drops_total",
            "Total number of dropped frames",
            ["camera_id", "reason"],
        )

        active_connections_gauge = Gauge(
            "active_rtsp_connections",
            "Number of active RTSP connections",
            ["camera_id"],
        )

        buffer_size_gauge = Gauge(
            "frame_buffer_size",
            "Current number of frames in buffer",
            ["camera_id"],
        )

        redis_queue_size_gauge = Gauge(
            "redis_queue_size",
            "Approximate size of Redis frame queue",
            ["stream_key"],
        )
    except ValueError as e:
        if "Duplicated timeseries" in str(e):
            # Metrics already exist in registry, get references
            from prometheus_client import REGISTRY

            # Find existing metrics by name
            for collector, names in REGISTRY._collector_to_names.items():
                if "frames_processed_total" in names:
                    frame_counter = collector
                elif "frame_processing_duration_seconds" in names:
                    frame_processing_time = collector
                elif "frame_drops_total" in names:
                    frame_drops_counter = collector
                elif "active_rtsp_connections" in names:
                    active_connections_gauge = collector
                elif "frame_buffer_size" in names:
                    buffer_size_gauge = collector
                elif "redis_queue_size" in names:
                    redis_queue_size_gauge = collector
        else:
            raise

    _metrics_initialized = True


# Don't initialize metrics on module load - wait for explicit init
# This prevents issues with duplicate metrics in tests
# _init_metrics_once()


def init_metrics():
    """Initialize and return Prometheus metrics (for testing)."""
    _init_metrics_once()
    return {
        "frame_counter": frame_counter,
        "frame_processing_time": frame_processing_time,
        "frame_drops_counter": frame_drops_counter,
        "active_connections_gauge": active_connections_gauge,
        "buffer_size_gauge": buffer_size_gauge,
        "redis_queue_size_gauge": redis_queue_size_gauge,
    }


def init_telemetry(
    service_name: str = "rtsp-capture",
    otlp_endpoint: Optional[str] = None,
    deployment_env: str = "production",
) -> TracerProvider:
    """
    Initialize OpenTelemetry with OTLP exporter.

    Args:
        service_name: Name of the service for tracing
        otlp_endpoint: OTLP collector endpoint (e.g., "localhost:4317")
        deployment_env: Deployment environment name

    Returns:
        Configured TracerProvider
    """
    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment": deployment_env,
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint provided
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # For development; use TLS in production
        )
        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument Redis automatically
    RedisInstrumentor().instrument()

    return provider


# Removed duplicate init_metrics() - using the one from line 96


@contextmanager
def create_frame_span(frame_id: str, camera_id: str):
    """
    Create a span for frame processing.

    Args:
        frame_id: Unique frame identifier
        camera_id: Camera identifier

    Yields:
        Span object for adding attributes and events
    """
    current_tracer = _get_tracer()
    with current_tracer.start_as_current_span(f"process_frame_{frame_id}") as span:
        span.set_attributes(
            {
                "frame.id": frame_id,
                "camera.id": camera_id,
                "service.name": "rtsp-capture",
            }
        )
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


@contextmanager
def create_operation_span(operation: str, parent_span: Optional[trace.Span] = None):
    """
    Create a span for a specific operation.

    Args:
        operation: Operation name (e.g., "decode", "buffer_put")
        parent_span: Optional parent span for context

    Yields:
        Span object
    """
    ctx = trace.set_span_in_context(parent_span) if parent_span else None
    current_tracer = _get_tracer()

    with current_tracer.start_as_current_span(operation, context=ctx) as span:
        span.set_attribute("operation.type", operation)
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


class TracedFrameBuffer(CircularFrameBuffer):
    """Frame buffer with automatic OpenTelemetry tracing."""

    def __init__(self, capacity: int, camera_id: str = "unknown"):
        """Initialize TracedFrameBuffer with capacity and camera ID."""
        super().__init__(capacity)
        self.camera_id = camera_id
        # Ensure metrics are initialized
        _init_metrics_once()

    def put(self, frame_id: str, frame_data: Any, timestamp: float) -> None:
        """Put frame with tracing."""
        with create_operation_span("buffer.put") as span:
            span.set_attributes(
                {
                    "frame.id": frame_id,
                    "buffer.capacity": self.capacity,
                    "buffer.size": self.size,
                    "camera.id": self.camera_id,
                }
            )

            # Call parent method
            super().put(frame_id, frame_data, timestamp)

            # Update metrics
            if buffer_size_gauge:
                buffer_size_gauge.labels(camera_id=self.camera_id).set(self.size)

            # Check if frame was dropped
            stats = self.get_statistics()
            if stats["total_frames_dropped"] > 0 and frame_drops_counter:
                frame_drops_counter.labels(
                    camera_id=self.camera_id, reason="buffer_full"
                ).inc()

    def get(self) -> tuple:
        """Get frame with tracing."""
        with create_operation_span("buffer.get") as span:
            span.set_attributes(
                {
                    "buffer.size": self.size,
                    "camera.id": self.camera_id,
                }
            )

            result = super().get()

            if result:
                frame_id, _, _ = result
                span.set_attribute("frame.id", frame_id)

            # Update metrics
            if buffer_size_gauge:
                buffer_size_gauge.labels(camera_id=self.camera_id).set(self.size)

            return result


class TracedRedisQueue:
    """Redis queue wrapper with tracing."""

    def __init__(self, redis_queue):
        """Initialize TracedRedisQueue with underlying queue."""
        self.queue = redis_queue

    async def publish_with_trace(
        self, metadata: Dict[str, Any], parent_span: Optional[trace.Span] = None
    ) -> str:
        """Publish to Redis with tracing."""
        ctx = trace.set_span_in_context(parent_span) if parent_span else None

        current_tracer = _get_tracer()
        with current_tracer.start_as_current_span("redis.publish", context=ctx) as span:
            span.set_attributes(
                {
                    "redis.stream": self.queue.stream_key,
                    "frame.id": metadata.get("frame_id", "unknown"),
                }
            )

            start_time = time.time()
            message_id = await self.queue.publish(metadata)
            publish_time = time.time() - start_time

            span.set_attribute("redis.message_id", message_id)
            span.set_attribute("publish.duration_ms", publish_time * 1000)

            # Update metrics
            if frame_processing_time:
                frame_processing_time.labels(
                    camera_id=metadata.get("camera_id", "unknown"), operation="publish"
                ).observe(publish_time)

            return message_id


def get_metrics_labels(camera_id: str, operation: str) -> Dict[str, str]:
    """
    Sanitize and validate metric labels to prevent cardinality explosion.

    Args:
        camera_id: Camera identifier
        operation: Operation type

    Returns:
        Sanitized labels dictionary
    """
    # Limit camera_id length
    if len(camera_id) > 50:
        camera_id = camera_id[:50]

    # Whitelist allowed operations
    allowed_operations = {"decode", "buffer", "publish", "end_to_end"}
    if operation not in allowed_operations:
        operation = "other"

    return {"camera_id": camera_id, "operation": operation}


def async_timed_operation(operation: str, camera_id: str):
    """
    Time async operations with Prometheus metrics.

    Args:
        operation: Operation name for metrics
        camera_id: Camera identifier
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Ensure metrics are initialized
            _init_metrics_once()

            labels = get_metrics_labels(camera_id, operation)

            if frame_processing_time:
                with frame_processing_time.labels(**labels).time():
                    return await func(*args, **kwargs)
            else:
                # Metrics not available, just run the function
                return await func(*args, **kwargs)

        return wrapper

    return decorator


class ObservabilityMiddleware:
    """
    ASGI middleware for HTTP endpoints with automatic tracing.

    Can be used with FastAPI for health/metrics endpoints.
    """

    def __init__(self, app):
        """Initialize middleware with ASGI app."""
        self.app = app

    async def __call__(self, scope, receive, send):
        """Handle ASGI requests with automatic tracing."""
        if scope["type"] == "http":
            current_tracer = _get_tracer()
            with current_tracer.start_as_current_span(
                f"{scope['method']} {scope['path']}"
            ) as span:
                span.set_attributes(
                    {
                        "http.method": scope["method"],
                        "http.url": scope["path"],
                        "http.scheme": scope["scheme"],
                    }
                )

                try:
                    await self.app(scope, receive, send)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR))
                    raise
        else:
            await self.app(scope, receive, send)
