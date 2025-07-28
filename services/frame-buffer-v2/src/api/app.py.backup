"""FastAPI application for Frame Buffer v2."""

import uuid
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import processors
from src.config import Settings
from src.orchestrator.processor_registry import ProcessorRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Load settings
    settings = Settings()
    app.state.settings = settings

    # Startup
    redis_client = aioredis.from_url(
        settings.redis_url, max_connections=settings.redis_max_connections
    )
    registry = ProcessorRegistry(redis_client)

    # Make instances available to routes
    app.state.registry = registry
    app.state.redis = redis_client

    yield

    # Shutdown
    await redis_client.close()


# Create FastAPI app
app = FastAPI(
    title="Frame Buffer v2 API",
    description="Intelligent frame orchestrator for video processing pipeline",
    version="2.0.0",
    lifespan=lifespan,
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
        await app.state.redis.ping()
        return {"status": "healthy", "service": "frame-buffer-v2"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)},
        )
