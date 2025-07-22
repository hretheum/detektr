"""Domain events for frame tracking."""

from .base import DomainEvent
from .frame_events import (
    FrameCaptured,
    FrameQueued,
    ProcessingCompleted,
    ProcessingFailed,
    ProcessingStarted,
    StageCompleted,
    StageFailed,
    StageStarted,
)

__all__ = [
    "DomainEvent",
    "FrameCaptured",
    "FrameQueued",
    "ProcessingStarted",
    "ProcessingCompleted",
    "ProcessingFailed",
    "StageStarted",
    "StageCompleted",
    "StageFailed",
]
