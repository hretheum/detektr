"""Simple health check endpoint that actually fucking works."""

import time

from fastapi import APIRouter

# Create router
health_router = APIRouter()

# Global state
_health_state = {
    "start_time": time.time(),
    "redis_connected": False,
    "camera_connected": False,
    "last_frame_time": None,
}


def update_health_state(key: str, value):
    """Update health state."""
    _health_state[key] = value


@health_router.get("/health")
async def health_check():
    """Return simple health check that returns immediately."""
    uptime = time.time() - _health_state["start_time"]

    # Determine status
    if _health_state["redis_connected"] and _health_state["camera_connected"]:
        status = "healthy"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "uptime": int(uptime),
        "redis": _health_state["redis_connected"],
        "camera": _health_state["camera_connected"],
    }


@health_router.get("/ping")
async def ping():
    """Return simple ping endpoint."""
    return {"ping": "pong"}
