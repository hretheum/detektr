"""Example FastAPI application with OpenTelemetry instrumentation."""

import os
import sys
import time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.shared.telemetry import (  # noqa: E402
    instrument_app,
    setup_auto_instrumentation,
    setup_telemetry,
)

# Setup telemetry first
tracer, meter, _ = setup_telemetry("fastapi-example", "0.1.0")

# Enable auto-instrumentation
setup_auto_instrumentation()

# Create FastAPI app
app = FastAPI(title="Telemetry Example API")

# Instrument the app
instrument_app(app)

# Create metrics
request_counter = meter.create_counter(
    name="http_requests_total",
    description="Total number of HTTP requests",
    unit="request",
)

request_duration = meter.create_histogram(
    name="http_request_duration_seconds",
    description="HTTP request duration",
    unit="s",
)


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/frames/{frame_id}")
async def get_frame(frame_id: str) -> Dict[str, Any]:
    """Get frame details with tracing."""
    with tracer.start_as_current_span("get_frame_details") as span:
        span.set_attribute("frame.id", frame_id)

        # Record metrics
        request_counter.add(1, {"endpoint": "/api/frames", "method": "GET"})

        # Simulate processing
        start_time = time.time()
        time.sleep(0.05)  # 50ms

        duration = time.time() - start_time
        request_duration.record(duration, {"endpoint": "/api/frames"})

        # Simulate not found
        if frame_id == "not-found":
            span.set_attribute("error", True)
            span.set_attribute("error.type", "NotFound")
            raise HTTPException(status_code=404, detail="Frame not found")

        return {
            "frame_id": frame_id,
            "size": 1920 * 1080,
            "format": "RGB",
            "timestamp": time.time(),
        }


@app.post("/api/frames")
async def create_frame(data: Dict[str, Any]) -> Dict[str, str]:
    """Create new frame with nested spans."""
    with tracer.start_as_current_span("create_frame") as span:
        span.set_attribute("frame.source", data.get("source", "unknown"))

        # Validation span
        with tracer.start_as_current_span("validate_frame_data"):
            time.sleep(0.01)  # 10ms

        # Storage span
        with tracer.start_as_current_span("store_frame") as storage_span:
            storage_span.set_attribute("storage.backend", "redis")
            time.sleep(0.02)  # 20ms

        # Notification span
        with tracer.start_as_current_span("send_notification"):
            time.sleep(0.01)  # 10ms

        return {"frame_id": "frame_123", "status": "created"}


if __name__ == "__main__":
    import uvicorn

    print("Starting FastAPI with OpenTelemetry instrumentation...")
    print("API docs: http://localhost:8000/docs")
    print("Traces will be sent to Jaeger")

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
