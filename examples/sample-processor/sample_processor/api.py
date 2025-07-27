"""FastAPI service for sample processor."""
import asyncio
import os
import signal
import time
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, validator

from .frame_consumer import FrameBufferConsumer
from .main import SampleProcessor

# Frame tracking
try:
    from frame_tracking import TraceContext

    FRAME_TRACKING_AVAILABLE = True
except ImportError:
    FRAME_TRACKING_AVAILABLE = False

# Create FastAPI app
app = FastAPI(
    title="Sample Processor Service",
    description="Example processor demonstrating BaseProcessor framework",
    version="1.0.0",
)

# Add CORS middleware for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Application state class to avoid global variables
class AppState:
    def __init__(self):
        self.processor: Optional[SampleProcessor] = None
        self.consumer: Optional[FrameBufferConsumer] = None
        self.shutdown_event = asyncio.Event()
        self.graceful_shutdown_timeout = 30  # seconds


app.state.app_state = AppState()


class HealthStatus(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    service: str = "sample-processor"
    version: str = "1.0.0"
    details: Dict[str, Any] = {}


class ProcessRequest(BaseModel):
    """Frame processing request."""

    frame_data: str = Field(
        ..., description="Base64 encoded frame data", max_length=10_000_000
    )  # ~7.5MB limit for base64
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Frame metadata")

    @validator("frame_data")
    def validate_frame_data(cls, v):
        if not v:
            raise ValueError("frame_data cannot be empty")
        # Basic base64 validation
        if not all(
            c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
            for c in v
        ):
            raise ValueError("Invalid base64 encoding")
        return v

    @validator("metadata")
    def validate_metadata(cls, v):
        # Limit metadata size to prevent abuse
        import json

        if len(json.dumps(v)) > 100_000:  # 100KB limit for metadata
            raise ValueError("Metadata too large")
        return v


class ProcessResponse(BaseModel):
    """Frame processing response."""

    frame_id: str
    detections: list
    total_objects: int
    processing_time_ms: float
    timestamp: str


@app.on_event("startup")
async def startup_event():
    """Initialize processor on startup."""
    app_state = app.state.app_state

    print("Starting Sample Processor Service...")

    # Register signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"Received signal {signum}, initiating graceful shutdown...")
        app_state.shutdown_event.set()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create processor with configuration
    app_state.processor = SampleProcessor(
        detection_threshold=float(os.getenv("DETECTION_THRESHOLD", "0.5")),
        simulate_gpu=os.getenv("SIMULATE_GPU", "false").lower() == "true",
        processing_delay_ms=int(os.getenv("PROCESSING_DELAY_MS", "10")),
    )

    # Initialize processor
    await app_state.processor.initialize()

    # Create and start consumer if enabled
    if os.getenv("ENABLE_FRAME_CONSUMER", "true").lower() == "true":
        app_state.consumer = FrameBufferConsumer(
            processor=app_state.processor,
            frame_buffer_url=os.getenv("FRAME_BUFFER_URL", "http://frame-buffer:8002"),
            batch_size=int(os.getenv("CONSUMER_BATCH_SIZE", "10")),
            poll_interval_ms=int(os.getenv("POLL_INTERVAL_MS", "100")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            backoff_ms=int(os.getenv("BACKOFF_MS", "1000")),
            connection_pool_size=int(os.getenv("CONNECTION_POOL_SIZE", "10")),
            connection_timeout=int(os.getenv("CONNECTION_TIMEOUT", "30")),
            read_timeout=int(os.getenv("READ_TIMEOUT", "60")),
        )
        await app_state.consumer.start()
        print("Frame consumer started")

    print("Sample Processor Service ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    app_state = app.state.app_state

    # Set shutdown event
    app_state.shutdown_event.set()

    # Create shutdown tasks with timeout
    shutdown_tasks = []

    # Stop consumer first
    if app_state.consumer:
        shutdown_tasks.append(app_state.consumer.stop())

    if app_state.processor:
        shutdown_tasks.append(app_state.processor.cleanup())

    # Wait for all shutdown tasks with timeout
    try:
        await asyncio.wait_for(
            asyncio.gather(*shutdown_tasks, return_exceptions=True),
            timeout=app_state.graceful_shutdown_timeout,
        )
        print("Sample Processor Service shutdown complete")
    except asyncio.TimeoutError:
        print(
            f"Graceful shutdown timed out after {app_state.graceful_shutdown_timeout}s, forcing shutdown"
        )


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    app_state = app.state.app_state

    # Basic health check
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "details": {
            "processor_initialized": app_state.processor is not None
            and app_state.processor.is_initialized,
            "consumer_enabled": os.getenv("ENABLE_FRAME_CONSUMER", "true").lower()
            == "true",
            "consumer_running": app_state.consumer is not None
            and hasattr(app_state.consumer, "_running")
            and app_state.consumer._running,
            "frame_buffer_url": app_state.consumer.frame_buffer_url
            if app_state.consumer
            else os.getenv("FRAME_BUFFER_URL", "http://frame-buffer:8002"),
            "shutting_down": app_state.shutdown_event.is_set(),
        },
    }

    # Add processor metrics if available
    if app_state.processor and app_state.processor.is_initialized:
        try:
            metrics = app_state.processor.get_metrics()
            health["details"]["metrics"] = {
                "frames_processed": metrics.get("frames_processed", 0),
                "active_frames": app_state.processor.active_frames,
            }
        except Exception as e:
            health["details"]["metrics_error"] = str(e)

    return HealthStatus(**health)


@app.post("/process", response_model=ProcessResponse)
async def process_frame(request: ProcessRequest, http_request: Request):
    """Process a single frame."""
    app_state = app.state.app_state

    # Check if shutting down
    if app_state.shutdown_event.is_set():
        raise HTTPException(status_code=503, detail="Service is shutting down")

    if not app_state.processor or not app_state.processor.is_initialized:
        raise HTTPException(status_code=503, detail="Processor not initialized")

    # Add request size validation
    content_length = http_request.headers.get("content-length")
    if content_length and int(content_length) > 10_000_000:  # 10MB limit
        raise HTTPException(status_code=413, detail="Request too large")

    try:
        # Decode frame data (in real implementation)
        # For demo, create a random frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Add frame_id if not present
        metadata = request.metadata.copy()
        if "frame_id" not in metadata:
            metadata["frame_id"] = f"api_frame_{datetime.now().timestamp()}"

        # Process frame
        result = await app_state.processor.process(frame, metadata)

        # Return response
        return ProcessResponse(
            frame_id=metadata["frame_id"],
            detections=result.get("detections", []),
            total_objects=result.get("total_objects", 0),
            processing_time_ms=result.get("processing_time_ms", 0),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/metrics")
async def get_metrics():
    """Get processor metrics."""
    app_state = app.state.app_state

    if not app_state.processor:
        raise HTTPException(status_code=503, detail="Processor not initialized")

    try:
        metrics = app_state.processor.get_metrics()
        state_stats = app_state.processor.state_machine.get_statistics()
        resource_stats = app_state.processor.resource_manager.get_allocation_stats()

        return {
            "processor_metrics": metrics,
            "state_statistics": state_stats,
            "resource_statistics": resource_stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@app.post("/process-with-tracking")
async def process_frame_with_tracking(request: ProcessRequest, http_request: Request):
    """Process frame with distributed tracing support."""
    app_state = app.state.app_state

    # Check if shutting down
    if app_state.shutdown_event.is_set():
        raise HTTPException(status_code=503, detail="Service is shutting down")

    if not app_state.processor or not app_state.processor.is_initialized:
        raise HTTPException(status_code=503, detail="Processor not initialized")

    if not FRAME_TRACKING_AVAILABLE:
        # Fallback to regular processing
        return await process_frame(request)

    try:
        # Create test frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Prepare metadata
        metadata = request.metadata.copy()
        frame_id = metadata.get("frame_id", f"api_frame_{datetime.now().timestamp()}")
        metadata["frame_id"] = frame_id

        # Use frame tracking
        with TraceContext.inject(frame_id) as ctx:
            ctx.add_event("sample_processor_api_start")
            ctx.set_attribute("api.endpoint", "/process-with-tracking")
            ctx.set_attribute("frame.shape", str(frame.shape))

            # Inject trace context into metadata
            ctx.inject_to_carrier(metadata)

            # Process with tracking (BaseProcessor has process_frame_with_tracking)
            result = await app_state.processor.process_frame_with_tracking(
                frame, metadata, frame_id
            )

            ctx.add_event("sample_processor_api_complete")
            ctx.set_attribute("result.detections", len(result.get("detections", [])))

            # Return response with trace context
            response = {
                "frame_tracking_enabled": True,
                "trace_id": ctx.trace_id,
                "frame_id": frame_id,
                "detections": result.get("detections", []),
                "total_objects": result.get("total_objects", 0),
                "processing_time_ms": result.get("processing_time_ms", 0),
                "timestamp": datetime.now().isoformat(),
            }

            # Inject trace context into response
            ctx.inject_to_carrier(response)
            return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# Run with: uvicorn sample_processor.api:app --host 0.0.0.0 --port 8099
