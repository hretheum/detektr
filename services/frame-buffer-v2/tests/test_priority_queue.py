"""Tests for priority queue implementation."""

import asyncio
from datetime import datetime, timedelta

import pytest

from src.models import FrameReadyEvent
from src.priority_queue import PriorityQueue


def create_test_frame(frame_id: str, priority: int = 0, **kwargs) -> FrameReadyEvent:
    """Helper to create test frames with default values."""
    defaults = {
        "camera_id": "cam1",
        "timestamp": datetime.now(),
        "size_bytes": 1024,
        "width": 1920,
        "height": 1080,
        "format": "jpeg",
        "trace_context": {"trace_id": "test", "span_id": "test"},
        "priority": priority,
    }
    defaults.update(kwargs)
    return FrameReadyEvent(frame_id=frame_id, **defaults)


@pytest.mark.asyncio
async def test_priority_processing():
    """Test priority-based frame processing."""
    queue = PriorityQueue()

    # Add frames with different priorities
    frames = [
        create_test_frame("low1", priority=0),
        create_test_frame("high1", priority=10),
        create_test_frame("med1", priority=5),
        create_test_frame("high2", priority=10),
        create_test_frame("low2", priority=0),
    ]

    for frame in frames:
        await queue.enqueue(frame)

    # Dequeue should return highest priority first
    order = []
    while not queue.empty():
        frame = await queue.dequeue()
        order.append(frame.frame_id)

    assert order == ["high1", "high2", "med1", "low1", "low2"]


@pytest.mark.asyncio
async def test_starvation_prevention():
    """Test that low priority frames aren't starved."""
    queue = PriorityQueue(starvation_threshold=10)

    # Add many high priority frames
    for i in range(15):
        await queue.enqueue(create_test_frame(f"high{i}", priority=10))

    # Add one old low priority frame
    await queue.enqueue(
        create_test_frame(
            "low_old", priority=0, timestamp=datetime.now() - timedelta(minutes=5)
        )
    )

    # Should eventually process old low priority frame
    processed = []
    found_low = False

    # Process up to 12 frames
    for _ in range(12):
        frame = await queue.dequeue()
        processed.append(frame.frame_id)
        if frame.frame_id == "low_old":
            found_low = True
            break

    # Low priority should be processed after starvation threshold
    assert found_low
    high_count = sum(1 for fid in processed if fid.startswith("high"))
    assert high_count >= 10  # At least 10 high priority before low


@pytest.mark.asyncio
async def test_fifo_within_priority():
    """Test FIFO ordering within same priority level."""
    queue = PriorityQueue()

    # Add frames with same priority
    for i in range(5):
        await queue.enqueue(create_test_frame(f"frame{i}", priority=5))

    # Should maintain FIFO order
    order = []
    while not queue.empty():
        frame = await queue.dequeue()
        order.append(frame.frame_id)

    assert order == [f"frame{i}" for i in range(5)]


@pytest.mark.asyncio
async def test_priority_queue_metrics():
    """Test queue metrics collection."""
    queue = PriorityQueue()

    # Add frames with different priorities
    for priority in [0, 5, 10]:
        for i in range(3):
            await queue.enqueue(
                create_test_frame(f"p{priority}_f{i}", priority=priority)
            )

    # Check metrics
    metrics = queue.get_metrics()
    assert metrics["total_size"] == 9
    assert metrics["priority_distribution"][0] == 3
    assert metrics["priority_distribution"][5] == 3
    assert metrics["priority_distribution"][10] == 3


@pytest.mark.asyncio
async def test_empty_queue_handling():
    """Test handling of empty queue."""
    queue = PriorityQueue()

    assert queue.empty()

    # Dequeue from empty should wait
    dequeue_task = asyncio.create_task(queue.dequeue())
    await asyncio.sleep(0.1)
    assert not dequeue_task.done()

    # Add frame should complete dequeue
    await queue.enqueue(create_test_frame("test", priority=5))

    frame = await dequeue_task
    assert frame.frame_id == "test"


@pytest.mark.asyncio
async def test_priority_queue_age_based_promotion():
    """Test age-based priority promotion."""
    queue = PriorityQueue(max_age_seconds=60)

    # Add old low priority frame
    old_time = datetime.now() - timedelta(seconds=120)
    await queue.enqueue(create_test_frame("old_low", priority=0, timestamp=old_time))

    # Add newer high priority frames
    for i in range(3):
        await queue.enqueue(create_test_frame(f"new_high{i}", priority=10))

    # Old frame should be promoted
    frame = await queue.dequeue()
    assert frame.frame_id == "old_low"  # Old frame processed first


@pytest.mark.asyncio
async def test_concurrent_access():
    """Test concurrent enqueue/dequeue operations."""
    queue = PriorityQueue()

    async def producer(prefix: str, count: int):
        for i in range(count):
            await queue.enqueue(
                create_test_frame(f"{prefix}_{i}", priority=i % 3 * 5)  # 0, 5, 10
            )
            await asyncio.sleep(0.01)

    async def consumer(consumer_id: int, results: list):
        for _ in range(5):
            try:
                frame = await asyncio.wait_for(queue.dequeue(), timeout=1.0)
                results.append((consumer_id, frame.frame_id))
            except asyncio.TimeoutError:
                break

    # Run producers and consumers concurrently
    results = []
    await asyncio.gather(
        producer("p1", 10),
        producer("p2", 10),
        consumer(1, results),
        consumer(2, results),
        consumer(3, results),
    )

    # Verify all consumed frames are unique
    consumed_frames = [frame_id for _, frame_id in results]
    assert len(consumed_frames) == len(set(consumed_frames))


@pytest.mark.asyncio
async def test_priority_queue_clear():
    """Test clearing the queue."""
    queue = PriorityQueue()

    # Add frames
    for i in range(10):
        await queue.enqueue(create_test_frame(f"frame{i}", priority=i % 3))

    assert not queue.empty()

    # Clear queue
    await queue.clear()
    assert queue.empty()

    metrics = queue.get_metrics()
    assert metrics["total_size"] == 0
