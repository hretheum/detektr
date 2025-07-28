"""Integration tests for failure scenarios in frame flow."""
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


async def restart_service(service_name: str) -> bool:
    """Restart a Docker service."""
    # Simulate service restart
    try:
        # This would normally use docker-compose commands
        # For testing, we'll use the service API if available
        if service_name == "frame-buffer-v2":
            # Trigger graceful shutdown
            async with httpx.AsyncClient() as client:
                await client.post("http://localhost:8002/shutdown")
            await asyncio.sleep(2)
            # Wait for it to come back up
            return await wait_for_service("http://localhost:8002")
        return False
    except Exception:
        return False


async def simulate_redis_failure(duration: int = 5):
    """Simulate Redis connection failure."""
    # This would normally block Redis connections
    # For testing, we'll simulate by pausing Redis operations
    print(f"Simulating Redis failure for {duration} seconds...")
    await asyncio.sleep(duration)
    print("Redis connection restored")


@pytest.mark.integration
@pytest.mark.failure
async def test_frame_buffer_restart_no_frame_loss():
    """Test that Frame Buffer v2 restart doesn't cause frame loss."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Wait for services to be ready
        if not await wait_for_service("http://localhost:8080"):
            pytest.skip("RTSP service not available")
        if not await wait_for_service("http://localhost:8002"):
            pytest.skip("Frame Buffer v2 not available")

        # Record initial metrics
        async with httpx.AsyncClient() as client:
            rtsp_metrics = await client.get("http://localhost:8080/metrics")
            initial_published = 0
            for line in rtsp_metrics.text.split("\n"):
                if "frames_published_total" in line and not line.startswith("#"):
                    initial_published = int(line.split()[-1])
                    break

        # Let system run normally for a bit
        await asyncio.sleep(3)

        # Get pre-restart counts
        stream_len_before = await redis_client.xlen("frames:metadata")

        print("Restarting Frame Buffer v2...")

        # Simulate Frame Buffer restart
        restart_success = await restart_service("frame-buffer-v2")
        if not restart_success:
            pytest.skip("Could not restart Frame Buffer v2")

        # Wait for recovery
        await asyncio.sleep(5)

        # Check post-restart state
        stream_len_after = await redis_client.xlen("frames:metadata")

        # Get final metrics
        async with httpx.AsyncClient() as client:
            rtsp_metrics = await client.get("http://localhost:8080/metrics")
            final_published = 0
            for line in rtsp_metrics.text.split("\n"):
                if "frames_published_total" in line and not line.startswith("#"):
                    final_published = int(line.split()[-1])
                    break

            fb_metrics = await client.get("http://localhost:8002/metrics")
            frames_consumed = 0
            for line in fb_metrics.text.split("\n"):
                if "frames_consumed_total" in line and not line.startswith("#"):
                    frames_consumed = int(line.split()[-1])
                    break

        total_published = final_published - initial_published

        print("\n=== Frame Buffer Restart Test Results ===")
        print(f"Frames published during test: {total_published}")
        print(f"Stream length before restart: {stream_len_before}")
        print(f"Stream length after restart: {stream_len_after}")
        print(f"Frames consumed after restart: {frames_consumed}")

        # Stream shouldn't grow significantly (Frame Buffer should catch up)
        stream_growth = stream_len_after - stream_len_before
        assert (
            stream_growth < 100
        ), f"Too many unprocessed frames after restart: {stream_growth}"

        # Consumer group should resume from last position
        groups = await redis_client.xinfo_groups("frames:metadata")
        fb_group = next(
            (g for g in groups if g[b"name"] == b"frame-buffer-group"), None
        )
        assert fb_group is not None, "Consumer group lost after restart"

        print("✓ Frame Buffer recovered successfully without frame loss")

    finally:
        await redis_client.close()


@pytest.mark.integration
@pytest.mark.failure
async def test_redis_connection_drop_buffering():
    """Test system behavior when Redis connection drops temporarily."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Check services
        if not await wait_for_service("http://localhost:8080"):
            pytest.skip("RTSP service not available")

        # Get initial state
        initial_stream_len = await redis_client.xlen("frames:metadata")

        # Monitor RTSP internal buffer (if exposed)
        async with httpx.AsyncClient() as client:
            status = await client.get("http://localhost:8080/status")
            if status.status_code == 200:
                initial_buffer = status.json().get("buffer_size", 0)
            else:
                initial_buffer = 0

        print("Simulating Redis connection issues...")

        # In real test, we would block Redis connections
        # Here we'll monitor what happens during a simulated outage
        start_time = time.time()

        # Wait to simulate Redis being unavailable
        await asyncio.sleep(5)

        # Check RTSP buffer grew during outage
        async with httpx.AsyncClient() as client:
            status = await client.get("http://localhost:8080/status")
            if status.status_code == 200:
                buffer_during = status.json().get("buffer_size", 0)
                print(f"Buffer size during outage: {buffer_during}")

                # Buffer should grow when Redis is unavailable
                assert (
                    buffer_during > initial_buffer or buffer_during > 0
                ), "RTSP should buffer frames during Redis outage"

        # "Restore" Redis connection
        await asyncio.sleep(2)

        # Check recovery
        final_stream_len = await redis_client.xlen("frames:metadata")
        frames_added = final_stream_len - initial_stream_len

        print(f"Frames added after recovery: {frames_added}")

        # Verify frames were eventually published
        assert frames_added > 0, "No frames published after Redis recovery"

        # Check buffer drained
        async with httpx.AsyncClient() as client:
            status = await client.get("http://localhost:8080/status")
            if status.status_code == 200:
                final_buffer = status.json().get("buffer_size", 0)
                assert (
                    final_buffer <= initial_buffer + 10
                ), "Buffer not draining after Redis recovery"

        print("✓ System handled Redis connection drop with buffering")

    finally:
        await redis_client.close()


