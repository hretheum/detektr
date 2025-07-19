"""
Example OpenTelemetry Service - FastAPI application with full observability.

This service demonstrates:
- OpenTelemetry tracing with Jaeger
- Prometheus metrics export
- Structured logging with correlation IDs
- Clean architecture patterns
- Health checks and monitoring
"""

import asyncio
import os
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from telemetry import (
    ObservabilityMiddleware,
    active_requests,
    get_or_create_correlation_id,
    init_metrics,
    request_counter,
    request_duration,
    setup_telemetry,
    traced,
)


# Models
class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(description="Service health status")
    timestamp: datetime = Field(description="Current timestamp")
    version: str = Field(description="Service version")
    checks: Dict[str, bool] = Field(description="Individual health checks")


class ProcessingRequest(BaseModel):
    """Example processing request."""

    data: str = Field(description="Data to process")
    delay_ms: Optional[int] = Field(
        default=None, description="Artificial delay in milliseconds"
    )
    fail_probability: Optional[float] = Field(
        default=0.0, description="Probability of failure (0.0-1.0)"
    )


class ProcessingResponse(BaseModel):
    """Example processing response."""

    correlation_id: str = Field(description="Request correlation ID")
    original_data: str = Field(description="Original input data")
    processed_data: str = Field(description="Processed result")
    processing_time_ms: float = Field(description="Processing time in milliseconds")


# Service layer
class ProcessingService:
    """Example service demonstrating clean architecture."""

    def __init__(self):
        """Initialize processing service."""
        self.logger = structlog.get_logger()
        self.processing_count = 0

    @traced("process_data")
    async def process_data(self, request: ProcessingRequest) -> ProcessingResponse:
        """Process data with simulated work and potential failures."""
        start_time = time.time()
        correlation_id = get_or_create_correlation_id()

        self.logger.info(
            "processing_started",
            data_length=len(request.data),
            delay_ms=request.delay_ms,
            fail_probability=request.fail_probability,
        )

        # Simulate processing with optional delay
        if request.delay_ms:
            await asyncio.sleep(request.delay_ms / 1000.0)

        # Simulate potential failure
        if request.fail_probability > 0 and random.random() < request.fail_probability:
            self.logger.error("processing_failed", reason="simulated_failure")
            raise HTTPException(status_code=500, detail="Processing failed (simulated)")

        # Simulate actual processing
        processed = request.data.upper()[::-1]  # Reverse and uppercase
        self.processing_count += 1

        processing_time = (time.time() - start_time) * 1000

        self.logger.info(
            "processing_completed",
            processing_time_ms=processing_time,
            total_processed=self.processing_count,
        )

        return ProcessingResponse(
            correlation_id=correlation_id,
            original_data=request.data,
            processed_data=processed,
            processing_time_ms=processing_time,
        )

    @traced("health_check")
    async def check_health(self) -> Dict[str, bool]:
        """Perform health checks."""
        checks = {
            "service": True,
            "memory": self._check_memory(),
            "processing": True,  # Always healthy for demo
        }

        self.logger.info("health_check_performed", checks=checks)
        return checks

    def _check_memory(self) -> bool:
        """Check if memory usage is acceptable."""
        import psutil

        memory_percent = psutil.virtual_memory().percent
        return memory_percent < 90  # Healthy if under 90%


# Dependency injection
def get_processing_service() -> ProcessingService:
    """Dependency provider for processing service."""
    return processing_service


# Create dependency instances
_processing_service_dependency = Depends(get_processing_service)


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger = structlog.get_logger()
    logger.info("service_starting", service_name="example-otel")

    # Setup telemetry
    tracer, meter = setup_telemetry()
    init_metrics(meter)

    # Initialize services
    global processing_service
    processing_service = ProcessingService()

    logger.info("service_started")

    yield

    logger.info("service_stopping")
    # Cleanup would go here
    logger.info("service_stopped")


# Create FastAPI app
app = FastAPI(
    title="Example OpenTelemetry Service",
    description="Minimal service demonstrating full observability stack",
    version="0.1.0",
    lifespan=lifespan,
)

# Add observability middleware
app.add_middleware(ObservabilityMiddleware)


# Middleware for metrics
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    """Track HTTP metrics for all requests."""
    if request.url.path == "/metrics":
        # Skip metrics endpoint to avoid recursion
        return await call_next(request)

    # Record active requests
    active_requests.add(1, {"method": request.method, "endpoint": request.url.path})

    start_time = time.time()
    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Record metrics
        request_counter.add(
            1,
            {
                "method": request.method,
                "endpoint": request.url.path,
                "status": response.status_code,
            },
        )
        request_duration.record(
            duration,
            {
                "method": request.method,
                "endpoint": request.url.path,
            },
        )

        return response
    finally:
        active_requests.add(
            -1, {"method": request.method, "endpoint": request.url.path}
        )


# API Endpoints
@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
async def health_check(service: ProcessingService = _processing_service_dependency):
    """
    Health check endpoint.

    Returns service status and individual component health.
    """
    checks = await service.check_health()
    current_time = datetime.utcnow()

    return HealthResponse(
        status="healthy" if all(checks.values()) else "degraded",
        timestamp=current_time,
        version="0.1.0",
        checks=checks,
    )


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """
    Prometheus metrics endpoint.

    Exports all collected metrics in Prometheus format.
    """
    return JSONResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/process", response_model=ProcessingResponse, tags=["processing"])
async def process_data(
    request: ProcessingRequest,
    service: ProcessingService = _processing_service_dependency,
):
    """
    Process data endpoint.

    Demonstrates tracing, metrics, and error handling.

    - **data**: Input data to process
    - **delay_ms**: Optional artificial delay to simulate slow processing
    - **fail_probability**: Optional failure probability (0.0-1.0) for testing
    """
    return await service.process_data(request)


@app.get("/", tags=["info"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "example-otel",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "process": "/process",
            "docs": "/docs",
        },
        "correlation_id": get_or_create_correlation_id(),
    }


# Example of a more complex traced operation
@traced("complex_operation")
async def complex_operation(steps: int = 5):
    """Execute operation with multiple traced steps."""
    logger = structlog.get_logger()
    results = []

    for i in range(steps):
        # Each step is also traced
        result = await process_step(i)
        results.append(result)

    logger.info("complex_operation_completed", steps=steps, results=results)
    return results


@traced("process_step")
async def process_step(step_number: int) -> Dict[str, Any]:
    """Individual step in complex operation."""
    # Simulate some work
    await asyncio.sleep(random.uniform(0.01, 0.1))

    current_time = datetime.utcnow()
    return {
        "step": step_number,
        "result": f"processed_{step_number}",
        "timestamp": current_time.isoformat(),
    }


@app.post("/complex", tags=["processing"])
async def run_complex_operation(steps: int = 5):
    """Execute complex multi-step operation with nested tracing."""
    if steps < 1 or steps > 20:
        raise HTTPException(status_code=400, detail="Steps must be between 1 and 20")

    results = await complex_operation(steps)

    return {
        "correlation_id": get_or_create_correlation_id(),
        "steps_completed": len(results),
        "results": results,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "production") == "development",
        log_config=None,  # Disable default logging, we use structlog
    )
