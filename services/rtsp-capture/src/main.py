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
from frame_buffer import FrameBufferError
from frame_capture import RTSPCapture

# from simple_health import health_router, update_health_state
from observability import init_telemetry
from redis_queue import RedisFrameQueue

# Create FastAPI app
app = FastAPI(
    title="RTSP Capture Service",
    description="Service for capturing RTSP streams with observability",
    version="1.0.0",
)

# Include health router - DISABLED, using inline endpoints instead
# app.include_router(health_router)

# Initialize service state
# update_health_state("start_time", time.time())
# update_health_state("redis_connected", False)  # Will be updated when Redis connects

# Global instances
redis_client = None
redis_queue = None
capture_instances: Dict[str, RTSPCapture] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    global redis_client, redis_queue, capture_instances
    print("RTSP Capture Service starting up...")

    # Initialize telemetry INSIDE the event loop
    init_telemetry(
        service_name="rtsp-capture",
        otlp_endpoint=os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
        ).replace("http://", ""),
        deployment_env=os.getenv("DEPLOYMENT_ENV", "development"),
    )

    # Initialize Redis connection
    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        print(f"[STARTUP] Connecting to Redis at {redis_host}:{redis_port}...")

        redis_client = redis.Redis(
            host=redis_host, port=redis_port, decode_responses=False
        )
        await redis_client.ping()
        # update_health_state("redis_connected", True)
        print(f"[STARTUP] Connected to Redis at {redis_host}:{redis_port}")

        # Initialize Redis queue
        redis_queue = RedisFrameQueue(redis_client)

        # Create consumer group for downstream services
        try:
            await redis_queue.create_consumer_group("frame-processors", start_id="0")
        except Exception as e:
            print(f"[STARTUP] Consumer group creation info: {e}")
            # Group might already exist, which is fine

    except Exception as e:
        print(f"[ERROR] Failed to connect to Redis: {e}")
        import traceback

        traceback.print_exc()
        # update_health_state("redis_connected", False)

    # Start RTSP capture for configured cameras
    camera_configs = [
        {
            "camera_id": os.getenv("CAMERA_ID", "default"),
            "rtsp_url": os.getenv("RTSP_URL", "rtsp://localhost:554/stream"),
            "fps_limit": int(os.getenv("FPS_LIMIT", "30")),
        }
    ]

    for config in camera_configs:
        try:
            print(f"[STARTUP] Creating RTSPCapture for camera {config['camera_id']}...")
            capture = RTSPCapture(
                rtsp_url=config["rtsp_url"],
                camera_id=config["camera_id"],
                fps_limit=config["fps_limit"],
            )
            capture_instances[config["camera_id"]] = capture

            # Connect to RTSP stream first
            print("[STARTUP] Connecting to RTSP stream...")
            if not capture.connect():
                print("[ERROR] Failed to connect to RTSP stream!")
                continue

            # Camera connected successfully
            print("[STARTUP] Camera connected successfully")

            # Start capture loop in background with error handling
            print(
                f"[STARTUP] Starting capture loop for camera {config['camera_id']}..."
            )
            # DON'T WAIT FOR TASK - just create it
            asyncio.create_task(capture_loop_with_publish(capture))
            print(f"[STARTUP] Started capture task for camera {config['camera_id']}")

        except Exception as e:
            print(
                f"[ERROR] Failed to start capture for camera {config['camera_id']}: {e}"
            )
            import traceback

            traceback.print_exc()

    print("[STARTUP] Startup complete")

    # IMPORTANT: Return immediately - don't block the event loop
    return


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


@app.get("/test")
async def test():
    """Test endpoint."""
    print("[DEBUG] Test endpoint called!")
    return {"test": "ok"}


@app.get("/health")
async def health():
    """Ultra simple health endpoint."""
    return {"status": "ok"}


async def capture_loop_with_publish(capture: RTSPCapture):
    """Capture loop that publishes frames to Redis."""
    global redis_queue

    print(f"[CAPTURE_LOOP] Starting for camera {capture.camera_id}")

    try:
        # Check if capture has capture_loop method
        if not hasattr(capture, "capture_loop"):
            print("[ERROR] RTSPCapture has no capture_loop method!")
            return

        # Start the capture loop
        print("[CAPTURE_LOOP] Creating capture task...")
        capture_task = asyncio.create_task(capture.capture_loop())
        print("[CAPTURE_LOOP] Capture task created")

        # Wait for capture loop to start
        print("[CAPTURE_LOOP] Waiting for capture loop to start...")
        for _ in range(50):  # Wait up to 5 seconds
            if capture.is_running:
                print("[CAPTURE_LOOP] Capture loop started!")
                break
            await asyncio.sleep(0.1)
        else:
            print("[ERROR] Capture loop failed to start!")
            return

        frame_count = 0
        last_log_time = time.time()

        while capture.is_running:
            try:
                # Get frame from buffer
                try:
                    frame_data = capture.get_frame()
                except FrameBufferError:
                    # Buffer is empty, wait a bit
                    await asyncio.sleep(0.01)
                    continue

                if frame_data:
                    frame_id, (frame, metadata), timestamp = frame_data
                    frame_count += 1

                    # Log every 10 frames or every 5 seconds
                    current_time = time.time()
                    if frame_count % 10 == 0 or (current_time - last_log_time) > 5:
                        print(f"[CAPTURE_LOOP] Processed {frame_count} frames")
                        last_log_time = current_time

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
                        if redis_queue:
                            message_id = await redis_queue.publish(redis_metadata)
                            if frame_count % 10 == 0:  # Log every 10th frame
                                print(
                                    f"[CAPTURE_LOOP] Published frame {frame_id} "
                                    f"to Redis: {message_id}"
                                )

                            # Frame published successfully
                            pass
                        else:
                            print("[ERROR] Redis queue not initialized!")
                            break
                    except Exception as e:
                        print(f"[ERROR] Failed to publish frame {frame_id}: {e}")
                        if frame_count % 10 == 0:
                            import traceback

                            traceback.print_exc()

                # Small delay to prevent busy loop and yield control
                await asyncio.sleep(0.001)

            except Exception as e:
                print(f"[ERROR] Error in capture loop iteration: {e}")
                import traceback

                traceback.print_exc()
                await asyncio.sleep(1)  # Wait before retry

        print(f"[CAPTURE_LOOP] Exiting loop, capture.is_running = {capture.is_running}")

        # Wait for capture task to complete
        print("[CAPTURE_LOOP] Waiting for capture task to complete...")
        await capture_task
        print("[CAPTURE_LOOP] Capture task completed")

    except Exception as e:
        print(f"[ERROR] Fatal error in capture_loop_with_publish: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")), access_log=True
    )
