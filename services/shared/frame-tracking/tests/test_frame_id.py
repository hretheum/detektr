"""Tests for FrameID generator."""

import time
from concurrent.futures import ThreadPoolExecutor

from frame_tracking import FrameID


class TestFrameID:
    """Test FrameID generation and properties."""

    def test_generate_returns_string(self):
        """Test that generate returns a string."""
        frame_id = FrameID.generate()
        assert isinstance(frame_id, str)
        assert len(frame_id) > 0

    def test_uniqueness(self):
        """Test that generated IDs are unique."""
        ids = [FrameID.generate() for _ in range(1000)]
        assert len(set(ids)) == 1000, "All IDs should be unique"

    def test_time_ordering(self):
        """Test that IDs are sortable by time."""
        ids = []
        for _ in range(10):
            ids.append(FrameID.generate())
            time.sleep(0.001)  # Small delay to ensure different timestamps

        assert sorted(ids) == ids, "IDs should be time-ordered"

    def test_thread_safety(self):
        """Test that ID generation is thread-safe."""

        def generate_ids(count):
            return [FrameID.generate() for _ in range(count)]

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_ids, 100) for _ in range(10)]
            all_ids = []
            for future in futures:
                all_ids.extend(future.result())

        assert len(set(all_ids)) == 1000, "All IDs should be unique across threads"

    def test_format(self):
        """Test ID format."""
        frame_id = FrameID.generate()
        parts = frame_id.split("_")
        assert len(parts) >= 3, "ID should have at least 3 parts"

        # Check timestamp part
        timestamp_part = parts[0]
        assert timestamp_part.isdigit(), "Timestamp should be numeric"
        assert len(timestamp_part) >= 13, "Timestamp should be millisecond precision"

    def test_with_camera_id(self):
        """Test generating ID with camera identifier."""
        frame_id = FrameID.generate(camera_id="cam01")
        assert "cam01" in frame_id

    def test_with_source(self):
        """Test generating ID with source identifier."""
        frame_id = FrameID.generate(source="rtsp-capture")
        assert "rtsp-capture" in frame_id

    def test_parse(self):
        """Test parsing frame ID components."""
        frame_id = FrameID.generate(camera_id="cam01", source="rtsp")
        components = FrameID.parse(frame_id)

        assert "timestamp" in components
        assert "camera_id" in components
        assert "source" in components
        assert components["camera_id"] == "cam01"
        assert components["source"] == "rtsp"
