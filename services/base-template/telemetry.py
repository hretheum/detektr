"""Telemetry configuration for observability."""

import os
import time
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Callable, Optional

import structlog
from fastapi import Request
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Gauge, Histogram

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[uuid.UUID]] = ContextVar(
    "correlation_id", default=None
)

# Service info
SERVICE_NAME = os.getenv("SERVICE_NAME", "base-template")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")

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

active_requests = Gauge(
    "http_requests_active",
    "Active HTTP requests",
    ["method", "endpoint"],
)

business_operations_total = Counter(
    "business_operations_total",
    "Total business operations",
    ["operation", "status"],
)

database_operations_total = Counter(
    "database_operations_total",
    "Total database operations",
    ["operation", "status"],
)

database_operation_duration_seconds = Histogram(
    "database_operation_duration_seconds",
    "Database operation duration",
    ["operation"],
)


def init_telemetry():
    """Initialize OpenTelemetry with OTLP exporters."""
    # Resource
    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": SERVICE_VERSION,
            "service.instance.id": os.getenv(
                "HOSTNAME", f"{SERVICE_NAME}-{uuid.uuid4().hex[:8]}"
            ),
        }
    )

    # Setup tracing
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"),
        insecure=True,
    )
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Setup metrics
    prometheus_reader = PrometheusMetricReader()
    metric_provider = MeterProvider(
        resource=resource,
        metric_readers=[prometheus_reader],
    )
    metrics.set_meter_provider(metric_provider)

    # Auto-instrumentation
    FastAPIInstrumentor().instrument(tracer_provider=tracer_provider)

    # Instrument SQLAlchemy
    from database import engine

    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine,
        service=SERVICE_NAME,
    )

    # Setup structured logging
    setup_structured_logging()


def setup_structured_logging():
    """Configure structured logging with correlation ID."""

    def add_correlation_id(logger, method_name, event_dict):
        """Add correlation ID to all log entries."""
        correlation_id = correlation_id_var.get()
        if correlation_id:
            event_dict["correlation_id"] = str(correlation_id)
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


def get_or_create_correlation_id() -> uuid.UUID:
    """Get existing correlation ID or create a new one."""
    correlation_id = correlation_id_var.get()
    if not correlation_id:
        correlation_id = uuid.uuid4()
        correlation_id_var.set(correlation_id)
    return correlation_id


def traced(name: Optional[str] = None):
    """Add tracing to functions via decorator."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(SERVICE_NAME)
            span_name = name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(span_name) as span:
                # Add correlation ID
                correlation_id = get_or_create_correlation_id()
                span.set_attribute("correlation_id", str(correlation_id))

                # Add function arguments as attributes
                if args:
                    for i, arg in enumerate(args[:3]):  # Limit to first 3
                        span.set_attribute(f"arg.{i}", str(arg))

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return async_wrapper

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
            correlation_id_header = headers.get(b"x-correlation-id", b"").decode()
            correlation_id = (
                uuid.UUID(correlation_id_header)
                if correlation_id_header
                else uuid.uuid4()
            )
            correlation_id_var.set(correlation_id)

            # Log request
            self.logger.info(
                "request_started",
                method=scope["method"],
                path=scope["path"],
                correlation_id=str(correlation_id),
            )

            # Propagate correlation ID in response
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"x-correlation-id", str(correlation_id).encode()))
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


async def track_metrics_middleware(request: Request, call_next):
    """Track HTTP metrics for all requests."""
    if request.url.path == "/metrics":
        # Skip metrics endpoint
        return await call_next(request)

    # Record active requests
    labels = {"method": request.method, "endpoint": request.url.path}
    active_requests.labels(**labels).inc()

    start_time = time.time()
    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        http_request_duration_seconds.labels(**labels).observe(duration)

        return response
    finally:
        active_requests.labels(**labels).dec()
