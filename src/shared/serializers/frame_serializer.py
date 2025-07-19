"""
Frame serialization with support for multiple formats and compression.

Supports:
- msgpack (binary) - primary format with full frame data
- JSON - fallback format without image data
- LZ4 compression for reduced size
"""
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

import lz4.frame
import msgpack
import numpy as np

from src.shared.kernel.domain.frame_data import FrameData


class SerializationFormat(Enum):
    """Supported serialization formats."""

    MSGPACK = "msgpack"
    JSON = "json"


class CompressionType(Enum):
    """Supported compression types."""

    NONE = "none"
    LZ4 = "lz4"


class SerializationError(Exception):
    """Raised when serialization fails."""

    pass


class DeserializationError(Exception):
    """Raised when deserialization fails."""

    pass


class FrameSerializer:
    """
    High-performance frame serializer with compression support.

    Primary format is msgpack for binary efficiency.
    Falls back to JSON for compatibility (without image data).
    """

    def __init__(
        self,
        format: SerializationFormat = SerializationFormat.MSGPACK,
        compression: CompressionType = CompressionType.NONE,
    ):
        """
        Initialize serializer with format and compression settings.

        Args:
            format: Serialization format to use
            compression: Compression type to apply
        """
        self.format = format
        self.compression = compression

        # msgpack configuration for numpy arrays
        self._msgpack_default = msgpack.Packer(
            default=self._msgpack_encode_default, use_bin_type=True
        ).pack

    def _msgpack_encode_default(self, obj: Any) -> Any:
        """Handle numpy arrays and datetime for msgpack encoding."""
        if isinstance(obj, np.ndarray):
            return {
                "__ndarray__": True,
                "dtype": str(obj.dtype),
                "shape": obj.shape,
                "data": obj.tobytes(),
            }
        elif isinstance(obj, datetime):
            return {"__datetime__": True, "iso": obj.isoformat()}
        return obj

    def _msgpack_decode_hook(self, obj: Dict[str, Any]) -> Any:
        """Restore numpy arrays and datetime from msgpack."""
        if "__ndarray__" in obj:
            data = np.frombuffer(obj["data"], dtype=obj["dtype"])
            return data.reshape(obj["shape"])
        elif "__datetime__" in obj:
            return datetime.fromisoformat(obj["iso"])
        return obj

    def serialize(self, frame: FrameData) -> bytes:
        """
        Serialize a frame to bytes.

        Args:
            frame: Frame to serialize

        Returns:
            Serialized frame data

        Raises:
            SerializationError: If serialization fails
        """
        if not isinstance(frame, FrameData):
            raise SerializationError(f"Expected FrameData object, got {type(frame)}")

        try:
            # Prepare frame data
            frame_dict = {
                "id": frame.id,
                "timestamp": frame.timestamp,
                "camera_id": frame.camera_id,
                "sequence_number": frame.sequence_number,
                "metadata": frame.metadata or {},
            }

            if self.format == SerializationFormat.MSGPACK:
                # Include image data for msgpack
                frame_dict["image_data"] = frame.image_data
                serialized = msgpack.packb(
                    frame_dict, default=self._msgpack_encode_default, use_bin_type=True
                )
            elif self.format == SerializationFormat.JSON:
                # Skip image data for JSON
                frame_dict["image_data"] = None
                serialized = json.dumps(frame_dict, default=str).encode("utf-8")
            else:
                raise SerializationError(f"Unsupported format: {self.format}")

            # Apply compression if requested
            if self.compression == CompressionType.LZ4:
                serialized = lz4.frame.compress(serialized)

            return serialized  # type: ignore[no-any-return]

        except Exception as e:
            raise SerializationError(f"Failed to serialize frame: {str(e)}") from e

    def deserialize(self, data: bytes) -> FrameData:
        """
        Deserialize bytes to a Frame object.

        Args:
            data: Serialized frame data

        Returns:
            Deserialized FrameData object

        Raises:
            DeserializationError: If deserialization fails
        """
        if not data:
            raise DeserializationError("Empty data cannot be deserialized")

        try:
            # Decompress if needed
            if self.compression == CompressionType.LZ4:
                data = lz4.frame.decompress(data)

            # Deserialize based on format
            if self.format == SerializationFormat.MSGPACK:
                frame_dict = msgpack.unpackb(
                    data, object_hook=self._msgpack_decode_hook, raw=False
                )
            elif self.format == SerializationFormat.JSON:
                frame_dict = json.loads(data.decode("utf-8"))
                # Convert timestamp string back to datetime
                if isinstance(frame_dict.get("timestamp"), str):
                    frame_dict["timestamp"] = datetime.fromisoformat(
                        frame_dict["timestamp"].replace("Z", "+00:00")
                    )
            else:
                raise DeserializationError(f"Unsupported format: {self.format}")

            # Create FrameData object
            return FrameData(
                id=frame_dict["id"],
                timestamp=frame_dict["timestamp"],
                camera_id=frame_dict["camera_id"],
                sequence_number=frame_dict["sequence_number"],
                image_data=frame_dict.get("image_data"),
                metadata=frame_dict.get("metadata", {}),
            )

        except Exception as e:
            raise DeserializationError(f"Failed to deserialize frame: {str(e)}") from e

    def detect_format(self, data: bytes) -> SerializationFormat:
        """
        Detect serialization format from data.

        Args:
            data: Serialized data to check

        Returns:
            Detected serialization format
        """
        # Check if compressed
        if data.startswith(b'\x04"M\x18'):  # LZ4 magic bytes
            data = lz4.frame.decompress(data)

        # Check format
        if data.startswith(b"{"):
            return SerializationFormat.JSON
        else:
            # Assume msgpack for binary data
            return SerializationFormat.MSGPACK

    def serialize_batch(self, frames: List[FrameData]) -> List[bytes]:
        """
        Serialize multiple frames efficiently.

        Args:
            frames: List of frames to serialize

        Returns:
            List of serialized frame data
        """
        return [self.serialize(frame) for frame in frames]

    def deserialize_batch(self, data_list: List[bytes]) -> List[FrameData]:
        """
        Deserialize multiple frames efficiently.

        Args:
            data_list: List of serialized frame data

        Returns:
            List of deserialized FrameData objects
        """
        return [self.deserialize(data) for data in data_list]
