#!/usr/bin/env python3
"""Test frame pipeline by injecting test frames."""

import asyncio
import json
import uuid
from datetime import datetime

import redis.asyncio as aioredis


async def inject_test_frame():
    """Inject a test frame into the pipeline."""
    # Connect to Redis
    redis = await aioredis.from_url(
        "redis://192.168.1.193:6379", decode_responses=False
    )

    # Create test frame
    frame_id = f"test-{uuid.uuid4().hex[:8]}"
    frame_data = {
        "frame_id": frame_id,
        "timestamp": datetime.now().isoformat(),
        "camera_id": "test-camera",
        "width": 1920,
        "height": 1080,
        "format": "RGB",
        "metadata": {
            "test": True,
            "source": "test_script",
            "detection_type": "sample_processing",  # Required by frame-buffer-v2!
        },
    }

    # Add to frames:metadata stream (this is where rtsp-capture publishes)
    result = await redis.xadd(
        "frames:metadata",
        {
            "frame_id": frame_id,
            "camera_id": frame_data["camera_id"],
            "timestamp": frame_data["timestamp"],
            "width": str(frame_data["width"]),
            "height": str(frame_data["height"]),
            "format": frame_data["format"],
            "size_bytes": "1024000",  # 1MB fake size
            "metadata": json.dumps(frame_data["metadata"]),
            "trace_context": json.dumps(
                {
                    "trace_id": uuid.uuid4().hex,
                    "span_id": uuid.uuid4().hex[:16],
                    "trace_flags": "01",
                    "trace_state": {},
                    "attributes": {},
                    "baggage": {},
                }
            ),
        },
    )

    print(f"Injected frame {frame_id} with stream ID: {result}")

    # Wait a bit
    await asyncio.sleep(2)

    # Check if frame was distributed to processor
    processor_queue_len = await redis.xlen("frames:ready:sample-processor-1")
    print(f"Processor queue length: {processor_queue_len}")

    # Check results stream
    results = await redis.xrange("sample:results", count=10)
    if results:
        print("\nResults found:")
        for msg_id, data in results:
            print(f"  {msg_id}: {data}")

    await redis.close()


if __name__ == "__main__":
    asyncio.run(inject_test_frame())
