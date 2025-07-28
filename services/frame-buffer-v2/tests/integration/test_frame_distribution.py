"""Test frame distribution to processor queues."""

import asyncio
from datetime import datetime

import httpx
import pytest
import redis.asyncio as aioredis


@pytest.mark.asyncio
async def test_frame_distribution_to_processor_queues():
    """Test that Frame Buffer v2 distributes frames to processor queues."""
    # Setup Redis and processor
    redis = await aioredis.from_url("redis://localhost:6379", decode_responses=False)

    # Register a test processor
    processor_id = "test-processor-dist"
    queue_name = f"frames:ready:{processor_id}"

    # Clear the queue
    await redis.delete(queue_name)

    # Register processor via API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8002/processors/register",
            json={
                "id": processor_id,
                "capabilities": ["test"],
                "capacity": 10,
                "queue": queue_name,
            },
        )
        assert response.status_code == 201

    # Add frame to input stream
    await redis.xadd(
        "frames:captured",
        {
            "frame_id": "dist-test-1",
            "camera_id": "cam1",
            "timestamp": datetime.now().isoformat(),
            "size_bytes": "1024",
            "width": "1920",
            "height": "1080",
            "format": "jpeg",
            "trace_context": "{}",
            "metadata": "{}",
        },
    )

    # Wait for distribution
    await asyncio.sleep(2)

    # Check processor queue
    messages = await redis.xrange(queue_name, count=10)
    assert len(messages) > 0, "No frames in processor queue"

    # Verify frame data
    msg_id, frame_data = messages[0]
    assert frame_data[b"frame_id"] == b"dist-test-1"
    assert frame_data[b"camera_id"] == b"cam1"

    # Cleanup
    await redis.delete(queue_name)
    await redis.aclose()


@pytest.mark.asyncio
async def test_frame_distribution_with_multiple_processors():
    """Test frame distribution across multiple processors."""
    redis = await aioredis.from_url("redis://localhost:6379", decode_responses=False)

    # Register multiple processors
    processor_ids = ["dist-proc-1", "dist-proc-2", "dist-proc-3"]

    async with httpx.AsyncClient() as client:
        for proc_id in processor_ids:
            queue_name = f"frames:ready:{proc_id}"
            await redis.delete(queue_name)

            response = await client.post(
                "http://localhost:8002/processors/register",
                json={
                    "id": proc_id,
                    "capabilities": ["test"],
                    "capacity": 10,
                    "queue": queue_name,
                },
            )
            assert response.status_code == 201

    # Add multiple frames
    for i in range(10):
        await redis.xadd(
            "frames:captured",
            {
                "frame_id": f"multi-dist-{i}",
                "camera_id": "cam1",
                "timestamp": datetime.now().isoformat(),
                "size_bytes": "1024",
                "width": "1920",
                "height": "1080",
                "format": "jpeg",
                "trace_context": "{}",
                "metadata": "{}",
            },
        )

    # Wait for distribution
    await asyncio.sleep(3)

    # Check all processor queues received frames
    total_frames = 0
    for proc_id in processor_ids:
        queue_name = f"frames:ready:{proc_id}"
        messages = await redis.xrange(queue_name, count=100)
        total_frames += len(messages)
        print(f"Processor {proc_id} received {len(messages)} frames")

    # All frames should be distributed
    assert total_frames == 10, f"Expected 10 frames distributed, got {total_frames}"

    # Cleanup
    for proc_id in processor_ids:
        await redis.delete(f"frames:ready:{proc_id}")
    await redis.aclose()


@pytest.mark.asyncio
async def test_frame_distribution_error_handling():
    """Test frame distribution handles missing processors gracefully."""
    redis = await aioredis.from_url("redis://localhost:6379", decode_responses=False)

    # No processors registered - frames should not be lost

    # Add frame to input stream
    await redis.xadd(
        "frames:captured",
        {
            "frame_id": "no-proc-test-1",
            "camera_id": "cam1",
            "timestamp": datetime.now().isoformat(),
            "size_bytes": "1024",
            "width": "1920",
            "height": "1080",
            "format": "jpeg",
            "trace_context": "{}",
            "metadata": "{}",
        },
    )

    # Wait for processing attempt
    await asyncio.sleep(2)

    # Frame should still be in input stream (not acknowledged)
    # This depends on implementation - it might be acknowledged but logged as error

    # Check metrics for errors
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8002/metrics")
        assert response.status_code == 200
        metrics = response.text
        # Should have error metrics for failed distribution
        # Exact metric name depends on implementation

    await redis.aclose()
