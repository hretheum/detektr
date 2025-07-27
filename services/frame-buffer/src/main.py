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
from typing import Any, Dict, Optional

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from starlette import status

# Import frame tracking
try:
    from frame_tracking import TraceContext

    FRAME_TRACKING_AVAILABLE = True
except ImportError:
    FRAME_TRACKING_AVAILABLE = False
    print("Warning: frame-tracking library not available")

# Import consumer
from consumer import FrameConsumer, create_consumer_from_env
from frame_buffer import FrameBuffer

# Import health check router
from health import health_router, update_health_state

# Import observability
from observability import init_telemetry
from prometheus_client import Counter, Gauge, Histogram

# Import shared buffer for consistent state
from shared_buffer import SharedFrameBuffer

# Regular Redis client - Sentinel disabled for now
# from redis_sentinel import RedisSentinelClient


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

# Global Redis client (regular, not Sentinel)
redis_client: Optional[redis.Redis] = None
# Global consumer instance
frame_consumer: Optional[FrameConsumer] = None
# Global shared buffer instance
shared_buffer: Optional[FrameBuffer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client, frame_consumer, shared_buffer

    # Initialize telemetry
    init_telemetry(SERVICE_NAME)

    # Update health state
    update_health_state("start_time", time.time())

    # Initialize shared buffer
    shared_buffer = await SharedFrameBuffer.get_instance()
    print("✅ Shared buffer initialized")

    # Connect to Redis (regular connection, not Sentinel)
    try:
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))

        redis_client = redis.from_url(
            f"redis://{redis_host}:{redis_port}/{redis_db}",
            encoding="utf-8",
            decode_responses=True,
        )

        # Test connection
        await redis_client.ping()
        update_health_state("redis_connected", True)
        print(f"✅ Connected to Redis at {redis_host}:{redis_port}")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        update_health_state("redis_connected", False)

    # Start frame consumer
    try:
        frame_consumer = await create_consumer_from_env()
        await frame_consumer.start()
        update_health_state("consumer_running", True)
        print("✅ Frame consumer started")
    except Exception as e:
        print(f"❌ Failed to start consumer: {e}")
        update_health_state("consumer_running", False)

    yield

    # Cleanup
    if frame_consumer:
        await frame_consumer.stop()
        print("Frame consumer stopped")

    if redis_client:
        await redis_client.close()


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
    """Get Redis client."""
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis client not initialized",
        )

    try:
        # Verify connection is still alive
        await redis_client.ping()
        return redis_client
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis connection failed: {e}",
        )


@app.post("/frames/enqueue")
async def enqueue_frame(frame_data: dict):
    """Add frame to buffer with trace context propagation."""
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

            # Prepare data with trace context
            queue_data = {"frame_data": json.dumps(frame_data)}

            # Use frame tracking if available
            if FRAME_TRACKING_AVAILABLE:
                with TraceContext.inject(frame_data.get("frame_id", "unknown")) as ctx:
                    ctx.add_event("frame_buffer_enqueue")
                    ctx.set_attribute("buffer.size", current_size)
                    ctx.set_attribute("buffer.max_size", MAX_BUFFER_SIZE)
                    ctx.set_attribute("frame.id", frame_data.get("frame_id", "unknown"))

                    # Inject trace context for propagation
                    ctx.inject_to_carrier(queue_data)

            # Add to queue with JSON serialization
            message_id = await client.xadd(FRAME_QUEUE_NAME, queue_data)

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
    """Retrieve frames from shared in-memory buffer with trace context extraction."""
    global shared_buffer

    # Validate count parameter
    if count < 1:
        count = 1
    elif count > 100:
        count = 100

    if not shared_buffer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shared buffer not initialized",
        )

    with frame_processing_time.labels(operation="dequeue").time():
        try:
            # Get frames from shared in-memory buffer
            result_frames = []

            for _ in range(count):
                # Check if buffer has frames (synchronous method)
                if shared_buffer.is_empty():
                    break

                # Get frame from buffer
                frame_data = await shared_buffer.get()
                if frame_data:
                    # Extract existing trace context or create new one
                    if FRAME_TRACKING_AVAILABLE and "frame_id" in frame_data:
                        # Try to extract existing trace context
                        if "traceparent" in frame_data:
                            # Extract and continue existing trace
                            with TraceContext.extract_from_carrier(frame_data) as ctx:
                                ctx.add_event("frame_buffer_dequeue")
                                ctx.set_attribute("buffer.size", shared_buffer.size())
                                ctx.set_attribute("frame.id", frame_data["frame_id"])
                        else:
                            # Create new trace context if none exists
                            with TraceContext.inject(frame_data["frame_id"]) as ctx:
                                ctx.add_event("frame_buffer_dequeue")
                                ctx.set_attribute("buffer.size", shared_buffer.size())
                                ctx.set_attribute("frame.id", frame_data["frame_id"])

                    result_frames.append(frame_data)
                    frame_counter.labels(operation="dequeue", status="success").inc()

            # Update metrics (synchronous method)
            remaining = shared_buffer.size()
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
    """Get current buffer status from shared in-memory buffer."""
    global shared_buffer

    try:
        # Get in-memory buffer status
        if shared_buffer:
            buffer_size = shared_buffer.size()
            buffer_usage = (buffer_size / MAX_BUFFER_SIZE) * 100
        else:
            buffer_size = 0
            buffer_usage = 0

        # Also check Redis for comparison
        try:
            client = await get_redis_client()
            redis_queue_size = await client.xlen(FRAME_QUEUE_NAME)
            dlq_size = await client.xlen(DLQ_NAME)
        except Exception:
            redis_queue_size = -1
            dlq_size = -1

        # Get backpressure stats
        backpressure_stats = {}
        if shared_buffer:
            backpressure_stats = shared_buffer.get_backpressure_stats()

        return {
            "connected": True,
            "consumer_running": frame_consumer is not None and frame_consumer._running,
            "buffer": {
                "size": buffer_size,
                "max_size": MAX_BUFFER_SIZE,
                "usage_percent": buffer_usage,
                "is_full": buffer_size >= MAX_BUFFER_SIZE,
                "backpressure": backpressure_stats,
            },
            "redis": {"queue_size": redis_queue_size, "dlq_size": dlq_size},
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}


