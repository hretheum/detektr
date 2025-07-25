"""Frame metadata model for tracking frame lifecycle."""

from datetime import datetime
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class ProcessingStage(BaseModel):
    """A single processing stage in frame lifecycle."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description="Stage name (e.g., capture, decode, analyze)")
    service: str = Field(description="Service that processed this stage")
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        default="pending", description="Current status of this stage"
    )
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class FrameMetadata(BaseModel):
    """Complete metadata for a video frame."""

    model_config = ConfigDict(from_attributes=True)

    # Core identifiers
    frame_id: str = Field(description="Unique frame identifier")
    timestamp: datetime = Field(description="Frame capture timestamp")

    # Source information
    camera_id: Optional[str] = Field(default=None, description="Camera identifier")
    source_url: Optional[str] = Field(default=None, description="Source stream URL")

    # Frame properties
    resolution: Optional[Tuple[int, int]] = Field(
        default=None, description="Frame resolution (width, height)"
    )
    format: Optional[str] = Field(default=None, description="Video format (e.g., h264)")
    size_bytes: Optional[int] = Field(default=None, description="Frame size in bytes")

    # Tracing context
    trace_id: Optional[str] = Field(default=None, description="Distributed trace ID")
    span_id: Optional[str] = Field(default=None, description="Current span ID")
    parent_span_id: Optional[str] = Field(default=None, description="Parent span ID")

    # Processing tracking
    processing_stages: List[ProcessingStage] = Field(
        default_factory=list, description="List of processing stages"
    )

    # Additional metadata
    tags: dict = Field(default_factory=dict, description="Custom tags")

    def add_processing_stage(
        self,
        name: str,
        service: str,
        status: Literal["pending", "processing", "completed", "failed"] = "processing",
        **kwargs,
    ) -> ProcessingStage:
        """
        Add a new processing stage.

        Args:
            name: Stage name
            service: Service name
            status: Initial status
            **kwargs: Additional stage properties

        Returns:
            Created ProcessingStage
        """
        stage = ProcessingStage(name=name, service=service, status=status, **kwargs)
        self.processing_stages.append(stage)
        return stage

    def get_stage(self, name: str) -> Optional[ProcessingStage]:
        """Get processing stage by name."""
        for stage in self.processing_stages:
            if stage.name == name:
                return stage
        return None

    def complete_stage(
        self,
        name: str,
        status: Literal["completed", "failed"] = "completed",
        error: Optional[str] = None,
    ):
        """Mark a processing stage as complete."""
        stage = self.get_stage(name)
        if stage:
            stage.status = status
            stage.completed_at = datetime.now()
            if stage.started_at:
                duration = (
                    stage.completed_at - stage.started_at
                ).total_seconds() * 1000
                stage.duration_ms = duration
            if error:
                stage.error = error

    def to_json(self) -> str:
        """Serialize metadata to JSON."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "FrameMetadata":
        """Deserialize metadata from JSON."""
        return cls.model_validate_json(json_str)

    def to_trace_attributes(self) -> dict:
        """Convert metadata to OpenTelemetry trace attributes."""
        attributes = {
            "frame.id": self.frame_id,
            "frame.timestamp": self.timestamp.isoformat(),
        }

        if self.camera_id:
            attributes["camera.id"] = self.camera_id
        if self.resolution:
            attributes["frame.width"] = self.resolution[0]
            attributes["frame.height"] = self.resolution[1]
        if self.format:
            attributes["frame.format"] = self.format
        if self.size_bytes:
            attributes["frame.size_bytes"] = self.size_bytes

        # Add tags as attributes
        for key, value in self.tags.items():
            attributes[f"frame.tag.{key}"] = str(value)

        return attributes
