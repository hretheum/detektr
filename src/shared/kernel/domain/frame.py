"""Frame domain model for tracking video frames through processing pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ProcessingState(Enum):
    """Frame processing states."""

    CAPTURED = "captured"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class FrameId:
    """Value object for frame identification."""

    value: str

    @classmethod
    def generate(cls, camera_id: str, timestamp: datetime) -> "FrameId":
        """Generate a new frame ID."""
        timestamp_str = timestamp.strftime("%Y%m%d%H%M%S%f")[:-3]
        sequence = str(uuid4()).split("-")[0]
        return cls(f"{timestamp_str}_{camera_id}_{sequence}")

    def __str__(self) -> str:
        """Return string representation of frame ID."""
        return self.value


@dataclass
class ProcessingStage:
    """Represents a stage in frame processing."""

    name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "in_progress"
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def complete(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Mark stage as completed."""
        self.completed_at = datetime.now()
        self.status = "completed"
        if metadata:
            self.metadata.update(metadata)

    def fail(self, error: str) -> None:
        """Mark stage as failed."""
        self.completed_at = datetime.now()
        self.status = "failed"
        self.error = error

    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate stage duration in milliseconds."""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() * 1000
        return None


@dataclass
class Frame:
    """Frame entity - aggregate root for frame tracking."""

    id: FrameId
    camera_id: str
    timestamp: datetime
    state: ProcessingState
    processing_stages: List[ProcessingStage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, camera_id: str, timestamp: Optional[datetime] = None) -> "Frame":
        """Create a new frame."""
        if timestamp is None:
            timestamp = datetime.now()

        frame_id = FrameId.generate(camera_id, timestamp)
        return cls(
            id=frame_id,
            camera_id=camera_id,
            timestamp=timestamp,
            state=ProcessingState.CAPTURED,
        )

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to frame."""
        self.metadata[key] = value
        self.updated_at = datetime.now()

    def start_processing_stage(
        self, stage_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessingStage:
        """Start a new processing stage."""
        stage = ProcessingStage(
            name=stage_name, started_at=datetime.now(), metadata=metadata or {}
        )
        self.processing_stages.append(stage)
        self.updated_at = datetime.now()
        return stage

    def get_current_stage(self) -> Optional[ProcessingStage]:
        """Get the current active processing stage."""
        for stage in reversed(self.processing_stages):
            if stage.status == "in_progress":
                return stage
        return None

    def transition_to(self, new_state: ProcessingState) -> None:
        """Transition frame to a new state."""
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid state transition from {self.state.value} to {new_state.value}"
            )

        self.state = new_state
        self.updated_at = datetime.now()

    def can_transition_to(self, target_state: ProcessingState) -> bool:
        """Check if transition to target state is valid."""
        valid_transitions = {
            ProcessingState.CAPTURED: [ProcessingState.QUEUED, ProcessingState.FAILED],
            ProcessingState.QUEUED: [
                ProcessingState.PROCESSING,
                ProcessingState.FAILED,
            ],
            ProcessingState.PROCESSING: [
                ProcessingState.COMPLETED,
                ProcessingState.FAILED,
            ],
            ProcessingState.COMPLETED: [],  # Terminal state
            ProcessingState.FAILED: [],  # Terminal state
        }

        transitions = valid_transitions.get(self.state, [])
        return target_state in transitions  # type: ignore[operator]

    def mark_as_failed(self, error: str) -> None:
        """Mark frame as failed with error."""
        current_stage = self.get_current_stage()
        if current_stage:
            current_stage.fail(error)

        self.transition_to(ProcessingState.FAILED)
        self.add_metadata("error", error)

    def mark_as_completed(self) -> None:
        """Mark frame as successfully completed."""
        current_stage = self.get_current_stage()
        if current_stage:
            current_stage.complete()

        self.transition_to(ProcessingState.COMPLETED)

    @property
    def total_processing_time_ms(self) -> float:
        """Calculate total processing time in milliseconds."""
        if not self.processing_stages:
            return 0.0

        total = 0.0
        for stage in self.processing_stages:
            if stage.duration_ms:
                total += stage.duration_ms
        return total

    @property
    def is_terminal(self) -> bool:
        """Check if frame is in terminal state."""
        return self.state in [ProcessingState.COMPLETED, ProcessingState.FAILED]

    def __repr__(self) -> str:
        """Return string representation of frame."""
        return f"Frame(id={self.id}, camera={self.camera_id}, state={self.state.value})"
