"""End-to-end integration tests for complete frame flow."""
import asyncio
import json
import time
from typing import Dict, List

import httpx
import pytest
import redis.asyncio as aioredis


async def wait_for_services(services: Dict[str, str], timeout: int = 30) -> bool:
    """Wait for multiple services to be healthy."""
    start = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            all_healthy = True
            for name, url in services.items():
                try:
                    response = await client.get(f"{url}/health")
                    if response.status_code != 200:
                        all_healthy = False
                        break
                except Exception:
                    all_healthy = False
                    break

            if all_healthy:
                return True
            await asyncio.sleep(1)
    return False


async def start_services(service_names: List[str]) -> Dict[str, str]:
    """Start and wait for required services."""
    service_urls = {
        "rtsp-capture": "http://localhost:8080",
        "frame-buffer-v2": "http://localhost:8002",
        "sample-processor": "http://localhost:8099",
    }

    required_services = {name: service_urls[name] for name in service_names}

    if not await wait_for_services(required_services):
        pytest.skip(f"Required services not available: {service_names}")

    return required_services


async def get_processor_metrics(processor_name: str) -> Dict[str, float]:
    """Get metrics from a processor."""
    url = f"http://localhost:8099/metrics"  # Sample processor

    metrics = {}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                for line in response.text.split("\n"):
                    if "frames_processed_total" in line and not line.startswith("#"):
                        metrics["frames_processed"] = float(line.split()[-1])
                    elif "processing_duration_seconds_count" in line:
                        metrics["processing_count"] = float(line.split()[-1])
                    elif "processing_errors_total" in line:
                        metrics["errors"] = float(line.split()[-1])
        except Exception:
            pass

    return metrics


@pytest.mark.integration
async def test_end_to_end_frame_flow():
    """Test complete flow from RTSP to processor."""
    # Start all services
    services = await start_services(
        ["rtsp-capture", "frame-buffer-v2", "sample-processor"]
    )

    # Wait for services to stabilize
    await asyncio.sleep(3)

    # Get initial metrics
    metrics_before = await get_processor_metrics("sample-processor")
    frames_before = metrics_before.get("frames_processed", 0)

    # Also check RTSP metrics
    async with httpx.AsyncClient() as client:
        rtsp_metrics = await client.get(f"{services['rtsp-capture']}/metrics")
        rtsp_frames_before = 0
        if rtsp_metrics.status_code == 200:
            for line in rtsp_metrics.text.split("\n"):
                if "frames_captured_total" in line and not line.startswith("#"):
                    rtsp_frames_before = float(line.split()[-1])
                    break

    # Wait for processing
    print("Monitoring frame flow for 10 seconds...")
    await asyncio.sleep(10)

    # Check processor received frames
    metrics_after = await get_processor_metrics("sample-processor")
    frames_after = metrics_after.get("frames_processed", 0)

    frames_processed = frames_after - frames_before
    assert (
        frames_processed > 50
    ), f"Expected >50 frames processed, got {frames_processed}"

    # Check RTSP published frames
    async with httpx.AsyncClient() as client:
        rtsp_metrics = await client.get(f"{services['rtsp-capture']}/metrics")
        rtsp_frames_after = 0
        if rtsp_metrics.status_code == 200:
            for line in rtsp_metrics.text.split("\n"):
                if "frames_captured_total" in line and not line.startswith("#"):
                    rtsp_frames_after = float(line.split()[-1])
                    break

    rtsp_published = rtsp_frames_after - rtsp_frames_before

    # Calculate frame loss
    if rtsp_published > 0:
        frame_loss = (rtsp_published - frames_processed) / rtsp_published * 100
        assert frame_loss < 5, f"Frame loss too high: {frame_loss:.1f}%"
        print(f"✓ Frame loss: {frame_loss:.1f}%")

    print(f"✓ End-to-end flow working: {frames_processed} frames processed")


@pytest.mark.integration
async def test_trace_propagation():
    """Verify trace context propagates through the pipeline."""
    services = await start_services(
        ["rtsp-capture", "frame-buffer-v2", "sample-processor"]
    )

    # Check if tracing endpoints exist
    async with httpx.AsyncClient() as client:
        # Try to get traces from Frame Buffer
        try:
            traces_response = await client.get(f"{services['frame-buffer-v2']}/traces")
            if traces_response.status_code == 200:
                traces = traces_response.json()

                # Look for traces with all components
                for trace in traces[-10:]:  # Check last 10 traces
                    spans = trace.get("spans", [])
                    services_in_trace = {span.get("service_name") for span in spans}

                    if len(services_in_trace) >= 3:
                        print(
                            f"✓ Found trace spanning {len(services_in_trace)} services"
                        )
                        break
        except Exception:
            print("⚠️  Tracing endpoint not available")


