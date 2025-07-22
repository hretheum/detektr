"""
Domain models for frame metadata.

These models represent the core business entities for metadata storage.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class DetectionMetadata(BaseModel):
    """Metadata about AI detections in a frame."""

    faces: int = Field(ge=0, description="Number of faces detected")
    objects: List[str] = Field(
        default_factory=list, description="List of detected objects"
    )
    motion_score: float = Field(
        ge=0.0, le=1.0, description="Motion detection score (0-1)"
    )

    @field_validator("motion_score")
    @classmethod
    def validate_motion_score(cls, v: float) -> float:
        """Ensure motion score is in valid range."""
        if not 0 <= v <= 1:
            raise ValueError("motion_score must be between 0 and 1")
        return v


class ProcessingMetadata(BaseModel):
    """Metadata about frame processing performance."""

    capture_latency_ms: int = Field(ge=0, description="Time to capture frame in ms")
    processing_latency_ms: int = Field(ge=0, description="Time to process frame in ms")
    total_latency_ms: int = Field(ge=0, description="Total end-to-end latency in ms")

    @field_validator("capture_latency_ms", "processing_latency_ms", "total_latency_ms")
    @classmethod
    def validate_positive_latency(cls, v: int) -> int:
        """Ensure latency values are non-negative."""
        if v < 0:
            raise ValueError("Latency values must be non-negative")
        return v

    @model_validator(mode="after")
    def validate_total_latency(self) -> "ProcessingMetadata":
        """Ensure total latency is consistent with components."""
        if self.total_latency_ms < (
            self.capture_latency_ms + self.processing_latency_ms
        ):
            raise ValueError("total_latency_ms must be >= capture + processing")
        return self


class FrameMetadata(BaseModel):
    """Complete metadata for a single frame."""

    frame_id: str = Field(description="Unique frame identifier")
    timestamp: datetime = Field(description="Frame capture timestamp")
    camera_id: str = Field(description="Camera identifier")
    sequence_number: int = Field(ge=0, description="Frame sequence number")
    metadata: Dict[str, Any] = Field(description="Nested metadata structure")

    @field_validator("camera_id")
    @classmethod
    def validate_camera_id(cls, v: str) -> str:
        """Validate camera ID format."""
        if not re.match(r"^cam\d{2}$", v):
            raise ValueError(
                "Invalid camera_id format. Must be 'camXX' where XX is 2 digits"
            )
        return v

    @field_validator("sequence_number")
    @classmethod
    def validate_sequence_number(cls, v: int) -> int:
        """Ensure sequence number is non-negative."""
        if v < 0:
            raise ValueError("sequence_number must be non-negative")
        return v

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class FrameMetadataCreate(BaseModel):
    """DTO for creating new frame metadata."""

    camera_id: str = Field(description="Camera identifier")
    sequence_number: int = Field(ge=0, description="Frame sequence number")
    detections: DetectionMetadata = Field(description="Detection results")
    processing: ProcessingMetadata = Field(description="Processing metrics")
    trace_id: str = Field(description="Distributed trace ID")
    span_id: str = Field(description="Span ID within trace")

    @field_validator("camera_id")
    @classmethod
    def validate_camera_id(cls, v: str) -> str:
        """Validate camera ID format."""
        if not re.match(r"^cam\d{2}$", v):
            raise ValueError(
                "Invalid camera_id format. Must be 'camXX' where XX is 2 digits"
            )
        return v

    def generate_frame_id(self, timestamp: Optional[datetime] = None) -> str:
        """Generate unique frame ID."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        return f"{timestamp.isoformat()}_{self.camera_id}_{self.sequence_number:06d}"

    def to_frame_metadata(self, timestamp: Optional[datetime] = None) -> FrameMetadata:
        """Convert to FrameMetadata entity."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return FrameMetadata(
            frame_id=self.generate_frame_id(timestamp),
            timestamp=timestamp,
            camera_id=self.camera_id,
            sequence_number=self.sequence_number,
            metadata={
                "detections": self.detections.model_dump(),
                "processing": self.processing.model_dump(),
                "trace_id": self.trace_id,
                "span_id": self.span_id,
            },
        )


class FrameMetadataQuery(BaseModel):
    """DTO for querying frame metadata."""

    camera_id: Optional[str] = Field(None, description="Filter by camera ID")
    start_time: Optional[datetime] = Field(None, description="Start of time range")
    end_time: Optional[datetime] = Field(None, description="End of time range")
    min_motion_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Minimum motion score"
    )
    has_faces: Optional[bool] = Field(
        None, description="Filter frames with/without faces"
    )
    limit: int = Field(100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")

    @model_validator(mode="after")
    def validate_time_range(self) -> "FrameMetadataQuery":
        """Ensure time range is valid."""
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self
