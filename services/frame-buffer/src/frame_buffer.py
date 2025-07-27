"""Frame buffer implementation for in-memory buffering."""

import asyncio
from collections import deque
from typing import Any, Dict, Optional


class FrameBuffer:
    """Thread-safe frame buffer with configurable size."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = asyncio.Lock()

    async def put(self, frame_data: Dict[str, Any]) -> bool:
        """Add frame to buffer. Returns True if successful, False if full."""
        async with self._lock:
            if len(self._buffer) >= self.max_size:
                return False
            self._buffer.append(frame_data)
            return True

    async def get(self) -> Optional[Dict[str, Any]]:
        """Get frame from buffer. Returns None if empty."""
        async with self._lock:
            if not self._buffer:
                return None
            return self._buffer.popleft()

    async def get_batch(self, count: int) -> list[Dict[str, Any]]:
        """Get multiple frames from buffer."""
        async with self._lock:
            batch = []
            for _ in range(min(count, len(self._buffer))):
                if self._buffer:
                    batch.append(self._buffer.popleft())
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
