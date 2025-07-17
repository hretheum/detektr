"""Frame-related domain events."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .base import DomainEvent


@dataclass
class FrameCaptured(DomainEvent):
    """Event raised when a frame is captured from camera."""

    frame_id: str
    camera_id: str
    timestamp: datetime
    frame_size: Optional[Dict[str, int]] = None

    def __post_init__(self) -> None:
        """Initialize event type."""
        super().__post_init__()
        self.event_type = "frame.captured"


@dataclass
class FrameQueued(DomainEvent):
    """Event raised when a frame is queued for processing."""

    frame_id: str
    queue_name: str
    priority: int = 0

    def __post_init__(self) -> None:
        """Initialize event type."""
        super().__post_init__()
        self.event_type = "frame.queued"


@dataclass
class ProcessingStarted(DomainEvent):
    """Event raised when frame processing begins."""

    frame_id: str
    processor_id: str
    processing_type: str

    def __post_init__(self) -> None:
        """Initialize event type."""
        super().__post_init__()
        self.event_type = "frame.processing_started"


@dataclass
class ProcessingCompleted(DomainEvent):
    """Event raised when frame processing completes successfully."""

    frame_id: str
    processor_id: str
    processing_type: str
    duration_ms: float
    results: Dict[str, Any]

    def __post_init__(self) -> None:
        """Initialize event type."""
        super().__post_init__()
        self.event_type = "frame.processing_completed"


@dataclass
class ProcessingFailed(DomainEvent):
    """Event raised when frame processing fails."""

    frame_id: str
    processor_id: str
    processing_type: str
    error: str
    duration_ms: float
    retry_count: int = 0

    def __post_init__(self) -> None:
        """Initialize event type."""
        super().__post_init__()
        self.event_type = "frame.processing_failed"


@dataclass
class StageStarted(DomainEvent):
    """Event raised when a processing stage starts."""

    frame_id: str
    stage_name: str
    stage_index: int

    def __post_init__(self) -> None:
        """Initialize event type."""
        super().__post_init__()
        self.event_type = "frame.stage_started"


@dataclass
class StageCompleted(DomainEvent):
    """Event raised when a processing stage completes."""

    frame_id: str
    stage_name: str
    stage_index: int
    duration_ms: float
    output_metadata: Dict[str, Any]

    def __post_init__(self) -> None:
        """Initialize event type."""
        super().__post_init__()
        self.event_type = "frame.stage_completed"


@dataclass
class StageFailed(DomainEvent):
    """Event raised when a processing stage fails."""

    frame_id: str
    stage_name: str
    stage_index: int
    error: str
    duration_ms: float

    def __post_init__(self) -> None:
        """Initialize event type."""
        super().__post_init__()
        self.event_type = "frame.stage_failed"
