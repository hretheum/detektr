"""Integration tests for Frame Buffer v2 consuming from Redis Stream."""
import asyncio
import json
import time

import httpx
import pytest
import redis.asyncio as aioredis


async def wait_for_service(url: str, timeout: int = 30) -> bool:
    """Wait for service to be healthy."""
    start = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            try:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
    return False


async def start_frame_buffer_v2():
    """Ensure Frame Buffer v2 is running."""
    fb_url = "http://localhost:8002"

    # Wait for service to be ready
    if not await wait_for_service(fb_url):
        pytest.skip("Frame Buffer v2 service not available")

    return fb_url


@pytest.mark.integration
async def test_frame_buffer_consumes_stream():
    """Verify Frame Buffer v2 consumes from Redis Stream."""
    # Connect to Redis
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Inject test frames
        test_frames = []
        for i in range(5):
            frame_data = {
                "frame_id": f"test_{i}_{int(time.time()*1000)}",
                "camera_id": "test_cam",
                "timestamp": time.time(),
                "metadata": json.dumps({"test": True, "index": i}),
            }

            # Add to stream
            frame_id = await redis_client.xadd("frames:metadata", frame_data)
            test_frames.append((frame_id, frame_data))

        # Start Frame Buffer v2
        fb_url = await start_frame_buffer_v2()

        # Give it time to consume
        await asyncio.sleep(2)

        # Check consumer group info
        try:
            groups = await redis_client.xinfo_groups("frames:metadata")

            # Find frame-buffer-group
            fb_group = None
            for group in groups:
                if group[b"name"] == b"frame-buffer-group":
                    fb_group = group
                    break

            assert fb_group is not None, "frame-buffer-group not found"

            # Check consumers in group
            consumers = await redis_client.xinfo_consumers(
                "frames:metadata", "frame-buffer-group"
            )

            assert len(consumers) > 0, "No consumers in frame-buffer-group"

            # Check consumer activity
            for consumer in consumers:
                consumer_name = consumer[b"name"].decode("utf-8")
                pending = consumer[b"pending"]
                idle = consumer[b"idle"]

                print(f"Consumer {consumer_name}: pending={pending}, idle={idle}ms")

                # Consumer should be active (idle < 5 seconds)
                assert idle < 5000, f"Consumer {consumer_name} is not active"

        except Exception as e:
            if "no such key" in str(e):
                pytest.fail(
                    "Consumer group not created - Frame Buffer v2 not consuming"
                )
            raise

    finally:
        await redis_client.close()


@pytest.mark.integration
async def test_frame_buffer_consumer_group_config():
    """Test Frame Buffer v2 consumer group configuration."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")
    fb_url = await start_frame_buffer_v2()

    try:
        # Get consumer group info
        groups = await redis_client.xinfo_groups("frames:metadata")

        fb_group = None
        for group in groups:
            if group[b"name"] == b"frame-buffer-group":
                fb_group = group
                break

        assert fb_group is not None, "frame-buffer-group not found"

        # Verify group configuration
        lag = fb_group.get(b"lag", 0)
        pending = fb_group.get(b"pending", 0)

        print(f"Consumer group status:")
        print(f"- Lag: {lag}")
        print(f"- Pending: {pending}")

        # In healthy system, lag should be minimal
        if lag > 100:
            print(f"⚠️  High lag detected: {lag} messages behind")

        # Check last delivered ID is advancing
        last_delivered_1 = fb_group[b"last-delivered-id"]
        await asyncio.sleep(2)

        groups = await redis_client.xinfo_groups("frames:metadata")
        fb_group = next(g for g in groups if g[b"name"] == b"frame-buffer-group")
        last_delivered_2 = fb_group[b"last-delivered-id"]

        assert last_delivered_2 > last_delivered_1, "Consumer group not making progress"

    finally:
        await redis_client.close()


@pytest.mark.integration
async def test_frame_buffer_processes_frames():
    """Verify Frame Buffer v2 actually processes consumed frames."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")
    fb_url = await start_frame_buffer_v2()

    try:
        # Check Frame Buffer metrics before
        async with httpx.AsyncClient() as client:
            metrics_before = await client.get(f"{fb_url}/metrics")

        # Extract frames_consumed metric
        frames_before = 0
        if metrics_before.status_code == 200:
            for line in metrics_before.text.split("\n"):
                if "frames_consumed_total" in line and not line.startswith("#"):
                    frames_before = int(line.split()[-1])
                    break

        # Wait for processing
        await asyncio.sleep(5)

        # Check metrics after
        async with httpx.AsyncClient() as client:
            metrics_after = await client.get(f"{fb_url}/metrics")

        frames_after = 0
        if metrics_after.status_code == 200:
            for line in metrics_after.text.split("\n"):
                if "frames_consumed_total" in line and not line.startswith("#"):
                    frames_after = int(line.split()[-1])
                    break

        frames_processed = frames_after - frames_before
        assert frames_processed > 0, (
            f"No frames processed in 5 seconds "
            f"(before: {frames_before}, after: {frames_after})"
        )

        print(f"✓ Frame Buffer processed {frames_processed} frames in 5 seconds")

        # Also check orchestrator endpoint
        async with httpx.AsyncClient() as client:
            orch_status = await client.get(f"{fb_url}/orchestrator/status")

        if orch_status.status_code == 200:
            status = orch_status.json()
            print(f"Orchestrator status: {status}")

    finally:
        await redis_client.close()


