"""
Dead Letter Queue (DLQ) handling for failed frames.

Provides:
- DLQ for storing failed frames
- Retry mechanism with exponential backoff
- Monitoring of DLQ operations
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from shared.kernel.domain.frame_data import FrameData
from shared.queue.metrics import dropped_frames

logger = logging.getLogger(__name__)


class DLQReason(Enum):
    """Reasons for moving frame to DLQ."""

    PROCESSING_ERROR = "processing_error"
    TIMEOUT = "timeout"
    VALIDATION_FAILED = "validation_failed"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


@dataclass
class DLQEntry:
    """Entry in the Dead Letter Queue."""

    frame: FrameData
    reason: DLQReason
    error_message: str
    retry_count: int = 0
    first_failure_time: datetime = field(default_factory=datetime.now)
    last_failure_time: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def increment_retry(self) -> None:
        """Increment retry count and update timestamp."""
        self.retry_count += 1
        self.last_failure_time = datetime.now()

    def can_retry(self, max_retries: int) -> bool:
        """Check if entry can be retried."""
        return self.retry_count < max_retries

    def get_next_retry_delay(self, base_delay: float = 1.0) -> float:
        """Calculate next retry delay with exponential backoff."""
        # Exponential backoff: base_delay * 2^retry_count
        # Cap at 5 minutes
        delay: float = min(base_delay * (2**self.retry_count), 300.0)
        return delay


class DeadLetterQueue:
    """
    Dead Letter Queue for handling failed frames.

    Features:
    - Automatic retry with exponential backoff
    - Configurable max retries
    - Monitoring and alerting
    - Manual inspection and reprocessing
    """

    def __init__(
        self,
        max_size: int = 10000,
        max_retries: int = 3,
        base_retry_delay: float = 1.0,
        enable_auto_retry: bool = True,
    ):
        """
        Initialize DLQ.

        Args:
            max_size: Maximum number of entries in DLQ
            max_retries: Maximum retry attempts per entry
            base_retry_delay: Base delay for exponential backoff
            enable_auto_retry: Whether to automatically retry failed frames
        """
        self.max_size = max_size
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        self.enable_auto_retry = enable_auto_retry

        self._queue: asyncio.Queue[DLQEntry] = asyncio.Queue(maxsize=max_size)
        self._retry_tasks: Dict[str, asyncio.Task] = {}
        self._stats = {
            "total_entries": 0,
            "successful_retries": 0,
            "permanent_failures": 0,
            "current_size": 0,
        }

        # Retry callback
        self._retry_callback: Optional[Callable] = None

    async def add_entry(
        self,
        frame: FrameData,
        reason: DLQReason,
        error_message: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Add failed frame to DLQ.

        Returns True if added, False if queue is full.
        """
        try:
            entry = DLQEntry(
                frame=frame,
                reason=reason,
                error_message=error_message,
                metadata=metadata or {},
            )

            # Try to add to queue
            self._queue.put_nowait(entry)
            self._stats["total_entries"] += 1
            self._stats["current_size"] = self._queue.qsize()

            # Record in metrics
            dropped_frames.labels(queue_name="dlq", reason=reason.value).inc()

            logger.warning(
                f"Frame {frame.id} added to DLQ. Reason: {reason.value}, "
                f"Error: {error_message}"
            )

            # Schedule retry if enabled
            if self.enable_auto_retry and entry.can_retry(self.max_retries):
                await self._schedule_retry(entry)

            return True

        except asyncio.QueueFull:
            logger.error(
                f"DLQ is full ({self.max_size} entries). "
                f"Cannot add frame {frame.id}"
            )
            return False

    async def _schedule_retry(self, entry: DLQEntry) -> None:
        """Schedule automatic retry for entry."""
        delay = entry.get_next_retry_delay(self.base_retry_delay)

        async def retry_task() -> None:
            await asyncio.sleep(delay)
            await self._retry_entry(entry)

        # Cancel existing retry task if any
        if entry.frame.id in self._retry_tasks:
            self._retry_tasks[entry.frame.id].cancel()

        # Schedule new retry
        task = asyncio.create_task(retry_task())
        self._retry_tasks[entry.frame.id] = task

    async def _retry_entry(self, entry: DLQEntry) -> bool:
        """
        Retry processing a DLQ entry.

        Returns True if successful, False otherwise.
        """
        if not self._retry_callback:
            logger.error("No retry callback configured for DLQ")
            return False

        entry.increment_retry()

        try:
            # Attempt to reprocess
            logger.info(
                f"Retrying frame {entry.frame.id} "
                f"(attempt {entry.retry_count}/{self.max_retries})"
            )

            result = await self._retry_callback(entry.frame)

            if result:
                # Success - remove from retry tasks
                self._retry_tasks.pop(entry.frame.id, None)
                self._stats["successful_retries"] += 1
                logger.info(f"Successfully retried frame {entry.frame.id}")
                return True
            else:
                # Failed - check if we can retry again
                if entry.can_retry(self.max_retries):
                    await self._schedule_retry(entry)
                else:
                    # Max retries exceeded
                    self._stats["permanent_failures"] += 1
                    self._retry_tasks.pop(entry.frame.id, None)
                    logger.error(
                        f"Frame {entry.frame.id} permanently failed "
                        f"after {entry.retry_count} retries"
                    )
                return False

        except Exception as e:
            logger.error(f"Error retrying frame {entry.frame.id}: {str(e)}")

            # Check if we can retry again
            if entry.can_retry(self.max_retries):
                await self._schedule_retry(entry)
            else:
                self._stats["permanent_failures"] += 1
                self._retry_tasks.pop(entry.frame.id, None)

            return False

    def set_retry_callback(self, callback: Callable) -> None:
        """Set callback function for retrying frames."""
        self._retry_callback = callback

    async def get_entries(
        self,
        limit: int = 100,
        reason: Optional[DLQReason] = None,
    ) -> List[DLQEntry]:
        """
        Get entries from DLQ for inspection.

        Args:
            limit: Maximum number of entries to return
            reason: Filter by specific reason

        Returns:
            List of DLQ entries
        """
        entries: List[DLQEntry] = []
        temp_storage: List[DLQEntry] = []

        # Extract entries from queue
        while len(entries) < limit and not self._queue.empty():
            try:
                entry = self._queue.get_nowait()
                if reason is None or entry.reason == reason:
                    entries.append(entry)
                else:
                    temp_storage.append(entry)
            except asyncio.QueueEmpty:
                break

        # Put back entries we're not returning
        for entry in temp_storage + entries:
            try:
                self._queue.put_nowait(entry)
            except asyncio.QueueFull:
                logger.error("Could not restore entry to DLQ")

        return entries[:limit]

    async def reprocess_entries(
        self,
        entries: List[DLQEntry],
        force: bool = False,
    ) -> Dict[str, int]:
        """
        Manually reprocess specific entries.

        Args:
            entries: Entries to reprocess
            force: Force retry even if max retries exceeded

        Returns:
            Dict with success/failure counts
        """
        results = {"success": 0, "failure": 0}

        for entry in entries:
            if force:
                entry.retry_count = 0  # Reset retry count

            if entry.can_retry(self.max_retries) or force:
                success = await self._retry_entry(entry)
                if success:
                    results["success"] += 1
                else:
                    results["failure"] += 1
            else:
                results["failure"] += 1
                logger.warning(
                    f"Skipping frame {entry.frame.id} - "
                    f"max retries exceeded and force=False"
                )

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get DLQ statistics."""
        self._stats["current_size"] = self._queue.qsize()
        self._stats["active_retries"] = len(self._retry_tasks)
        return self._stats.copy()

    async def clear(self) -> int:
        """
        Clear all entries from DLQ.

        Returns number of entries cleared.
        """
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break

        # Cancel all retry tasks
        for task in self._retry_tasks.values():
            task.cancel()
        self._retry_tasks.clear()

        self._stats["current_size"] = 0
        logger.info(f"Cleared {count} entries from DLQ")

        return count

    async def shutdown(self) -> None:
        """Shutdown DLQ and cancel all retry tasks."""
        logger.info("Shutting down DLQ...")

        # Cancel all retry tasks
        for task in self._retry_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self._retry_tasks:
            await asyncio.gather(*self._retry_tasks.values(), return_exceptions=True)

        self._retry_tasks.clear()
        logger.info("DLQ shutdown complete")
