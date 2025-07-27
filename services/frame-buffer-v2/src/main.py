"""Frame Buffer v2 - Main entry point."""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import uvicorn
from fastapi import FastAPI

from src.api.app import app as api_app
from src.orchestrator import (
    FrameDistributor,
    ProcessorRegistry,
    StreamConsumer,
    WorkQueueManager,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FrameBufferService:
    """Main service orchestrator."""

    def __init__(self):
        self.redis_client = None
        self.consumer = None
        self.distributor = None
        self.registry = None
        self.queue_manager = None
        self._running = False

    async def start(self):
        """Start the frame buffer service."""
        logger.info("Starting Frame Buffer v2...")

        # Connect to Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = await aioredis.from_url(
            redis_url, decode_responses=False, health_check_interval=30
        )

        # Initialize components
        self.registry = ProcessorRegistry()
        self.queue_manager = WorkQueueManager(self.redis_client)
        self.distributor = FrameDistributor(self.registry, self.redis_client)

        # Initialize consumer for input stream
        input_stream = os.getenv("INPUT_STREAM", "frames:captured")
        consumer_group = os.getenv("CONSUMER_GROUP", "frame-buffer-group")

        self.consumer = StreamConsumer(
            redis_client=self.redis_client,
            stream=input_stream,
            group=consumer_group,
            consumer_id="frame-buffer-1",
        )

        # Start consuming frames
        self._running = True
        consume_task = asyncio.create_task(self._consume_frames())

        # Store components in app state for API access
        api_app.state.registry = self.registry
        api_app.state.redis_client = self.redis_client
        api_app.state.queue_manager = self.queue_manager

        logger.info("Frame Buffer v2 started successfully")

        # Wait for shutdown
        try:
            await consume_task
        except asyncio.CancelledError:
            logger.info("Frame consumption cancelled")

    async def stop(self):
        """Stop the service gracefully."""
        logger.info("Stopping Frame Buffer v2...")
        self._running = False

        if self.redis_client:
            await self.redis_client.aclose()

        logger.info("Frame Buffer v2 stopped")

    async def _consume_frames(self):
        """Consume frames from input stream and distribute them."""
        while self._running:
            try:
                async for frame_data in self.consumer.consume(max_count=10):
                    # Convert to FrameReadyEvent
                    import json
                    from datetime import datetime

                    from src.models import FrameReadyEvent

                    # Extract frame data
                    frame = FrameReadyEvent(
                        frame_id=frame_data.get(b"frame_id", b"").decode(),
                        camera_id=frame_data.get(b"camera_id", b"").decode(),
                        timestamp=datetime.fromisoformat(
                            frame_data.get(b"timestamp", b"").decode()
                        ),
                        size_bytes=int(frame_data.get(b"size_bytes", b"0")),
                        width=int(frame_data.get(b"width", b"1920")),
                        height=int(frame_data.get(b"height", b"1080")),
                        format=frame_data.get(b"format", b"jpeg").decode(),
                        trace_context=json.loads(
                            frame_data.get(b"trace_context", b"{}")
                        ),
                        metadata=json.loads(frame_data.get(b"metadata", b"{}")),
                    )

                    # Distribute to processors
                    success = await self.distributor.distribute_frame(frame)

                    if success:
                        # Acknowledge the message
                        await self.consumer.ack_message(frame_data["id"])
                    else:
                        logger.warning(f"Failed to distribute frame {frame.frame_id}")

            except Exception as e:
                logger.error(f"Error in frame consumption: {e}", exc_info=True)
                await asyncio.sleep(1)


# Global service instance
service = FrameBufferService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager."""
    # Start the service
    service_task = asyncio.create_task(service.start())

    yield

    # Stop the service
    await service.stop()
    service_task.cancel()
    try:
        await service_task
    except asyncio.CancelledError:
        pass


# Set lifespan for API app
api_app.router.lifespan_context = lifespan


def handle_shutdown(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}")
    asyncio.create_task(service.stop())
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Run the API server
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(api_app, host="0.0.0.0", port=port, log_level="info")
