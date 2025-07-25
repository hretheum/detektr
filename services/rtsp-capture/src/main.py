"""
Main entry point for RTSP capture service.

Provides a FastAPI application with health checks and metrics endpoints.
"""

import asyncio
import os
import time
from typing import Dict

import redis.asyncio as redis
from fastapi import FastAPI
from frame_capture import RTSPCapture
from health import health_router, update_health_state
from observability import init_telemetry
from redis_queue import RedisFrameQueue

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

# Global instances
redis_client = None
redis_queue = None
capture_instances: Dict[str, RTSPCapture] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    global redis_client, redis_queue, capture_instances
    print("RTSP Capture Service starting up...")

    # Initialize Redis connection
    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_client = redis.Redis(
            host=redis_host, port=redis_port, decode_responses=False
        )
        await redis_client.ping()
        update_health_state("redis_connected", True)
        print(f"Connected to Redis at {redis_host}:{redis_port}")

        # Initialize Redis queue
        redis_queue = RedisFrameQueue(redis_client)

        # Create consumer group for downstream services
        await redis_queue.create_consumer_group("frame-processors")

    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        update_health_state("redis_connected", False)

    # Start RTSP capture for configured cameras
    camera_configs = [
        {
            "camera_id": os.getenv("CAMERA_ID", "default"),
            "rtsp_url": os.getenv("RTSP_URL", "rtsp://localhost:554/stream"),
            "fps_limit": int(os.getenv("FPS_LIMIT", "30")),
        }
    ]

    for config in camera_configs:
        capture = RTSPCapture(
            rtsp_url=config["rtsp_url"],
            camera_id=config["camera_id"],
            fps_limit=config["fps_limit"],
        )
        capture_instances[config["camera_id"]] = capture

        # Start capture loop in background
        asyncio.create_task(capture_loop_with_publish(capture))
        print(f"Started capture for camera {config['camera_id']}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global redis_client, capture_instances
    print("RTSP Capture Service shutting down...")

    # Stop all captures
    for camera_id, capture in capture_instances.items():
        capture.stop()
        print(f"Stopped capture for camera {camera_id}")

    # Close Redis connection
    if redis_client:
        await redis_client.close()
        print("Redis connection closed")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "rtsp-capture", "version": "1.0.0", "status": "operational"}


async def capture_loop_with_publish(capture: RTSPCapture):
    """Capture loop that publishes frames to Redis."""
    global redis_queue

    # Start the capture loop
    capture_task = asyncio.create_task(capture.capture_loop())

    while capture.is_running:
        # Get frame from buffer
        frame_data = capture.get_frame()
        if frame_data:
            frame_id, (frame, metadata), timestamp = frame_data

            # Prepare metadata for Redis
            if hasattr(metadata, "model_dump"):
                # FrameMetadata object
                redis_metadata = metadata.model_dump(mode="json")
            else:
                # Basic dict metadata
                redis_metadata = metadata

            # Add frame location info for downstream processors
            redis_metadata["frame_buffer_key"] = f"frame:{frame_id}"
            redis_metadata["capture_timestamp"] = timestamp

            # Publish to Redis queue with trace propagation
            try:
                message_id = await redis_queue.publish(redis_metadata)
                print(f"Published frame {frame_id} to Redis: {message_id}")
            except Exception as e:
                print(f"Failed to publish frame {frame_id}: {e}")

        # Small delay to prevent busy loop
        await asyncio.sleep(0.001)

    # Wait for capture task to complete
    await capture_task


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")), access_log=True
    )
