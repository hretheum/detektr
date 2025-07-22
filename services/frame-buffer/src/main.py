"""
Frame Buffer Service - High-performance frame buffering with Redis Sentinel HA.

This service provides:
- Circular frame buffer with Redis Streams
- Backpressure handling
- Dead Letter Queue (DLQ)
- Full observability (metrics, tracing)
- Redis Sentinel High Availability support
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

# Import Redis Sentinel client
from redis_sentinel import RedisSentinelClient

# Configuration
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

# Global Redis client with Sentinel support
redis_sentinel: Optional[RedisSentinelClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_sentinel

    # Initialize telemetry
    init_telemetry(SERVICE_NAME)

    # Update health state
    update_health_state("start_time", time.time())

    # Connect to Redis via Sentinel
    try:
        redis_sentinel = RedisSentinelClient()
        await redis_sentinel.connect()
        update_health_state("redis_connected", True)
        print("✅ Connected to Redis via Sentinel HA setup")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        update_health_state("redis_connected", False)

    yield

    # Cleanup
    if redis_sentinel:
        await redis_sentinel.close()


# Create FastAPI app
app = FastAPI(
    title="Frame Buffer Service",
    description="High-performance frame buffering with Redis HA backend",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(health_router)


async def get_redis_client() -> redis.Redis:
    """Get Redis client with HA support."""
    if not redis_sentinel:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis Sentinel not initialized",
        )

    try:
        return await redis_sentinel.get_client()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis connection failed: {e}",
        )


@app.post("/frames/enqueue")
async def enqueue_frame(frame_data: dict):
    """Add frame to buffer."""
    client = await get_redis_client()

    with frame_processing_time.labels(operation="enqueue").time():
        try:
            # Check buffer size
            current_size = await client.xlen(FRAME_QUEUE_NAME)

            if current_size >= MAX_BUFFER_SIZE:
                # Send to DLQ
                await client.xadd(
                    DLQ_NAME, {"frame": str(frame_data), "reason": "buffer_full"}
                )
                dlq_counter.labels(reason="buffer_full").inc()
                frame_counter.labels(operation="enqueue", status="dropped").inc()

                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Buffer full",
                )

            # Add to queue with JSON serialization
            message_id = await client.xadd(
                FRAME_QUEUE_NAME, {"frame_data": json.dumps(frame_data)}
            )

            frame_counter.labels(operation="enqueue", status="success").inc()
            buffer_size_gauge.set(current_size + 1)

            return {
                "status": "enqueued",
                "frame_id": frame_data.get("frame_id", "unknown"),
                "message_id": message_id,
                "queue_size": current_size + 1,
            }

        except Exception as e:
            frame_counter.labels(operation="enqueue", status="error").inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )


@app.get("/frames/dequeue")
async def dequeue_frame(count: int = 1):
    """Retrieve frames from buffer."""
    client = await get_redis_client()

    with frame_processing_time.labels(operation="dequeue").time():
        try:
            # Read frames
            frames = await client.xread(
                {FRAME_QUEUE_NAME: "0"}, count=count, block=1000  # 1 second timeout
            )

            if not frames:
                return {
                    "frames": [],
                    "remaining": await client.xlen(FRAME_QUEUE_NAME),
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
                        await client.xadd(
                            DLQ_NAME,
                            {"frame": str(data), "reason": f"parse_failed: {str(e)}"},
                        )
                        dlq_counter.labels(reason="parse_failed").inc()

            # Acknowledge and remove frames
            if message_ids:
                await client.xdel(FRAME_QUEUE_NAME, *message_ids)
                frame_counter.labels(operation="dequeue", status="success").inc(
                    len(message_ids)
                )

            # Update buffer size
            remaining = await client.xlen(FRAME_QUEUE_NAME)
            buffer_size_gauge.set(remaining)

            return {
                "frames": result_frames,
                "count": len(result_frames),
                "remaining": remaining,
            }

        except Exception as e:
            frame_counter.labels(operation="dequeue", status="error").inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )


@app.get("/frames/status")
async def get_buffer_status():
    """Get current buffer status."""
    try:
        client = await get_redis_client()
        queue_size = await client.xlen(FRAME_QUEUE_NAME)
        dlq_size = await client.xlen(DLQ_NAME)

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
    client = await get_redis_client()

    try:
        # Get current size
        size_before = await client.xlen(FRAME_QUEUE_NAME)

        # Clear the stream
        await client.delete(FRAME_QUEUE_NAME)

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
    client = await get_redis_client()

    try:
        # Get current size
        size_before = await client.xlen(DLQ_NAME)

        # Clear the DLQ
        await client.delete(DLQ_NAME)

        return {
            "status": "cleared",
            "message": "DLQ cleared successfully",
            "cleared_count": size_before,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/dlq/status")
async def get_dlq_status():
    """Get Dead Letter Queue status."""
    try:
        client = await get_redis_client()
        dlq_size = await client.xlen(DLQ_NAME)

        # Get sample of DLQ messages
        samples = await client.xrange(DLQ_NAME, count=5)

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
    client = await get_redis_client()

    try:
        # Read from DLQ
        messages = await client.xrange(DLQ_NAME, count=max_items)

        reprocessed = 0
        failed = 0

        for msg_id, data in messages:
            try:
                # Try to add back to main queue
                frame_data = eval(data.get("frame", "{}"))  # Careful with eval!
                await client.xadd(FRAME_QUEUE_NAME, frame_data)
                await client.xdel(DLQ_NAME, msg_id)
                reprocessed += 1
            except Exception:
                failed += 1

        return {
            "reprocessed": reprocessed,
            "failed": failed,
            "remaining": await client.xlen(DLQ_NAME),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT, log_level="info")
