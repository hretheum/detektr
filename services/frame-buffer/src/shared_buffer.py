"""
Shared Frame Buffer - Singleton pattern for sharing buffer between consumer and API.

This module provides a thread-safe singleton implementation of FrameBuffer
to ensure that both the consumer and API endpoints use the same buffer instance.
"""

import asyncio
import threading
from typing import Optional

from frame_buffer import FrameBuffer


class SharedFrameBuffer:
    """
    Singleton wrapper for FrameBuffer to ensure shared state between components.

    This class implements a thread-safe singleton pattern to guarantee that
    all parts of the application (consumer, API endpoints) use the same
    FrameBuffer instance.
    """

    _instance: Optional["SharedFrameBuffer"] = None
    _buffer: Optional[FrameBuffer] = None
    _lock = asyncio.Lock()
    _sync_lock = threading.Lock()

    def __new__(cls) -> "SharedFrameBuffer":
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_instance(cls) -> FrameBuffer:
        """
        Get the shared FrameBuffer instance.

        This method is thread-safe and ensures that only one FrameBuffer
        instance is created, even when called concurrently.

        Returns:
            FrameBuffer: The shared buffer instance
        """
        if cls._buffer is None:
            async with cls._lock:
                # Double-check pattern to avoid race conditions
                if cls._buffer is None:
                    cls._buffer = FrameBuffer()
        return cls._buffer

    @classmethod
    def get_instance_sync(cls) -> FrameBuffer:
        """
        Synchronous version for compatibility with sync code.

        This method is thread-safe and can be called from synchronous contexts.

        Returns:
            FrameBuffer: The shared buffer instance

        Raises:
            RuntimeError: If called within an already running event loop
        """
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                raise RuntimeError(
                    "Cannot use get_instance_sync in async context. "
                    "Use await get_instance() instead."
                )
        except RuntimeError:
            # No event loop running, safe to proceed
            pass

        with cls._sync_lock:
            if cls._buffer is None:
                cls._buffer = FrameBuffer()
            return cls._buffer

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance.

        This is mainly useful for testing to ensure clean state between tests.
        This method is thread-safe.
        """
        with cls._sync_lock:
            cls._buffer = None
            cls._instance = None