@pytest.mark.integration
async def test_consumer_acknowledgment():
    """Test that Frame Buffer v2 properly acknowledges consumed messages."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")
    fb_url = await start_frame_buffer_v2()

    try:
        # Check pending messages
        pending_info = await redis_client.xpending(
            "frames:metadata", "frame-buffer-group"
        )

        if pending_info:
            total_pending = pending_info[0]
            print(f"Total pending messages: {total_pending}")

            # If there are pending messages, check they're being processed
            if total_pending > 0:
                # Wait a bit
                await asyncio.sleep(2)

                # Check again
                pending_info_2 = await redis_client.xpending(
                    "frames:metadata", "frame-buffer-group"
                )

                total_pending_2 = pending_info_2[0] if pending_info_2 else 0

                # Pending count should decrease or stay same (not increase)
                assert (
                    total_pending_2 <= total_pending
                ), f"Pending messages increasing: {total_pending} -> {total_pending_2}"

                if total_pending_2 < total_pending:
                    print(
                        f"✓ Pending messages decreasing: "
                        f"{total_pending} -> {total_pending_2}"
                    )

    finally:
        await redis_client.close()


@pytest.mark.integration
async def test_frame_buffer_stream_position():
    """Verify Frame Buffer v2 maintains proper stream position."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")
    fb_url = await start_frame_buffer_v2()

    try:
        # Add marker frame
        marker_data = {
            "frame_id": f"marker_{int(time.time()*1000)}",
            "camera_id": "test_cam",
            "timestamp": time.time(),
            "metadata": json.dumps({"marker": True}),
        }

        marker_id = await redis_client.xadd("frames:metadata", marker_data)
        print(f"Added marker frame: {marker_id.decode()}")

        # Wait for consumption
        await asyncio.sleep(3)

        # Check if marker was consumed
        groups = await redis_client.xinfo_groups("frames:metadata")
        fb_group = next(
            (g for g in groups if g[b"name"] == b"frame-buffer-group"), None
        )

        if fb_group:
            last_delivered = fb_group[b"last-delivered-id"].decode()

            # Last delivered should be at or past our marker
            assert (
                last_delivered >= marker_id.decode()
            ), f"Marker not consumed: {marker_id.decode()} > {last_delivered}"

            print(f"✓ Consumer processed up to: {last_delivered}")

    finally:
        await redis_client.close()


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_frame_buffer_consumes_stream())
    asyncio.run(test_frame_buffer_consumer_group_config())
    asyncio.run(test_frame_buffer_processes_frames())
    asyncio.run(test_consumer_acknowledgment())
    asyncio.run(test_frame_buffer_stream_position())
    print("All tests passed!")
