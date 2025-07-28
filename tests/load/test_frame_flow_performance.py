"""Load tests for frame flow performance validation."""
import asyncio
import time
from typing import Dict

import httpx
import pytest
import redis.asyncio as aioredis


async def configure_rtsp_fps(fps: int = 30) -> bool:
    """Configure RTSP capture for specific FPS."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8080/config",
                json={"fps": fps, "resolution": "1920x1080"},
            )
            return response.status_code == 200
        except Exception:
            return False


async def collect_all_metrics() -> Dict[str, Dict[str, float]]:
    """Collect metrics from all services."""
    metrics = {"rtsp": {}, "frame_buffer": {}, "processors": {}}

    async with httpx.AsyncClient() as client:
        # RTSP metrics
        try:
            response = await client.get("http://localhost:8080/metrics")
            if response.status_code == 200:
                for line in response.text.split("\n"):
                    if "frames_captured_total" in line and not line.startswith("#"):
                        metrics["rtsp"]["frames"] = float(line.split()[-1])
                    elif "frames_published_total" in line and not line.startswith("#"):
                        metrics["rtsp"]["published"] = float(line.split()[-1])
        except Exception:
            pass

        # Frame Buffer metrics
        try:
            response = await client.get("http://localhost:8002/metrics")
            if response.status_code == 200:
                for line in response.text.split("\n"):
                    if "frames_consumed_total" in line and not line.startswith("#"):
                        metrics["frame_buffer"]["frames"] = float(line.split()[-1])
                    elif "frames_distributed_total" in line and not line.startswith(
                        "#"
                    ):
                        metrics["frame_buffer"]["distributed"] = float(line.split()[-1])
        except Exception:
            pass

        # Processor metrics
        try:
            response = await client.get("http://localhost:8099/metrics")
            if response.status_code == 200:
                for line in response.text.split("\n"):
                    if "frames_processed_total" in line and not line.startswith("#"):
                        metrics["processors"]["frames"] = float(line.split()[-1])
        except Exception:
            pass

    return metrics


@pytest.mark.load
@pytest.mark.integration
async def test_high_throughput_flow():
    """Test system under high throughput load."""
    # Configure RTSP for 30 FPS
    configured = await configure_rtsp_fps(30)
    if not configured:
        pytest.skip("Could not configure RTSP FPS")

    # Connect to Redis for stream monitoring
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Run for 60 seconds
        duration = 60
        start_time = time.time()
        start_metrics = await collect_all_metrics()
        start_stream_len = await redis_client.xlen("frames:metadata")

        print(f"Running high throughput test for {duration} seconds at 30 FPS...")
        print(f"Initial metrics: {start_metrics}")

        # Monitor every 10 seconds
        checkpoints = []
        while time.time() - start_time < duration:
            await asyncio.sleep(10)
            checkpoint_metrics = await collect_all_metrics()
            checkpoint_stream_len = await redis_client.xlen("frames:metadata")
            checkpoints.append(
                {
                    "time": time.time() - start_time,
                    "metrics": checkpoint_metrics,
                    "stream_len": checkpoint_stream_len,
                }
            )

        # Final metrics
        end_metrics = await collect_all_metrics()
        end_stream_len = await redis_client.xlen("frames:metadata")
        actual_duration = time.time() - start_time

        # Calculate rates
        rtsp_frames = end_metrics["rtsp"].get("frames", 0) - start_metrics["rtsp"].get(
            "frames", 0
        )
        fb_frames = end_metrics["frame_buffer"].get("frames", 0) - start_metrics[
            "frame_buffer"
        ].get("frames", 0)
        proc_frames = end_metrics["processors"].get("frames", 0) - start_metrics[
            "processors"
        ].get("frames", 0)

        rtsp_rate = rtsp_frames / actual_duration
        fb_rate = fb_frames / actual_duration
        proc_rate = proc_frames / actual_duration

        stream_growth_rate = (end_stream_len - start_stream_len) / actual_duration

        # Performance report
        print("\n=== Performance Test Results ===")
        print(f"Test duration: {actual_duration:.1f} seconds")
        print(f"RTSP capture rate: {rtsp_rate:.1f} FPS")
        print(f"Frame Buffer rate: {fb_rate:.1f} FPS")
        print(f"Processor rate: {proc_rate:.1f} FPS")
        print(f"Stream growth rate: {stream_growth_rate:.1f} frames/s")

        # Calculate frame loss
        if rtsp_frames > 0:
            fb_loss = ((rtsp_frames - fb_frames) / rtsp_frames) * 100
            proc_loss = ((rtsp_frames - proc_frames) / rtsp_frames) * 100
            print(f"Frame loss (RTSP → FB): {fb_loss:.2f}%")
            print(f"Frame loss (RTSP → Proc): {proc_loss:.2f}%")

        # Verify performance criteria
        assert rtsp_rate >= 29, f"RTSP rate too low: {rtsp_rate:.1f} FPS (expected ≥29)"
        assert (
            fb_rate >= 28
        ), f"Frame Buffer rate too low: {fb_rate:.1f} FPS (expected ≥28)"
        assert (
            proc_rate >= 25
        ), f"Processor rate too low: {proc_rate:.1f} FPS (expected ≥25)"

        # Frame loss should be minimal
        if rtsp_frames > 0:
            assert (
                proc_loss < 5
            ), f"Frame loss too high: {proc_loss:.2f}% (expected <5%)"

        # Stream shouldn't grow indefinitely (backpressure working)
        assert (
            stream_growth_rate < 5
        ), f"Stream growing too fast: {stream_growth_rate:.1f} frames/s"

        print("\n✓ Performance test PASSED")

    finally:
        await redis_client.close()


@pytest.mark.load
@pytest.mark.integration
async def test_sustained_load():
    """Test system under sustained load for extended period."""
    # Configure RTSP for 25 FPS (slightly lower for sustained test)
    configured = await configure_rtsp_fps(25)
    if not configured:
        pytest.skip("Could not configure RTSP FPS")

    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Run for 5 minutes
        duration = 300  # 5 minutes
        start_time = time.time()
        start_metrics = await collect_all_metrics()

        print(f"Running sustained load test for {duration/60:.0f} minutes at 25 FPS...")

        # Monitor every 30 seconds
        intervals = []
        last_metrics = start_metrics

        while time.time() - start_time < duration:
            await asyncio.sleep(30)

            current_metrics = await collect_all_metrics()
            interval_time = 30

            # Calculate interval rates
            rtsp_interval = (
                current_metrics["rtsp"].get("frames", 0)
                - last_metrics["rtsp"].get("frames", 0)
            ) / interval_time
            proc_interval = (
                current_metrics["processors"].get("frames", 0)
                - last_metrics["processors"].get("frames", 0)
            ) / interval_time

            intervals.append(
                {
                    "time": time.time() - start_time,
                    "rtsp_fps": rtsp_interval,
                    "proc_fps": proc_interval,
                }
            )

            print(
                f"[{(time.time()-start_time)/60:.1f}m] RTSP: {rtsp_interval:.1f} FPS, "
                f"Proc: {proc_interval:.1f} FPS"
            )

            last_metrics = current_metrics

        # Final analysis
        end_metrics = await collect_all_metrics()
        total_rtsp = end_metrics["rtsp"].get("frames", 0) - start_metrics["rtsp"].get(
            "frames", 0
        )
        total_proc = end_metrics["processors"].get("frames", 0) - start_metrics[
            "processors"
        ].get("frames", 0)

        avg_rtsp_rate = total_rtsp / duration
        avg_proc_rate = total_proc / duration

        # Check rate stability
        rtsp_rates = [i["rtsp_fps"] for i in intervals]
        proc_rates = [i["proc_fps"] for i in intervals]

        rtsp_std = sum((r - avg_rtsp_rate) ** 2 for r in rtsp_rates) / len(rtsp_rates)
        proc_std = sum((r - avg_proc_rate) ** 2 for r in proc_rates) / len(proc_rates)

        print("\n=== Sustained Load Test Results ===")
        print(f"Total duration: {duration/60:.1f} minutes")
        print(f"Average RTSP rate: {avg_rtsp_rate:.1f} FPS")
        print(f"Average Processor rate: {avg_proc_rate:.1f} FPS")
        print(f"RTSP rate variance: {rtsp_std:.2f}")
        print(f"Processor rate variance: {proc_std:.2f}")

        # Verify sustained performance
        assert avg_rtsp_rate >= 24, f"Average RTSP rate too low: {avg_rtsp_rate:.1f}"
        assert (
            avg_proc_rate >= 22
        ), f"Average processor rate too low: {avg_proc_rate:.1f}"

        # Check stability (low variance)
        assert rtsp_std < 4, f"RTSP rate too unstable: variance={rtsp_std:.2f}"
        assert proc_std < 4, f"Processor rate too unstable: variance={proc_std:.2f}"

        print("\n✓ Sustained load test PASSED")

    finally:
        await redis_client.close()


@pytest.mark.load
@pytest.mark.integration
async def test_burst_load():
    """Test system behavior under burst load."""
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        print("Running burst load test...")

        # Normal load (15 FPS)
        await configure_rtsp_fps(15)
        await asyncio.sleep(10)

        pre_burst_metrics = await collect_all_metrics()
        pre_burst_stream = await redis_client.xlen("frames:metadata")

        # Burst load (60 FPS)
        print("Applying burst load (60 FPS)...")
        await configure_rtsp_fps(60)
        burst_start = time.time()

        # Monitor during burst
        burst_metrics = []
        for i in range(10):  # 10 seconds of burst
            await asyncio.sleep(1)
            metrics = await collect_all_metrics()
            stream_len = await redis_client.xlen("frames:metadata")
            burst_metrics.append(
                {"time": i + 1, "metrics": metrics, "stream_len": stream_len}
            )

        # Return to normal
        print("Returning to normal load (15 FPS)...")
        await configure_rtsp_fps(15)

        # Monitor recovery
        recovery_metrics = []
        for i in range(20):  # 20 seconds recovery
            await asyncio.sleep(1)
            metrics = await collect_all_metrics()
            stream_len = await redis_client.xlen("frames:metadata")
            recovery_metrics.append(
                {"time": i + 1, "metrics": metrics, "stream_len": stream_len}
            )

        # Analyze burst handling
        max_stream_growth = (
            max(m["stream_len"] for m in burst_metrics) - pre_burst_stream
        )

        # Check if stream returned to normal
        final_growth_rate = (
            recovery_metrics[-1]["stream_len"] - recovery_metrics[-10]["stream_len"]
        ) / 10

        print("\n=== Burst Load Test Results ===")
        print(f"Max stream growth during burst: {max_stream_growth} frames")
        print(f"Final stream growth rate: {final_growth_rate:.1f} frames/s")

        # System should handle burst without unbounded growth
        assert (
            max_stream_growth < 1000
        ), f"Stream grew too much during burst: {max_stream_growth}"

        # System should recover after burst
        assert (
            final_growth_rate < 2
        ), f"Stream still growing after burst: {final_growth_rate:.1f} frames/s"

        print("\n✓ Burst load test PASSED")

    finally:
        await redis_client.close()


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_high_throughput_flow())
    asyncio.run(test_sustained_load())
    asyncio.run(test_burst_load())
    print("All performance tests completed!")
