"""Unit tests for data models."""

from datetime import datetime

import pytest

from src.models import (
    BackpressureLevel,
    FrameReadyEvent,
    ProcessorCapabilities,
    ProcessorHealth,
    ProcessorRegistration,
)


def test_frame_ready_event_creation():
    """Test FrameReadyEvent model creation and validation."""
    event = FrameReadyEvent(
        frame_id="test_123",
        camera_id="camera_01",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={"trace_id": "abc123"},
        priority=1,
    )

    assert event.frame_id == "test_123"
    assert event.camera_id == "camera_01"
    assert event.size_bytes == 1024
    assert event.width == 1920
    assert event.height == 1080
    assert event.format == "jpeg"
    assert event.trace_context == {"trace_id": "abc123"}
    assert event.priority == 1
    assert event.metadata == {}  # Default empty


def test_frame_ready_event_serialization():
    """Test FrameReadyEvent serialization and deserialization."""
    original = FrameReadyEvent(
        frame_id="test_123",
        camera_id="camera_01",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={"trace_id": "abc123", "span_id": "def456"},
        priority=2,
        metadata={"location": "entrance", "quality": "high"},
    )

    # Test to_json
    json_data = original.to_json()
    assert json_data["frame_id"] == "test_123"
    assert json_data["camera_id"] == "camera_01"
    assert "timestamp" in json_data
    assert json_data["trace_context"]["trace_id"] == "abc123"
    assert json_data["metadata"]["location"] == "entrance"

    # Test from_json
    restored = FrameReadyEvent.from_json(json_data)
    assert restored.frame_id == original.frame_id
    assert restored.camera_id == original.camera_id
    assert restored.trace_context == original.trace_context
    assert restored.metadata == original.metadata

    # Timestamps might differ slightly due to serialization
    assert abs((restored.timestamp - original.timestamp).total_seconds()) < 1


def test_processor_registration():
    """Test ProcessorRegistration model."""
    reg = ProcessorRegistration(
        id="face-detector-1",
        capabilities=["face_detection", "person_detection"],
        capacity=100,
        queue="frames:ready:face-detector-1",
    )

    assert reg.id == "face-detector-1"
    assert reg.can_process("face_detection") is True
    assert reg.can_process("person_detection") is True
    assert reg.can_process("vehicle_detection") is False
    assert reg.capacity == 100
    assert reg.queue == "frames:ready:face-detector-1"


def test_processor_registration_with_endpoint():
    """Test ProcessorRegistration with optional fields."""
    reg = ProcessorRegistration(
        id="object-detector-1",
        capabilities=["object_detection"],
        capacity=50,
        queue="frames:ready:object-detector-1",
        endpoint="http://object-detector:8080",
        health_endpoint="http://object-detector:8080/health",
        metadata={"version": "1.2.3", "gpu": True},
    )

    assert reg.endpoint == "http://object-detector:8080"
    assert reg.health_endpoint == "http://object-detector:8080/health"
    assert reg.metadata["version"] == "1.2.3"
    assert reg.metadata["gpu"] is True


def test_processor_health():
    """Test ProcessorHealth model."""
    health = ProcessorHealth(
        processor_id="test-proc-1",
        status="healthy",
        capacity_used=0.75,
        frames_processed=1000,
        avg_processing_time_ms=42.5,
        errors_last_minute=2,
        last_health_check=datetime.now(),
    )

    assert health.processor_id == "test-proc-1"
    assert health.status == "healthy"
    assert health.capacity_used == 0.75
    assert health.is_healthy is True
    assert health.is_overloaded is True  # >70% capacity

    # Test unhealthy processor
    unhealthy = ProcessorHealth(
        processor_id="test-proc-2",
        status="unhealthy",
        capacity_used=0.5,
        frames_processed=0,
        avg_processing_time_ms=0,
        errors_last_minute=50,
        last_health_check=datetime.now(),
    )

    assert unhealthy.is_healthy is False
    assert unhealthy.status == "unhealthy"


def test_processor_health_degraded():
    """Test ProcessorHealth degraded state."""
    degraded = ProcessorHealth(
        processor_id="test-proc-3",
        status="degraded",
        capacity_used=0.6,
        frames_processed=500,
        avg_processing_time_ms=150.0,  # Slow processing
        errors_last_minute=10,  # Some errors
        last_health_check=datetime.now(),
    )

    assert degraded.status == "degraded"
    assert degraded.is_healthy is True  # Still operational
    assert degraded.is_overloaded is False  # <70% capacity


def test_backpressure_level():
    """Test BackpressureLevel enum."""
    assert BackpressureLevel.NORMAL.value == 0
    assert BackpressureLevel.MODERATE.value == 1
    assert BackpressureLevel.HIGH.value == 2
    assert BackpressureLevel.CRITICAL.value == 3

    # Test comparison
    assert BackpressureLevel.NORMAL < BackpressureLevel.MODERATE
    assert BackpressureLevel.HIGH > BackpressureLevel.MODERATE
    assert BackpressureLevel.CRITICAL > BackpressureLevel.HIGH


def test_processor_capabilities():
    """Test ProcessorCapabilities model."""
    caps = ProcessorCapabilities(
        capabilities=["face_detection", "emotion_detection"],
        min_resolution=(640, 480),
        max_resolution=(3840, 2160),
        supported_formats=["jpeg", "png", "h264"],
        max_fps=30,
        gpu_required=True,
    )

    assert caps.can_handle("face_detection") is True
    assert caps.can_handle("object_detection") is False

    # Test resolution checks
    assert caps.supports_resolution(1920, 1080) is True
    assert caps.supports_resolution(320, 240) is False  # Too small
    assert caps.supports_resolution(7680, 4320) is False  # Too large

    # Test format checks
    assert caps.supports_format("jpeg") is True
    assert caps.supports_format("bmp") is False


def test_frame_ready_event_validation():
    """Test FrameReadyEvent validation."""
    # Test invalid frame_id
    with pytest.raises(ValueError, match="frame_id cannot be empty"):
        FrameReadyEvent(
            frame_id="",
            camera_id="cam1",
            timestamp=datetime.now(),
            size_bytes=1024,
            width=1920,
            height=1080,
            format="jpeg",
            trace_context={},
        )

    # Test invalid dimensions
    with pytest.raises(ValueError, match="Invalid dimensions"):
        FrameReadyEvent(
            frame_id="test",
            camera_id="cam1",
            timestamp=datetime.now(),
            size_bytes=1024,
            width=0,
            height=1080,
            format="jpeg",
            trace_context={},
        )

    # Test invalid priority
    with pytest.raises(ValueError, match="Priority must be between 0 and 10"):
        FrameReadyEvent(
            frame_id="test",
            camera_id="cam1",
            timestamp=datetime.now(),
            size_bytes=1024,
            width=1920,
            height=1080,
            format="jpeg",
            trace_context={},
            priority=11,
        )
