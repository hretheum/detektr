"""FastAPI application for Frame Buffer v2."""

import uuid

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import processors
from src.config import Settings

# Create FastAPI app
app = FastAPI(
    title="Frame Buffer v2 API",
    description="Intelligent frame orchestrator for video processing pipeline",
    version="2.0.0",
)

# Configure CORS
settings = Settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracking."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# API versioning
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(processors.router, prefix="/processors", tags=["processors"])
app.include_router(v1_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check Redis connection
        # Note: redis_client is set by main.py during startup
        if hasattr(app.state, "redis_client") and app.state.redis_client:
            await app.state.redis_client.ping()
            return {"status": "healthy", "service": "frame-buffer-v2"}
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "error": "Redis client not initialized",
                },
            )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)},
        )


@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint for Frame Buffer v2."""
    metrics = {
        "status": "healthy",
        "service": "frame-buffer-v2",
        "version": "2.0.0",
    }

    try:
        # Add registry metrics if available
        if hasattr(app.state, "registry") and app.state.registry:
            processors = await app.state.registry.list_all()
            metrics["processors"] = {
                "total": len(processors),
                "active": len(
                    processors
                ),  # All registered processors are considered active,
            }

        # Add Redis metrics if available
        if hasattr(app.state, "redis_client") and app.state.redis_client:
            info = await app.state.redis_client.info()
            metrics["redis"] = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }

            # Get stream info
            try:
                stream_info = await app.state.redis_client.xinfo_stream(
                    "frames:metadata"
                )
                metrics["input_stream"] = {
                    "length": stream_info.get("length", 0),
                    "groups": stream_info.get("groups", 0),
                    "last_generated_id": stream_info.get(
                        "last-generated-id", "unknown"
                    ),
                }
            except Exception:
                metrics["input_stream"] = {"error": "Stream not found"}

        return metrics
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)},
        )