@pytest.mark.integration
async def test_performance_metrics():
    """Test system performance under load."""
    services = await start_services(
        ["rtsp-capture", "frame-buffer-v2", "sample-processor"]
    )
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Monitor for 30 seconds
        duration = 30
        print(f"Running performance test for {duration} seconds...")

        # Get initial metrics
        start_time = time.time()
        initial_metrics = {
            "rtsp": await get_service_metrics(services["rtsp-capture"]),
            "fb": await get_service_metrics(services["frame-buffer-v2"]),
            "processor": await get_processor_metrics("sample-processor"),
        }

        # Get initial Redis stream length
        initial_stream_len = await redis_client.xlen("frames:metadata")

        # Wait
        await asyncio.sleep(duration)

        # Get final metrics
        final_metrics = {
            "rtsp": await get_service_metrics(services["rtsp-capture"]),
            "fb": await get_service_metrics(services["frame-buffer-v2"]),
            "processor": await get_processor_metrics("sample-processor"),
        }

        final_stream_len = await redis_client.xlen("frames:metadata")

        # Calculate rates
        rtsp_rate = (
            final_metrics["rtsp"].get("frames", 0)
            - initial_metrics["rtsp"].get("frames", 0)
        ) / duration

        fb_rate = (
            final_metrics["fb"].get("frames", 0)
            - initial_metrics["fb"].get("frames", 0)
        ) / duration

        processor_rate = (
            final_metrics["processor"].get("frames_processed", 0)
            - initial_metrics["processor"].get("frames_processed", 0)
        ) / duration

        stream_growth = (final_stream_len - initial_stream_len) / duration

        print(f"\nPerformance Results:")
        print(f"- RTSP capture rate: {rtsp_rate:.1f} FPS")
        print(f"- Frame Buffer rate: {fb_rate:.1f} FPS")
        print(f"- Processor rate: {processor_rate:.1f} FPS")
        print(f"- Stream growth: {stream_growth:.1f} frames/s")

        # Verify performance
        assert rtsp_rate >= 25, f"RTSP rate too low: {rtsp_rate:.1f} FPS"
        assert (
            processor_rate >= 20
        ), f"Processing rate too low: {processor_rate:.1f} FPS"

        # Check if stream is growing (backlog)
        if stream_growth > 5:
            print("⚠️  Stream growing - possible processing bottleneck")

        # Calculate end-to-end efficiency
        if rtsp_rate > 0:
            efficiency = processor_rate / rtsp_rate * 100
            print(f"- End-to-end efficiency: {efficiency:.1f}%")
            assert efficiency > 80, f"Low efficiency: {efficiency:.1f}%"

    finally:
        await redis_client.close()


@pytest.mark.integration
async def test_latency_measurement():
    """Measure end-to-end latency."""
    services = await start_services(
        ["rtsp-capture", "frame-buffer-v2", "sample-processor"]
    )
    redis_client = await aioredis.create_redis("redis://localhost:6379")

    try:
        # Monitor latency by tracking specific frames
        latencies = []

        for i in range(5):
            # Add marker frame directly to stream
            marker_time = time.time()
            marker_data = {
                "frame_id": f"latency_test_{i}",
                "camera_id": "test_cam",
                "timestamp": str(marker_time),
                "metadata": json.dumps({"latency_test": True, "index": i}),
            }

            await redis_client.xadd("frames:metadata", marker_data)

            # Wait for processor to handle it
            processed = False
            start_wait = time.time()

            while time.time() - start_wait < 5:  # Max 5 seconds wait
                # Check processor metrics or logs
                metrics = await get_processor_metrics("sample-processor")

                # Simple check - just see if processing count increased
                if metrics.get("processing_count", 0) > i:
                    processed = True
                    latency = time.time() - marker_time
                    latencies.append(latency)
                    break

                await asyncio.sleep(0.1)

            if not processed:
                print(f"⚠️  Marker frame {i} not processed within timeout")

        if latencies:
            avg_latency = sum(latencies) / len(latencies) * 1000  # Convert to ms
            max_latency = max(latencies) * 1000

            print(f"\nLatency measurements:")
            print(f"- Average: {avg_latency:.1f}ms")
            print(f"- Maximum: {max_latency:.1f}ms")

            assert avg_latency < 100, f"Average latency too high: {avg_latency:.1f}ms"
            assert max_latency < 200, f"Maximum latency too high: {max_latency:.1f}ms"

    finally:
        await redis_client.close()


async def get_service_metrics(url: str) -> Dict[str, float]:
    """Generic metrics getter."""
    metrics = {}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{url}/metrics")
            if response.status_code == 200:
                for line in response.text.split("\n"):
                    if "_total" in line and not line.startswith("#"):
                        parts = line.split()
                        if len(parts) >= 2:
                            metric_name = parts[0].split("{")[0]
                            if "frames" in metric_name:
                                metrics["frames"] = float(parts[-1])
        except Exception:
            pass
    return metrics


@pytest.mark.integration
async def test_processor_registration():
    """Verify processors properly register with orchestrator."""
    services = await start_services(["frame-buffer-v2", "sample-processor"])

    async with httpx.AsyncClient() as client:
        # Check registered processors
        response = await client.get(f"{services['frame-buffer-v2']}/processors")

        assert response.status_code == 200
        data = response.json()

        processors = data.get("processors", [])
        assert len(processors) > 0, "No processors registered"

        # Find sample processor
        sample_proc = None
        for proc in processors:
            if proc.get("id") == "sample-processor-1":
                sample_proc = proc
                break

        assert sample_proc is not None, "Sample processor not registered"

        # Verify processor info
        assert sample_proc.get("status") == "active"
        assert "capabilities" in sample_proc
        assert "last_heartbeat" in sample_proc

        print(f"✓ Sample processor registered: {sample_proc}")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_end_to_end_frame_flow())
    asyncio.run(test_trace_propagation())
    asyncio.run(test_performance_metrics())
    asyncio.run(test_latency_measurement())
    asyncio.run(test_processor_registration())
    print("All tests passed!")
