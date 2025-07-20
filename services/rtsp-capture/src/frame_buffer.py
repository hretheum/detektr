"""
Circular frame buffer implementation for high-performance frame management.

Features:
- Zero-copy operations for performance
- Thread-safe concurrent access
- Automatic overflow handling (circular overwrite)
- Built-in statistics tracking
"""

import threading
from collections import deque
from dataclasses import dataclass
from typing import Tuple

import numpy as np


class FrameBufferError(Exception):
    """Base exception for frame buffer errors."""

    pass


@dataclass
class FrameData:
    """Container for frame data with metadata."""

    frame_id: str
    frame: np.ndarray
    timestamp: float

    @property
    def size_bytes(self) -> int:
        """Calculate frame size in bytes."""
        return self.frame.nbytes


class CircularFrameBuffer:
    """
    Thread-safe circular buffer for video frames.

    Implements a fixed-size buffer that overwrites oldest frames
    when capacity is reached (circular behavior).
    """

    def __init__(self, capacity: int):
        """
        Initialize circular frame buffer.

        Args:
            capacity: Maximum number of frames to store
        """
        if capacity <= 0:
            raise ValueError(f"Capacity must be positive, got {capacity}")

        self._capacity = capacity
        self._buffer: deque = deque(maxlen=capacity)
        self._lock = threading.RLock()

        # Statistics tracking
        self._total_frames_added = 0
        self._total_frames_dropped = 0
        self._total_frames_retrieved = 0

    @property
    def capacity(self) -> int:
        """Get buffer capacity."""
        return self._capacity

    @property
    def size(self) -> int:
        """Get current number of frames in buffer."""
        with self._lock:
            return len(self._buffer)

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        with self._lock:
            return len(self._buffer) == 0

    def is_full(self) -> bool:
        """Check if buffer is at capacity."""
        with self._lock:
            return len(self._buffer) == self._capacity

    def put(self, frame_id: str, frame: np.ndarray, timestamp: float) -> None:
        """
        Add frame to buffer.

        If buffer is full, oldest frame is automatically dropped.

        Args:
            frame_id: Unique frame identifier
            frame: Video frame as numpy array
            timestamp: Frame capture timestamp
        """
        frame_data = FrameData(frame_id, frame, timestamp)

        with self._lock:
            # Check if we'll drop a frame
            if len(self._buffer) == self._capacity:
                self._total_frames_dropped += 1

            self._buffer.append(frame_data)
            self._total_frames_added += 1

    def get(self) -> Tuple[str, np.ndarray, float]:
        """
        Retrieve and remove oldest frame from buffer.

        Returns:
            Tuple of (frame_id, frame, timestamp)

        Raises:
            FrameBufferError: If buffer is empty
        """
        with self._lock:
            if not self._buffer:
                raise FrameBufferError("Buffer is empty")

            frame_data = self._buffer.popleft()
            self._total_frames_retrieved += 1

            return frame_data.frame_id, frame_data.frame, frame_data.timestamp

    def peek(self) -> Tuple[str, np.ndarray, float]:
        """
        Peek at oldest frame without removing it.

        Returns:
            Tuple of (frame_id, frame, timestamp)

        Raises:
            FrameBufferError: If buffer is empty
        """
        with self._lock:
            if not self._buffer:
                raise FrameBufferError("Buffer is empty")

            frame_data = self._buffer[0]
            return frame_data.frame_id, frame_data.frame, frame_data.timestamp

    def clear(self) -> None:
        """Clear all frames from buffer."""
        with self._lock:
            dropped_count = len(self._buffer)
            self._buffer.clear()
            self._total_frames_dropped += dropped_count

    def get_statistics(self) -> dict:
        """
        Get buffer statistics.

        Returns:
            Dictionary with statistics:
            - total_frames_added: Total frames ever added
            - total_frames_dropped: Frames dropped due to overflow
            - total_frames_retrieved: Frames retrieved via get()
            - current_size: Current number of frames in buffer
            - capacity: Buffer capacity
            - utilization: Current utilization percentage
        """
        with self._lock:
            current_size = len(self._buffer)
            return {
                "total_frames_added": self._total_frames_added,
                "total_frames_dropped": self._total_frames_dropped,
                "total_frames_retrieved": self._total_frames_retrieved,
                "current_size": current_size,
                "capacity": self._capacity,
                "utilization": (current_size / self._capacity) * 100
                if self._capacity > 0
                else 0,
            }

    def __repr__(self) -> str:
        """Return string representation of buffer state."""
        with self._lock:
            return (
                f"CircularFrameBuffer(capacity={self._capacity}, "
                f"size={len(self._buffer)}, "
                f"dropped={self._total_frames_dropped})"
            )
