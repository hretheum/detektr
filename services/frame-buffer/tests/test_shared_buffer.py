"""Tests for SharedFrameBuffer singleton implementation."""

import asyncio

import pytest

from src.shared_buffer import SharedFrameBuffer


class TestSharedFrameBuffer:
    """Test cases for SharedFrameBuffer."""

    def setup_method(self):
        """Reset singleton before each test."""
        SharedFrameBuffer.reset()

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that get_instance always returns same buffer."""
        # Get instance multiple times
        buffer1 = await SharedFrameBuffer.get_instance()
        buffer2 = await SharedFrameBuffer.get_instance()
        buffer3 = SharedFrameBuffer.get_instance_sync()

        # All should be the same instance
        assert buffer1 is buffer2
        assert buffer2 is buffer3

    @pytest.mark.asyncio
    async def test_concurrent_initialization(self):
        """Test thread-safe initialization under concurrent access."""
        # Reset to ensure clean state
        SharedFrameBuffer.reset()

        # Create multiple concurrent tasks trying to get instance
        tasks = [SharedFrameBuffer.get_instance() for _ in range(10)]

        # Run concurrently
        buffers = await asyncio.gather(*tasks)

        # All should be the same instance
        first_buffer = buffers[0]
        for buffer in buffers[1:]:
            assert buffer is first_buffer

    def test_sync_access(self):
        """Test synchronous access to buffer."""
        buffer1 = SharedFrameBuffer.get_instance_sync()
        buffer2 = SharedFrameBuffer.get_instance_sync()

        assert buffer1 is buffer2

    def test_reset_functionality(self):
        """Test that reset clears the singleton."""
        # Get instance
        buffer1 = SharedFrameBuffer.get_instance_sync()

        # Reset
        SharedFrameBuffer.reset()

        # Get new instance
        buffer2 = SharedFrameBuffer.get_instance_sync()

        # Should be different instances after reset
        assert buffer1 is not buffer2

    @pytest.mark.asyncio
    async def test_buffer_functionality(self):
        """Test that shared buffer works correctly."""
        buffer = await SharedFrameBuffer.get_instance()

        # Test basic operations
        test_frame = {"frame_id": "test123", "data": "test"}

        # Put frame
        await buffer.put(test_frame)

        # Get frame
        retrieved = await buffer.get()

        assert retrieved == test_frame
