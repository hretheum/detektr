"""Processor client library for easy processor implementation."""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

import httpx
import redis.asyncio as aioredis
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Metrics
frames_processed = Counter(
    "processor_frames_processed_total",
    "Total frames processed",
    ["processor_id", "result"],
)

processing_duration = Histogram(
    "processor_frame_duration_seconds", "Frame processing duration", ["processor_id"]
)

active_tasks = Gauge(
    "processor_active_tasks", "Number of active processing tasks", ["processor_id"]
)

processing_errors = Counter(
    "processor_errors_total", "Total processing errors", ["processor_id", "error_type"]
)


class ProcessorClient(ABC):
    """Base class for processor implementations."""

    def __init__(
        self,
        processor_id: str,
        capabilities: List[str],
        orchestrator_url: str,
        capacity: int = 10,
        redis_client: Optional[aioredis.Redis] = None,
        redis_url: str = "redis://localhost:6379",
        result_stream: Optional[str] = None,
        health_port: Optional[int] = None,
        health_check_interval: float = 30.0,
    ):
        """Initialize processor client.

        Args:
            processor_id: Unique processor identifier
            capabilities: List of processing capabilities
            orchestrator_url: URL of the orchestrator service
            capacity: Maximum concurrent processing tasks
            redis_client: Redis client (will create if not provided)
            redis_url: Redis connection URL (used if redis_client not provided)
            result_stream: Stream name for publishing results
            health_port: Port for health endpoint (if needed)
            health_check_interval: Interval for health reporting (seconds)
        """
        self.id = processor_id
        self.capabilities = capabilities
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.capacity = capacity
        self.redis_url = redis_url
        self.result_stream = result_stream
        self.health_port = health_port
        self.health_check_interval = health_check_interval

        self.queue_name = f"frames:ready:{processor_id}"
        self.group_name = f"{processor_id}-group"
        self.consumer_name = f"{processor_id}-1"

        self.redis = redis_client
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_keepalive_connections=5, max_connections=10, keepalive_expiry=30.0
            ),
        )

        self._running = False
        self._active_tasks = 0
        self._start_time = time.time()
        self._errors_total = 0
        self._frames_total = 0

    async def start(self):
        """Start the processor."""
        logger.info(f"Starting processor {self.id}")

        # Create Redis client if not provided
        if not self.redis:
            try:
                self.redis = await aioredis.from_url(
                    self.redis_url,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

        # Register with orchestrator
        await self.register()

        # Create consumer group
        try:
            await self.redis.xgroup_create(self.queue_name, self.group_name, id="0")
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        self._running = True

        # Start background tasks
        tasks = [
            asyncio.create_task(self._consume_frames()),
            asyncio.create_task(self._health_reporter()),
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info(f"Processor {self.id} stopped")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Gracefully shutdown the processor."""
        logger.info(f"Shutting down processor {self.id}")

        self._running = False

        # Wait for active tasks to complete
        max_wait = 30
        start = time.time()
        while self._active_tasks > 0 and (time.time() - start) < max_wait:
            logger.info(f"Waiting for {self._active_tasks} active tasks to complete...")
            await asyncio.sleep(1)

        # Unregister from orchestrator
        try:
            await self.unregister()
        except Exception as e:
            logger.error(f"Failed to unregister: {e}")

        # Cleanup
        await self.http_client.aclose()
        if self.redis:
            await self.redis.aclose()

    def stop(self):
        """Stop the processor."""
        self._running = False

    async def register(self):
        """Register with the orchestrator."""
        registration_data = {
            "id": self.id,
            "capabilities": self.capabilities,
            "capacity": self.capacity,
            "queue": self.queue_name,
            "health_endpoint": f"http://{self.id}:{self.health_port}/health"
            if self.health_port
            else None,
        }

        response = await self.http_client.post(
            f"{self.orchestrator_url}/processors/register", json=registration_data
        )

        if response.status_code != 201:
            raise RuntimeError(
                f"Registration failed: {response.status_code} - {response.text}"
            )

        logger.info(f"Processor {self.id} registered successfully")

    async def unregister(self):
        """Unregister from the orchestrator."""
        response = await self.http_client.delete(
            f"{self.orchestrator_url}/processors/{self.id}"
        )

        if response.status_code not in [204, 404]:
            raise RuntimeError(f"Unregistration failed: {response.status_code}")

        logger.info(f"Processor {self.id} unregistered")

    async def update_configuration(self, config: Dict):
        """Update processor configuration.

        Args:
            config: New configuration values
        """
        # Update local config
        if "capacity" in config:
            self.capacity = config["capacity"]
        if "capabilities" in config:
            self.capabilities = config["capabilities"]

        # Update registration
        update_data = {
            "id": self.id,
            "capabilities": self.capabilities,
            "capacity": self.capacity,
            "queue": self.queue_name,
        }

        response = await self.http_client.put(
            f"{self.orchestrator_url}/processors/{self.id}", json=update_data
        )

        if response.status_code != 200:
            raise RuntimeError(f"Configuration update failed: {response.status_code}")

        logger.info(f"Processor {self.id} configuration updated")

    async def _consume_frames(self):
        """Consume frames from the queue."""
        # Ensure we have Redis connection
        if not self.redis:
            logger.error("No Redis connection available for consuming frames")
            return

        while self._running:
            try:
                # Check capacity
                if self._active_tasks >= self.capacity:
                    await asyncio.sleep(0.1)
                    continue

                # Read messages with dynamic timeout
                block_timeout = (
                    100 if self._active_tasks > 0 else 5000
                )  # 100ms when busy, 5s when idle
                batch_size = min(10, self.capacity - self._active_tasks)

                messages = await self.redis.xreadgroup(
                    self.group_name,
                    self.consumer_name,
                    {self.queue_name: ">"},
                    count=batch_size,
                    block=block_timeout,
                )

                if not messages:
                    continue

                # Process messages
                for stream_name, stream_messages in messages:
                    for msg_id, frame_data in stream_messages:
                        if self._active_tasks >= self.capacity:
                            break

                        # Process frame asynchronously
                        asyncio.create_task(
                            self._process_frame_wrapper(msg_id, frame_data)
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error consuming frames: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_frame_wrapper(self, msg_id: str, frame_data: Dict[bytes, bytes]):
        """Wrapper for frame processing with error handling."""
        self._active_tasks += 1
        active_tasks.labels(processor_id=self.id).set(self._active_tasks)

        start_time = time.time()
        result_status = "success"

        try:
            # Extract trace context
            trace_context = {}
            if b"trace_context" in frame_data:
                try:
                    trace_context = json.loads(frame_data[b"trace_context"])
                except Exception:
                    pass

            # Process frame
            result = await self.process_frame(frame_data)

            # Publish result if configured
            if self.result_stream and result:
                await self.publish_result(result)

            # Acknowledge message
            await self.redis.xack(self.queue_name, self.group_name, msg_id)

            self._frames_total += 1

        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)
            result_status = "error"
            error_type = type(e).__name__
            processing_errors.labels(processor_id=self.id, error_type=error_type).inc()
            self._errors_total += 1

        finally:
            # Update metrics
            duration = time.time() - start_time
            processing_duration.labels(processor_id=self.id).observe(duration)
            frames_processed.labels(processor_id=self.id, result=result_status).inc()

            self._active_tasks -= 1
            active_tasks.labels(processor_id=self.id).set(self._active_tasks)

    @abstractmethod
    async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Optional[Dict]:
        """Process a single frame.

        Args:
            frame_data: Frame data from Redis (keys and values are bytes)

        Returns:
            Processing result or None
        """
        pass

    async def publish_result(self, result: Dict) -> Optional[str]:
        """Publish processing result.

        Args:
            result: Processing result to publish

        Returns:
            Message ID or None
        """
        if not self.result_stream:
            return None

        # Add metadata
        result["processor_id"] = self.id
        result["processed_at"] = datetime.now().isoformat()

        # Convert to Redis format
        redis_data = {}
        for key, value in result.items():
            if isinstance(value, (dict, list)):
                redis_data[key] = json.dumps(value)
            else:
                redis_data[key] = str(value)

        try:
            msg_id = await self.redis.xadd(self.result_stream, redis_data)
            return msg_id
        except Exception as e:
            logger.error(f"Failed to publish result: {e}")
            return None

    async def _health_reporter(self):
        """Report health status periodically."""
        while self._running:
            try:
                # TODO: Implement actual health reporting to orchestrator
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break

    async def _health_handler(self, request):
        """Handle health check requests."""
        return {
            "status": "healthy",
            "processor_id": self.id,
            "capacity_used": self._active_tasks / self.capacity,
            "frames_processed": self._frames_total,
            "errors_total": self._errors_total,
            "uptime_seconds": time.time() - self._start_time,
        }

    def get_available_capacity(self) -> int:
        """Get available processing capacity."""
        return max(0, self.capacity - self._active_tasks)

    def is_at_capacity(self) -> bool:
        """Check if processor is at capacity."""
        return self._active_tasks >= self.capacity

    def get_metrics(self) -> Dict:
        """Get processor metrics."""
        return {
            "processor_id": self.id,
            "frames_processed": self._frames_total,
            "errors_total": self._errors_total,
            "capacity": self.capacity,
            "active_tasks": self._active_tasks,
            "uptime_seconds": time.time() - self._start_time,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
