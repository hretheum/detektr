"""
Observability setup for frame buffer service.
"""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes

# Global tracer
tracer: Optional[trace.Tracer] = None


def init_telemetry(service_name: str) -> None:
    """Initialize OpenTelemetry instrumentation."""
    global tracer

    # Create resource
    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: "1.0.0",
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(processor)

    # Set global tracer provider
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(service_name)

    # Auto-instrument libraries
    FastAPIInstrumentor().instrument()
    RedisInstrumentor().instrument()

    print(f"✅ OpenTelemetry initialized for {service_name}")
    print(f"   Sending traces to: {otlp_endpoint}")


def get_tracer() -> Optional[trace.Tracer]:
    """Get the global tracer instance."""
    return tracer
