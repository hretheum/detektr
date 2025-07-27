#!/usr/bin/env python3
"""Test script to verify sample-processor integration with frame-buffer."""

import asyncio
import json
import sys
import time
from typing import Any, Dict

import aiohttp


async def check_health(
    session: aiohttp.ClientSession, service_name: str, url: str
) -> bool:
    """Check if a service is healthy."""
    try:
        async with session.get(f"{url}/health") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ {service_name} is healthy: {data}")
                return True
            else:
                print(f"❌ {service_name} returned status {response.status}")
                return False
    except Exception as e:
        print(f"❌ {service_name} is not reachable: {e}")
        return False


async def send_test_frame(
    session: aiohttp.ClientSession, frame_buffer_url: str
) -> Dict[str, Any]:
    """Send a test frame to the frame buffer."""
    test_frame = {
        "frame_id": f"test_frame_{int(time.time())}",
        "timestamp": time.time(),
        "camera_id": "test_camera",
        "width": 640,
        "height": 480,
        "format": "RGB",
        "metadata": {"test": True, "source": "integration_test"},
    }

    try:
        async with session.post(
            f"{frame_buffer_url}/frames", json=test_frame
        ) as response:
            if response.status in [200, 201]:
                result = await response.json()
                print(f"✅ Frame sent successfully: {result}")
                return result
            else:
                text = await response.text()
                print(f"❌ Failed to send frame: {response.status} - {text}")
                return {}
    except Exception as e:
        print(f"❌ Error sending frame: {e}")
        return {}


async def check_buffer_status(
    session: aiohttp.ClientSession, frame_buffer_url: str
) -> Dict[str, Any]:
    """Check the frame buffer status."""
    try:
        async with session.get(f"{frame_buffer_url}/frames/status") as response:
            if response.status == 200:
                data = await response.json()
                print(f"📊 Buffer status: {data}")
                return data
            else:
                print(f"❌ Failed to get buffer status: {response.status}")
                return {}
    except Exception as e:
        print(f"❌ Error getting buffer status: {e}")
        return {}


async def check_processor_metrics(
    session: aiohttp.ClientSession, processor_url: str
) -> Dict[str, Any]:
    """Check the processor metrics."""
    try:
        async with session.get(f"{processor_url}/metrics") as response:
            if response.status == 200:
                data = await response.json()
                print(f"📈 Processor metrics: {json.dumps(data, indent=2)}")
                return data
            else:
                print(f"❌ Failed to get processor metrics: {response.status}")
                return {}
    except Exception as e:
        print(f"❌ Error getting processor metrics: {e}")
        return {}


async def main():
    """Run the integration test."""
    frame_buffer_url = "http://localhost:8002"
    sample_processor_url = "http://localhost:8099"

    print("🧪 Starting Sample Processor Integration Test")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:
        # Step 1: Check health of both services
        print("\n1️⃣ Checking service health...")
        frame_buffer_healthy = await check_health(
            session, "Frame Buffer", frame_buffer_url
        )
        processor_healthy = await check_health(
            session, "Sample Processor", sample_processor_url
        )

        if not (frame_buffer_healthy and processor_healthy):
            print(
                "\n❌ Services are not healthy. Please ensure both services are running."
            )
            return 1

        # Step 2: Check initial buffer status
        print("\n2️⃣ Checking initial buffer status...")
        initial_status = await check_buffer_status(session, frame_buffer_url)

        # Step 3: Send test frames
        print("\n3️⃣ Sending test frames...")
        num_frames = 5
        for i in range(num_frames):
            await send_test_frame(session, frame_buffer_url)
            await asyncio.sleep(0.1)  # Small delay between frames

        # Step 4: Wait for processing
        print("\n4️⃣ Waiting for processing...")
        await asyncio.sleep(2)  # Give time for the processor to consume frames

        # Step 5: Check final buffer status
        print("\n5️⃣ Checking final buffer status...")
        final_status = await check_buffer_status(session, frame_buffer_url)

        # Step 6: Check processor metrics
        print("\n6️⃣ Checking processor metrics...")
        metrics = await check_processor_metrics(session, sample_processor_url)

        # Step 7: Verify processing
        print("\n7️⃣ Verification...")
        if metrics and "processor_metrics" in metrics:
            frames_processed = metrics["processor_metrics"].get("frames_processed", 0)
            if frames_processed > 0:
                print(f"✅ Success! Processor consumed {frames_processed} frames")
                return 0
            else:
                print("❌ No frames were processed")
                return 1
        else:
            print("❌ Could not verify frame processing")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
