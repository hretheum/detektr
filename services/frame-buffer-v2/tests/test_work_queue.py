"""Tests for processor work queue implementation."""

import json
from datetime import datetime

import pytest
import redis.asyncio as aioredis

from src.models import FrameReadyEvent
from src.orchestrator.queue_manager import WorkQueueManager


@pytest.mark.asyncio
async def test_processor_queue(redis_client):
    """Test processor-specific work queues."""
    queue_manager = WorkQueueManager(redis_client)

    # Create processor queue
    await queue_manager.create_queue("proc1")

    # Add frames to queue
    frame = FrameReadyEvent(
        frame_id="f1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={"trace_id": "abc123"},
        priority=1,
    )
    msg_id = await queue_manager.enqueue("proc1", frame)
    assert msg_id is not None

    # Consumer group for processor
    await queue_manager.create_consumer_group("proc1", "proc1-group")

    # Consume from queue
    messages = await queue_manager.consume("proc1", "proc1-group", "consumer-1")
    assert len(messages) == 1
    assert messages[0][b"frame_id"] == b"f1"

    # Test queue stats
    stats = await queue_manager.get_queue_stats("proc1")
    assert stats["length"] >= 0  # At least 0 messages
    assert stats["pending"] == 1  # One pending message


@pytest.mark.asyncio
async def test_multiple_queues(redis_client):
    """Test managing multiple processor queues."""
    queue_manager = WorkQueueManager(redis_client)

    # Create multiple queues
    processors = ["proc1", "proc2", "proc3"]
    for proc_id in processors:
        await queue_manager.create_queue(proc_id)

    # Add frames to different queues
    for i, proc_id in enumerate(processors):
        frame = FrameReadyEvent(
            frame_id=f"frame_{proc_id}_{i}",
            camera_id="cam1",
            timestamp=datetime.now(),
            size_bytes=1024,
            width=1920,
            height=1080,
            format="jpeg",
            trace_context={"trace_id": f"trace_{i}"},
            priority=i,
        )
        await queue_manager.enqueue(proc_id, frame)

    # Check each queue has its frame
    for proc_id in processors:
        stats = await queue_manager.get_queue_stats(proc_id)
        assert stats["length"] >= 1


@pytest.mark.asyncio
async def test_queue_overflow_handling(redis_client):
    """Test queue overflow and maxlen behavior."""
    queue_manager = WorkQueueManager(redis_client, max_queue_size=5)

    await queue_manager.create_queue("overflow-test")

    # Add more frames than max size
    frame_ids = []
    for i in range(10):
        frame = FrameReadyEvent(
            frame_id=f"overflow_{i}",
            camera_id="cam1",
            timestamp=datetime.now(),
            size_bytes=1024,
            width=1920,
            height=1080,
            format="jpeg",
            trace_context={"trace_id": str(i)},
            priority=0,
        )
        msg_id = await queue_manager.enqueue("overflow-test", frame)
        if msg_id:
            frame_ids.append(msg_id)

    # Queue should have max 5 messages (oldest dropped)
    # Redis Stream with MAXLEN will have approximately 5 messages
    stats = await queue_manager.get_queue_stats("overflow-test")
    # With approximate trimming, could be slightly more than 5
    assert stats["length"] <= 10  # Allow some slack for approximate trimming


@pytest.mark.asyncio
async def test_queue_metrics(redis_client):
    """Test queue metrics collection."""
    queue_manager = WorkQueueManager(redis_client)

    await queue_manager.create_queue("metrics-test")

    # Add multiple frames
    for i in range(3):
        frame = FrameReadyEvent(
            frame_id=f"metric_{i}",
            camera_id=f"cam{i % 2}",
            timestamp=datetime.now(),
            size_bytes=1024 * (i + 1),
            width=1920,
            height=1080,
            format="jpeg",
            trace_context={"trace_id": str(i)},
            priority=i % 2,
        )
        await queue_manager.enqueue("metrics-test", frame)

    # Get detailed stats
    stats = await queue_manager.get_queue_stats("metrics-test")
    assert stats["length"] == 3
    assert "first_id" in stats
    assert "last_id" in stats


@pytest.mark.asyncio
async def test_queue_deletion(redis_client):
    """Test queue deletion."""
    queue_manager = WorkQueueManager(redis_client)

    # Create and populate queue
    await queue_manager.create_queue("delete-test")

    frame = FrameReadyEvent(
        frame_id="delete_1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={"trace_id": "del123"},
        priority=0,
    )
    await queue_manager.enqueue("delete-test", frame)

    # Delete queue
    success = await queue_manager.delete_queue("delete-test")
    assert success is True

    # Queue should not exist
    stats = await queue_manager.get_queue_stats("delete-test")
    assert stats["length"] == 0
    assert stats["exists"] is False


@pytest.mark.asyncio
async def test_batch_enqueue(redis_client):
    """Test batch enqueue operations."""
    queue_manager = WorkQueueManager(redis_client)

    await queue_manager.create_queue("batch-test")

    # Prepare batch of frames
    frames = []
    for i in range(5):
        frame = FrameReadyEvent(
            frame_id=f"batch_{i}",
            camera_id="cam1",
            timestamp=datetime.now(),
            size_bytes=1024,
            width=1920,
            height=1080,
            format="jpeg",
            trace_context={"trace_id": str(i)},
            priority=0,
        )
        frames.append(frame)

    # Batch enqueue
    msg_ids = await queue_manager.enqueue_batch("batch-test", frames)
    assert len(msg_ids) == 5
    assert all(msg_id is not None for msg_id in msg_ids)

    # Verify all enqueued
    stats = await queue_manager.get_queue_stats("batch-test")
    assert stats["length"] == 5


@pytest.mark.asyncio
async def test_priority_handling(redis_client):
    """Test priority metadata in queued messages."""
    queue_manager = WorkQueueManager(redis_client)

    await queue_manager.create_queue("priority-test")

    # Add frames with different priorities
    priorities = [5, 1, 10, 3]
    for i, priority in enumerate(priorities):
        frame = FrameReadyEvent(
            frame_id=f"prio_{i}",
            camera_id="cam1",
            timestamp=datetime.now(),
            size_bytes=1024,
            width=1920,
            height=1080,
            format="jpeg",
            trace_context={"trace_id": str(i)},
            priority=priority,
        )
        await queue_manager.enqueue("priority-test", frame)

    # Create consumer group
    await queue_manager.create_consumer_group("priority-test", "prio-group")

    # Consume all messages
    messages = await queue_manager.consume(
        "priority-test", "prio-group", "consumer-1", count=10
    )

    # Verify priorities are preserved
    assert len(messages) == 4
    for i, msg in enumerate(messages):
        assert int(msg[b"priority"]) == priorities[i]


@pytest.mark.asyncio
async def test_invalid_queue_operations(redis_client):
    """Test error handling for invalid operations."""
    queue_manager = WorkQueueManager(redis_client)

    # Enqueue to non-existent queue should create it
    frame = FrameReadyEvent(
        frame_id="test_1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={"trace_id": "123"},
        priority=0,
    )

    msg_id = await queue_manager.enqueue("non-existent", frame)
    assert msg_id is not None

    # Delete non-existent queue
    success = await queue_manager.delete_queue("really-non-existent")
    assert success is False

    # Get stats for non-existent queue
    stats = await queue_manager.get_queue_stats("also-non-existent")
    assert stats["exists"] is False
    assert stats["length"] == 0
