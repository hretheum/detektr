"""Frame buffer implementation for in-memory buffering."""

import asyncio
import time
from collections import deque
from typing import Any, Dict, Optional

from metrics import buffer_size, buffer_usage_ratio, frames_dropped


class FrameBuffer:
    """Thread-safe frame buffer with configurable size."""

    def __init__(self, max_size: int = 1000):
        """Initialize frame buffer with specified maximum size."""
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = asyncio.Lock()
        self._backpressure_events = 0
        self._last_backpressure_time = 0

    async def put(self, frame_data: Dict[str, Any]) -> bool:
        """Add frame to buffer. Returns True if successful, False if full."""
        async with self._lock:
            if len(self._buffer) >= self.max_size:
                # Track backpressure event
                self._backpressure_events += 1
                self._last_backpressure_time = time.time()
                frames_dropped.labels(reason="buffer_full").inc()
                return False
            self._buffer.append(frame_data)
            # Update metrics
            buffer_size.set(len(self._buffer))
            buffer_usage_ratio.set(self.usage_ratio())
            return True

    async def get(self) -> Optional[Dict[str, Any]]:
        """Get frame from buffer. Returns None if empty."""
        async with self._lock:
            if not self._buffer:
                return None
            frame = self._buffer.popleft()
            # Update metrics
            buffer_size.set(len(self._buffer))
            buffer_usage_ratio.set(self.usage_ratio())
            return frame

    async def get_batch(self, count: int) -> list[Dict[str, Any]]:
        """Get multiple frames from buffer."""
        async with self._lock:
            batch = []
            for _ in range(min(count, len(self._buffer))):
                if self._buffer:
                    batch.append(self._buffer.popleft())
            # Update metrics
            buffer_size.set(len(self._buffer))
            buffer_usage_ratio.set(self.usage_ratio())
            return batch

    def is_full(self) -> bool:
        """Check if buffer is full."""
        return len(self._buffer) >= self.max_size

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self._buffer) == 0

    def size(self) -> int:
        """Get current buffer size."""
        return len(self._buffer)

    def capacity(self) -> int:
        """Get buffer capacity."""
        return self.max_size

    def usage_ratio(self) -> float:
        """Get buffer usage ratio (0.0 to 1.0)."""
        return len(self._buffer) / self.max_size if self.max_size > 0 else 0.0

    async def clear(self):
        """Clear all frames from buffer."""
        async with self._lock:
            self._buffer.clear()
            buffer_size.set(0)
            buffer_usage_ratio.set(0.0)

    def get_backpressure_stats(self) -> Dict[str, Any]:
        """Get backpressure statistics."""
        return {
            "backpressure_events": self._backpressure_events,
            "last_backpressure_time": self._last_backpressure_time,
            "seconds_since_last_backpressure": (
                time.time() - self._last_backpressure_time
                if self._last_backpressure_time > 0
                else None
            ),
        }
