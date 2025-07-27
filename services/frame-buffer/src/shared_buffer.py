"""Shared frame buffer implementation to fix dead-end issue."""

import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SharedFrameBuffer:
    """Thread-safe shared frame buffer accessible by both consumer and API."""

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_size: int = 1000):
        """Initialize shared frame buffer."""
        if self._initialized:
            return

        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.dropped_count = 0
        self.total_processed = 0
        self._initialized = True
        logger.info(f"SharedFrameBuffer initialized with max_size={max_size}")

    async def add_frame(self, frame_data: Dict[str, Any]) -> bool:
        """Add frame to buffer."""
        async with self._lock:
            if len(self.buffer) >= self.max_size:
                self.dropped_count += 1
                logger.warning(
                    f"Buffer full, dropping frame. Total dropped: {self.dropped_count}"
                )
                return False

            # Add timestamp
            frame_data["buffered_at"] = datetime.now().isoformat()
            self.buffer.append(frame_data)
            self.total_processed += 1
            return True

    async def get_frame(self) -> Optional[Dict[str, Any]]:
        """Get oldest frame from buffer."""
        async with self._lock:
            if not self.buffer:
                return None
            return self.buffer.popleft()

    async def get_status(self) -> Dict[str, Any]:
        """Get buffer status."""
        async with self._lock:
            return {
                "size": len(self.buffer),
                "max_size": self.max_size,
                "dropped_count": self.dropped_count,
                "total_processed": self.total_processed,
                "is_full": len(self.buffer) >= self.max_size,
            }

    async def clear(self):
        """Clear the buffer."""
        async with self._lock:
            self.buffer.clear()
            logger.info("Buffer cleared")


# Global shared instance
shared_buffer = SharedFrameBuffer()
