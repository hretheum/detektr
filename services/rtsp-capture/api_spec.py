"""
RTSP Capture Service API Specification

OpenAPI/Swagger documentation according to Phase 2 requirements.
This file defines the API before implementation (Design-First approach).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

# ========================
# REQUEST/RESPONSE MODELS
# ========================


class StreamProtocol(str, Enum):
    """Supported streaming protocols"""

    RTSP_TCP = "rtsp_tcp"
    RTSP_UDP = "rtsp_udp"
    HTTP = "http"


class StreamStatus(str, Enum):
    """Stream connection status"""

    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class RTSPStreamRequest(BaseModel):
    """Request model for RTSP stream configuration"""

    stream_url: str = Field(
        ...,
        description="RTSP stream URL",
        example="rtsp://admin:password@192.168.1.100:554/stream1",
        regex=r"^rtsp://.*",
    )
    camera_id: str = Field(
        ...,
        description="Unique camera identifier",
        example="cam_front_door",
        min_length=1,
        max_length=64,
    )
    protocol: StreamProtocol = Field(
        StreamProtocol.RTSP_TCP, description="Transport protocol to use"
    )
    fps_limit: int = Field(30, description="Maximum FPS to capture", ge=1, le=60)
    resolution_limit: Optional[str] = Field(
        None,
        description="Maximum resolution (WxH)",
        example="1920x1080",
        regex=r"^\d+x\d+$",
    )
    buffer_size: int = Field(
        30, description="Frame buffer size in seconds", ge=5, le=300
    )
    auto_reconnect: bool = Field(
        True, description="Enable automatic reconnection on failure"
    )
    reconnect_interval: int = Field(
        5, description="Reconnection interval in seconds", ge=1, le=60
    )
    timeout: int = Field(10, description="Connection timeout in seconds", ge=1, le=60)

    @validator("stream_url")
    def validate_stream_url(cls, v):
        """Validate RTSP URL format"""
        if not v.startswith("rtsp://"):
            raise ValueError("Stream URL must start with rtsp://")
        if len(v) < 10:
            raise ValueError("Stream URL too short")
        return v

    @validator("camera_id")
    def validate_camera_id(cls, v):
        """Validate camera ID format"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Camera ID must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v


class StreamConnectionResponse(BaseModel):
    """Response model for stream connection"""

    camera_id: str = Field(..., description="Camera identifier")
    status: StreamStatus = Field(..., description="Connection status")
    stream_url: str = Field(..., description="Stream URL")
    connected_at: Optional[datetime] = Field(None, description="Connection timestamp")
    stream_info: Optional[Dict[str, Any]] = Field(None, description="Stream metadata")
    error_message: Optional[str] = Field(
        None, description="Error details if status is error"
    )


class StreamInfoResponse(BaseModel):
    """Response model for stream information"""

    camera_id: str = Field(..., description="Camera identifier")
    status: StreamStatus = Field(..., description="Current status")
    stream_url: str = Field(..., description="Stream URL")
    connected_at: Optional[datetime] = Field(None, description="Connection timestamp")
    last_frame_at: Optional[datetime] = Field(None, description="Last frame timestamp")
    frames_captured: int = Field(0, description="Total frames captured")
    fps_current: float = Field(0.0, description="Current FPS")
    fps_average: float = Field(0.0, description="Average FPS")
    reconnect_count: int = Field(0, description="Number of reconnections")
    error_count: int = Field(0, description="Number of errors")
    buffer_usage: Dict[str, Any] = Field(
        default_factory=dict, description="Frame buffer usage statistics"
    )
    stream_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Stream technical metadata"
    )


class FrameRequest(BaseModel):
    """Request model for frame capture"""

    camera_id: str = Field(..., description="Camera identifier")
    format: str = Field("jpeg", description="Frame format", regex=r"^(jpeg|png|raw)$")
    quality: int = Field(85, description="JPEG quality (1-100)", ge=1, le=100)
    max_age: int = Field(1, description="Maximum frame age in seconds", ge=0, le=60)


