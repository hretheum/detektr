"""Integration tests for RTSP Capture → Redis Stream flow."""
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


async def start_rtsp_capture():
    """Ensure RTSP Capture is running."""
    rtsp_url = "http://localhost:8080"

    # Wait for service to be ready
    if not await wait_for_service(rtsp_url):
        pytest.skip("RTSP Capture service not available")

    return rtsp_url


@pytest.mark.integration
async def test_rtsp_publishes_to_redis_stream():
    """Verify RTSP Capture publishes frames to Redis Stream."""
    # Start RTSP Capture
    rtsp_url = await start_rtsp_capture()

    # Connect to Redis
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Clear any existing data
        await redis_client.delete("frames:metadata")

        # Wait a bit for RTSP to start publishing
        await asyncio.sleep(2)

        # Monitor Redis Stream
        frames = []
        start_time = time.time()

        while len(frames) < 10 and (time.time() - start_time) < 10:
            # Read new messages from stream
            messages = await redis_client.xread(
                ["frames:metadata"], count=10, block=1000  # Block for 1 second
            )

            if messages:
                stream_messages = messages[0][1]  # Get messages from first stream
                frames.extend(stream_messages)

            await asyncio.sleep(0.1)

        # Verify frames published
        assert (
            len(frames) >= 10
        ), f"Expected at least 10 frames in 10 seconds, got {len(frames)}"

        # Verify frame structure
        frame_id, frame_data = frames[0]

        # Check required fields
        assert b"frame_id" in frame_data, "Missing frame_id"
        assert b"camera_id" in frame_data, "Missing camera_id"
        assert b"timestamp" in frame_data, "Missing timestamp"
        assert b"traceparent" in frame_data, "Missing trace context"

        # Verify frame_id format
        frame_id_str = frame_data[b"frame_id"].decode("utf-8")
        assert "_" in frame_id_str, f"Invalid frame_id format: {frame_id_str}"

        # Verify timestamp is recent
        timestamp = float(frame_data[b"timestamp"])
        assert abs(time.time() - timestamp) < 60, "Timestamp too old"

        # Verify trace context format (W3C Trace Context)
        traceparent = frame_data[b"traceparent"].decode("utf-8")
        parts = traceparent.split("-")
        assert len(parts) == 4, f"Invalid traceparent format: {traceparent}"
        assert parts[0] == "00", "Wrong trace version"
        assert len(parts[1]) == 32, "Invalid trace ID length"
        assert len(parts[2]) == 16, "Invalid span ID length"

        # Check frame metadata if present
        if b"metadata" in frame_data:
            metadata = json.loads(frame_data[b"metadata"])
            assert isinstance(metadata, dict), "Metadata should be a dict"

    finally:
        await redis_client.close()


@pytest.mark.integration
async def test_rtsp_stream_continuous_flow():
    """Test continuous frame flow from RTSP."""
    rtsp_url = await start_rtsp_capture()
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Monitor for 5 seconds
        duration = 5
        start_time = time.time()
        frame_count = 0
        last_frame_id = None

        while time.time() - start_time < duration:
            messages = await redis_client.xread(
                ["frames:metadata"], count=100, block=100
            )

            if messages:
                stream_messages = messages[0][1]
                frame_count += len(stream_messages)

                # Check frame ordering
                for msg_id, data in stream_messages:
                    frame_id = data[b"frame_id"].decode("utf-8")
                    if last_frame_id:
                        # Frame IDs should be incrementing
                        assert (
                            frame_id > last_frame_id
                        ), f"Frame order issue: {frame_id} <= {last_frame_id}"
                    last_frame_id = frame_id

        # Calculate FPS
        fps = frame_count / duration
        assert fps >= 25, f"Frame rate too low: {fps:.1f} FPS"

        print(f"✓ Received {frame_count} frames in {duration}s ({fps:.1f} FPS)")

    finally:
        await redis_client.close()


@pytest.mark.integration
async def test_rtsp_metadata_in_stream():
    """Verify RTSP metadata is properly included in stream."""
    rtsp_url = await start_rtsp_capture()
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Get RTSP metrics first
        async with httpx.AsyncClient() as client:
            metrics_response = await client.get(f"{rtsp_url}/metrics")
            assert metrics_response.status_code == 200

        # Read a few frames
        messages = await redis_client.xread(["frames:metadata"], count=5, block=2000)

        assert messages, "No frames received"

        for msg_id, frame_data in messages[0][1]:
            # Verify all expected fields
            assert b"frame_id" in frame_data
            assert b"camera_id" in frame_data
            assert b"timestamp" in frame_data
            assert b"traceparent" in frame_data

            # Check camera_id matches expected format
            camera_id = frame_data[b"camera_id"].decode("utf-8")
            assert camera_id, "Empty camera_id"

            # If metadata present, validate it
            if b"metadata" in frame_data:
                metadata = json.loads(frame_data[b"metadata"])

                # Common metadata fields
                possible_fields = ["width", "height", "format", "fps", "source_url"]
                assert any(
                    field in metadata for field in possible_fields
                ), f"No expected metadata fields found in: {metadata.keys()}"

    finally:
        await redis_client.close()


@pytest.mark.integration
async def test_redis_stream_persistence():
    """Test that Redis Stream persists frames correctly."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Get current stream length
        initial_length = await redis_client.xlen("frames:metadata")

        # Wait for more frames
        await asyncio.sleep(2)

        # Check new length
        new_length = await redis_client.xlen("frames:metadata")

        assert (
            new_length > initial_length
        ), f"Stream not growing: {initial_length} -> {new_length}"

        # Get stream info
        info = await redis_client.xinfo_stream("frames:metadata")

        assert info[b"length"] > 0, "Stream is empty"
        assert info[b"first-entry"] is not None, "No first entry"
        assert info[b"last-entry"] is not None, "No last entry"

        # Verify entries are ordered
        first_id = info[b"first-entry"][0].decode("utf-8")
        last_id = info[b"last-entry"][0].decode("utf-8")
        assert last_id > first_id, "Stream entries not ordered"

    finally:
        await redis_client.close()


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_rtsp_publishes_to_redis_stream())
    asyncio.run(test_rtsp_stream_continuous_flow())
    asyncio.run(test_rtsp_metadata_in_stream())
    asyncio.run(test_redis_stream_persistence())
    print("All tests passed!")
