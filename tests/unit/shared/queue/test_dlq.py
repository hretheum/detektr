"""
Tests for Dead Letter Queue handling.

Verifies:
- Failed frames are properly stored in DLQ
- Retry mechanism with exponential backoff
- Manual reprocessing capabilities
"""
import asyncio
from datetime import datetime

import pytest

from src.shared.kernel.domain.frame_data import FrameData
from src.shared.queue.dlq import DeadLetterQueue, DLQEntry, DLQReason


class TestDeadLetterQueue:
    """Test cases for Dead Letter Queue."""

    @pytest.fixture
    def dlq(self):
        """Create DLQ instance."""
        return DeadLetterQueue(
            max_size=100,
            max_retries=3,
            base_retry_delay=0.1,  # Short delay for tests
            enable_auto_retry=True,
        )

    @pytest.fixture
    def sample_frame(self):
        """Create sample frame."""
        return FrameData(
            id="test_frame_001",
            timestamp=datetime.now(),
            camera_id="camera_01",
            sequence_number=1,
            image_data=None,
            metadata={"test": True},
        )

    @pytest.mark.asyncio
    async def test_add_entry_to_dlq(self, dlq, sample_frame):
        """Test adding failed frame to DLQ."""
        result = await dlq.add_entry(
            frame=sample_frame,
            reason=DLQReason.PROCESSING_ERROR,
            error_message="Test error",
            metadata={"attempt": 1},
        )

        assert result is True
        assert dlq.get_stats()["total_entries"] == 1
        assert dlq.get_stats()["current_size"] == 1

    @pytest.mark.asyncio
    async def test_dlq_full_handling(self, dlq, sample_frame):
        """Test behavior when DLQ is full."""
        # Set small max size
        dlq.max_size = 2
        dlq._queue = asyncio.Queue(maxsize=2)

        # Fill DLQ
        for i in range(2):
            frame = FrameData(
                id=f"frame_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            result = await dlq.add_entry(
                frame=frame, reason=DLQReason.TIMEOUT, error_message="Timeout"
            )
            assert result is True

        # Try to add one more - should fail
        result = await dlq.add_entry(
            frame=sample_frame, reason=DLQReason.TIMEOUT, error_message="Timeout"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_automatic_retry(self, dlq, sample_frame):
        """Test automatic retry mechanism."""
        retry_count = 0
        success_on_attempt = 2

        async def retry_callback(frame):
            nonlocal retry_count
            retry_count += 1
            # Succeed on second attempt
            return retry_count >= success_on_attempt

        dlq.set_retry_callback(retry_callback)

        # Add entry to DLQ
        await dlq.add_entry(
            frame=sample_frame,
            reason=DLQReason.PROCESSING_ERROR,
            error_message="Initial failure",
        )

        # Wait for retries
        await asyncio.sleep(0.5)

        # Should have retried successfully
        assert retry_count >= success_on_attempt
        assert dlq.get_stats()["successful_retries"] == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, dlq, sample_frame):
        """Test that entries stop retrying after max attempts."""
        retry_count = 0

        async def failing_callback(frame):
            nonlocal retry_count
            retry_count += 1
            return False  # Always fail

        dlq.set_retry_callback(failing_callback)
        dlq.max_retries = 2  # Reduce for faster test

        # Add entry to DLQ
        await dlq.add_entry(
            frame=sample_frame,
            reason=DLQReason.VALIDATION_FAILED,
            error_message="Validation error",
        )

        # Wait for all retries
        await asyncio.sleep(1.0)

        # Should have retried max times
        assert retry_count == dlq.max_retries
        assert dlq.get_stats()["permanent_failures"] == 1

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        entry = DLQEntry(
            frame=FrameData(
                id="test",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=1,
                image_data=None,
                metadata={},
            ),
            reason=DLQReason.TIMEOUT,
            error_message="Timeout",
        )

        base_delay = 1.0

        # Test backoff progression
        assert entry.get_next_retry_delay(base_delay) == 1.0  # 2^0
        entry.increment_retry()
        assert entry.get_next_retry_delay(base_delay) == 2.0  # 2^1
        entry.increment_retry()
        assert entry.get_next_retry_delay(base_delay) == 4.0  # 2^2
        entry.increment_retry()
        assert entry.get_next_retry_delay(base_delay) == 8.0  # 2^3

        # Test max cap (5 minutes)
        entry.retry_count = 10
        assert entry.get_next_retry_delay(base_delay) == 300.0

    @pytest.mark.asyncio
    async def test_get_entries_filtering(self, dlq):
        """Test retrieving entries with filtering."""
        # Add entries with different reasons
        for i in range(5):
            frame = FrameData(
                id=f"frame_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            reason = DLQReason.TIMEOUT if i % 2 == 0 else DLQReason.PROCESSING_ERROR
            await dlq.add_entry(frame=frame, reason=reason, error_message=f"Error {i}")

        # Get all entries
        all_entries = await dlq.get_entries(limit=10)
        assert len(all_entries) == 5

        # Get filtered entries
        timeout_entries = await dlq.get_entries(limit=10, reason=DLQReason.TIMEOUT)
        assert len(timeout_entries) == 3
        assert all(e.reason == DLQReason.TIMEOUT for e in timeout_entries)

    @pytest.mark.asyncio
    async def test_manual_reprocess(self, dlq):
        """Test manual reprocessing of entries."""
        processed_frames = []

        async def tracking_callback(frame):
            processed_frames.append(frame.id)
            return True  # Always succeed

        dlq.set_retry_callback(tracking_callback)

        # Add entries to DLQ
        frames = []
        for i in range(3):
            frame = FrameData(
                id=f"manual_frame_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            frames.append(frame)
            await dlq.add_entry(
                frame=frame, reason=DLQReason.PROCESSING_ERROR, error_message="Error"
            )

        # Disable auto retry to test manual reprocess
        dlq.enable_auto_retry = False

        # Get entries and reprocess manually
        entries = await dlq.get_entries()
        results = await dlq.reprocess_entries(entries)

        assert results["success"] == 3
        assert results["failure"] == 0
        assert len(processed_frames) == 3

    @pytest.mark.asyncio
    async def test_force_reprocess_exceeded_retries(self, dlq, sample_frame):
        """Test force reprocessing entries that exceeded max retries."""
        # Create entry with exceeded retries
        entry = DLQEntry(
            frame=sample_frame,
            reason=DLQReason.MAX_RETRIES_EXCEEDED,
            error_message="Max retries",
            retry_count=10,  # Exceeds max
        )

        # Set successful callback
        async def success_callback(frame):
            return True

        dlq.set_retry_callback(success_callback)

        # Try normal reprocess - should fail
        results = await dlq.reprocess_entries([entry], force=False)
        assert results["failure"] == 1
        assert results["success"] == 0

        # Force reprocess - should succeed
        results = await dlq.reprocess_entries([entry], force=True)
        assert results["success"] == 1
        assert results["failure"] == 0

    @pytest.mark.asyncio
    async def test_clear_dlq(self, dlq):
        """Test clearing all entries from DLQ."""
        # Add multiple entries
        for i in range(5):
            frame = FrameData(
                id=f"frame_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            await dlq.add_entry(
                frame=frame, reason=DLQReason.TIMEOUT, error_message="Timeout"
            )

        assert dlq.get_stats()["current_size"] == 5

        # Clear DLQ
        cleared_count = await dlq.clear()

        assert cleared_count == 5
        assert dlq.get_stats()["current_size"] == 0
        assert len(dlq._retry_tasks) == 0

    @pytest.mark.asyncio
    async def test_dlq_shutdown(self, dlq, sample_frame):
        """Test graceful shutdown of DLQ."""
        # Add entry with retry
        await dlq.add_entry(
            frame=sample_frame, reason=DLQReason.PROCESSING_ERROR, error_message="Error"
        )

        # Should have active retry task
        assert len(dlq._retry_tasks) > 0

        # Shutdown
        await dlq.shutdown()

        # All retry tasks should be cancelled
        assert len(dlq._retry_tasks) == 0

    @pytest.mark.asyncio
    async def test_concurrent_retry_handling(self, dlq):
        """Test handling of concurrent retries."""
        retry_results = {}

        async def concurrent_callback(frame):
            # Simulate some processing time
            await asyncio.sleep(0.05)
            retry_results[frame.id] = True
            return True

        dlq.set_retry_callback(concurrent_callback)

        # Add multiple entries
        for i in range(5):
            frame = FrameData(
                id=f"concurrent_{i}",
                timestamp=datetime.now(),
                camera_id="camera_01",
                sequence_number=i,
                image_data=None,
                metadata={},
            )
            await dlq.add_entry(
                frame=frame, reason=DLQReason.PROCESSING_ERROR, error_message="Error"
            )

        # Wait for all retries
        await asyncio.sleep(0.5)

        # All should have been retried
        assert len(retry_results) == 5
        assert all(retry_results.values())
