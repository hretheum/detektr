"""Priority queue implementation for frame processing."""

import asyncio
import heapq
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from prometheus_client import Counter, Gauge, Histogram

from .models import FrameReadyEvent

logger = logging.getLogger(__name__)


# Metrics
priority_queue_size = Gauge(
    "frame_buffer_priority_queue_size", "Current size of priority queue", ["priority"]
)

priority_queue_age = Histogram(
    "frame_buffer_priority_queue_age_seconds",
    "Age of frames when dequeued",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

priority_queue_operations = Counter(
    "frame_buffer_priority_queue_operations_total",
    "Priority queue operations",
    ["operation", "priority"],
)

starvation_events = Counter(
    "frame_buffer_starvation_events_total", "Times starvation prevention was triggered"
)


class PriorityQueueItem:
    """Wrapper for priority queue items to handle sorting."""

    def __init__(self, frame: FrameReadyEvent, sequence: int):
        self.frame = frame
        self.sequence = sequence  # For FIFO within same priority

    def __lt__(self, other):
        # Higher priority first (negative for min heap)
        if self.frame.priority != other.frame.priority:
            return -self.frame.priority < -other.frame.priority
        # FIFO for same priority
        return self.sequence < other.sequence


class PriorityQueue:
    """Priority queue with starvation prevention."""

    def __init__(
        self, starvation_threshold: int = 100, max_age_seconds: Optional[int] = None
    ):
        """Initialize priority queue.

        Args:
            starvation_threshold: High priority frames before forcing low priority
            max_age_seconds: Age threshold for priority promotion
        """
        self.starvation_threshold = starvation_threshold
        self.max_age_seconds = max_age_seconds

        # Separate queues per priority for better control
        self.queues: Dict[int, List[PriorityQueueItem]] = defaultdict(list)
        self.sequence_counter = 0
        self.high_priority_count = 0

        # Async coordination
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)

        # Metrics
        self.enqueue_count = 0
        self.dequeue_count = 0

    async def enqueue(self, frame: FrameReadyEvent):
        """Add frame to priority queue.

        Args:
            frame: Frame to enqueue
        """
        async with self._lock:
            # Create queue item
            item = PriorityQueueItem(frame, self.sequence_counter)
            self.sequence_counter += 1

            # Add to appropriate priority queue
            priority = frame.priority
            heapq.heappush(self.queues[priority], item)

            # Update metrics
            self.enqueue_count += 1
            priority_queue_operations.labels(
                operation="enqueue", priority=str(priority)
            ).inc()

            # Notify waiting consumers
            self._not_empty.notify()

            logger.debug(f"Enqueued frame {frame.frame_id} with priority {priority}")

    async def dequeue(self) -> FrameReadyEvent:
        """Remove and return highest priority frame.

        Returns:
            Frame with highest priority
        """
        async with self._not_empty:
            # Wait for items if empty
            while self._is_empty():
                await self._not_empty.wait()

            # Check for starvation prevention
            if self._should_prevent_starvation():
                frame = self._dequeue_lowest_priority()
                starvation_events.inc()
                logger.info("Starvation prevention triggered")
            else:
                frame = self._dequeue_highest_priority()

            # Track age
            age = (datetime.now() - frame.timestamp).total_seconds()
            priority_queue_age.observe(age)

            # Update metrics
            self.dequeue_count += 1
            priority_queue_operations.labels(
                operation="dequeue", priority=str(frame.priority)
            ).inc()

            # Track high priority processing
            if frame.priority > 5:
                self.high_priority_count += 1
            else:
                self.high_priority_count = 0

            logger.debug(
                f"Dequeued frame {frame.frame_id} with priority {frame.priority}, "
                f"age={age:.1f}s"
            )

            return frame

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._is_empty()

    def _is_empty(self) -> bool:
        """Internal empty check (must be called with lock)."""
        return all(len(q) == 0 for q in self.queues.values())

    def _should_prevent_starvation(self) -> bool:
        """Check if we should force low priority processing."""
        # Check if we've processed too many high priority frames
        if self.high_priority_count >= self.starvation_threshold:
            # Check if there are low priority frames
            for priority in sorted(self.queues.keys()):
                if priority <= 5 and len(self.queues[priority]) > 0:
                    return True

        # Check for old frames (age-based promotion)
        if self.max_age_seconds:
            cutoff_time = datetime.now() - timedelta(seconds=self.max_age_seconds)
            for priority in sorted(self.queues.keys()):
                if self.queues[priority]:
                    oldest = self.queues[priority][0]
                    if oldest.frame.timestamp < cutoff_time:
                        return True

        return False

    def _dequeue_lowest_priority(self) -> FrameReadyEvent:
        """Dequeue from lowest priority queue (for starvation prevention)."""
        # Find lowest priority with items
        for priority in sorted(self.queues.keys()):
            if self.queues[priority]:
                item = heapq.heappop(self.queues[priority])
                return item.frame

        raise RuntimeError("No items to dequeue")

    def _dequeue_highest_priority(self) -> FrameReadyEvent:
        """Dequeue from highest priority queue."""
        # Find highest priority with items
        for priority in sorted(self.queues.keys(), reverse=True):
            if self.queues[priority]:
                item = heapq.heappop(self.queues[priority])
                return item.frame

        raise RuntimeError("No items to dequeue")

    def get_metrics(self) -> dict:
        """Get queue metrics.

        Returns:
            Dictionary of metrics
        """
        priority_distribution = {}
        total_size = 0
        oldest_frame = None

        for priority, queue in self.queues.items():
            size = len(queue)
            if size > 0:
                priority_distribution[priority] = size
                total_size += size

                # Track oldest frame
                if queue and (
                    oldest_frame is None or queue[0].frame.timestamp < oldest_frame
                ):
                    oldest_frame = queue[0].frame.timestamp

                # Update gauge
                priority_queue_size.labels(priority=str(priority)).set(size)

        oldest_age = None
        if oldest_frame:
            oldest_age = (datetime.now() - oldest_frame).total_seconds()

        return {
            "total_size": total_size,
            "priority_distribution": priority_distribution,
            "oldest_frame_age_seconds": oldest_age,
            "enqueue_count": self.enqueue_count,
            "dequeue_count": self.dequeue_count,
            "high_priority_streak": self.high_priority_count,
        }

    async def clear(self):
        """Clear all items from queue."""
        async with self._lock:
            self.queues.clear()
            self.high_priority_count = 0
            logger.info("Priority queue cleared")

            # Reset metrics
            for priority in range(11):  # 0-10 priority range
                priority_queue_size.labels(priority=str(priority)).set(0)
