"""Telemetry configuration for GPU Demo service.

Provides OpenTelemetry tracing, Prometheus metrics, and structured logging.
"""

import os
import time
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Optional

import structlog
from fastapi import Request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Gauge, Histogram, Info

# Service metadata
SERVICE_NAME = os.getenv("SERVICE_NAME", "gpu-demo")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")

# Context variable for correlation ID
correlation_id_context: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Prometheus metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
)

http_requests_active = Gauge(
    "http_requests_active",
    "Active HTTP requests",
    ["method", "endpoint"],
)

# GPU-specific metrics
gpu_inference_total = Counter(
    "gpu_inference_total",
    "Total GPU inference operations",
    ["device", "status"],
)

gpu_inference_duration = Histogram(
    "gpu_inference_duration_seconds",
    "GPU inference duration",
    ["device"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

gpu_memory_usage_bytes = Gauge(
    "gpu_memory_usage_bytes",
    "Current GPU memory usage",
    ["device_id"],
)

gpu_temperature_celsius = Gauge(
    "gpu_temperature_celsius",
    "GPU temperature in Celsius",
    ["device_id"],
)

model_load_duration = Histogram(
    "model_load_duration_seconds",
    "Time to load ML model",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# Service info
service_info = Info("service_info", "Service metadata")
service_info.info(
    {
        "service_name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
    }
)


def init_telemetry():
    """Initialize OpenTelemetry tracing."""
    # Create resource
    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": SERVICE_VERSION,
            "deployment.environment": os.getenv("ENV", "production"),
        }
    )

    # Configure tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint is configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Get tracer
    return trace.get_tracer(__name__)


def get_or_create_correlation_id() -> str:
    """Get existing or create new correlation ID."""
    correlation_id = correlation_id_context.get()
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
        correlation_id_context.set(correlation_id)
    return correlation_id


def traced(span_name: str):
    """Add tracing to functions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name) as span:
                # Add correlation ID to span
                correlation_id = get_or_create_correlation_id()
                span.set_attribute("correlation_id", correlation_id)

                # Add function arguments as span attributes
                span.set_attribute("function.name", func.__name__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name) as span:
                # Add correlation ID to span
                correlation_id = get_or_create_correlation_id()
                span.set_attribute("correlation_id", correlation_id)

                # Add function arguments as span attributes
                span.set_attribute("function.name", func.__name__)

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class ObservabilityMiddleware:
    """Middleware for correlation ID propagation and logging."""

    async def __call__(self, request: Request, call_next):
        """Process request with correlation ID."""
        # Extract or create correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        correlation_id_context.set(correlation_id)

        # Add to structlog context
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            path=request.url.path,
            method=request.method,
        )

        # Process request
        response = await call_next(request)

        # Add correlation ID to response
        response.headers["X-Correlation-ID"] = correlation_id

        return response


async def track_metrics_middleware(request: Request, call_next):
    """Middleware for tracking HTTP metrics."""
    start_time = time.time()

    # Track active requests
    http_requests_active.labels(method=request.method, endpoint=request.url.path).inc()

    try:
        response = await call_next(request)

        # Track request metrics
        duration = time.time() - start_time
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method, endpoint=request.url.path
        ).observe(duration)

        return response
    finally:
        http_requests_active.labels(
            method=request.method, endpoint=request.url.path
        ).dec()


def update_gpu_metrics():
    """Update GPU metrics (call periodically)."""
    try:
        import torch

        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                # Memory usage
                memory_allocated = torch.cuda.memory_allocated(i)
                gpu_memory_usage_bytes.labels(device_id=str(i)).set(memory_allocated)

                # Temperature (if nvidia-ml-py is available)
                try:
                    import pynvml

                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    temp = pynvml.nvmlDeviceGetTemperature(
                        handle, pynvml.NVML_TEMPERATURE_GPU
                    )
                    gpu_temperature_celsius.labels(device_id=str(i)).set(temp)
                except ImportError:
                    pass  # nvidia-ml-py not installed
                except Exception:
                    pass  # NVML not available

    except Exception as e:
        structlog.get_logger().error("gpu_metrics_update_failed", error=str(e))
