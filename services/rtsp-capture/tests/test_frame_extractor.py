"""
Test suite for RTSP frame extraction and validation.

Tests cover frame decoding, validation, and error handling.
"""
import asyncio
from fractions import Fraction
from unittest.mock import Mock

import numpy as np
import pytest

from src.frame_extractor import Frame, FrameExtractor, FrameValidationError


class TestFrameExtractor:
    """Test suite for frame extraction."""

    @pytest.fixture
    def mock_rtsp_connection(self):
        """Mock RTSP connection manager."""
        connection = Mock()
        connection.is_connected = True

        # Mock video stream
        mock_stream = Mock()
        mock_stream.codec_context = Mock()
        mock_stream.codec_context.width = 1920
        mock_stream.codec_context.height = 1080
        mock_stream.codec_context.pix_fmt = "yuv420p"
        mock_stream.time_base = Fraction(1, 90000)

        # Mock container with decode method
        mock_frame = Mock()
        mock_frame.width = 1920
        mock_frame.height = 1080
        mock_frame.pts = 1000
        mock_frame.time = 0.011  # pts * time_base
        mock_frame.to_ndarray = Mock(
            return_value=np.ones((1080, 1920, 3), dtype=np.uint8) * 128
        )

        mock_packet = Mock()
        mock_packet.decode = Mock(return_value=[mock_frame])

        connection.container = Mock()
        connection.container.decode = Mock(return_value=iter([mock_packet]))
        connection.get_video_stream = Mock(return_value=mock_stream)

        return connection

    @pytest.fixture
    def frame_extractor(self, mock_rtsp_connection):
        """Create frame extractor instance."""
        return FrameExtractor(
            connection_manager=mock_rtsp_connection, camera_id="test_camera_001"
        )

    def test_frame_initialization(self):
        """Test Frame dataclass initialization."""
        frame_data = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame = Frame(
            camera_id="cam_001",
            timestamp=1234567890.123,
            frame_number=42,
            width=1920,
            height=1080,
            format="bgr24",
            data=frame_data,
        )

        assert frame.camera_id == "cam_001"
        assert frame.timestamp == 1234567890.123
        assert frame.frame_number == 42
        assert frame.width == 1920
        assert frame.height == 1080
        assert frame.format == "bgr24"
        assert frame.data.shape == (1080, 1920, 3)
        assert frame.frame_id == "1234567890123_cam_001_42"

    @pytest.mark.asyncio
    async def test_extract_single_frame(self, frame_extractor, mock_rtsp_connection):
        """Test extracting a single frame."""
        # Extract frame
        frame = await frame_extractor.extract_frame()

        assert frame is not None
        assert isinstance(frame, Frame)
        assert frame.camera_id == "test_camera_001"
        assert frame.width == 1920
        assert frame.height == 1080
        assert frame.data.shape == (1080, 1920, 3)
        assert frame.format == "bgr24"

        # Verify decode was called
        mock_rtsp_connection.container.decode.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_frame_not_connected(
        self, frame_extractor, mock_rtsp_connection
    ):
        """Test frame extraction when not connected."""
        mock_rtsp_connection.is_connected = False

        with pytest.raises(RuntimeError) as exc_info:
            await frame_extractor.extract_frame()

        assert "Not connected to RTSP stream" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_frame_validation(self, frame_extractor):
        """Test frame validation logic."""
        # Valid frame
        valid_frame = Frame(
            camera_id="cam_001",
            timestamp=1234567890.123,
            frame_number=1,
            width=1920,
            height=1080,
            format="bgr24",
            data=np.ones((1080, 1920, 3), dtype=np.uint8) * 128,
        )

        # Should not raise
        frame_extractor.validate_frame(valid_frame)

        # Invalid frame - all black
        black_frame = Frame(
            camera_id="cam_001",
            timestamp=1234567890.123,
            frame_number=2,
            width=1920,
            height=1080,
            format="bgr24",
            data=np.zeros((1080, 1920, 3), dtype=np.uint8),
        )

        with pytest.raises(FrameValidationError) as exc_info:
            frame_extractor.validate_frame(black_frame)
        assert "black frame" in str(exc_info.value).lower()

        # Invalid frame - wrong dimensions
        wrong_dims = Frame(
            camera_id="cam_001",
            timestamp=1234567890.123,
            frame_number=3,
            width=1920,
            height=1080,
            format="bgr24",
            data=np.zeros((720, 1280, 3), dtype=np.uint8),
        )

        with pytest.raises(FrameValidationError) as exc_info:
            frame_extractor.validate_frame(wrong_dims)
        assert "dimensions mismatch" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_extract_frames_generator(
        self, frame_extractor, mock_rtsp_connection
    ):
        """Test frame extraction generator."""
        # Mock multiple frames
        frames = []
        for i in range(5):
            mock_frame = Mock()
            mock_frame.width = 1920
            mock_frame.height = 1080
            mock_frame.pts = 1000 + i * 3000  # ~30fps
            mock_frame.time = mock_frame.pts / 90000.0
            mock_frame.to_ndarray = Mock(
                return_value=np.ones((1080, 1920, 3), dtype=np.uint8) * (i + 1) * 50
            )
            frames.append(mock_frame)

        # Create packets that yield frames
        packets = []
        for frame in frames:
            packet = Mock()
            packet.decode = Mock(return_value=[frame])
            packets.append(packet)

        mock_rtsp_connection.container.decode = Mock(return_value=iter(packets))

        # Extract frames
        extracted_frames = []
        async for frame in frame_extractor.extract_frames(max_frames=5):
            extracted_frames.append(frame)

        assert len(extracted_frames) == 5
        for i, frame in enumerate(extracted_frames):
            assert frame.frame_number == i
            assert frame.data.mean() > 0  # Not black

    @pytest.mark.asyncio
    async def test_frame_rate_limiting(self, frame_extractor, mock_rtsp_connection):
        """Test frame rate limiting."""
        frame_extractor.target_fps = 10  # Limit to 10 FPS

        # Mock high-rate frames
        frames = []
        for i in range(10):
            mock_frame = Mock()
            mock_frame.width = 1920
            mock_frame.height = 1080
            mock_frame.pts = 1000 + i * 1500  # ~60fps
            mock_frame.time = mock_frame.pts / 90000.0
            mock_frame.to_ndarray = Mock(
                return_value=np.ones((1080, 1920, 3), dtype=np.uint8) * 128
            )
            frames.append(mock_frame)

        packets = [Mock(decode=Mock(return_value=[f])) for f in frames]
        mock_rtsp_connection.container.decode = Mock(return_value=iter(packets))

        # Extract with rate limiting
        start_time = asyncio.get_event_loop().time()
        extracted = []

        async for frame in frame_extractor.extract_frames(max_frames=3):
            extracted.append(frame)

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should take at least 0.2s for 3 frames at 10 FPS
        assert elapsed >= 0.15  # Allow some tolerance
        assert len(extracted) == 3

    @pytest.mark.asyncio
    async def test_decode_error_handling(self, frame_extractor, mock_rtsp_connection):
        """Test handling of decode errors."""
        # Mock decode error
        mock_packet = Mock()
        mock_packet.decode = Mock(side_effect=Exception("Decode failed"))

        mock_rtsp_connection.container.decode = Mock(return_value=iter([mock_packet]))

        # Should handle error gracefully - will raise because it's not av.FFmpegError
        with pytest.raises(Exception) as exc_info:
            await frame_extractor.extract_frame()
        assert "Decode failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_frame_timestamp_generation(
        self, frame_extractor, mock_rtsp_connection
    ):
        """Test frame timestamp generation."""
        # Mock frame without PTS
        mock_frame = Mock()
        mock_frame.width = 1920
        mock_frame.height = 1080
        mock_frame.pts = None  # No PTS
        mock_frame.time = None
        mock_frame.to_ndarray = Mock(
            return_value=np.ones((1080, 1920, 3), dtype=np.uint8) * 128
        )

        mock_packet = Mock()
        mock_packet.decode = Mock(return_value=[mock_frame])

        mock_rtsp_connection.container.decode = Mock(return_value=iter([mock_packet]))

        # Should generate timestamp
        frame = await frame_extractor.extract_frame()
        assert frame is not None
        assert frame.timestamp > 0
        assert isinstance(frame.timestamp, float)

    @pytest.mark.asyncio
    async def test_concurrent_frame_extraction(
        self, frame_extractor, mock_rtsp_connection
    ):
        """Test concurrent frame extraction protection."""
        # Start two concurrent extractions
        task1 = asyncio.create_task(frame_extractor.extract_frame())
        task2 = asyncio.create_task(frame_extractor.extract_frame())

        # One should succeed, other should get None or raise
        results = await asyncio.gather(task1, task2, return_exceptions=True)

        # At least one should succeed
        successful = [r for r in results if isinstance(r, Frame)]
        assert len(successful) >= 1

    def test_frame_statistics(self, frame_extractor):
        """Test frame statistics calculation."""
        frame_data = np.array(
            [
                [[255, 0, 0], [0, 255, 0]],  # Red, Green
                [[0, 0, 255], [128, 128, 128]],  # Blue, Gray
            ],
            dtype=np.uint8,
        )

        frame = Frame(
            camera_id="cam_001",
            timestamp=1234567890.123,
            frame_number=1,
            width=2,
            height=2,
            format="bgr24",
            data=frame_data,
        )

        stats = frame_extractor.calculate_frame_stats(frame)

        assert "mean_brightness" in stats
        assert "std_brightness" in stats
        assert "is_color" in stats
        assert stats["is_color"] is True
        assert 0 <= stats["mean_brightness"] <= 255
