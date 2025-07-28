"""Sample Processor using ProcessorClient pattern."""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict

# Add parent directories to path to import shared modules
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

from services.shared.processor_client import ProcessorClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class SampleProcessor(ProcessorClient):
    """Sample processor implementation using ProcessorClient pattern."""

    def __init__(self, **kwargs):
        """Initialize sample processor.

        Additional kwargs are passed to ProcessorClient.
        """
        # Set default capabilities if not provided
        if "capabilities" not in kwargs:
            kwargs["capabilities"] = ["sample_processing"]

        # Set default result stream if not provided
        if "result_stream" not in kwargs:
            kwargs["result_stream"] = "sample:results"

        super().__init__(**kwargs)

        # Sample processor specific attributes
        self.frames_processed = 0
        self.start_time = time.time()

        logger.info(
            f"Initializing {self.processor_id} with capabilities: {self.capabilities}"
        )

    async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Dict:
        """Process a single frame - sample implementation.

        This is where real processing logic would go.
        For now, we just add some metadata and simulate processing.

        Args:
            frame_data: Frame data from Redis stream

        Returns:
            Processing result dictionary
        """
        start_time = time.time()

        # Extract frame information
        frame_id = frame_data.get(b"frame_id", b"unknown").decode("utf-8")
        camera_id = frame_data.get(b"camera_id", b"unknown").decode("utf-8")
        timestamp = frame_data.get(b"timestamp", b"0").decode("utf-8")

        # Extract metadata if present
        metadata = {}
        if b"metadata" in frame_data:
            try:
                metadata = json.loads(frame_data[b"metadata"])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse metadata for frame {frame_id}")

        logger.info(f"Processing frame {frame_id} from camera {camera_id}")

        # Simulate some processing work
        await asyncio.sleep(0.01)  # 10ms processing time

        # In a real processor, this would be actual detection/analysis results
        processing_result = {
            "frame_id": frame_id,
            "camera_id": camera_id,
            "timestamp": timestamp,
            "processed": True,
            "processing_time": time.time() - start_time,
            "processor_id": self.processor_id,
            "processor_timestamp": time.time(),
            "sample_metadata": {
                "original_metadata": metadata,
                "frames_processed_total": self.frames_processed + 1,
                "processor_uptime": time.time() - self.start_time,
            },
            # Simulated detection results
            "detections": [
                {
                    "type": "sample_object",
                    "confidence": 0.95,
                    "bbox": [100, 100, 200, 200],
                }
            ],
            "detection_count": 1,
        }

        self.frames_processed += 1

        # Log every 100 frames
        if self.frames_processed % 100 == 0:
            logger.info(
                f"Processed {self.frames_processed} frames, "
                f"average time: {(time.time() - self.start_time) / self.frames_processed:.3f}s"
            )

        return processing_result

    async def on_start(self):
        """Called when processor starts."""
        logger.info(f"Sample processor {self.processor_id} started")
        logger.info(f"Orchestrator URL: {self.orchestrator_url}")
        logger.info(f"Redis: {self.redis_host}:{self.redis_port}")
        logger.info(f"Consumer group: {self.consumer_group}")
        logger.info(f"Result stream: {self.result_stream}")

    async def on_stop(self):
        """Called when processor stops."""
        runtime = time.time() - self.start_time
        logger.info(
            f"Sample processor {self.processor_id} stopped. "
            f"Processed {self.frames_processed} frames in {runtime:.1f}s "
            f"({self.frames_processed / runtime:.1f} fps)"
        )


async def main():
    """Main entry point for sample processor."""
    # Get configuration from environment
    processor_id = os.getenv("PROCESSOR_ID", "sample-processor-1")
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://frame-buffer-v2:8002")
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    # Create processor
    processor = SampleProcessor(
        processor_id=processor_id,
        orchestrator_url=orchestrator_url,
        redis_host=redis_host,
        redis_port=redis_port,
        capabilities=["sample_processing", "object_detection"],
        heartbeat_interval=30,
    )

    # Run processor
    try:
        await processor.start()
        await processor.on_start()

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Processor error: {e}", exc_info=True)
    finally:
        await processor.on_stop()
        await processor.stop()


if __name__ == "__main__":
    asyncio.run(main())
