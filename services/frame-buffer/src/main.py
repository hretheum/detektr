"""
Frame Buffer Service - High-performance frame buffering with Redis backend.

This service provides:
- Circular frame buffer with Redis Streams
- Backpressure handling
- Dead Letter Queue (DLQ)
- Full observability (metrics, tracing)
"""

import json
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, status

# Import health check router
from health import health_router, update_health_state

# Import observability
from observability import init_telemetry
from prometheus_client import Counter, Gauge, Histogram

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
FRAME_QUEUE_NAME = os.getenv("FRAME_QUEUE_NAME", "frame_queue")
DLQ_NAME = os.getenv("DLQ_NAME", "frame_dlq")
MAX_BUFFER_SIZE = int(os.getenv("MAX_BUFFER_SIZE", "1000"))
SERVICE_NAME = "frame-buffer"
SERVICE_PORT = int(os.getenv("PORT", "8002"))

# Metrics
frame_counter = Counter(
    "frame_buffer_frames_total", "Total frames processed", ["operation", "status"]
)
buffer_size_gauge = Gauge("frame_buffer_queue_size", "Current buffer size")
frame_processing_time = Histogram(
    "frame_buffer_processing_seconds", "Frame processing time", ["operation"]
)
dlq_counter = Counter("frame_buffer_dlq_total", "Frames sent to DLQ", ["reason"])

# Global Redis client
redis_client: Optional[redis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client

    # Initialize telemetry
    init_telemetry(SERVICE_NAME)

    # Update health state
    update_health_state("start_time", time.time())

    # Connect to Redis
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
        )
        await redis_client.ping()
        update_health_state("redis_connected", True)
        print(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        update_health_state("redis_connected", False)

    yield

    # Cleanup
    if redis_client:
        await redis_client.close()


# Create FastAPI app
app = FastAPI(
    title="Frame Buffer Service",
    description="High-performance frame buffering with Redis backend",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(health_router)


def compress_frame(data: dict) -> bytes:
    """Compress frame data (placeholder for LZ4)."""
    import lz4.frame
    json_data = json.dumps(data)
    return lz4.frame.compress(json_data.encode())


def decompress_frame(data: bytes) -> dict:
    """Decompress frame data (placeholder for LZ4)."""
    import lz4.frame
    json_data = lz4.frame.decompress(data).decode()
    return json.loads(json_data)


@app.post("/frames/enqueue")
async def enqueue_frame(frame_data: dict):
    """Add frame to buffer."""
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not connected",
        )

    with frame_processing_time.labels(operation="enqueue").time():
        try:
            # Check buffer size
            current_size = await redis_client.xlen(FRAME_QUEUE_NAME)

            if current_size >= MAX_BUFFER_SIZE:
                # Send to DLQ
                await redis_client.xadd(
                    DLQ_NAME, {"frame": str(frame_data), "reason": "buffer_full"}
                )
                dlq_counter.labels(reason="buffer_full").inc()
                frame_counter.labels(operation="enqueue", status="dropped").inc()

                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Buffer full",
                )

            # Add to queue with JSON serialization
            message_id = await redis_client.xadd(
                FRAME_QUEUE_NAME,
                {"frame_data": json.dumps(frame_data)}
            )

            frame_counter.labels(operation="enqueue", status="success").inc()
            buffer_size_gauge.set(current_size + 1)

            return {
                "status": "enqueued",
                "frame_id": frame_data.get("frame_id", "unknown"),
                "message_id": message_id,
                "queue_size": current_size + 1
            }

        except Exception as e:
            frame_counter.labels(operation="enqueue", status="error").inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )


