"""
OpenTelemetry configuration and utilities.

Provides automatic instrumentation, decorators, and correlation ID propagation.
"""

import os
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Callable, Optional

import structlog
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)

# Service resource
service_name = os.getenv("SERVICE_NAME", "example-otel")
service_version = os.getenv("SERVICE_VERSION", "0.1.0")

resource = Resource.create(
    {
        "service.name": service_name,
        "service.version": service_version,
        "service.instance.id": os.getenv(
            "HOSTNAME", f"{service_name}-{uuid.uuid4().hex[:8]}"
        ),
    }
)


def setup_telemetry():
    """Initialize OpenTelemetry with OTLP exporters and Prometheus metrics."""
    # Setup tracing
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # OTLP exporter for Jaeger
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"),
        insecure=True,
    )
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Setup metrics with Prometheus
    prometheus_reader = PrometheusMetricReader()
    metric_provider = MeterProvider(
        resource=resource,
        metric_readers=[prometheus_reader],
    )
    metrics.set_meter_provider(metric_provider)

    # Auto-instrumentation
    FastAPIInstrumentor().instrument(tracer_provider=tracer_provider)
    RequestsInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=True)

    # Setup structured logging
    setup_structured_logging()

    return trace.get_tracer(service_name), metrics.get_meter(service_name)


def setup_structured_logging():
    """Configure structured logging with correlation ID."""

    def add_correlation_id(logger, method_name, event_dict):
        """Add correlation ID to all log entries."""
        correlation_id = correlation_id_var.get()
        if correlation_id:
            event_dict["correlation_id"] = correlation_id
        return event_dict

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
            add_correlation_id,
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_or_create_correlation_id() -> str:
    """Get existing correlation ID or create a new one."""
    correlation_id = correlation_id_var.get()
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
        correlation_id_var.set(correlation_id)
    return correlation_id


def traced(name: Optional[str] = None):
    """Add tracing to functions via decorator."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(service_name)
            span_name = name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(span_name) as span:
                # Add correlation ID to span
                correlation_id = get_or_create_correlation_id()
                span.set_attribute("correlation_id", correlation_id)

                # Add function arguments as span attributes
                if args:
                    for i, arg in enumerate(args[:3]):  # Limit to first 3 args
                        span.set_attribute(f"arg.{i}", str(arg))
                for k, v in list(kwargs.items())[:5]:  # Limit to first 5 kwargs
                    span.set_attribute(f"kwarg.{k}", str(v))

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(service_name)
            span_name = name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(span_name) as span:
                # Add correlation ID to span
                correlation_id = get_or_create_correlation_id()
                span.set_attribute("correlation_id", correlation_id)

                # Add function arguments as span attributes
                if args:
                    for i, arg in enumerate(args[:3]):  # Limit to first 3 args
                        span.set_attribute(f"arg.{i}", str(arg))
                for k, v in list(kwargs.items())[:5]:  # Limit to first 5 kwargs
                    span.set_attribute(f"kwarg.{k}", str(v))

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
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
    """Middleware to propagate correlation IDs and trace context."""

    def __init__(self, app):
        """Initialize observability middleware."""
        self.app = app
        self.logger = structlog.get_logger()

    async def __call__(self, scope, receive, send):
        """Handle HTTP requests with observability features."""
        if scope["type"] == "http":
            # Extract or create correlation ID
            headers = dict(scope.get("headers", []))
            correlation_id = headers.get(b"x-correlation-id", b"").decode() or str(
                uuid.uuid4()
            )
            correlation_id_var.set(correlation_id)

            # Log request
            self.logger.info(
                "request_started",
                method=scope["method"],
                path=scope["path"],
                correlation_id=correlation_id,
            )

            # Propagate correlation ID in response
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"x-correlation-id", correlation_id.encode()))
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


# Metrics for the example service
request_counter = None
request_duration = None
active_requests = None


def init_metrics(meter):
    """Initialize application metrics."""
    global request_counter, request_duration, active_requests

    request_counter = meter.create_counter(
        name="http_requests_total",
        description="Total number of HTTP requests",
        unit="1",
    )

    request_duration = meter.create_histogram(
        name="http_request_duration_seconds",
        description="HTTP request duration",
        unit="s",
    )

    active_requests = meter.create_up_down_counter(
        name="http_requests_active",
        description="Number of active HTTP requests",
        unit="1",
    )