class FrameResponse(BaseModel):
    """Response model for frame data"""

    camera_id: str = Field(..., description="Camera identifier")
    frame_id: str = Field(..., description="Unique frame identifier")
    timestamp: datetime = Field(..., description="Frame capture timestamp")
    format: str = Field(..., description="Frame format")
    width: int = Field(..., description="Frame width")
    height: int = Field(..., description="Frame height")
    size_bytes: int = Field(..., description="Frame size in bytes")
    data: Optional[str] = Field(None, description="Base64 encoded frame data")
    url: Optional[str] = Field(None, description="Frame download URL")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    uptime_seconds: int = Field(..., description="Service uptime")
    active_streams: int = Field(..., description="Number of active streams")
    total_frames: int = Field(..., description="Total frames processed")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    cpu_usage_percent: float = Field(..., description="CPU usage percentage")


class MetricsResponse(BaseModel):
    """Metrics response"""

    timestamp: datetime = Field(..., description="Metrics timestamp")
    streams: Dict[str, StreamInfoResponse] = Field(
        default_factory=dict, description="Per-stream metrics"
    )
    system: Dict[str, Any] = Field(default_factory=dict, description="System metrics")
    performance: Dict[str, Any] = Field(
        default_factory=dict, description="Performance metrics"
    )


# ========================
# ERROR RESPONSES
# ========================


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Error timestamp"
    )


# ========================
# API ROUTER DEFINITION
# ========================

router = APIRouter(prefix="/api/v1", tags=["rtsp-capture"])


# ========================
# STREAM MANAGEMENT
# ========================


@router.post(
    "/streams/connect",
    response_model=StreamConnectionResponse,
    status_code=201,
    summary="Connect to RTSP stream",
    description="""
    Establishes connection to an RTSP camera stream and starts frame capture.

    The service will:
    1. Validate the stream URL and parameters
    2. Attempt to connect to the RTSP stream
    3. Start frame capture and buffering
    4. Return connection status and stream information

    If auto_reconnect is enabled, the service will automatically
    reconnect on connection loss.
    """,
    responses={
        201: {"description": "Successfully connected to stream"},
        400: {
            "description": "Invalid stream URL or parameters",
            "model": ErrorResponse,
        },
        503: {"description": "Unable to connect to stream", "model": ErrorResponse},
        409: {"description": "Stream already connected", "model": ErrorResponse},
    },
)
async def connect_stream(
    request: RTSPStreamRequest,
    background_tasks: BackgroundTasks,
    # service: RTSPService = Depends(get_rtsp_service)  # Will be implemented
) -> StreamConnectionResponse:
    """Connect to RTSP stream and begin frame capture."""
    # Implementation will be added in next blocks
    pass


@router.delete(
    "/streams/{camera_id}",
    response_model=Dict[str, str],
    summary="Disconnect from RTSP stream",
    description="Stops frame capture and closes connection to the specified camera stream.",
    responses={
        200: {"description": "Stream disconnected successfully"},
        404: {"description": "Stream not found", "model": ErrorResponse},
    },
)
async def disconnect_stream(
    camera_id: str,
    # service: RTSPService = Depends(get_rtsp_service)  # Will be implemented
) -> Dict[str, str]:
    """Disconnect from RTSP stream."""
    # Implementation will be added in next blocks
    pass


@router.get(
    "/streams/{camera_id}",
    response_model=StreamInfoResponse,
    summary="Get stream information",
    description="Returns detailed information about the specified camera stream.",
    responses={
        200: {"description": "Stream information retrieved"},
        404: {"description": "Stream not found", "model": ErrorResponse},
    },
)
async def get_stream_info(
    camera_id: str,
    # service: RTSPService = Depends(get_rtsp_service)  # Will be implemented
) -> StreamInfoResponse:
    """Get information about a specific stream."""
    # Implementation will be added in next blocks
    pass


@router.get(
    "/streams",
    response_model=List[StreamInfoResponse],
    summary="List all active streams",
    description="Returns information about all currently active camera streams.",
    responses={
        200: {"description": "List of active streams"},
    },
)
async def list_streams(
    # service: RTSPService = Depends(get_rtsp_service)  # Will be implemented
) -> List[StreamInfoResponse]:
    """List all active streams."""
    # Implementation will be added in next blocks
    pass


# ========================
# FRAME CAPTURE
# ========================


