"""Data models for Frame Buffer v2."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple


class BackpressureLevel(IntEnum):
    """Backpressure severity levels."""

    NORMAL = 0
    MODERATE = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class FrameReadyEvent:
    """Event published when frame is ready for processing."""

    frame_id: str
    camera_id: str
    timestamp: datetime
    size_bytes: int
    width: int
    height: int
    format: str
    trace_context: Dict[str, str]
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate frame data."""
        if not self.frame_id:
            raise ValueError("frame_id cannot be empty")

        if self.width <= 0 or self.height <= 0:
            raise ValueError("Invalid dimensions")

        if not 0 <= self.priority <= 10:
            raise ValueError("Priority must be between 0 and 10")

    def to_json(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "frame_id": self.frame_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "size_bytes": self.size_bytes,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "trace_context": self.trace_context,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, data: dict) -> "FrameReadyEvent":
        """Create instance from JSON data."""
        return cls(
            frame_id=data["frame_id"],
            camera_id=data["camera_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            size_bytes=data["size_bytes"],
            width=data["width"],
            height=data["height"],
            format=data["format"],
            trace_context=data["trace_context"],
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ProcessorRegistration:
    """Processor registration information."""

    id: str
    capabilities: List[str]
    capacity: int
    queue: str
    endpoint: Optional[str] = None
    health_endpoint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_process(self, capability: str) -> bool:
        """Check if processor has a specific capability."""
        return capability in self.capabilities

    def to_json(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "id": self.id,
            "capabilities": self.capabilities,
            "capacity": self.capacity,
            "queue": self.queue,
            "endpoint": self.endpoint,
            "health_endpoint": self.health_endpoint,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, data: dict) -> "ProcessorRegistration":
        """Create instance from JSON data."""
        return cls(
            id=data["id"],
            capabilities=data["capabilities"],
            capacity=data["capacity"],
            queue=data["queue"],
            endpoint=data.get("endpoint"),
            health_endpoint=data.get("health_endpoint"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ProcessorHealth:
    """Processor health information."""

    processor_id: str
    status: str  # healthy, degraded, unhealthy
    capacity_used: float  # 0.0 to 1.0
    frames_processed: int
    avg_processing_time_ms: float
    errors_last_minute: int
    last_health_check: datetime

    @property
    def is_healthy(self) -> bool:
        """Check if processor is healthy enough to receive frames."""
        return self.status in ["healthy", "degraded"]

    @property
    def is_overloaded(self) -> bool:
        """Check if processor is overloaded."""
        return self.capacity_used > 0.7

    def to_json(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "processor_id": self.processor_id,
            "status": self.status,
            "capacity_used": self.capacity_used,
            "frames_processed": self.frames_processed,
            "avg_processing_time_ms": self.avg_processing_time_ms,
            "errors_last_minute": self.errors_last_minute,
            "last_health_check": self.last_health_check.isoformat(),
        }


@dataclass
class ProcessorCapabilities:
    """Detailed processor capabilities."""

    capabilities: List[str]
    min_resolution: Tuple[int, int] = (0, 0)
    max_resolution: Tuple[int, int] = (7680, 4320)  # 8K
    supported_formats: List[str] = field(default_factory=lambda: ["jpeg", "png"])
    max_fps: int = 30
    gpu_required: bool = False

    def can_handle(self, capability: str) -> bool:
        """Check if processor can handle a capability."""
        return capability in self.capabilities

    def supports_resolution(self, width: int, height: int) -> bool:
        """Check if processor supports given resolution."""
        min_w, min_h = self.min_resolution
        max_w, max_h = self.max_resolution
        return min_w <= width <= max_w and min_h <= height <= max_h

    def supports_format(self, format: str) -> bool:
        """Check if processor supports given format."""
        return format in self.supported_formats


@dataclass
class QueueStats:
    """Queue statistics."""

    queue_name: str
    length: int
    pending: int
    consumers: int
    oldest_message_age_seconds: Optional[float] = None

    @property
    def is_healthy(self) -> bool:
        """Check if queue is in healthy state."""
        # Unhealthy if too many pending or messages too old
        if self.pending > 1000:
            return False
        if (
            self.oldest_message_age_seconds and self.oldest_message_age_seconds > 300
        ):  # 5 minutes
            return False
        return True


@dataclass
class OrchestratorState:
    """Orchestrator state information."""

    version: str
    start_time: datetime
    is_paused: bool
    consumption_rate: float  # 0.0 to 1.0
    backpressure_level: BackpressureLevel
    active_processors: int
    total_frames_routed: int
    frames_dropped: int

    def to_json(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "version": self.version,
            "start_time": self.start_time.isoformat(),
            "is_paused": self.is_paused,
            "consumption_rate": self.consumption_rate,
            "backpressure_level": self.backpressure_level.name,
            "active_processors": self.active_processors,
            "total_frames_routed": self.total_frames_routed,
            "frames_dropped": self.frames_dropped,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
        }
