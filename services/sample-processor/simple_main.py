#!/usr/bin/env python3
"""Simple sample processor for testing ProcessorClient pattern."""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict

import httpx
import redis.asyncio as aioredis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleProcessorClient:
    """Simplified ProcessorClient for testing."""

    def __init__(self, processor_id: str, orchestrator_url: str):
        self.processor_id = processor_id
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.redis_url = "redis://detektr-redis-1:6379"  # Nebula Redis
        self._running = False

    async def register(self) -> bool:
        """Register with orchestrator."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.orchestrator_url}/api/v1/processors/register",
                    json={
                        "processor_id": self.processor_id,
                        "capabilities": ["sample_processing"],
                        "queue": f"frames:ready:{self.processor_id}",
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    logger.info(f"✓ Registered processor {self.processor_id}")
                    return True
                else:
                    logger.error(
                        f"Registration failed: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False

    async def consume_frames(self):
        """Consume frames from Redis queue."""
        redis_client = await aioredis.create_redis(self.redis_url)
        stream_key = f"frames:ready:{self.processor_id}"
        consumer_group = "frame-processors"

        logger.info(f"Starting consumer for {stream_key}")

        try:
            # Create consumer group if needed
            try:
                await redis_client.xgroup_create(stream_key, consumer_group, id="0")
            except:
                pass  # Already exists

            self._running = True
            frames_processed = 0

            while self._running:
                try:
                    # Read from stream
                    messages = await redis_client.xreadgroup(
                        consumer_group,
                        self.processor_id,
                        {stream_key: ">"},
                        count=1,
                        block=1000,
                    )

                    if messages:
                        for stream, stream_messages in messages:
                            for msg_id, frame_data in stream_messages:
                                # Process frame
                                frame_id = frame_data.get(
                                    b"frame_id", b"unknown"
                                ).decode()
                                logger.info(f"Processing frame {frame_id}")

                                # Simulate processing
                                await asyncio.sleep(0.01)

                                # Acknowledge
                                await redis_client.xack(
                                    stream_key, consumer_group, msg_id
                                )
                                frames_processed += 1

                                if frames_processed % 10 == 0:
                                    logger.info(f"Processed {frames_processed} frames")

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Consumer error: {e}")
                    await asyncio.sleep(1)

        finally:
            await redis_client.close()
            logger.info(f"Processed {frames_processed} frames total")

    async def run(self):
        """Run the processor."""
        # Register
        if not await self.register():
            logger.error("Failed to register, exiting")
            return

        # Start consuming
        try:
            await self.consume_frames()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self._running = False


async def main():
    """Main entry point."""
    processor_id = os.getenv("PROCESSOR_ID", "simple-processor-1")
    orchestrator_url = os.getenv(
        "ORCHESTRATOR_URL", "http://detektr-frame-buffer-v2-1:8002"
    )

    logger.info(f"Starting processor {processor_id}")
    logger.info(f"Orchestrator: {orchestrator_url}")

    processor = SimpleProcessorClient(processor_id, orchestrator_url)
    await processor.run()


if __name__ == "__main__":
    asyncio.run(main())
