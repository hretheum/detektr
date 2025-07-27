"""Frame buffer implementation for in-memory buffering."""

import logging
import threading
import time
from collections import deque
from typing import Any, Dict, Optional

from metrics import buffer_size, buffer_usage_ratio, frames_dropped

logger = logging.getLogger(__name__)


class FrameBuffer:
    """Thread-safe frame buffer with configurable size."""

    def __init__(self, max_size: int = 1000):
        """Initialize frame buffer with specified maximum size."""
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)
        # Use threading.Lock for cross-task synchronization
        self._lock = threading.Lock()
        self._backpressure_events = 0
        self._last_backpressure_time = 0
        logger.info(f"FrameBuffer initialized with max_size={max_size}")

    async def put(self, frame_data: Dict[str, Any]) -> bool:
        """Add frame to buffer. Returns True if successful, False if full."""
        with self._lock:
            current_size = len(self._buffer)
            if current_size >= self.max_size:
                # Track backpressure event
                self._backpressure_events += 1
                self._last_backpressure_time = time.time()
                frames_dropped.labels(reason="buffer_full").inc()
                logger.warning(
                    f"Buffer full ({current_size}/{self.max_size}), dropping frame"
                )
                return False
            self._buffer.append(frame_data)
            new_size = len(self._buffer)
            # Update metrics
            buffer_size.set(new_size)
            buffer_usage_ratio.set(self.usage_ratio())
            logger.debug(f"Frame added to buffer, new size: {new_size}")
            return True

    async def get(self) -> Optional[Dict[str, Any]]:
        """Get frame from buffer. Returns None if empty."""
        with self._lock:
            if not self._buffer:
                return None
            frame = self._buffer.popleft()
            new_size = len(self._buffer)
            # Update metrics
            buffer_size.set(new_size)
            buffer_usage_ratio.set(self.usage_ratio())
            logger.debug(f"Frame retrieved from buffer, new size: {new_size}")
            return frame

    async def get_batch(self, count: int) -> list[Dict[str, Any]]:
        """Get multiple frames from buffer."""
        with self._lock:
            batch = []
            initial_size = len(self._buffer)
            for _ in range(min(count, len(self._buffer))):
                if self._buffer:
                    batch.append(self._buffer.popleft())
            new_size = len(self._buffer)
            # Update metrics
            buffer_size.set(new_size)
            buffer_usage_ratio.set(self.usage_ratio())
            if batch:
                logger.debug(
                    f"Retrieved {len(batch)} frames from buffer, "
                    f"size: {initial_size} -> {new_size}"
                )
            return batch

    def is_full(self) -> bool:
        """Check if buffer is full."""
        with self._lock:
            return len(self._buffer) >= self.max_size

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        with self._lock:
            return len(self._buffer) == 0

    def size(self) -> int:
        """Get current buffer size."""
        with self._lock:
            return len(self._buffer)

    def capacity(self) -> int:
        """Get buffer capacity."""
        return self.max_size

    def usage_ratio(self) -> float:
        """Get buffer usage ratio (0.0 to 1.0)."""
        with self._lock:
            return len(self._buffer) / self.max_size if self.max_size > 0 else 0.0

    async def clear(self):
        """Clear all frames from buffer."""
        with self._lock:
            self._buffer.clear()
            buffer_size.set(0)
            buffer_usage_ratio.set(0.0)
            logger.info("Buffer cleared")

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
