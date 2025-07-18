"""
OpenTelemetry configuration module.

Provides centralized setup for traces, metrics, and logs with support for
Jaeger and Prometheus exporters.
"""

import os
from typing import Callable

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(
    service_name: str, service_version: str = "1.0.0"
) -> Callable[[], None]:
    """Set up OpenTelemetry for traces and metrics.

    Args:
        service_name: Name of the service
        service_version: Version of the service

    Returns:
        Shutdown function to clean up telemetry
    """
    # Create resource identifying this service
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
        }
    )

    # Setup tracing
    tracer_provider = TracerProvider(resource=resource)

    # Configure OTLP exporter for Jaeger if enabled
    if os.getenv("OTEL_TRACES_EXPORTER", "otlp") == "otlp":
        otlp_exporter = OTLPSpanExporter(
            endpoint=os.getenv(
                "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://localhost:4318/v1/traces"
            ),
        )
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer(service_name)

    # Setup metrics
    readers = []

    # Add Prometheus exporter if enabled
    if os.getenv("OTEL_METRICS_EXPORTER", "prometheus") == "prometheus":
        prometheus_reader = PrometheusMetricReader()
        readers.append(prometheus_reader)

    meter_provider = MeterProvider(resource=resource, metric_readers=readers)
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter(service_name)
    
    def shutdown():
        """Shutdown telemetry providers."""
        # Shutdown span processors
        if hasattr(tracer_provider, 'shutdown'):
            tracer_provider.shutdown()
        
        # Shutdown metric readers  
        if hasattr(meter_provider, 'shutdown'):
            meter_provider.shutdown()
    
    return shutdown
