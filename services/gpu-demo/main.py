"""
GPU Demo Service - Simple ML inference service demonstrating GPU usage.

This service demonstrates:
- GPU utilization with PyTorch and YOLO
- Object detection on images
- Full observability with GPU metrics
- Proper error handling for GPU/CPU fallback
"""

import io
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel, Field
from telemetry import (
    ObservabilityMiddleware,
    get_or_create_correlation_id,
    gpu_inference_duration,
    gpu_inference_total,
    init_telemetry,
    model_load_duration,
    traced,
    track_metrics_middleware,
)
from ultralytics import YOLO

# Configure structured logging
logger = structlog.get_logger()

# Global model instance
model: Optional[YOLO] = None
device: str = "cpu"


# API Models
class DetectionResult(BaseModel):
    """Single detection result."""

    class_name: str
    confidence: float
    bbox: List[float] = Field(description="Bounding box [x1, y1, x2, y2]")


class InferenceResponse(BaseModel):
    """Response from inference endpoint."""

    image_size: List[int] = Field(description="Image dimensions [width, height]")
    detections: List[DetectionResult]
    inference_time_ms: float
    device_used: str
    gpu_memory_used_mb: Optional[float] = None
    model_name: str
    correlation_id: str
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: str
    checks: Dict[str, bool]
    gpu_info: Optional[Dict[str, Any]]


class GPUService:
    """Service for GPU operations and inference."""

    def __init__(self):
        """Initialize service."""
        self.logger = structlog.get_logger()
        self.model = None
        self.device = None

    async def initialize(self):
        """Initialize model and GPU."""
        start_time = time.time()

        try:
            # Check GPU availability
            if torch.cuda.is_available():
                self.device = "cuda"
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = (
                    torch.cuda.get_device_properties(0).total_memory / 1024**3
                )
                self.logger.info(
                    "gpu_available",
                    device_name=gpu_name,
                    memory_gb=f"{gpu_memory:.2f}",
                )
            else:
                self.device = "cpu"
                self.logger.warning("gpu_not_available", fallback="cpu")

            # Load YOLO model
            self.logger.info("loading_model", model="yolov8n")
            self.model = YOLO("yolov8n.pt")  # Nano model for demo
            self.model.to(self.device)

            # Warm up model
            dummy_image = torch.zeros((1, 3, 640, 640)).to(self.device)
            _ = self.model(dummy_image, verbose=False)

            load_time = time.time() - start_time
            model_load_duration.observe(load_time)

            self.logger.info(
                "model_loaded",
                device=self.device,
                load_time_s=f"{load_time:.2f}",
            )

        except Exception as e:
            self.logger.error("model_initialization_failed", error=str(e))
            raise

    @traced("process_image")
    async def process_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Process image and return detections."""
        start_time = time.time()
        correlation_id = get_or_create_correlation_id()

        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != "RGB":
                image = image.convert("RGB")

            original_size = list(image.size)

            self.logger.info(
                "processing_image",
                size=original_size,
                device=self.device,
            )

            # Get GPU memory before inference
            gpu_memory_before = 0
            if self.device == "cuda":
                torch.cuda.synchronize()
                gpu_memory_before = torch.cuda.memory_allocated() / 1024**2

            # Run inference
            results = self.model(image, verbose=False)

            # Get GPU memory after inference
            gpu_memory_used = 0
            if self.device == "cuda":
                torch.cuda.synchronize()
                gpu_memory_after = torch.cuda.memory_allocated() / 1024**2
                gpu_memory_used = gpu_memory_after - gpu_memory_before

            # Process results
            detections = []
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        detection = DetectionResult(
                            class_name=self.model.names[int(box.cls)],
                            confidence=float(box.conf),
                            bbox=box.xyxy[0].tolist(),
                        )
                        detections.append(detection)

            inference_time = (time.time() - start_time) * 1000

            # Track metrics
            gpu_inference_duration.labels(device=self.device).observe(
                inference_time / 1000
            )
            gpu_inference_total.labels(device=self.device, status="success").inc()

            self.logger.info(
                "inference_completed",
                num_detections=len(detections),
                inference_time_ms=f"{inference_time:.2f}",
                gpu_memory_mb=f"{gpu_memory_used:.2f}"
                if self.device == "cuda"
                else "N/A",
            )

            return {
                "image_size": original_size,
                "detections": [d.dict() for d in detections],
                "inference_time_ms": inference_time,
                "device_used": self.device,
                "gpu_memory_used_mb": gpu_memory_used
                if self.device == "cuda"
                else None,
                "model_name": "yolov8n",
                "correlation_id": str(correlation_id),
                "timestamp": datetime.utcnow(),
            }

        except Exception as e:
            gpu_inference_total.labels(device=self.device, status="error").inc()
            self.logger.error("inference_failed", error=str(e))
            raise

    async def get_gpu_info(self) -> Optional[Dict[str, Any]]:
        """Get current GPU information."""
        if not torch.cuda.is_available():
            return None

        try:
            return {
                "device_name": torch.cuda.get_device_name(0),
                "device_count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
                "memory_allocated_mb": torch.cuda.memory_allocated() / 1024**2,
                "memory_reserved_mb": torch.cuda.memory_reserved() / 1024**2,
                "memory_total_mb": torch.cuda.get_device_properties(0).total_memory
                / 1024**2,
                "cuda_version": torch.version.cuda,
                "cudnn_version": torch.backends.cudnn.version(),
            }
        except Exception as e:
            self.logger.error("gpu_info_failed", error=str(e))
            return None

    async def check_health(self) -> Dict[str, Any]:
        """Perform health checks."""
        checks = {
            "service": True,
            "model_loaded": self.model is not None,
            "gpu_available": torch.cuda.is_available(),
            "inference_test": await self._test_inference(),
        }

        gpu_info = await self.get_gpu_info()

        self.logger.info("health_check_performed", checks=checks)
        return {"checks": checks, "gpu_info": gpu_info}

    async def _test_inference(self) -> bool:
        """Test inference with dummy image."""
        try:
            # Create small test image
            test_image = Image.new("RGB", (224, 224), color="white")
            img_bytes = io.BytesIO()
            test_image.save(img_bytes, format="JPEG")
            img_bytes.seek(0)

            result = await self.process_image(img_bytes.getvalue())
            return "inference_time_ms" in result
        except Exception as e:
            self.logger.error("inference_test_failed", error=str(e))
            return False


# Create service instance
gpu_service = GPUService()


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("service_starting", service_name=SERVICE_NAME)

    # Initialize telemetry
    init_telemetry()

    # Initialize GPU service
    await gpu_service.initialize()

    logger.info("service_started", device=gpu_service.device)

    yield

    logger.info("service_stopping")
    # Cleanup
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("service_stopped")


# Service configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "gpu-demo")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")

# Create FastAPI app
app = FastAPI(
    title="GPU Demo Service",
    description="ML inference service demonstrating GPU utilization",
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

    Returns service status, GPU info, and feature checks.
    """
    result = await gpu_service.check_health()

    return HealthResponse(
        status="healthy" if all(result["checks"].values()) else "degraded",
        timestamp=datetime.utcnow(),
        version=SERVICE_VERSION,
        checks=result["checks"],
        gpu_info=result["gpu_info"],
    )


