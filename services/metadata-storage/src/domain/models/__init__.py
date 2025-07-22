"""Domain models for metadata storage."""

from .frame_metadata import (
    DetectionMetadata,
    FrameMetadata,
    FrameMetadataCreate,
    FrameMetadataQuery,
    ProcessingMetadata,
)

__all__ = [
    "FrameMetadata",
    "DetectionMetadata",
    "ProcessingMetadata",
    "FrameMetadataCreate",
    "FrameMetadataQuery",
]
