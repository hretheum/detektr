"""
Frame Tracking Service - Event Sourcing for frame processing pipeline.

This service implements:
- Event sourcing pattern for frame tracking
- TimescaleDB for time-series data
- Full observability with OpenTelemetry
- RESTful API for frame management
- Fixed database configuration
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from database import get_db, init_db
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from models import EventType, FrameEvent
from pydantic import BaseModel, Field
from repositories import FrameEventRepository
from sqlalchemy.ext.asyncio import AsyncSession
from telemetry import (
    ObservabilityMiddleware,
    get_or_create_correlation_id,
    init_telemetry,
    traced,
    track_metrics_middleware,
)

# Configure structured logging
logger = structlog.get_logger()


# API Models
class CreateFrameEventRequest(BaseModel):
    """Request model for creating a frame event."""

    frame_id: str = Field(description="Unique frame identifier")
    camera_id: str = Field(description="Camera identifier")
    event_type: EventType = Field(description="Type of event")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata"
    )


class FrameEventResponse(BaseModel):
    """Response model for frame event."""

    event_id: UUID
    frame_id: str
    camera_id: str
    event_type: EventType
    event_timestamp: datetime
    correlation_id: Optional[UUID]
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime


class FrameHistoryResponse(BaseModel):
    """Response model for frame history."""

    frame_id: str
    events: List[FrameEventResponse]
    total_events: int
    first_event: Optional[datetime]
    last_event: Optional[datetime]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: str
    database: bool
    checks: Dict[str, bool]


# Service layer
class FrameTrackingService:
    """Service for managing frame events."""

    def __init__(self):
        """Initialize frame tracking service."""
        self.logger = structlog.get_logger()

    @traced("create_frame_event")
    async def create_event(
        self, request: CreateFrameEventRequest, db: AsyncSession
    ) -> FrameEvent:
        """Create a new frame event."""
        correlation_id = get_or_create_correlation_id()

        self.logger.info(
            "creating_frame_event",
            frame_id=request.frame_id,
            camera_id=request.camera_id,
            event_type=request.event_type,
        )

        repo = FrameEventRepository(db)
        event = await repo.create_event(
            frame_id=request.frame_id,
            camera_id=request.camera_id,
            event_type=request.event_type,
            data=request.data,
            metadata=request.metadata or {},
            correlation_id=correlation_id,
        )

        self.logger.info(
            "frame_event_created",
            event_id=str(event.event_id),
            frame_id=event.frame_id,
        )

        return event

    @traced("get_frame_history")
    async def get_frame_history(
        self, frame_id: str, db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> FrameHistoryResponse:
        """Get complete history of a frame."""
        self.logger.info(
            "fetching_frame_history", frame_id=frame_id, limit=limit, offset=offset
        )

        repo = FrameEventRepository(db)
        events = await repo.get_frame_events(frame_id, limit, offset)
        total = await repo.count_frame_events(frame_id)

        if not events and offset == 0:
            raise HTTPException(status_code=404, detail=f"Frame {frame_id} not found")

        first_event = events[0].event_timestamp if events else None
        last_event = events[-1].event_timestamp if events else None

        return FrameHistoryResponse(
            frame_id=frame_id,
            events=[
                FrameEventResponse(
                    event_id=e.event_id,
                    frame_id=e.frame_id,
                    camera_id=e.camera_id,
                    event_type=e.event_type,
                    event_timestamp=e.event_timestamp,
                    correlation_id=e.correlation_id,
                    data=e.data,
                    metadata=e.event_metadata,
                    created_at=e.created_at,
                )
                for e in events
            ],
            total_events=total,
            first_event=first_event,
            last_event=last_event,
        )

    @traced("get_latest_frames")
    async def get_latest_frames(
        self, db: AsyncSession, camera_id: Optional[str] = None, limit: int = 10
    ) -> List[FrameEvent]:
        """Get latest frame events."""
        self.logger.info(
            "fetching_latest_frames", camera_id=camera_id or "all", limit=limit
        )

        repo = FrameEventRepository(db)
        return await repo.get_latest_events(camera_id=camera_id, limit=limit)

    @traced("health_check")
    async def check_health(self, db: AsyncSession) -> Dict[str, bool]:
        """Perform health checks."""
        checks = {
            "service": True,
            "database": await self._check_database(db),
        }

        self.logger.info("health_check_performed", checks=checks)
        return checks

    async def _check_database(self, db: AsyncSession) -> bool:
        """Check database connectivity."""
        try:
            from sqlalchemy import text

            await db.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error("database_health_check_failed", error=str(e))
            return False


# Create service instance
frame_tracking_service = FrameTrackingService()


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("service_starting", service_name="frame-tracking")

    # Initialize telemetry
    init_telemetry()

    # Initialize database
    await init_db()

    logger.info("service_started")

    yield

    logger.info("service_stopping")
    # Cleanup would go here
    logger.info("service_stopped")


# Create FastAPI app
app = FastAPI(
    title="Frame Tracking Service",
    description="Event sourcing service for frame processing pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(ObservabilityMiddleware)
app.middleware("http")(track_metrics_middleware)


# API Endpoints
@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
async def health_check(db: AsyncSession = Depends(get_db)):  # noqa: B008
    """
    Health check endpoint.

    Returns service status and database connectivity.
    """
    checks = await frame_tracking_service.check_health(db)

    return HealthResponse(
        status="healthy" if all(checks.values()) else "degraded",
        timestamp=datetime.utcnow(),
        version="0.1.0",
        database=checks.get("database", False),
        checks=checks,
    )


@app.post(
    "/api/v1/frames",
    response_model=FrameEventResponse,
    status_code=201,
    tags=["frames"],
)
async def create_frame_event(
    request: CreateFrameEventRequest, db: AsyncSession = Depends(get_db)  # noqa: B008
):
    """
    Create a new frame event.

    Records an event in the frame's history using event sourcing pattern.
    """
    event = await frame_tracking_service.create_event(request, db)

    return FrameEventResponse(
        event_id=event.event_id,
        frame_id=event.frame_id,
        camera_id=event.camera_id,
        event_type=event.event_type,
        event_timestamp=event.event_timestamp,
        correlation_id=event.correlation_id,
        data=event.data,
        metadata=event.event_metadata,
        created_at=event.created_at,
    )


@app.get(
    "/api/v1/frames/{frame_id}",
    response_model=FrameHistoryResponse,
    tags=["frames"],
)
async def get_frame_history(
    frame_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    limit: int = Query(default=100, ge=1, le=1000),  # noqa: B008
    offset: int = Query(default=0, ge=0),  # noqa: B008
):
    """
    Get complete history of a frame.

    Returns all events for a specific frame in chronological order.
    """
    return await frame_tracking_service.get_frame_history(frame_id, db, limit, offset)


@app.get(
    "/api/v1/frames",
    response_model=List[FrameEventResponse],
    tags=["frames"],
)
async def get_latest_frames(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    camera_id: Optional[str] = Query(  # noqa: B008
        default=None, description="Filter by camera ID"
    ),
    limit: int = Query(default=10, ge=1, le=100),  # noqa: B008
):
    """
    Get latest frame events.

    Returns most recent events, optionally filtered by camera.
    """
    events = await frame_tracking_service.get_latest_frames(db, camera_id, limit)

    return [
        FrameEventResponse(
            event_id=e.event_id,
            frame_id=e.frame_id,
            camera_id=e.camera_id,
            event_type=e.event_type,
            event_timestamp=e.event_timestamp,
            correlation_id=e.correlation_id,
            data=e.data,
            metadata=e.event_metadata,
            created_at=e.created_at,
        )
        for e in events
    ]


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
        "service": "frame-tracking",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "api": "/api/v1/frames",
            "docs": "/docs",
        },
        "correlation_id": str(get_or_create_correlation_id()),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8006")),
        reload=os.getenv("ENV", "production") == "development",
    )
