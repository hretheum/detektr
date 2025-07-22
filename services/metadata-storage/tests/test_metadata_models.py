"""
Test suite for metadata domain models.

Following TDD approach - tests written before implementation.
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

# These imports will be created next
from src.domain.models.frame_metadata import (
    DetectionMetadata,
    FrameMetadata,
    FrameMetadataCreate,
    FrameMetadataQuery,
    ProcessingMetadata,
)


class TestFrameMetadataModels:
    """Test suite for frame metadata domain models."""

    def test_frame_metadata_creation_with_valid_data(self):
        """Test creating frame metadata with all valid fields."""
        # Arrange
        frame_id = f"{datetime.now(timezone.utc).isoformat()}_cam01_000123"
        metadata = {
            "detections": {
                "faces": 2,
                "objects": ["person", "car"],
                "motion_score": 0.85,
            },
            "processing": {
                "capture_latency_ms": 15,
                "processing_latency_ms": 45,
                "total_latency_ms": 60,
            },
            "trace_id": str(uuid4()),
            "span_id": str(uuid4())[:16],
        }

        # Act
        frame = FrameMetadata(
            frame_id=frame_id,
            timestamp=datetime.now(timezone.utc),
            camera_id="cam01",
            sequence_number=123,
            metadata=metadata,
        )

        # Assert
        assert frame.frame_id == frame_id
        assert frame.camera_id == "cam01"
        assert frame.sequence_number == 123
        assert frame.metadata["detections"]["faces"] == 2
        assert frame.metadata["detections"]["motion_score"] == 0.85

    def test_frame_metadata_validation_invalid_camera_id(self):
        """Test that invalid camera ID raises validation error."""
        # Arrange
        frame_id = f"{datetime.now(timezone.utc).isoformat()}_invalid_cam_000123"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid camera_id format"):
            FrameMetadata(
                frame_id=frame_id,
                timestamp=datetime.now(timezone.utc),
                camera_id="invalid cam",  # Contains space
                sequence_number=123,
                metadata={},
            )

    def test_frame_metadata_validation_negative_sequence(self):
        """Test that negative sequence number raises validation error."""
        # Act & Assert
        from pydantic import ValidationError

        with pytest.raises(
            ValidationError, match="Input should be greater than or equal to 0"
        ):
            FrameMetadata(
                frame_id="test_frame",
                timestamp=datetime.now(timezone.utc),
                camera_id="cam01",
                sequence_number=-1,
                metadata={},
            )

    def test_detection_metadata_model(self):
        """Test detection metadata nested model."""
        # Arrange & Act
        detection = DetectionMetadata(
            faces=3, objects=["person", "bicycle", "dog"], motion_score=0.92
        )

        # Assert
        assert detection.faces == 3
        assert len(detection.objects) == 3
        assert detection.motion_score == 0.92

    def test_detection_metadata_validation_motion_score_range(self):
        """Test motion score must be between 0 and 1."""
        # Act & Assert
        from pydantic import ValidationError

        with pytest.raises(
            ValidationError, match="Input should be less than or equal to 1"
        ):
            DetectionMetadata(faces=0, objects=[], motion_score=1.5)  # Invalid

    def test_processing_metadata_model(self):
        """Test processing metadata nested model."""
        # Arrange & Act
        processing = ProcessingMetadata(
            capture_latency_ms=20, processing_latency_ms=55, total_latency_ms=75
        )

        # Assert
        assert processing.capture_latency_ms == 20
        assert processing.processing_latency_ms == 55
        assert processing.total_latency_ms == 75

    def test_processing_metadata_validation_negative_latency(self):
        """Test that negative latency values raise validation error."""
        # Act & Assert
        from pydantic import ValidationError

        with pytest.raises(
            ValidationError, match="Input should be greater than or equal to 0"
        ):
            ProcessingMetadata(
                capture_latency_ms=-5, processing_latency_ms=10, total_latency_ms=5
            )

    def test_processing_metadata_validation_total_latency_consistency(self):
        """Test that total latency must be >= sum of components."""
        # Act & Assert
        from pydantic import ValidationError

        with pytest.raises(
            ValidationError, match="total_latency_ms must be >= capture"
        ):
            ProcessingMetadata(
                capture_latency_ms=50,
                processing_latency_ms=60,
                total_latency_ms=100,  # Should be at least 110
            )

    def test_frame_metadata_create_dto(self):
        """Test frame metadata creation DTO."""
        # Arrange
        data = {
            "camera_id": "cam05",
            "sequence_number": 12345,
            "detections": {"faces": 1, "objects": ["person"], "motion_score": 0.65},
            "processing": {
                "capture_latency_ms": 18,
                "processing_latency_ms": 42,
                "total_latency_ms": 60,
            },
            "trace_id": str(uuid4()),
            "span_id": str(uuid4())[:16],
        }

        # Act
        create_dto = FrameMetadataCreate(**data)

        # Assert
        assert create_dto.camera_id == "cam05"
        assert create_dto.sequence_number == 12345
        assert create_dto.generate_frame_id().startswith(
            datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )

    def test_frame_metadata_query_dto(self):
        """Test frame metadata query DTO."""
        # Arrange & Act
        start = datetime.now(timezone.utc)
        query = FrameMetadataQuery(
            camera_id="cam02",
            start_time=start,
            end_time=start.replace(hour=start.hour + 1),
            min_motion_score=0.5,
            has_faces=True,
            limit=100,
        )

        # Assert
        assert query.camera_id == "cam02"
        assert query.min_motion_score == 0.5
        assert query.has_faces is True
        assert query.limit == 100

    def test_frame_metadata_query_validation_time_range(self):
        """Test that end_time must be after start_time."""
        # Arrange
        start = datetime.now(timezone.utc)
        end = start.replace(hour=start.hour - 1)  # 1 hour before

        # Act & Assert
        with pytest.raises(ValueError, match="end_time must be after start_time"):
            FrameMetadataQuery(start_time=start, end_time=end)

    def test_frame_metadata_serialization(self):
        """Test frame metadata can be serialized to JSON."""
        # Arrange
        frame = FrameMetadata(
            frame_id="test_frame_123",
            timestamp=datetime.now(timezone.utc),
            camera_id="cam01",
            sequence_number=123,
            metadata={
                "detections": {"faces": 1, "objects": ["person"], "motion_score": 0.75},
                "processing": {
                    "capture_latency_ms": 20,
                    "processing_latency_ms": 40,
                    "total_latency_ms": 60,
                },
            },
        )

        # Act
        json_str = frame.model_dump_json()
        parsed = json.loads(json_str)

        # Assert
        assert parsed["frame_id"] == "test_frame_123"
        assert parsed["camera_id"] == "cam01"
        assert parsed["metadata"]["detections"]["motion_score"] == 0.75

    def test_frame_metadata_from_dict(self):
        """Test creating frame metadata from dictionary."""
        # Arrange
        data = {
            "frame_id": "2024-01-20T10:15:30.123456Z_cam03_000456",
            "timestamp": "2024-01-20T10:15:30.123456Z",
            "camera_id": "cam03",
            "sequence_number": 456,
            "metadata": {
                "detections": {"faces": 0, "objects": [], "motion_score": 0.12},
                "processing": {
                    "capture_latency_ms": 25,
                    "processing_latency_ms": 35,
                    "total_latency_ms": 60,
                },
                "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                "span_id": "64e8400-e29b-41d4",
            },
        }

        # Act
        frame = FrameMetadata.model_validate(data)

        # Assert
        assert frame.camera_id == "cam03"
        assert frame.sequence_number == 456
        assert frame.metadata["detections"]["motion_score"] == 0.12

    def test_frame_metadata_copy_with_update(self):
        """Test creating a copy of frame metadata with updates."""
        # Arrange
        original = FrameMetadata(
            frame_id="original_frame",
            timestamp=datetime.now(timezone.utc),
            camera_id="cam01",
            sequence_number=100,
            metadata={"detections": {"faces": 1, "objects": [], "motion_score": 0.5}},
        )

        # Act
        updated = original.model_copy(
            update={
                "sequence_number": 101,
                "metadata": {
                    "detections": {
                        "faces": 2,
                        "objects": ["person"],
                        "motion_score": 0.8,
                    }
                },
            }
        )

        # Assert
        assert original.sequence_number == 100  # Original unchanged
        assert updated.sequence_number == 101
        assert updated.metadata["detections"]["faces"] == 2
