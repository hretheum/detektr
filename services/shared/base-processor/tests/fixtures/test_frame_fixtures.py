"""Test frame fixtures for processor testing."""
from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np
import pytest


class FrameFixtures:
    """Reusable frame fixtures for testing."""

    @staticmethod
    def create_test_frame(
        width: int = 640,
        height: int = 480,
        channels: int = 3,
        dtype: np.dtype = np.uint8,
    ) -> np.ndarray:
        """Create a test frame with specified dimensions.

        Args:
            width: Frame width
            height: Frame height
            channels: Number of channels (1=grayscale, 3=RGB)
            dtype: Data type

        Returns:
            numpy array representing frame
        """
        if channels == 1:
            # Grayscale pattern
            frame = np.zeros((height, width), dtype=dtype)
            # Add gradient
            for y in range(height):
                frame[y, :] = int((y / height) * 255)
        else:
            # RGB pattern with different colors
            frame = np.zeros((height, width, channels), dtype=dtype)
            # Red gradient horizontally
            frame[:, :, 0] = np.linspace(0, 255, width, dtype=dtype)
            # Green gradient vertically
            frame[:, :, 1] = np.linspace(0, 255, height, dtype=dtype).reshape(-1, 1)
            # Blue checkerboard
            checker_size = 32
            for y in range(0, height, checker_size * 2):
                for x in range(0, width, checker_size * 2):
                    frame[y : y + checker_size, x : x + checker_size, 2] = 255
                    frame[
                        y + checker_size : y + 2 * checker_size,
                        x + checker_size : x + 2 * checker_size,
                        2,
                    ] = 255

        return frame

    @staticmethod
    def create_test_metadata(
        frame_id: str = None,
        camera_id: str = "test_camera_001",
        timestamp: datetime = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create test metadata for a frame.

        Args:
            frame_id: Unique frame identifier
            camera_id: Camera identifier
            timestamp: Frame timestamp
            **kwargs: Additional metadata fields

        Returns:
            Dictionary with frame metadata
        """
        if frame_id is None:
            frame_id = f"frame_{datetime.now().timestamp()}"
        if timestamp is None:
            timestamp = datetime.now()

        metadata = {
            "frame_id": frame_id,
            "camera_id": camera_id,
            "timestamp": timestamp.isoformat(),
            "source": "test_fixture",
            "format": "BGR",
            "encoding": "raw",
        }
        metadata.update(kwargs)
        return metadata

    @staticmethod
    def create_batch_frames(
        count: int = 10,
        width_range: Tuple[int, int] = (320, 1920),
        height_range: Tuple[int, int] = (240, 1080),
        channels: int = 3,
    ) -> Tuple[List[np.ndarray], List[Dict[str, Any]]]:
        """Create a batch of test frames with varying dimensions.

        Args:
            count: Number of frames to create
            width_range: Min and max width
            height_range: Min and max height
            channels: Number of channels

        Returns:
            Tuple of (frames list, metadata list)
        """
        frames = []
        metadata_list = []

        for i in range(count):
            # Vary dimensions
            width = np.random.randint(width_range[0], width_range[1])
            height = np.random.randint(height_range[0], height_range[1])

            frame = FrameFixtures.create_test_frame(width, height, channels)
            metadata = FrameFixtures.create_test_metadata(
                frame_id=f"batch_frame_{i:04d}",
                width=width,
                height=height,
                channels=channels,
                batch_index=i,
            )

            frames.append(frame)
            metadata_list.append(metadata)

        return frames, metadata_list

    @staticmethod
    def create_edge_case_frames() -> Dict[str, Tuple[np.ndarray, Dict[str, Any]]]:
        """Create frames for edge case testing.

        Returns:
            Dictionary mapping edge case name to (frame, metadata) tuple
        """
        edge_cases = {}

        # Empty frame (all zeros)
        edge_cases["empty"] = (
            np.zeros((480, 640, 3), dtype=np.uint8),
            FrameFixtures.create_test_metadata(
                frame_id="edge_empty",
                description="All zeros frame",
            ),
        )

        # Saturated frame (all max values)
        edge_cases["saturated"] = (
            np.full((480, 640, 3), 255, dtype=np.uint8),
            FrameFixtures.create_test_metadata(
                frame_id="edge_saturated",
                description="All max values frame",
            ),
        )

        # Very small frame
        edge_cases["tiny"] = (
            FrameFixtures.create_test_frame(16, 16, 3),
            FrameFixtures.create_test_metadata(
                frame_id="edge_tiny",
                description="Very small frame",
                width=16,
                height=16,
            ),
        )

        # Very large frame
        edge_cases["huge"] = (
            FrameFixtures.create_test_frame(4096, 2160, 3),
            FrameFixtures.create_test_metadata(
                frame_id="edge_huge",
                description="4K resolution frame",
                width=4096,
                height=2160,
            ),
        )

        # Grayscale frame
        edge_cases["grayscale"] = (
            FrameFixtures.create_test_frame(640, 480, 1),
            FrameFixtures.create_test_metadata(
                frame_id="edge_grayscale",
                description="Single channel frame",
                channels=1,
                format="GRAY",
            ),
        )

        # High dynamic range (16-bit)
        edge_cases["hdr"] = (
            FrameFixtures.create_test_frame(640, 480, 3, np.uint16),
            FrameFixtures.create_test_metadata(
                frame_id="edge_hdr",
                description="16-bit HDR frame",
                dtype="uint16",
                bit_depth=16,
            ),
        )

        # Corrupted frame (random noise)
        edge_cases["corrupted"] = (
            np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8),
            FrameFixtures.create_test_metadata(
                frame_id="edge_corrupted",
                description="Random noise frame",
                corrupted=True,
            ),
        )

        return edge_cases

    @staticmethod
    def create_synthetic_video_frames(
        duration_seconds: float = 1.0,
        fps: int = 30,
        width: int = 640,
        height: int = 480,
    ) -> Tuple[List[np.ndarray], List[Dict[str, Any]]]:
        """Create synthetic video sequence for testing.

        Args:
            duration_seconds: Duration of video
            fps: Frames per second
            width: Frame width
            height: Frame height

        Returns:
            Tuple of (frames list, metadata list)
        """
        num_frames = int(duration_seconds * fps)
        frames = []
        metadata_list = []

        # Create moving object
        object_size = 50
        object_speed = width // (fps * duration_seconds)  # Cross screen in duration

        for i in range(num_frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)

            # Moving red square
            x = int(i * object_speed) % (width - object_size)
            y = height // 2 - object_size // 2
            frame[y : y + object_size, x : x + object_size, 2] = 255  # Red in BGR

            # Simple frame number marker (without cv2)
            # Draw white pixels for frame number
            marker_y = 10
            marker_x = 10
            # Simple dot pattern to indicate frame number
            for j in range(min(i, 10)):
                if marker_x + j * 5 < width:
                    frame[marker_y, marker_x + j * 5] = 255
                    frame[marker_y, marker_x + j * 5, :] = 255

            timestamp = datetime.now()
            timestamp = timestamp.replace(
                microsecond=int((i / fps) * 1_000_000) % 1_000_000
            )

            metadata = FrameFixtures.create_test_metadata(
                frame_id=f"video_frame_{i:04d}",
                timestamp=timestamp,
                frame_number=i,
                fps=fps,
                video_duration=duration_seconds,
                object_position=(x, y),
            )

            frames.append(frame)
            metadata_list.append(metadata)

        return frames, metadata_list


# Pytest fixtures
@pytest.fixture
def frame_fixtures():
    """Provide FrameFixtures instance."""
    return FrameFixtures()


@pytest.fixture
def simple_frame():
    """Provide a simple test frame."""
    return FrameFixtures.create_test_frame()


@pytest.fixture
def simple_metadata():
    """Provide simple frame metadata."""
    return FrameFixtures.create_test_metadata()


@pytest.fixture
def batch_frames():
    """Provide a batch of test frames."""
    return FrameFixtures.create_batch_frames(count=5)


@pytest.fixture
def edge_case_frames():
    """Provide edge case test frames."""
    return FrameFixtures.create_edge_case_frames()


@pytest.fixture
def video_frames():
    """Provide synthetic video frames."""
    return FrameFixtures.create_synthetic_video_frames(duration_seconds=0.5, fps=10)


# Tests for the fixtures themselves
class TestFrameFixtures:
    """Test the frame fixtures."""

    def test_create_test_frame_rgb(self):
        """Test RGB frame creation."""
        frame = FrameFixtures.create_test_frame(100, 50, 3)
        assert frame.shape == (50, 100, 3)
        assert frame.dtype == np.uint8
        assert np.any(frame > 0)  # Not all zeros

    def test_create_test_frame_grayscale(self):
        """Test grayscale frame creation."""
        frame = FrameFixtures.create_test_frame(80, 60, 1)
        assert frame.shape == (60, 80)
        assert frame.dtype == np.uint8

    def test_create_test_metadata(self):
        """Test metadata creation."""
        metadata = FrameFixtures.create_test_metadata(
            frame_id="test_123", custom_field="value"
        )
        assert metadata["frame_id"] == "test_123"
        assert metadata["camera_id"] == "test_camera_001"
        assert "timestamp" in metadata
        assert metadata["custom_field"] == "value"

    def test_create_batch_frames(self):
        """Test batch frame creation."""
        frames, metadata_list = FrameFixtures.create_batch_frames(count=3)
        assert len(frames) == 3
        assert len(metadata_list) == 3

        for i, (frame, metadata) in enumerate(zip(frames, metadata_list)):
            assert isinstance(frame, np.ndarray)
            assert frame.ndim == 3
            assert metadata["batch_index"] == i

    def test_edge_case_frames(self):
        """Test edge case frame creation."""
        edge_cases = FrameFixtures.create_edge_case_frames()

        # Test empty frame
        assert "empty" in edge_cases
        frame, metadata = edge_cases["empty"]
        assert np.all(frame == 0)

        # Test saturated frame
        frame, metadata = edge_cases["saturated"]
        assert np.all(frame == 255)

        # Test tiny frame
        frame, metadata = edge_cases["tiny"]
        assert frame.shape == (16, 16, 3)

        # Test grayscale
        frame, metadata = edge_cases["grayscale"]
        assert frame.ndim == 2

    def test_synthetic_video_frames(self):
        """Test synthetic video frame creation."""
        frames, metadata_list = FrameFixtures.create_synthetic_video_frames(
            duration_seconds=0.1, fps=10
        )
        assert len(frames) == 1  # 0.1s * 10fps = 1 frame

        # Check frame has moving object
        frame = frames[0]
        assert np.any(frame[:, :, 2] == 255)  # Red channel has object

    def test_frame_fixtures_pytest_fixture(self, frame_fixtures):
        """Test pytest fixture integration."""
        assert isinstance(frame_fixtures, FrameFixtures)
        frame = frame_fixtures.create_test_frame()
        assert isinstance(frame, np.ndarray)

    def test_all_fixtures_loadable(
        self,
        simple_frame,
        simple_metadata,
        batch_frames,
        edge_case_frames,
        video_frames,
    ):
        """Test all pytest fixtures are loadable."""
        assert isinstance(simple_frame, np.ndarray)
        assert isinstance(simple_metadata, dict)
        assert len(batch_frames) == 2
        assert isinstance(edge_case_frames, dict)
        assert len(video_frames) == 2
