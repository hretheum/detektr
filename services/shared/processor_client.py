"""ProcessorClient - base class for processors using orchestrator pattern."""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import httpx
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class ProcessorClient(ABC):
    """Base class for processors that register with orchestrator and consume from Redis.
    
    This class provides the ProcessorClient pattern for Frame Buffer v2 integration.
    """

    def __init__(
        self,
        processor_id: str,
        orchestrator_url: str,
        capabilities: List[str],
        redis_host: str = "localhost",
        redis_port: int = 6379,
        consumer_group: str = "frame-processors",
        result_stream: Optional[str] = None,
        heartbeat_interval: int = 30,
        max_retries: int = 3,
        **kwargs,
    ):
        """Initialize processor client.

        Args:
            processor_id: Unique processor identifier
            orchestrator_url: URL of Frame Buffer v2 orchestrator
            capabilities: List of capabilities this processor provides
            redis_host: Redis host for stream consumption
            redis_port: Redis port
            consumer_group: Redis consumer group name
            result_stream: Optional stream for publishing results
            heartbeat_interval: Seconds between heartbeats
            max_retries: Max retries for registration
        """
        self.processor_id = processor_id
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.capabilities = capabilities
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.consumer_group = consumer_group
        self.result_stream = result_stream
        self.heartbeat_interval = heartbeat_interval
        self.max_retries = max_retries

        self._redis_client: Optional[aioredis.Redis] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._consumer_task: Optional[asyncio.Task] = None
        self._retry_count = 0

    async def start(self):
        """Start the processor - register and begin consuming frames."""
        if self._running:
            logger.warning(f"Processor {self.processor_id} already running")
            return

        self._running = True

        # Initialize clients
        self._redis_client = await aioredis.create_redis(
            f"redis://{self.redis_host}:{self.redis_port}"
        )
        self._http_client = httpx.AsyncClient(timeout=30.0)

        # Register with orchestrator
        registered = await self.register()
        if not registered:
            logger.error(f"Failed to register processor {self.processor_id}")
            await self.stop()
            return

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Start consuming frames
        self._consumer_task = asyncio.create_task(self._consume_loop())

        logger.info(f"Processor {self.processor_id} started successfully")

    async def stop(self):
        """Stop the processor gracefully."""
        self._running = False

        # Cancel tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        # Unregister from orchestrator
        await self.unregister()

        # Close clients
        if self._redis_client:
            await self._redis_client.close()

        if self._http_client:
            await self._http_client.aclose()

        logger.info(f"Processor {self.processor_id} stopped")

    async def register(self) -> bool:
        """Register with the orchestrator."""
        for attempt in range(self.max_retries):
            try:
                response = await self._http_client.post(
                    f"{self.orchestrator_url}/processors/register",
                    json={
                        "processor_id": self.processor_id,
                        "capabilities": self.capabilities,
                        "queue": f"frames:ready:{self.processor_id}",
                    },
                )

                if response.status_code == 200:
                    logger.info(
                        f"Successfully registered processor {self.processor_id}"
                    )
                    self._retry_count = 0
                    return True
                else:
                    logger.error(
                        f"Registration failed: {response.status_code} - {response.text}"
                    )

            except Exception as e:
                self._retry_count = attempt + 1
                logger.error(
                    f"Registration attempt {attempt + 1} failed: {type(e).__name__}: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff

        return False

    async def unregister(self):
        """Unregister from the orchestrator."""
        try:
            await self._http_client.post(
                f"{self.orchestrator_url}/processors/unregister",
                json={"processor_id": self.processor_id},
            )
            logger.info(f"Unregistered processor {self.processor_id}")
        except Exception as e:
            logger.error(f"Failed to unregister: {e}")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats to orchestrator."""
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                response = await self._http_client.post(
                    f"{self.orchestrator_url}/processors/heartbeat",
                    json={
                        "processor_id": self.processor_id,
                        "status": "healthy",
                        "timestamp": time.time(),
                    },
                )

                if response.status_code != 200:
                    logger.warning(
                        f"Heartbeat failed: {response.status_code} - {response.text}"
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _consume_loop(self):
        """Consume frames from Redis stream."""
        stream_key = f"frames:ready:{self.processor_id}"

        # Create consumer group if it doesn't exist
        try:
            await self._redis_client.xgroup_create(
                stream_key, self.consumer_group, id="0"
            )
            logger.info(f"Created consumer group {self.consumer_group}")
        except Exception:
            # Group might already exist
            pass

        while self._running:
            try:
                # Read from stream
                messages = await self._redis_client.xreadgroup(
                    self.consumer_group,
                    self.processor_id,
                    {stream_key: ">"},
                    count=10,
                    block=1000,  # Block for 1 second
                )

                if messages:
                    for stream, stream_messages in messages:
                        for msg_id, frame_data in stream_messages:
                            # Process frame
                            await self._process_frame_wrapper(
                                msg_id, frame_data, stream_key
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consumer loop error: {e}")
                await asyncio.sleep(1)

    async def _process_frame_wrapper(
        self, msg_id: bytes, frame_data: Dict[bytes, bytes], stream_key: str
    ):
        """Wrapper to handle frame processing with error handling."""
        frame_id = frame_data.get(b"frame_id", b"unknown").decode()

        try:
            # Process the frame
            start_time = time.time()
            result = await self.process_frame(frame_data)
            processing_time = time.time() - start_time

            # Publish result if configured
            if self.result_stream and result:
                await self._publish_result(frame_id, result)

            # Acknowledge frame
            await self._redis_client.xack(stream_key, self.consumer_group, msg_id)

            logger.debug(f"Processed frame {frame_id} in {processing_time:.3f}s")

        except Exception as e:
            logger.error(f"Error processing frame {frame_id}: {e}")

            # TODO: Implement retry logic or dead letter queue

    async def _publish_result(self, frame_id: str, result: Dict):
        """Publish processing result to result stream."""
        try:
            result_data = {
                "frame_id": frame_id,
                "processor_id": self.processor_id,
                "timestamp": time.time(),
                "result": json.dumps(result),
            }

            await self._redis_client.xadd(self.result_stream, result_data)

        except Exception as e:
            logger.error(f"Failed to publish result for {frame_id}: {e}")

    @abstractmethod
    async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Dict:
        """Process a single frame.

        Args:
            frame_data: Frame data from Redis stream

        Returns:
            Processing result dictionary
        """
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
