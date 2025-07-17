"""Unit tests for Frame domain model."""

from datetime import datetime

import pytest

from src.shared.kernel.domain import Frame, FrameId, ProcessingState
from src.shared.kernel.events import FrameCaptured


def test_frame_creation():
    """Test frame creation."""
    frame = Frame.create(camera_id="cam01")

    assert isinstance(frame.id, FrameId)
    assert frame.camera_id == "cam01"
    assert frame.state == ProcessingState.CAPTURED
    assert frame.processing_stages == []
    assert isinstance(frame.timestamp, datetime)


def test_frame_id_generation():
    """Test frame ID generation."""
    timestamp = datetime(2024, 1, 1, 12, 0, 0)
    frame_id = FrameId.generate("cam01", timestamp)

    assert frame_id.value.startswith("20240101120000000_cam01_")
    assert len(frame_id.value.split("_")) == 3


def test_frame_state_transitions():
    """Test valid state transitions."""
    frame = Frame.create(camera_id="cam01")

    # Valid transitions
    assert frame.can_transition_to(ProcessingState.QUEUED)
    assert frame.can_transition_to(ProcessingState.FAILED)
    assert not frame.can_transition_to(ProcessingState.COMPLETED)

    frame.transition_to(ProcessingState.QUEUED)
    assert frame.state == ProcessingState.QUEUED

    assert frame.can_transition_to(ProcessingState.PROCESSING)
    assert not frame.can_transition_to(ProcessingState.CAPTURED)

    frame.transition_to(ProcessingState.PROCESSING)
    assert frame.can_transition_to(ProcessingState.COMPLETED)
    assert frame.can_transition_to(ProcessingState.FAILED)


def test_invalid_state_transition():
    """Test invalid state transition raises error."""
    frame = Frame.create(camera_id="cam01")

    with pytest.raises(ValueError) as exc:
        frame.transition_to(ProcessingState.COMPLETED)

    assert "Invalid state transition" in str(exc.value)


def test_processing_stages():
    """Test processing stage management."""
    frame = Frame.create(camera_id="cam01")

    # Start stage
    stage = frame.start_processing_stage("face_detection", {"model": "insightface"})
    assert stage.name == "face_detection"
    assert stage.status == "in_progress"
    assert stage.metadata == {"model": "insightface"}

    # Get current stage
    current = frame.get_current_stage()
    assert current == stage

    # Complete stage
    stage.complete({"faces_found": 2})
    assert stage.status == "completed"
    assert stage.metadata["faces_found"] == 2
    assert stage.duration_ms is not None

    # No current stage after completion
    assert frame.get_current_stage() is None


def test_frame_failure():
    """Test frame failure handling."""
    frame = Frame.create(camera_id="cam01")
    frame.transition_to(ProcessingState.PROCESSING)

    stage = frame.start_processing_stage("object_detection")
    frame.mark_as_failed("GPU out of memory")

    assert frame.state == ProcessingState.FAILED
    assert stage.status == "failed"
    assert stage.error == "GPU out of memory"
    assert frame.metadata["error"] == "GPU out of memory"


def test_frame_completion():
    """Test frame completion."""
    frame = Frame.create(camera_id="cam01")
    frame.transition_to(ProcessingState.QUEUED)
    frame.transition_to(ProcessingState.PROCESSING)

    stage = frame.start_processing_stage("inference")
    frame.mark_as_completed()

    assert frame.state == ProcessingState.COMPLETED
    assert stage.status == "completed"
    assert frame.is_terminal


def test_total_processing_time():
    """Test total processing time calculation."""
    frame = Frame.create(camera_id="cam01")

    # Add stages
    stage1 = frame.start_processing_stage("stage1")
    stage1.complete()

    stage2 = frame.start_processing_stage("stage2")
    stage2.complete()

    total_time = frame.total_processing_time_ms
    assert total_time > 0
    assert total_time == (stage1.duration_ms + stage2.duration_ms)


def test_frame_metadata():
    """Test frame metadata management."""
    frame = Frame.create(camera_id="cam01")

    frame.add_metadata("resolution", {"width": 1920, "height": 1080})
    frame.add_metadata("fps", 30)

    assert frame.metadata["resolution"]["width"] == 1920
    assert frame.metadata["fps"] == 30


def test_frame_event_creation():
    """Test frame event creation."""
    event = FrameCaptured(
        frame_id="test_frame_123",
        camera_id="cam01",
        timestamp=datetime.now(),
        frame_size={"width": 1920, "height": 1080},
    )

    assert event.event_type == "frame.captured"
    assert event.frame_id == "test_frame_123"
    assert event.camera_id == "cam01"

    event_dict = event.to_dict()
    assert event_dict["event_type"] == "frame.captured"
    assert "frame_id" in event_dict["data"]
    assert "camera_id" in event_dict["data"]
