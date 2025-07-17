"""Example frame processor service with full observability.

This service demonstrates best practices for:
- Distributed tracing with OpenTelemetry
- Custom metrics for business logic
- Proper error handling and logging
- Health checks and monitoring
- Docker-ready deployment
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.examples.telemetry_service.processor import FrameProcessor  # noqa: E402
from src.examples.telemetry_service.storage import FrameStorage  # noqa: E402
from src.shared.telemetry import (  # noqa: E402
    get_metrics,
    instrument_app,
    setup_auto_instrumentation,
    setup_telemetry,
    traced,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Global service instances
frame_processor: FrameProcessor = None
frame_storage: FrameStorage = None
metrics = get_metrics("example_service")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle with proper startup/shutdown."""
    global frame_processor, frame_storage

    logger.info("Starting example frame processor service...")

    # Setup telemetry
    tracer, meter, _ = setup_telemetry("example-frame-processor", "1.0.0")
    setup_auto_instrumentation()

    # Initialize services
    frame_storage = FrameStorage()
    frame_processor = FrameProcessor(frame_storage)

    # Register shutdown handler
    def shutdown_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        asyncio.create_task(shutdown())

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("Example frame processor service started successfully")
    metrics.increment_frames_processed(0)  # Initialize counter

    yield

    # Cleanup
    logger.info("Shutting down example frame processor service...")
    if frame_processor:
        await frame_processor.shutdown()
    if frame_storage:
        await frame_storage.shutdown()
    logger.info("Example frame processor service stopped")


async def shutdown():
    """Graceful shutdown handler."""
    logger.info("Performing graceful shutdown...")
    # Add cleanup logic here


# Create FastAPI app with OpenTelemetry instrumentation
app = FastAPI(
    title="Example Frame Processor Service",
    description="Example service demonstrating full observability with OpenTelemetry",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument the FastAPI app
instrument_app(app)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    import time

    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Record request metrics
    metrics.record_processing_time(
        "http_request",
        process_time,
        {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
        },
    )

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with observability."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Record error metrics
    metrics.increment_errors(
        "unhandled_exception",
        {
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


@app.get("/health")
@traced
async def health_check():
    """Health check endpoint with tracing."""
    return {
        "status": "healthy",
        "service": "example-frame-processor",
        "version": "1.0.0",
    }


@app.get("/metrics")
@traced
async def get_service_metrics():
    """Get service-specific metrics."""
    return {
        "service": "example-frame-processor",
        "metrics": {
            "frames_processed": "Counter: total frames processed",
            "processing_duration": "Histogram: processing time per stage",
            "detections_total": "Counter: total detections by type",
            "errors_total": "Counter: total errors by type",
        },
        "prometheus_endpoint": "http://localhost:9090/metrics",
        "jaeger_endpoint": "http://localhost:16686",
    }


@app.post("/process")
@traced
async def process_frame(request: dict):
    """Process a frame with full observability."""
    if not frame_processor:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        # Extract frame data
        frame_id = request.get("frame_id")
        camera_id = request.get("camera_id", "unknown")
        frame_data = request.get("frame_data", {})

        if not frame_id:
            metrics.increment_errors("missing_frame_id")
            raise HTTPException(status_code=400, detail="frame_id is required")

        # Process frame
        result = await frame_processor.process_frame(frame_id, camera_id, frame_data)

        # Record success metrics
        metrics.increment_frames_processed(1, {"camera_id": camera_id})

        return {
            "status": "success",
            "frame_id": frame_id,
            "camera_id": camera_id,
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error processing frame: {e}", exc_info=True)
        metrics.increment_errors("processing_error", {"error_type": type(e).__name__})
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/frames/{frame_id}")
@traced
async def get_frame_results(frame_id: str):
    """Get processing results for a specific frame."""
    if not frame_storage:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        result = await frame_storage.get_frame_results(frame_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Frame not found")

        return {
            "frame_id": frame_id,
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving frame results: {e}", exc_info=True)
        metrics.increment_errors("retrieval_error", {"error_type": type(e).__name__})
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")


@app.get("/cameras/{camera_id}/stats")
@traced
async def get_camera_stats(camera_id: str):
    """Get processing statistics for a specific camera."""
    if not frame_storage:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        stats = await frame_storage.get_camera_stats(camera_id)
        return {
            "camera_id": camera_id,
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Error retrieving camera stats: {e}", exc_info=True)
        metrics.increment_errors("stats_error", {"error_type": type(e).__name__})
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")


@app.post("/simulate")
@traced
async def simulate_processing():
    """Simulate frame processing for testing observability."""
    if not frame_processor:
        raise HTTPException(status_code=503, detail="Service not ready")

    import random
    import time

    results = []

    # Simulate processing multiple frames
    for i in range(5):
        frame_id = f"sim_frame_{int(time.time())}_{i:03d}"
        camera_id = f"sim_camera_{random.randint(1, 3):03d}"

        frame_data = {
            "width": random.choice([1920, 1280, 640]),
            "height": random.choice([1080, 720, 480]),
            "format": "rgb24",
            "timestamp": time.time(),
        }

        try:
            result = await frame_processor.process_frame(
                frame_id, camera_id, frame_data
            )
            results.append(
                {
                    "frame_id": frame_id,
                    "camera_id": camera_id,
                    "status": "success",
                    "result": result,
                }
            )

            metrics.increment_frames_processed(1, {"camera_id": camera_id})

        except Exception as e:
            results.append(
                {
                    "frame_id": frame_id,
                    "camera_id": camera_id,
                    "status": "error",
                    "error": str(e),
                }
            )

            metrics.increment_errors(
                "simulation_error", {"error_type": type(e).__name__}
            )

    return {
        "simulation_results": results,
        "total_frames": len(results),
        "success_count": sum(1 for r in results if r["status"] == "success"),
    }


def main():
    """Run the service."""
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info(f"Starting example frame processor service on {host}:{port}")

    uvicorn.run(
        "src.examples.telemetry_service.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