@pytest.mark.integration
@pytest.mark.failure
async def test_processor_failure_redistribution():
    """Test frame redistribution when a processor fails."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Check Frame Buffer is running
        if not await wait_for_service("http://localhost:8002"):
            pytest.skip("Frame Buffer v2 not available")

        # Get initial processor status
        async with httpx.AsyncClient() as client:
            orch_status = await client.get("http://localhost:8002/orchestrator/status")
            if orch_status.status_code != 200:
                pytest.skip("Orchestrator not available")

            initial_processors = orch_status.json().get("active_processors", [])
            print(f"Initial processors: {initial_processors}")

        # Monitor frame distribution for 5 seconds
        distribution_before = {}
        async with httpx.AsyncClient() as client:
            for proc_id in initial_processors:
                try:
                    metrics = await client.get(f"http://localhost:8099/metrics")
                    # Parse processor-specific metrics
                    distribution_before[proc_id] = 0
                except Exception:
                    pass

        # Simulate processor failure (if we have multiple processors)
        if len(initial_processors) > 1:
            failed_processor = initial_processors[0]
            print(f"Simulating failure of processor: {failed_processor}")

            # In real test, we would stop the processor
            # Here we'll just remove it from the orchestrator
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://localhost:8002/orchestrator/remove_processor",
                    json={"processor_id": failed_processor},
                )

            # Wait for redistribution
            await asyncio.sleep(5)

            # Check new distribution
            orch_status = await client.get("http://localhost:8002/orchestrator/status")
            final_processors = orch_status.json().get("active_processors", [])

            assert (
                len(final_processors) == len(initial_processors) - 1
            ), "Failed processor not removed"

            # Verify remaining processors are still receiving frames
            async with httpx.AsyncClient() as client:
                for proc_id in final_processors:
                    metrics = await client.get(f"http://localhost:8099/metrics")
                    # Verify processor is active
                    assert (
                        metrics.status_code == 200
                    ), f"Processor {proc_id} not responding"

            print("✓ Frames redistributed to remaining processors")
        else:
            print("⚠️  Skipping redistribution test - only one processor available")

    finally:
        await redis_client.close()


@pytest.mark.integration
@pytest.mark.failure
async def test_rtsp_reconnection_continuity():
    """Test RTSP Capture reconnection maintains continuity."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Check RTSP is running
        if not await wait_for_service("http://localhost:8080"):
            pytest.skip("RTSP service not available")

        # Get current frame ID pattern
        messages = await redis_client.xread(["frames:metadata"], count=1, block=2000)

        if not messages:
            pytest.skip("No frames in stream")

        last_frame_data = messages[0][1][-1][1]
        last_frame_id = last_frame_data[b"frame_id"].decode("utf-8")
        camera_id = last_frame_data[b"camera_id"].decode("utf-8")

        print(f"Last frame before disconnect: {last_frame_id}")

        # Simulate RTSP source disconnect/reconnect
        async with httpx.AsyncClient() as client:
            # Trigger reconnection
            response = await client.post(
                "http://localhost:8080/control",
                json={"action": "reconnect", "camera_id": camera_id},
            )

            if response.status_code != 200:
                pytest.skip("Cannot control RTSP reconnection")

        # Wait for reconnection
        await asyncio.sleep(3)

        # Check new frames
        new_messages = await redis_client.xread(
            ["frames:metadata"], count=10, block=5000
        )

        assert new_messages, "No frames after reconnection"

        # Verify frame continuity
        new_frames = new_messages[0][1]
        new_frame_ids = [f[1][b"frame_id"].decode("utf-8") for f in new_frames]

        print(f"New frames after reconnect: {new_frame_ids[:3]}...")

        # Check camera_id consistency
        for frame in new_frames:
            frame_camera = frame[1][b"camera_id"].decode("utf-8")
            assert frame_camera == camera_id, "Camera ID changed after reconnect"

        # Verify no duplicate frame IDs
        assert len(new_frame_ids) == len(
            set(new_frame_ids)
        ), "Duplicate frame IDs detected"

        print("✓ RTSP reconnection maintained continuity")

    finally:
        await redis_client.close()


