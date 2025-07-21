"""
Main entry point for RTSP capture service.

Provides a FastAPI application with health checks and metrics endpoints.
"""

import os
import time

from fastapi import FastAPI
from health import health_router, update_health_state
from observability import init_telemetry

# Create FastAPI app
app = FastAPI(
    title="RTSP Capture Service",
    description="Service for capturing RTSP streams with observability",
    version="1.0.0",
)

# Include health router
app.include_router(health_router)

# Initialize telemetry
init_telemetry(
    service_name="rtsp-capture",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT", "localhost:4317"),
    deployment_env=os.getenv("DEPLOYMENT_ENV", "development"),
)

# Initialize service state
update_health_state("start_time", time.time())
update_health_state("redis_connected", False)  # Will be updated when Redis connects


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    print("RTSP Capture Service starting up...")
    # TODO: Initialize Redis connection
    # TODO: Start RTSP connections based on config


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("RTSP Capture Service shutting down...")
    # TODO: Close RTSP connections
    # TODO: Close Redis connection


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "rtsp-capture", "version": "1.0.0", "status": "operational"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")), access_log=True
    )
