"""FastAPI service for sample processor."""
import os
from datetime import datetime
from typing import Any, Dict

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .main import SampleProcessor

# Create FastAPI app
app = FastAPI(
    title="Sample Processor Service",
    description="Example processor demonstrating BaseProcessor framework",
    version="1.0.0",
)

# Global processor instance
processor = None


class HealthStatus(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    service: str = "sample-processor"
    version: str = "1.0.0"
    details: Dict[str, Any] = {}


class ProcessRequest(BaseModel):
    """Frame processing request."""

    frame_data: str  # Base64 encoded frame
    metadata: Dict[str, Any] = {}


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
    global processor
    
    print("Starting Sample Processor Service...")
    
    # Create processor with configuration
    processor = SampleProcessor(
        detection_threshold=float(os.getenv("DETECTION_THRESHOLD", "0.5")),
        simulate_gpu=os.getenv("SIMULATE_GPU", "false").lower() == "true",
        processing_delay_ms=int(os.getenv("PROCESSING_DELAY_MS", "10")),
    )
    
    # Initialize processor
    await processor.initialize()
    print("Sample Processor Service ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global processor
    
    if processor:
        await processor.cleanup()
        print("Sample Processor Service shutdown complete")


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    global processor
    
    # Basic health check
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "details": {
            "processor_initialized": processor is not None and processor.is_initialized,
        }
    }
    
    # Add processor metrics if available
    if processor and processor.is_initialized:
        try:
            metrics = processor.get_metrics()
            health["details"]["metrics"] = {
                "frames_processed": metrics.get("frames_processed", 0),
                "active_frames": processor.active_frames,
            }
        except Exception as e:
            health["details"]["metrics_error"] = str(e)
    
    return HealthStatus(**health)


@app.post("/process", response_model=ProcessResponse)
async def process_frame(request: ProcessRequest):
    """Process a single frame."""
    global processor
    
    if not processor or not processor.is_initialized:
        raise HTTPException(status_code=503, detail="Processor not initialized")
    
    try:
        # Decode frame data (in real implementation)
        # For demo, create a random frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Add frame_id if not present
        metadata = request.metadata.copy()
        if "frame_id" not in metadata:
            metadata["frame_id"] = f"api_frame_{datetime.now().timestamp()}"
        
        # Process frame
        result = await processor.process(frame, metadata)
        
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
    global processor
    
    if not processor:
        raise HTTPException(status_code=503, detail="Processor not initialized")
    
    try:
        metrics = processor.get_metrics()
        state_stats = processor.state_machine.get_statistics()
        resource_stats = processor.resource_manager.get_allocation_stats()
        
        return {
            "processor_metrics": metrics,
            "state_statistics": state_stats,
            "resource_statistics": resource_stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


# Run with: uvicorn sample_processor.api:app --host 0.0.0.0 --port 8099