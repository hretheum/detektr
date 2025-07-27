"""Tests for Redis Streams consumer implementation."""

import asyncio
import json

import pytest
import redis.asyncio as aioredis

from src.orchestrator.consumer import StreamConsumer


@pytest.mark.asyncio
async def test_stream_consumption(redis_client):
    """Test consuming from Redis Streams."""
    consumer = StreamConsumer(
        stream="frames:capture",
        group="frame-buffer",
        consumer_id="fb-1",
        redis_client=redis_client,
    )

    # Add test frames to stream
    for i in range(10):
        await redis_client.xadd(
            "frames:capture", {"frame_id": f"test_{i}", "data": "test_data"}
        )

    # Create consumer group
    try:
        await redis_client.xgroup_create("frames:capture", "frame-buffer", id="0")
    except aioredis.ResponseError:
        # Group already exists
        pass

    # Consume frames
    frames = []
    async for frame in consumer.consume(max_count=5):
        frames.append(frame)
        if len(frames) >= 5:
            break

    assert len(frames) == 5
    assert frames[0][b"frame_id"] == b"test_0"

    # Test acknowledgment
    await consumer.ack_frames([f["id"] for f in frames])

    # Consume remaining frames but don't ack them
    unacked_frames = []
    async for frame in consumer.consume(max_count=5):
        unacked_frames.append(frame)
        if len(unacked_frames) >= 5:
            break

    # Now we should have 5 pending messages (not acked)
    pending = await redis_client.xpending("frames:capture", "frame-buffer")
    assert pending["pending"] == 5


@pytest.mark.asyncio
async def test_consumer_group_creation(redis_client):
    """Test consumer group creation and management."""
    consumer = StreamConsumer(
        stream="frames:test_group",
        group="test-group",
        consumer_id="test-consumer",
        redis_client=redis_client,
    )

    # Add a frame to create the stream
    await redis_client.xadd("frames:test_group", {"test": "data"})

    # Create group
    await consumer.create_group()

    # Verify group exists
    groups = await redis_client.xinfo_groups("frames:test_group")
    group_names = [
        g["name"].decode() if isinstance(g["name"], bytes) else g["name"]
        for g in groups
    ]
    assert "test-group" in group_names


@pytest.mark.asyncio
async def test_reconnection_handling(redis_client):
    """Test consumer handles reconnections gracefully."""
    consumer = StreamConsumer(
        stream="frames:reconnect",
        group="reconnect-group",
        consumer_id="reconnect-1",
        redis_client=redis_client,
    )

    # Add frames
    await redis_client.xadd("frames:reconnect", {"frame_id": "test_1"})
    await consumer.create_group()

    # Consume one frame
    frames = []
    async for frame in consumer.consume(max_count=1):
        frames.append(frame)
        break

    assert len(frames) == 1

    # Simulate disconnect/reconnect by creating new consumer with same ID
    consumer2 = StreamConsumer(
        stream="frames:reconnect",
        group="reconnect-group",
        consumer_id="reconnect-1",
        redis_client=redis_client,
    )

    # Add more frames
    await redis_client.xadd("frames:reconnect", {"frame_id": "test_2"})

    # Should continue from where it left off
    frames2 = []
    async for frame in consumer2.consume(max_count=1):
        frames2.append(frame)
        break

    assert len(frames2) == 1
    assert frames2[0][b"frame_id"] == b"test_2"


@pytest.mark.asyncio
async def test_batch_consumption(redis_client):
    """Test batch consumption of frames."""
    consumer = StreamConsumer(
        stream="frames:batch",
        group="batch-group",
        consumer_id="batch-1",
        redis_client=redis_client,
    )

    # Add many frames
    for i in range(100):
        await redis_client.xadd(
            "frames:batch", {"frame_id": f"batch_{i}", "timestamp": str(i)}
        )

    await consumer.create_group()

    # Consume in batches
    total_consumed = 0
    async for batch in consumer.consume_batch(batch_size=10):
        assert len(batch) <= 10
        total_consumed += len(batch)
        if total_consumed >= 50:
            break

    assert total_consumed >= 50


@pytest.mark.asyncio
async def test_error_handling(redis_client):
    """Test error handling in consumer."""
    # Test with very short block timeout
    consumer = StreamConsumer(
        stream="frames:error_test",
        group="error-group",
        consumer_id="error-1",
        redis_client=redis_client,
        block_ms=100,  # 100ms timeout
    )

    # Create stream with a message
    await redis_client.xadd("frames:error_test", {"test": "data"})

    # Create group
    await consumer.create_group()

    # Consume the one message
    frames = []
    async for frame in consumer.consume(max_count=1):
        frames.append(frame)
        break

    assert len(frames) == 1

    # Stop consumer to avoid hanging
    consumer.stop()


@pytest.mark.asyncio
async def test_pending_message_recovery(redis_client):
    """Test recovery of pending messages."""
    # First consumer
    consumer1 = StreamConsumer(
        stream="frames:pending",
        group="pending-group",
        consumer_id="pending-1",
        redis_client=redis_client,
    )

    # Add frames
    for i in range(5):
        await redis_client.xadd("frames:pending", {"frame_id": f"pending_{i}"})

    await consumer1.create_group()

    # Consume but don't ack
    frames = []
    async for frame in consumer1.consume(max_count=3):
        frames.append(frame)
        if len(frames) >= 3:
            break

    # Messages are now pending

    # Second consumer claims pending messages
    consumer2 = StreamConsumer(
        stream="frames:pending",
        group="pending-group",
        consumer_id="pending-2",
        redis_client=redis_client,
    )

    # Claim old pending messages
    claimed = await consumer2.claim_pending_messages(min_idle_time=0)
    assert len(claimed) == 3

    # Verify claimed messages match original
    claimed_ids = [msg[b"frame_id"] for msg in claimed]
    assert all(f"pending_{i}".encode() in claimed_ids for i in range(3))