@app.get("/buffer/backpressure")
async def get_backpressure_status():
    """Get detailed backpressure monitoring information."""
    global shared_buffer

    if not shared_buffer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shared buffer not initialized",
        )

    # Get current buffer status
    current_size = shared_buffer.size()
    usage_ratio = shared_buffer.usage_ratio()
    backpressure_stats = shared_buffer.get_backpressure_stats()

    # Calculate backpressure severity
    severity = "none"
    if usage_ratio > 0.9:
        severity = "critical"
    elif usage_ratio > 0.7:
        severity = "high"
    elif usage_ratio > 0.5:
        severity = "moderate"

    # Get consumer status
    consumer_status = {
        "running": frame_consumer is not None and frame_consumer._running,
        "batch_size": frame_consumer.batch_size if frame_consumer else 0,
    }

    return {
        "buffer": {
            "current_size": current_size,
            "max_size": MAX_BUFFER_SIZE,
            "usage_ratio": usage_ratio,
            "usage_percent": usage_ratio * 100,
        },
        "backpressure": {
            "severity": severity,
            "is_experiencing_backpressure": usage_ratio > 0.7,
            "total_events": backpressure_stats["backpressure_events"],
            "last_event_time": backpressure_stats["last_backpressure_time"],
            "seconds_since_last_event": (
                backpressure_stats["seconds_since_last_backpressure"]
            ),
        },
        "consumer": consumer_status,
        "recommendations": _get_backpressure_recommendations(
            usage_ratio, backpressure_stats
        ),
    }


def _get_backpressure_recommendations(
    usage_ratio: float, stats: Dict[str, Any]
) -> list[str]:
    """Generate recommendations based on backpressure status."""
    recommendations = []

    if usage_ratio > 0.9:
        recommendations.append(
            "CRITICAL: Buffer is almost full. Consider scaling consumers."
        )
        recommendations.append(
            "Increase consumer batch size or add more consumer instances."
        )
    elif usage_ratio > 0.7:
        recommendations.append("WARNING: High buffer usage. Monitor closely.")
        recommendations.append(
            "Consider increasing buffer size or optimizing consumer performance."
        )

    if stats["backpressure_events"] > 100:
        recommendations.append("High number of dropped frames. Review system capacity.")

    if (
        stats["seconds_since_last_backpressure"]
        and stats["seconds_since_last_backpressure"] < 60
    ):
        recommendations.append(
            "Recent backpressure detected. System may be under load."
        )

    return recommendations


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
                frame_json = data.get("frame", "{}")
                if isinstance(frame_json, bytes):
                    frame_json = frame_json.decode("utf-8")
                frame_data = json.loads(frame_json)
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


@app.post("/test-frame")
async def test_frame_with_trace(test_data: dict):
    """Test endpoint to verify trace propagation."""
    if not FRAME_TRACKING_AVAILABLE:
        return {"error": "Frame tracking not available"}

    # Use frame tracking for test
    with TraceContext.inject(test_data.get("frame_id", "test")) as ctx:
        ctx.add_event("test_frame_buffer")

        # Test enqueue
        enqueue_result = await enqueue_frame(test_data)

        # Test dequeue
        dequeue_result = await dequeue_frame(count=1)

        return {
            "frame_tracking_enabled": True,
            "trace_id": ctx.trace_id,
            "enqueue_result": enqueue_result,
            "dequeue_result": dequeue_result,
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT, log_level="info")