@app.get("/frames/dequeue")
async def dequeue_frame(count: int = 1):
    """Retrieve frames from buffer."""
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not connected",
        )

    with frame_processing_time.labels(operation="dequeue").time():
        try:
            # Read frames
            frames = await redis_client.xread(
                {FRAME_QUEUE_NAME: "0"}, count=count, block=1000  # 1 second timeout
            )

            if not frames:
                return {
                    "frames": [],
                    "remaining": await redis_client.xlen(FRAME_QUEUE_NAME),
                }

            # Extract and parse frame data
            result_frames = []
            message_ids = []

            for _, messages in frames:
                for message_id, data in messages:
                    try:
                        # Parse JSON frame data
                        frame_json = data.get("frame_data", "{}")
                        frame_data = json.loads(frame_json)
                        result_frames.append(frame_data)
                        message_ids.append(message_id)
                    except Exception as e:
                        # Send to DLQ if parsing fails
                        await redis_client.xadd(
                            DLQ_NAME,
                            {"frame": str(data), "reason": f"parse_failed: {str(e)}"}
                        )
                        dlq_counter.labels(reason="parse_failed").inc()

            # Acknowledge and remove frames
            if message_ids:
                await redis_client.xdel(FRAME_QUEUE_NAME, *message_ids)
                frame_counter.labels(operation="dequeue", status="success").inc(
                    len(message_ids)
                )

            # Update buffer size
            remaining = await redis_client.xlen(FRAME_QUEUE_NAME)
            buffer_size_gauge.set(remaining)

            return {"frames": result_frames, "count": len(result_frames), "remaining": remaining}

        except Exception as e:
            frame_counter.labels(operation="dequeue", status="error").inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )


@app.get("/frames/status")
async def get_buffer_status():
    """Get current buffer status."""
    if not redis_client:
        return {
            "connected": False,
            "size": 0,
            "max_size": MAX_BUFFER_SIZE,
            "dlq_size": 0,
        }

    try:
        queue_size = await redis_client.xlen(FRAME_QUEUE_NAME)
        dlq_size = await redis_client.xlen(DLQ_NAME)

        return {
            "connected": True,
            "size": queue_size,
            "max_size": MAX_BUFFER_SIZE,
            "usage_percent": (queue_size / MAX_BUFFER_SIZE) * 100,
            "dlq_size": dlq_size,
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}


@app.post("/buffer/clear")
async def clear_buffer():
    """Clear all frames from buffer."""
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not connected",
        )

    try:
        # Get current size
        size_before = await redis_client.xlen(FRAME_QUEUE_NAME)

        # Clear the stream
        await redis_client.delete(FRAME_QUEUE_NAME)

        # Update metrics
        buffer_size_gauge.set(0)
        frame_counter.labels(operation="clear", status="success").inc(size_before)

        return {"cleared": size_before}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/frames/dlq/clear")
async def clear_dlq():
    """Clear all frames from DLQ."""
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not connected",
        )
    
    try:
        # Get current size
        size_before = await redis_client.xlen(DLQ_NAME)
        
        # Clear the DLQ
        await redis_client.delete(DLQ_NAME)
        
        return {"status": "cleared", "message": "DLQ cleared successfully", "cleared_count": size_before}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/dlq/status")
async def get_dlq_status():
    """Get Dead Letter Queue status."""
    if not redis_client:
        return {"size": 0, "connected": False}

    try:
        dlq_size = await redis_client.xlen(DLQ_NAME)

        # Get sample of DLQ messages
        samples = await redis_client.xrange(DLQ_NAME, count=5)

        return {
            "size": dlq_size,
            "connected": True,
            "recent_failures": [
                {
                    "id": msg_id,
                    "reason": data.get("reason", "unknown"),
                    "timestamp": msg_id.split("-")[0],
                }
                for msg_id, data in samples
            ],
        }
    except Exception as e:
        return {"size": 0, "connected": False, "error": str(e)}


@app.post("/dlq/reprocess")
async def reprocess_dlq(max_items: int = 100):
    """Reprocess items from DLQ."""
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not connected",
        )

    try:
        # Read from DLQ
        messages = await redis_client.xrange(DLQ_NAME, count=max_items)

        reprocessed = 0
        failed = 0

        for msg_id, data in messages:
            try:
                # Try to add back to main queue
                frame_data = eval(data.get("frame", "{}"))  # Careful with eval!
                await redis_client.xadd(FRAME_QUEUE_NAME, frame_data)
                await redis_client.xdel(DLQ_NAME, msg_id)
                reprocessed += 1
            except Exception:
                failed += 1

        return {
            "reprocessed": reprocessed,
            "failed": failed,
            "remaining": await redis_client.xlen(DLQ_NAME),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT, log_level="info")
