"""Tests for Frame metadata."""

import json
from datetime import datetime

import pytest
from frame_tracking import FrameID
from frame_tracking.metadata import FrameMetadata, ProcessingStage
from pydantic import ValidationError


class TestFrameMetadata:
    """Test frame metadata functionality."""

    def test_create_metadata(self):
        """Test creating frame metadata."""
        frame_id = FrameID.generate()
        metadata = FrameMetadata(
            frame_id=frame_id,
            timestamp=datetime.now(),
            camera_id="cam01",
            resolution=(1920, 1080),
            format="h264",
        )

        assert metadata.frame_id == frame_id
        assert metadata.camera_id == "cam01"
        assert metadata.resolution == (1920, 1080)
        assert metadata.format == "h264"
        assert metadata.processing_stages == []

    def test_serialization(self):
        """Test metadata serialization/deserialization."""
        metadata = FrameMetadata(
            frame_id="test_123",
            timestamp=datetime.now(),
            camera_id="cam01",
            resolution=(1920, 1080),
            format="h264",
        )

        # To JSON
        json_data = metadata.to_json()
        assert isinstance(json_data, str)

        # Parse JSON
        data = json.loads(json_data)
        assert data["frame_id"] == "test_123"
        assert data["camera_id"] == "cam01"

        # From JSON
        restored = FrameMetadata.from_json(json_data)
        assert restored.frame_id == metadata.frame_id
        assert restored.camera_id == metadata.camera_id
        assert restored.resolution == metadata.resolution

    def test_add_processing_stage(self):
        """Test adding processing stages."""
        metadata = FrameMetadata(frame_id="test_123", timestamp=datetime.now())

        # Add stage
        stage = metadata.add_processing_stage(
            name="capture", service="rtsp-capture", status="completed", duration_ms=25.5
        )

        assert len(metadata.processing_stages) == 1
        assert stage.name == "capture"
        assert stage.service == "rtsp-capture"
        assert stage.status == "completed"
        assert stage.duration_ms == 25.5

    def test_optional_fields(self):
        """Test metadata with optional fields."""
        # Minimal metadata
        metadata = FrameMetadata(frame_id="test_123", timestamp=datetime.now())

        assert metadata.camera_id is None
        assert metadata.resolution is None
        assert metadata.format is None
        assert metadata.source_url is None
        assert metadata.trace_id is None
        assert metadata.span_id is None

    def test_trace_context_fields(self):
        """Test trace context fields."""
        metadata = FrameMetadata(
            frame_id="test_123",
            timestamp=datetime.now(),
            trace_id="abc123def456",
            span_id="789012",
        )

        assert metadata.trace_id == "abc123def456"
        assert metadata.span_id == "789012"

    def test_validation(self):
        """Test metadata validation."""
        # Missing required fields
        with pytest.raises(ValidationError):
            FrameMetadata()

        # Invalid resolution
        with pytest.raises(ValidationError):
            FrameMetadata(
                frame_id="test",
                timestamp=datetime.now(),
                resolution=(1920,),  # Should be tuple of 2
            )

    def test_processing_stage_enum(self):
        """Test ProcessingStage status values."""
        stage = ProcessingStage(name="test", service="test-service", status="pending")

        # Valid statuses
        for status in ["pending", "processing", "completed", "failed"]:
            stage.status = status  # Should not raise

        # Invalid status
        with pytest.raises(ValidationError):
            ProcessingStage(name="test", service="test-service", status="invalid")

    def test_metadata_dict_export(self):
        """Test exporting metadata as dict."""
        metadata = FrameMetadata(
            frame_id="test_123", timestamp=datetime.now(), camera_id="cam01"
        )

        data = metadata.model_dump()
        assert isinstance(data, dict)
        assert data["frame_id"] == "test_123"
        assert data["camera_id"] == "cam01"
        assert "timestamp" in data

        # Exclude None values
        data_compact = metadata.model_dump(exclude_none=True)
        assert "resolution" not in data_compact  # None value excluded
