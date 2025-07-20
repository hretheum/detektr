"""Database models for frame tracking service."""

from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class EventType(str, Enum):
    """Types of frame events."""

    CAPTURED = "captured"
    QUEUED = "queued"
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"
    PROCESSING_FAILED = "processing_failed"
    FACE_DETECTED = "face_detected"
    OBJECT_DETECTED = "object_detected"
    GESTURE_DETECTED = "gesture_detected"
    ACTION_TRIGGERED = "action_triggered"
    STORED = "stored"
    DELETED = "deleted"
    ERROR = "error"


class FrameEvent(Base):
    """Frame event model for event sourcing."""

    __tablename__ = "frame_events"
    __table_args__ = {"schema": "tracking"}

    # Composite primary key for TimescaleDB
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    event_timestamp = Column(
        DateTime(timezone=True),
        primary_key=True,
        default=func.now(),
        nullable=False,
    )

    # Event data
    event_id = Column(PGUUID(as_uuid=True), default=uuid4, nullable=False, unique=True)
    frame_id = Column(String, nullable=False, index=True)
    camera_id = Column(String, nullable=False, index=True)
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    correlation_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)

    # JSON data
    data = Column(JSON, nullable=False, default=dict)
    metadata = Column(JSON, nullable=False, default=dict)

    # Audit
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    def __repr__(self):
        """Return string representation of FrameEvent."""
        return (
            f"<FrameEvent(frame_id={self.frame_id}, "
            f"event_type={self.event_type}, "
            f"timestamp={self.event_timestamp})>"
        )