@app.post("/api/v1/inference", response_model=InferenceResponse, tags=["inference"])
async def run_inference(
    image: UploadFile = File(  # noqa: B008
        description="Image file for object detection"
    ),
):
    """
    Run object detection on uploaded image.

    Accepts common image formats (JPEG, PNG, etc).
    Returns detected objects with bounding boxes and confidence scores.
    """
    # Validate file type
    if not image.content_type.startswith("image/"):
        raise HTTPException(400, f"Invalid file type: {image.content_type}")

    # Read image
    contents = await image.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(400, "Image too large (max 10MB)")

    # Process image
    result = await gpu_service.process_image(contents)

    return InferenceResponse(**result)


@app.get("/api/v1/gpu/info", tags=["monitoring"])
async def gpu_info():
    """Get current GPU status and memory usage."""
    info = await gpu_service.get_gpu_info()

    if info is None:
        return {
            "gpu_available": False,
            "message": "No GPU available, running on CPU",
            "correlation_id": str(get_or_create_correlation_id()),
        }

    return {
        "gpu_available": True,
        "info": info,
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
        "description": "GPU demo service with YOLO object detection",
        "device": gpu_service.device,
        "model": "yolov8n" if gpu_service.model else "not loaded",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "inference": "/api/v1/inference",
            "gpu_info": "/api/v1/gpu/info",
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
        port=int(os.getenv("PORT", "8008")),
        reload=os.getenv("ENV", "production") == "development",
    )