@router.post(
    "/frames/capture",
    response_model=FrameResponse,
    summary="Capture current frame",
    description="""
    Captures the most recent frame from the specified camera stream.

    The frame can be returned in different formats:
    - jpeg: Compressed JPEG image
    - png: Compressed PNG image
    - raw: Raw RGB pixel data

    For large frames, the response may include a download URL
    instead of inline data.
    """,
    responses={
        200: {"description": "Frame captured successfully"},
        404: {"description": "Stream not found", "model": ErrorResponse},
        503: {"description": "No recent frames available", "model": ErrorResponse},
    },
)
async def capture_frame(
    request: FrameRequest,
    # service: RTSPService = Depends(get_rtsp_service)  # Will be implemented
) -> FrameResponse:
    """Capture current frame from stream."""
    # Implementation will be added in next blocks
    pass


@router.get(
    "/frames/{frame_id}",
    summary="Download frame by ID",
    description="Downloads a specific frame by its unique identifier.",
    responses={
        200: {"description": "Frame data", "content": {"image/jpeg": {}}},
        404: {"description": "Frame not found", "model": ErrorResponse},
        410: {"description": "Frame expired", "model": ErrorResponse},
    },
)
async def download_frame(
    frame_id: str,
    # service: RTSPService = Depends(get_rtsp_service)  # Will be implemented
):
    """Download frame by ID."""
    # Implementation will be added in next blocks
    pass


# ========================
# MONITORING
# ========================


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service health status and basic metrics.",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy", "model": ErrorResponse},
    },
)
async def health_check(
    # service: RTSPService = Depends(get_rtsp_service)  # Will be implemented
) -> HealthResponse:
    """Health check endpoint."""
    # Implementation will be added in next blocks
    pass


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get service metrics",
    description="Returns detailed metrics about streams and service performance.",
    responses={
        200: {"description": "Service metrics"},
    },
)
async def get_metrics(
    # service: RTSPService = Depends(get_rtsp_service)  # Will be implemented
) -> MetricsResponse:
    """Get service metrics."""
    # Implementation will be added in next blocks
    pass


# ========================
# CONFIGURATION
# ========================


@router.get(
    "/config",
    response_model=Dict[str, Any],
    summary="Get service configuration",
    description="Returns current service configuration.",
    responses={
        200: {"description": "Service configuration"},
    },
)
async def get_config(
    # service: RTSPService = Depends(get_rtsp_service)  # Will be implemented
) -> Dict[str, Any]:
    """Get service configuration."""
    # Implementation will be added in next blocks
    pass


@router.put(
    "/config",
    response_model=Dict[str, str],
    summary="Update service configuration",
    description="Updates service configuration (requires restart for some changes).",
    responses={
        200: {"description": "Configuration updated"},
        400: {"description": "Invalid configuration", "model": ErrorResponse},
    },
)
async def update_config(
    config: Dict[str, Any],
    # service: RTSPService = Depends(get_rtsp_service)  # Will be implemented
) -> Dict[str, str]:
    """Update service configuration."""
    # Implementation will be added in next blocks
    pass


# ========================
# FASTAPI APPLICATION
# ========================


def create_app() -> FastAPI:
    """Create FastAPI application with OpenAPI documentation"""
    app = FastAPI(
        title="RTSP Capture Service",
        description="""
        ## RTSP Video Stream Capture Service

        This service provides real-time capture and processing of RTSP video streams
        from IP cameras and other RTSP sources.

        ### Features
        - Connect to multiple RTSP streams simultaneously
        - Automatic reconnection on connection loss
        - Frame buffering with configurable size
        - Multiple frame formats (JPEG, PNG, Raw)
        - Real-time metrics and monitoring
        - Health checks and status reporting

        ### Performance Targets
        - Support for 8+ concurrent streams
        - < 100ms frame capture latency
        - 99.9% uptime with auto-recovery
        - Linear scaling with stream count

        ### Authentication
        Currently no authentication is required. In production,
        consider implementing API key or JWT authentication.
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "Detektor Team",
            "email": "team@detektor.dev",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    # Add CORS middleware
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add OpenTelemetry middleware
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)

    # Include router
    app.include_router(router)

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
