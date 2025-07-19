"""
TDD tests for frame serialization.

Test różnych formatów serializacji klatek:
- msgpack (binary)
- JSON (fallback)
- Compression support (LZ4)
"""
import time
from datetime import datetime

import numpy as np
import pytest

from src.shared.kernel.domain.frame_data import FrameData
from src.shared.serializers.frame_serializer import (
    CompressionType,
    DeserializationError,
    FrameSerializer,
    SerializationError,
    SerializationFormat,
)


class TestFrameSerializer:
    """Test cases for frame serialization."""

    @pytest.fixture
    def sample_frame(self):
        """Create sample frame for testing."""
        # Full HD frame (1920x1080) with 3 channels (RGB)
        image_data = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

        return FrameData(
            id="frame_123_456",
            timestamp=datetime.now(),
            camera_id="camera_01",
            sequence_number=456,
            image_data=image_data,
            metadata={"fps": 30, "resolution": "1920x1080", "codec": "h264"},
        )

    @pytest.fixture
    def small_frame(self):
        """Create small frame for performance testing."""
        # Small frame (640x480)
        image_data = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        return FrameData(
            id="frame_small_001",
            timestamp=datetime.now(),
            camera_id="camera_test",
            sequence_number=1,
            image_data=image_data,
            metadata={"resolution": "640x480"},
        )

    def test_msgpack_serialization_round_trip(self, sample_frame):
        """Test that msgpack serialization preserves all frame data."""
        serializer = FrameSerializer(format=SerializationFormat.MSGPACK)

        # Serialize
        serialized = serializer.serialize(sample_frame)
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0

        # Deserialize
        deserialized = serializer.deserialize(serialized)

        # Verify all fields
        assert deserialized.id == sample_frame.id
        assert deserialized.camera_id == sample_frame.camera_id
        assert deserialized.sequence_number == sample_frame.sequence_number
        assert deserialized.metadata == sample_frame.metadata
        assert np.array_equal(deserialized.image_data, sample_frame.image_data)
        # Timestamp might have microsecond precision differences
        assert (
            abs((deserialized.timestamp - sample_frame.timestamp).total_seconds())
            < 0.001
        )

    def test_json_serialization_fallback(self, sample_frame):
        """Test JSON serialization as fallback (without image data)."""
        serializer = FrameSerializer(format=SerializationFormat.JSON)

        # JSON serialization should work but skip image data
        serialized = serializer.serialize(sample_frame)
        assert isinstance(serialized, bytes)

        # Deserialize
        deserialized = serializer.deserialize(serialized)

        # Verify metadata preserved
        assert deserialized.id == sample_frame.id
        assert deserialized.camera_id == sample_frame.camera_id
        assert deserialized.sequence_number == sample_frame.sequence_number
        assert deserialized.metadata == sample_frame.metadata
        # Image data should be None or empty for JSON
        assert deserialized.image_data is None or deserialized.image_data.size == 0

    def test_lz4_compression(self):
        """Test LZ4 compression reduces size for compressible data."""
        # Create frame with compressible data (not random)
        # Full HD frame with patterns that compress well
        image_data = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # Add some patterns
        image_data[::10, ::10] = 255  # White dots every 10 pixels

        frame = FrameData(
            id="frame_compress_test",
            timestamp=datetime.now(),
            camera_id="camera_01",
            sequence_number=1,
            image_data=image_data,
            metadata={"test": "compression"},
        )

        serializer_uncompressed = FrameSerializer(
            format=SerializationFormat.MSGPACK, compression=CompressionType.NONE
        )
        serializer_compressed = FrameSerializer(
            format=SerializationFormat.MSGPACK, compression=CompressionType.LZ4
        )

        # Serialize both ways
        uncompressed = serializer_uncompressed.serialize(frame)
        compressed = serializer_compressed.serialize(frame)

        # Compressed should be smaller
        assert len(compressed) < len(uncompressed)

        # Should achieve significant compression on zeros
        compression_ratio = 1 - (len(compressed) / len(uncompressed))
        assert compression_ratio > 0.5  # At least 50% compression for mostly zeros

        # Verify decompression works
        decompressed_frame = serializer_compressed.deserialize(compressed)
        assert np.array_equal(decompressed_frame.image_data, frame.image_data)

    def test_serialization_performance(self, sample_frame):
        """Test serialization performance meets requirements."""
        serializer = FrameSerializer(format=SerializationFormat.MSGPACK)

        # Warm up
        for _ in range(5):
            serializer.serialize(sample_frame)

        # Measure serialization time
        start = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            serializer.serialize(sample_frame)
        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000

        # Should be under 5ms for Full HD frame
        assert avg_time_ms < 5.0

    def test_compression_overhead(self, sample_frame):
        """Test LZ4 compression overhead is acceptable."""
        serializer = FrameSerializer(
            format=SerializationFormat.MSGPACK, compression=CompressionType.LZ4
        )

        # Warm up
        for _ in range(5):
            serializer.serialize(sample_frame)

        # Measure with compression
        start = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            serializer.serialize(sample_frame)
        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000

        # Should be under 7ms even with compression (5ms + 2ms overhead)
        assert avg_time_ms < 7.0

    def test_invalid_data_handling(self):
        """Test proper error handling for invalid data."""
        serializer = FrameSerializer()

        # Test deserialization of invalid data
        with pytest.raises(DeserializationError):
            serializer.deserialize(b"invalid data")

        with pytest.raises(DeserializationError):
            serializer.deserialize(b"")

        # Test serialization of invalid frame
        with pytest.raises(SerializationError):
            serializer.serialize(None)

        with pytest.raises(SerializationError):
            serializer.serialize("not a frame")

    def test_format_compatibility(self, sample_frame):
        """Test different serialization formats can be detected."""
        msgpack_serializer = FrameSerializer(format=SerializationFormat.MSGPACK)
        json_serializer = FrameSerializer(format=SerializationFormat.JSON)

        msgpack_data = msgpack_serializer.serialize(sample_frame)
        json_data = json_serializer.serialize(sample_frame)

        # Should be able to detect format from data
        assert (
            msgpack_serializer.detect_format(msgpack_data)
            == SerializationFormat.MSGPACK
        )
        assert json_serializer.detect_format(json_data) == SerializationFormat.JSON

    def test_metadata_preservation(self, sample_frame):
        """Test that complex metadata is preserved correctly."""
        # Add complex metadata
        sample_frame.metadata = {
            "nested": {"values": [1, 2, 3], "config": {"key": "value"}},
            "unicode": "测试中文",
            "numbers": [1.23, 4.56, 7.89],
            "boolean": True,
            "null": None,
        }

        serializer = FrameSerializer(format=SerializationFormat.MSGPACK)
        serialized = serializer.serialize(sample_frame)
        deserialized = serializer.deserialize(serialized)

        assert deserialized.metadata == sample_frame.metadata

    def test_large_frame_handling(self):
        """Test handling of 4K frames."""
        # 4K frame (3840x2160)
        large_image = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)
        large_frame = FrameData(
            id="frame_4k",
            timestamp=datetime.now(),
            camera_id="camera_4k",
            sequence_number=1,
            image_data=large_image,
            metadata={"resolution": "3840x2160"},
        )

        serializer = FrameSerializer(
            format=SerializationFormat.MSGPACK, compression=CompressionType.LZ4
        )

        # Should handle large frames
        serialized = serializer.serialize(large_frame)
        deserialized = serializer.deserialize(serialized)

        assert np.array_equal(deserialized.image_data, large_frame.image_data)

    def test_batch_serialization(self, small_frame):
        """Test batch serialization functionality."""
        serializer = FrameSerializer(format=SerializationFormat.MSGPACK)
        frames = [small_frame for _ in range(10)]

        # Test batch serialize
        serialized_frames = serializer.serialize_batch(frames)

        # Should produce same number of serialized items
        assert len(serialized_frames) == len(frames)

        # Each should be valid serialized data
        for data in serialized_frames:
            assert isinstance(data, bytes)
            assert len(data) > 0

        # Verify all frames can be deserialized
        deserialized = serializer.deserialize_batch(serialized_frames)
        assert len(deserialized) == len(frames)

        # Verify content preserved
        for original, restored in zip(frames, deserialized):
            assert restored.id == original.id
            assert restored.camera_id == original.camera_id
            assert restored.sequence_number == original.sequence_number
            assert np.array_equal(restored.image_data, original.image_data)

    @pytest.mark.parametrize(
        "format,compression",
        [
            (SerializationFormat.MSGPACK, CompressionType.NONE),
            (SerializationFormat.MSGPACK, CompressionType.LZ4),
            (SerializationFormat.JSON, CompressionType.NONE),
        ],
    )
    def test_serialization_formats_combinations(
        self, sample_frame, format, compression
    ):
        """Test all valid format and compression combinations."""
        serializer = FrameSerializer(format=format, compression=compression)

        if format == SerializationFormat.JSON:
            # JSON doesn't support image data
            sample_frame.image_data = None

        serialized = serializer.serialize(sample_frame)
        deserialized = serializer.deserialize(serialized)

        assert deserialized.id == sample_frame.id
        assert deserialized.camera_id == sample_frame.camera_id
        assert deserialized.metadata == sample_frame.metadata
