"""Health check endpoints for frame buffer service."""

import time
from typing import Any, Dict

from fastapi import APIRouter, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

# Create router
health_router = APIRouter(tags=["health"])

# Global health state
_health_state = {
    "start_time": None,
    "redis_connected": False,
    "last_frame_time": None,
    "buffer_stats": {},
}


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    uptime_seconds: float
    checks: Dict[str, Dict[str, Any]]


class ServiceMetrics:
    """Service metrics helper."""

    def __init__(self):
        """Initialize service metrics."""
        pass

    def record_frame_buffered(self):
        """Record frame buffered event."""
        _health_state["last_frame_time"] = time.time()

    def update_buffer_stats(self, stats: dict):
        """Update buffer statistics."""
        _health_state["buffer_stats"] = stats


# Global instance
service_metrics = ServiceMetrics()


def update_health_state(key: str, value: Any) -> None:
    """Update health state."""
    _health_state[key] = value


@health_router.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    print("🏥 Health check called")
    start_time = _health_state.get("start_time", time.time())
    uptime = time.time() - start_time

    # Check Redis
    redis_healthy = _health_state.get("redis_connected", False)

    # Check frame processing
    last_frame = _health_state.get("last_frame_time")
    frame_processing_healthy = True
    if last_frame:
        frame_age = time.time() - last_frame
        # Unhealthy if no frames for 60 seconds
        frame_processing_healthy = frame_age < 60

    # Overall status
    if redis_healthy and frame_processing_healthy:
        overall_status = "healthy"
    elif redis_healthy or frame_processing_healthy:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    buffer_stats = _health_state.get("buffer_stats", {})

    return HealthStatus(
        status=overall_status,
        version="1.0.0",
        uptime_seconds=uptime,
        checks={
            "redis": {"healthy": redis_healthy, "connected": redis_healthy},
            "frame_processing": {
                "healthy": frame_processing_healthy,
                "last_frame_age": time.time() - last_frame if last_frame else None,
            },
            "buffer": {
                "healthy": True,
                "size": buffer_stats.get("size", 0),
                "max_size": buffer_stats.get("max_size", 1000),
                "utilization": buffer_stats.get("utilization", 0),
            },
        },
    )


@health_router.get("/ready")
async def readiness_probe(response: Response):
    """Readiness probe endpoint."""
    redis_ready = _health_state.get("redis_connected", False)

    if not redis_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"ready": False, "reason": "Redis not connected"}

    return {"ready": True}


@health_router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    print("📊 Metrics endpoint called")
    try:
        from prometheus_client import REGISTRY

        metrics_output = generate_latest(REGISTRY)

        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
            },
        )
    except Exception as e:
        print(f"❌ Metrics error: {e}")
        import traceback

        traceback.print_exc()
        raise
