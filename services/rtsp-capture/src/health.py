"""
Health check and monitoring endpoints for RTSP capture service.

Provides:
- Health check endpoint with detailed status
- Readiness probe for Kubernetes/Docker
- Prometheus metrics endpoint
"""

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

# Metrics are imported lazily to avoid circular imports

# Create router for health endpoints
health_router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    uptime_seconds: float
    checks: Dict[str, Dict[str, Any]]


class ReadinessStatus(BaseModel):
    """Readiness probe response model."""

    ready: bool
    reason: Optional[str] = None
    dependencies: Dict[str, bool]


# Global health state (to be updated by service)
_health_state = {
    "start_time": None,
    "rtsp_connections": {},
    "redis_connected": False,
    "last_frame_time": {},
}


def update_health_state(key: str, value: Any) -> None:
    """Update health state for monitoring."""
    _health_state[key] = value


def add_rtsp_connection(camera_id: str, url: str, connected: bool) -> None:
    """Register RTSP connection status."""
    _health_state["rtsp_connections"][camera_id] = {
        "url": url,
        "connected": connected,
        "last_frame": None,
    }


def update_last_frame(camera_id: str, timestamp: float) -> None:
    """Update last frame timestamp for camera."""
    if camera_id in _health_state["rtsp_connections"]:
        _health_state["rtsp_connections"][camera_id]["last_frame"] = timestamp

    _health_state["last_frame_time"][camera_id] = timestamp


@health_router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Comprehensive health check endpoint.

    Returns detailed status of all service components.
    """
    import time

    # Calculate uptime
    start_time = _health_state.get("start_time", time.time())
    uptime = time.time() - start_time

    # Check RTSP connections
    rtsp_healthy = True
    rtsp_details = {}

    for camera_id, conn_info in _health_state["rtsp_connections"].items():
        last_frame = conn_info.get("last_frame")
        if last_frame:
            # Check if we've received frames recently (within 10 seconds)
            frame_age = time.time() - last_frame
            is_healthy = conn_info["connected"] and frame_age < 10.0
        else:
            is_healthy = conn_info["connected"]

        rtsp_details[camera_id] = {
            "connected": conn_info["connected"],
            "healthy": is_healthy,
            "last_frame_age": frame_age if last_frame else None,
        }

        if not is_healthy:
            rtsp_healthy = False

    # Check Redis
    redis_healthy = _health_state.get("redis_connected", False)

    # Overall status
    if rtsp_healthy and redis_healthy:
        overall_status = "healthy"
    elif rtsp_healthy or redis_healthy:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return HealthStatus(
        status=overall_status,
        version="1.0.0",
        uptime_seconds=uptime,
        checks={
            "rtsp_connections": {
                "healthy": rtsp_healthy,
                "details": rtsp_details,
            },
            "redis": {
                "healthy": redis_healthy,
                "connected": redis_healthy,
            },
            "memory": {
                "healthy": True,  # TODO: Add actual memory check
                "usage_mb": 0,  # TODO: Get from psutil
            },
        },
    )


@health_router.get("/ready", response_model=ReadinessStatus)
async def readiness_probe(response: Response):
    """
    Kubernetes-style readiness probe.

    Returns 200 if service is ready to accept traffic, 503 otherwise.
    """
    # Check critical dependencies
    redis_ready = _health_state.get("redis_connected", False)
    has_rtsp = len(_health_state["rtsp_connections"]) > 0

    if not has_rtsp:
        # No RTSP connections configured yet
        ready = redis_ready
        reason = None if ready else "Redis not connected"
    else:
        # Check if at least one RTSP connection is healthy
        any_rtsp_healthy = any(
            conn.get("connected", False)
            for conn in _health_state["rtsp_connections"].values()
        )
        ready = redis_ready and any_rtsp_healthy

        if not ready:
            reasons = []
            if not redis_ready:
                reasons.append("Redis not connected")
            if not any_rtsp_healthy:
                reasons.append("No healthy RTSP connections")
            reason = "; ".join(reasons)
        else:
            reason = None

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessStatus(
        ready=ready,
        reason=reason,
        dependencies={
            "redis": redis_ready,
            "rtsp": any_rtsp_healthy if has_rtsp else True,
        },
    )


@health_router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Exposes all service metrics in Prometheus format.
    """
    # Ensure metrics are initialized
    from prometheus_client import REGISTRY

    from .observability import _init_metrics_once
    from .observability import active_connections_gauge as acg

    # Initialize metrics if needed
    _init_metrics_once()

    # Update active connections gauge
    if acg is not None:
        for camera_id, conn_info in _health_state["rtsp_connections"].items():
            if conn_info.get("connected", False):
                acg.labels(camera_id=camera_id).set(1)
            else:
                acg.labels(camera_id=camera_id).set(0)

    # Generate Prometheus metrics
    metrics_output = generate_latest(REGISTRY)

    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@health_router.get("/ping")
async def ping():
    """Respond with pong for basic connectivity check."""
    return {"ping": "pong"}


class ServiceMetrics:
    """Helper class to track and expose service-level metrics."""

    def __init__(self):
        """Initialize ServiceMetrics instance."""
        self.cameras: List[str] = []

    def register_camera(self, camera_id: str, rtsp_url: str):
        """Register a camera for monitoring."""
        if camera_id not in self.cameras:
            self.cameras.append(camera_id)

        add_rtsp_connection(camera_id, rtsp_url, False)

    def on_frame_received(self, camera_id: str):
        """Handle frame received event from camera."""
        update_last_frame(camera_id, time.time())
        # Ensure metrics are initialized
        from .observability import frame_counter as fc

        if fc is not None:
            fc.labels(camera_id=camera_id, status="success").inc()

    def on_frame_error(self, camera_id: str, error: str):
        """Handle frame processing error."""
        # Ensure metrics are initialized
        from .observability import frame_counter as fc
        from .observability import frame_drops_counter as fdc

        if fc is not None:
            fc.labels(camera_id=camera_id, status="error").inc()

        if fdc is not None:
            if "buffer_full" in error.lower():
                fdc.labels(camera_id=camera_id, reason="buffer_full").inc()
            else:
                fdc.labels(camera_id=camera_id, reason="error").inc()

    def on_connection_state_changed(self, camera_id: str, connected: bool):
        """Handle RTSP connection state change."""
        if camera_id in _health_state["rtsp_connections"]:
            _health_state["rtsp_connections"][camera_id]["connected"] = connected

        # Ensure metrics are initialized
        from .observability import active_connections_gauge as acg

        if acg is not None:
            if connected:
                acg.labels(camera_id=camera_id).set(1)
            else:
                acg.labels(camera_id=camera_id).set(0)

    def set_buffer_size(self, camera_id: str, size: int):
        """Update buffer size metric."""
        # Ensure metrics are initialized
        from .observability import buffer_size_gauge as bsg

        if bsg is not None:
            bsg.labels(camera_id=camera_id).set(size)

    def record_processing_time(self, camera_id: str, operation: str, duration: float):
        """Record processing time for an operation."""
        # Ensure metrics are initialized
        from .observability import frame_processing_time as fpt

        if fpt is not None:
            fpt.labels(camera_id=camera_id, operation=operation).observe(duration)


# Global metrics instance
service_metrics = ServiceMetrics()
