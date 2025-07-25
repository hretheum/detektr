"""
Main entry point for RTSP capture service.

Provides a FastAPI application with health checks and metrics endpoints.
"""

import os
import time

import redis.asyncio as redis
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

# Global Redis client
redis_client = None


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    global redis_client
    print("RTSP Capture Service starting up...")

    # Initialize Redis connection
    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_client = redis.Redis(
            host=redis_host, port=redis_port, decode_responses=True
        )
        await redis_client.ping()
        update_health_state("redis_connected", True)
        print(f"Connected to Redis at {redis_host}:{redis_port}")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        update_health_state("redis_connected", False)

    # TODO: Start RTSP connections based on config


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global redis_client
    print("RTSP Capture Service shutting down...")

    # Close Redis connection
    if redis_client:
        await redis_client.close()
        print("Redis connection closed")

    # TODO: Close RTSP connections


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "rtsp-capture", "version": "1.0.0", "status": "operational"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")), access_log=True
    )