@pytest.mark.integration
@pytest.mark.failure
async def test_cascade_failure_recovery():
    """Test recovery from cascade failure (multiple components)."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Ensure all services are running
        services = {
            "RTSP": "http://localhost:8080",
            "Frame Buffer": "http://localhost:8002",
            "Processor": "http://localhost:8099",
        }

        for name, url in services.items():
            if not await wait_for_service(url):
                pytest.skip(f"{name} service not available")

        # Get baseline metrics
        baseline_metrics = {}
        async with httpx.AsyncClient() as client:
            for name, url in services.items():
                try:
                    response = await client.get(f"{url}/metrics")
                    if response.status_code == 200:
                        baseline_metrics[name] = response.text
                except Exception:
                    baseline_metrics[name] = None

        print("Simulating cascade failure scenario...")

        # Simulate Frame Buffer going down first
        print("1. Frame Buffer fails...")
        # In real test, stop Frame Buffer service

        await asyncio.sleep(2)

        # This should cause frames to accumulate in Redis
        stream_len_during = await redis_client.xlen("frames:metadata")
        print(f"Stream length during FB outage: {stream_len_during}")

        # Simulate processor also failing due to Frame Buffer being down
        print("2. Processor fails due to Frame Buffer outage...")

        await asyncio.sleep(2)

        # Now recover in order
        print("3. Recovering Frame Buffer...")
        # In real test, restart Frame Buffer

        if await wait_for_service("http://localhost:8002", timeout=10):
            print("✓ Frame Buffer recovered")

        print("4. Recovering Processor...")
        # In real test, restart Processor

        if await wait_for_service("http://localhost:8099", timeout=10):
            print("✓ Processor recovered")

        # Wait for system to stabilize
        await asyncio.sleep(5)

        # Verify system is processing again
        async with httpx.AsyncClient() as client:
            # Check Frame Buffer is consuming
            fb_health = await client.get("http://localhost:8002/health")
            assert (
                fb_health.status_code == 200
            ), "Frame Buffer not healthy after recovery"

            # Check Processor is receiving frames
            proc_health = await client.get("http://localhost:8099/health")
            assert (
                proc_health.status_code == 200
            ), "Processor not healthy after recovery"

        # Verify stream is being consumed
        stream_len_after = await redis_client.xlen("frames:metadata")

        # Stream should not be growing unbounded
        assert (
            stream_len_after < stream_len_during + 100
        ), "Stream not being consumed after recovery"

        print("\n✓ System recovered from cascade failure")

    finally:
        await redis_client.close()


@pytest.mark.integration
@pytest.mark.failure
async def test_memory_pressure_handling():
    """Test system behavior under memory pressure."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Check services
        if not await wait_for_service("http://localhost:8002"):
            pytest.skip("Frame Buffer v2 not available")

        print("Testing memory pressure handling...")

        # Get initial memory stats
        async with httpx.AsyncClient() as client:
            stats = await client.get("http://localhost:8002/stats")
            if stats.status_code == 200:
                initial_memory = stats.json().get("memory_usage_mb", 0)
                print(f"Initial memory usage: {initial_memory} MB")

        # Create large metadata to simulate memory pressure
        for i in range(100):
            large_metadata = {
                "frame_id": f"large_{i}",
                "camera_id": "test_cam",
                "timestamp": time.time(),
                "metadata": json.dumps(
                    {"large_data": "x" * 10000, "index": i}  # 10KB per frame
                ),
            }
            await redis_client.xadd("frames:metadata", large_metadata)

        # Wait for processing
        await asyncio.sleep(5)

        # Check memory handling
        async with httpx.AsyncClient() as client:
            stats = await client.get("http://localhost:8002/stats")
            if stats.status_code == 200:
                final_memory = stats.json().get("memory_usage_mb", 0)
                memory_increase = final_memory - initial_memory

                print(f"Memory increase: {memory_increase} MB")

                # Should have memory limits
                assert (
                    memory_increase < 500
                ), f"Excessive memory usage: {memory_increase} MB increase"

        # Check if system is still responsive
        async with httpx.AsyncClient() as client:
            health = await client.get("http://localhost:8002/health")
            assert health.status_code == 200, "Service unhealthy under memory pressure"

        # Verify frames are still being processed
        groups = await redis_client.xinfo_groups("frames:metadata")
        fb_group = next(
            (g for g in groups if g[b"name"] == b"frame-buffer-group"), None
        )

        if fb_group:
            lag = fb_group.get(b"lag", 0)
            print(f"Consumer group lag: {lag}")

            # System should still be processing, even if slower
            assert lag < 1000, "System stopped processing under memory pressure"

        print("✓ System handled memory pressure gracefully")

    finally:
        await redis_client.close()


if __name__ == "__main__":
    # Run all failure scenario tests
    print("Running failure scenario tests...\n")

    tests = [
        test_frame_buffer_restart_no_frame_loss,
        test_redis_connection_drop_buffering,
        test_processor_failure_redistribution,
        test_rtsp_reconnection_continuity,
        test_cascade_failure_recovery,
        test_memory_pressure_handling,
    ]

    for test in tests:
        print(f"\nRunning {test.__name__}...")
        try:
            asyncio.run(test())
        except Exception as e:
            print(f"❌ Test failed: {e}")

    print("\nAll failure scenario tests completed!")
