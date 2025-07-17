"""Unit tests for FrameProcessor service - TDD approach."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.examples.frame_processor import (
    FrameProcessor,
    ProcessingError,
    ProcessingResult,
)
from src.shared.kernel.domain import Frame, ProcessingState


@pytest.mark.unit
class TestFrameProcessor:
    """Test FrameProcessor using TDD approach."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies."""
        return {
            "face_detector": Mock(detect=AsyncMock(return_value=[])),
            "object_detector": Mock(detect=AsyncMock(return_value=[])),
            "frame_repository": Mock(save=AsyncMock(), get_by_id=AsyncMock()),
            "event_publisher": Mock(publish=AsyncMock()),
        }

    @pytest.fixture
    def processor(self, mock_dependencies):
        """Create FrameProcessor with mocked dependencies."""
        return FrameProcessor(
            face_detector=mock_dependencies["face_detector"],
            object_detector=mock_dependencies["object_detector"],
            frame_repository=mock_dependencies["frame_repository"],
            event_publisher=mock_dependencies["event_publisher"],
        )

    @pytest.fixture
    def sample_frame(self):
        """Create sample frame for testing."""
        return Frame.create(camera_id="test_cam_01", timestamp=datetime.now())

    @pytest.mark.asyncio
    async def test_process_frame_success(
        self, processor, sample_frame, mock_dependencies
    ):
        """Test successful frame processing."""
        # Arrange
        mock_dependencies["face_detector"].detect.return_value = [
            {"confidence": 0.95, "bbox": [10, 20, 100, 120]}
        ]
        mock_dependencies["object_detector"].detect.return_value = [
            {"class": "person", "confidence": 0.89}
        ]

        # Act
        result = await processor.process_frame(sample_frame)

        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.frame_id == str(sample_frame.id)
        assert len(result.detections["faces"]) == 1
        assert len(result.detections["objects"]) == 1
        assert result.processing_time_ms > 0

        # Verify frame was saved
        mock_dependencies["frame_repository"].save.assert_called_once()
        saved_frame = mock_dependencies["frame_repository"].save.call_args[0][0]
        assert saved_frame.state == ProcessingState.COMPLETED

        # Verify event was published
        mock_dependencies["event_publisher"].publish.assert_called()

    @pytest.mark.asyncio
    async def test_process_frame_with_no_detections(self, processor, sample_frame):
        """Test processing frame with no detections."""
        # Act
        result = await processor.process_frame(sample_frame)

        # Assert
        assert result.success is True
        assert len(result.detections["faces"]) == 0
        assert len(result.detections["objects"]) == 0

    @pytest.mark.asyncio
    async def test_process_frame_face_detection_error(
        self, processor, sample_frame, mock_dependencies
    ):
        """Test handling face detection errors."""
        # Arrange
        mock_dependencies["face_detector"].detect.side_effect = Exception(
            "GPU memory error"
        )

        # Act
        result = await processor.process_frame(sample_frame)

        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.success is False
        assert "face_detection" in result.errors
        assert "GPU memory error" in result.errors["face_detection"]

        # Frame should still be saved with partial results
        saved_frame = mock_dependencies["frame_repository"].save.call_args[0][0]
        assert saved_frame.state == ProcessingState.COMPLETED

    @pytest.mark.asyncio
    async def test_process_frame_total_failure(
        self, processor, sample_frame, mock_dependencies
    ):
        """Test handling total processing failure."""
        # Arrange
        mock_dependencies["face_detector"].detect.side_effect = Exception(
            "Critical error"
        )
        mock_dependencies["object_detector"].detect.side_effect = Exception(
            "Critical error"
        )
        mock_dependencies["frame_repository"].save.side_effect = Exception("DB error")

        # Act & Assert
        with pytest.raises(ProcessingError) as exc_info:
            await processor.process_frame(sample_frame)

        assert "Failed to process frame" in str(exc_info.value)
        assert exc_info.value.frame_id == str(sample_frame.id)

    @pytest.mark.asyncio
    async def test_concurrent_frame_processing(self, processor, mock_dependencies):
        """Test processing multiple frames concurrently."""
        # Arrange
        frames = [
            Frame.create(camera_id=f"cam_{i}", timestamp=datetime.now())
            for i in range(5)
        ]

        # Act
        results = await asyncio.gather(
            *[processor.process_frame(frame) for frame in frames],
            return_exceptions=True,
        )

        # Assert
        assert len(results) == 5
        assert all(isinstance(r, ProcessingResult) for r in results)
        assert mock_dependencies["frame_repository"].save.call_count == 5

    @pytest.mark.asyncio
    async def test_process_frame_timeout(self, processor, sample_frame):
        """Test frame processing timeout."""
        # Arrange
        processor.processing_timeout = 0.1  # 100ms timeout

        # Mock slow detection
        async def slow_detect(*args):
            await asyncio.sleep(0.5)
            return []

        processor.face_detector.detect = slow_detect

        # Act
        with pytest.raises(ProcessingError) as exc_info:
            await processor.process_frame(sample_frame)

        # Assert
        assert "timeout" in str(exc_info.value).lower()

    def test_validate_frame_valid(self, processor, sample_frame):
        """Test frame validation with valid frame."""
        # Should not raise
        processor.validate_frame(sample_frame)

    def test_validate_frame_invalid_state(self, processor, sample_frame):
        """Test frame validation with invalid state."""
        # Arrange
        sample_frame.state = ProcessingState.COMPLETED

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            processor.validate_frame(sample_frame)

        assert "already processed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_enrichment_pipeline(self, processor, sample_frame):
        """Test frame enrichment with metadata."""
        # Arrange
        detections = {"faces": [{"confidence": 0.95}], "objects": [{"class": "person"}]}

        # Act
        enriched_frame = await processor.enrich_frame(sample_frame, detections)

        # Assert
        assert "face_count" in enriched_frame.metadata
        assert enriched_frame.metadata["face_count"] == 1
        assert "object_types" in enriched_frame.metadata
        assert "person" in enriched_frame.metadata["object_types"]
