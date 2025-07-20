"""
Echo Service - Simple service demonstrating request/response patterns.

This service demonstrates:
- Full observability (tracing, metrics, logs)
- Correlation ID propagation
- Simple echo functionality
- Health checks
- Proper error handling
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from telemetry import (
    ObservabilityMiddleware,
    business_operations_total,
    get_or_create_correlation_id,
    init_telemetry,
    traced,
    track_metrics_middleware,
)

# Configure structured logging
logger = structlog.get_logger()


# API Models
class EchoRequest(BaseModel):
    """Request model for echo endpoint."""

    message: str = Field(description="Message to echo", min_length=1, max_length=1000)
    delay_ms: Optional[int] = Field(
        default=0, description="Artificial delay in milliseconds", ge=0, le=5000
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class EchoResponse(BaseModel):
    """Response model for echo endpoint."""

    message: str
    echo_message: str
    timestamp: datetime
    correlation_id: str
    metadata: Dict[str, Any]
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: str
    checks: Dict[str, bool]
    features: Dict[str, bool]


# Service layer
class EchoService:
    """Service for echo functionality."""

    def __init__(self):
        """Initialize service."""
        self.logger = structlog.get_logger()

    @traced("echo_message")
    async def echo(self, request: EchoRequest) -> Dict[str, Any]:
        """Echo the message with optional delay."""
        import asyncio
        import time

        start_time = time.time()
        correlation_id = get_or_create_correlation_id()

        self.logger.info(
            "echo_request_received",
            message_length=len(request.message),
            has_delay=request.delay_ms > 0,
            has_metadata=bool(request.metadata),
        )

        # Apply artificial delay if requested
        if request.delay_ms > 0:
            await asyncio.sleep(request.delay_ms / 1000.0)

        # Process the echo
        echo_message = request.message[::-1]  # Reverse the message as echo

        processing_time_ms = (time.time() - start_time) * 1000

        business_operations_total.labels(operation="echo", status="success").inc()

        self.logger.info(
            "echo_request_processed",
            processing_time_ms=processing_time_ms,
            correlation_id=str(correlation_id),
        )

        return {
            "message": request.message,
            "echo_message": echo_message,
            "timestamp": datetime.utcnow(),
            "correlation_id": str(correlation_id),
            "metadata": request.metadata,
            "processing_time_ms": processing_time_ms,
        }

    async def check_health(self) -> Dict[str, bool]:
        """Perform health checks."""
        checks = {
            "service": True,
            "echo_function": await self._test_echo(),
        }

        features = {
            "tracing": True,
            "metrics": True,
            "correlation_id": True,
            "structured_logging": True,
        }

        self.logger.info("health_check_performed", checks=checks, features=features)
        return {"checks": checks, "features": features}

    async def _test_echo(self) -> bool:
        """Test echo functionality."""
        try:
            test_request = EchoRequest(message="test")
            result = await self.echo(test_request)
            return result["echo_message"] == "tset"
        except Exception as e:
            self.logger.error("echo_test_failed", error=str(e))
            return False


# Create service instance
echo_service = EchoService()


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("service_starting", service_name=SERVICE_NAME)

    # Initialize telemetry
    init_telemetry()

    logger.info("service_started")

    yield

    logger.info("service_stopping")
    # Cleanup would go here
    logger.info("service_stopped")


# Service configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "echo-service")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")

# Create FastAPI app
app = FastAPI(
    title="Echo Service",
    description="A simple echo service with full observability",
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(ObservabilityMiddleware)
app.middleware("http")(track_metrics_middleware)


# API Endpoints
@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
async def health_check():
    """
    Health check endpoint.

    Returns service status and feature flags.
    """
    result = await echo_service.check_health()

    return HealthResponse(
        status="healthy" if all(result["checks"].values()) else "degraded",
        timestamp=datetime.utcnow(),
        version=SERVICE_VERSION,
        checks=result["checks"],
        features=result["features"],
    )


@app.post("/api/v1/echo", response_model=EchoResponse, tags=["echo"])
async def echo(
    request: EchoRequest,
    x_correlation_id: Optional[str] = Header(  # noqa: B008
        default=None, description="Correlation ID"
    ),
):
    """
    Echo endpoint that reverses the input message.

    Features:
    - Reverses the input message
    - Supports artificial delay for testing
    - Propagates correlation ID
    - Returns processing time
    """
    result = await echo_service.echo(request)

    return EchoResponse(**result)


@app.post("/api/v1/shout", response_model=EchoResponse, tags=["echo"])
async def shout(
    request: EchoRequest,
    x_correlation_id: Optional[str] = Header(  # noqa: B008
        default=None, description="Correlation ID"
    ),
):
    """
    Shout endpoint that returns the message in uppercase.

    Similar to echo but transforms to uppercase instead of reversing.
    """
    # Modify the request to uppercase
    uppercase_request = EchoRequest(
        message=request.message.upper(),
        delay_ms=request.delay_ms,
        metadata={**request.metadata, "shouted": True},
    )

    result = await echo_service.echo(uppercase_request)

    # Override echo_message to be uppercase instead of reversed
    result["echo_message"] = request.message.upper()

    return EchoResponse(**result)


@app.get("/api/v1/ping", tags=["echo"])
async def ping():
    """Return pong with timestamp and correlation ID."""
    return {
        "ping": "pong",
        "timestamp": datetime.utcnow(),
        "correlation_id": str(get_or_create_correlation_id()),
    }


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return JSONResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/", tags=["info"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "description": "Echo service with full observability",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "echo": "/api/v1/echo",
            "shout": "/api/v1/shout",
            "ping": "/api/v1/ping",
            "docs": "/docs",
        },
        "correlation_id": str(get_or_create_correlation_id()),
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with correlation ID."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "correlation_id": str(get_or_create_correlation_id()),
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions with correlation ID."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "correlation_id": str(get_or_create_correlation_id()),
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8007")),
        reload=os.getenv("ENV", "production") == "development",
    )
