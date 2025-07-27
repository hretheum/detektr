"""Frame consumer module for processing frames from Redis Stream."""

import asyncio
import contextlib
import logging
import os
from typing import Dict, List, Optional, Tuple

import redis.asyncio as aioredis
from frame_buffer import FrameBuffer
from frame_tracking import TraceContext
from metrics import (
    consumer_errors_total,
    consumer_lag_seconds,
    frames_consumed_total,
    frames_dropped_total,
)
from shared_buffer import SharedFrameBuffer

logger = logging.getLogger(__name__)


class FrameConsumer:
    """Active consumer that reads frames from Redis Stream and buffers them."""

    def __init__(
        self,
        redis_url: str,
        stream_key: str = "frames:metadata",
        consumer_group: str = "frame-buffer-group",
        consumer_name: str = "frame-buffer-1",
        frame_buffer: Optional[FrameBuffer] = None,
        batch_size: int = 10,
        block_ms: int = 1000,
    ):
        """Initialize frame consumer."""
        self.redis_url = redis_url
        self.stream_key = stream_key
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        # Frame buffer will be initialized in start() method
        self.frame_buffer = frame_buffer
        self.batch_size = batch_size
        self.block_ms = block_ms
        self.redis: Optional[aioredis.Redis] = None
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the consumer."""
        if self._running:
            logger.warning("Consumer already running")
            return

        logger.info(
            f"Starting consumer {self.consumer_name} for stream {self.stream_key}"
        )

        # Initialize shared buffer if not provided
        if not self.frame_buffer:
            self.frame_buffer = await SharedFrameBuffer.get_instance()
            logger.info("✅ Consumer: Shared buffer initialized")

        # Connect to Redis
        self.redis = aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

        # Create consumer group if it doesn't exist
        try:
            await self.redis.xgroup_create(
                self.stream_key,
                self.consumer_group,
                id="0",
                mkstream=True,
            )
            logger.info(f"Created consumer group {self.consumer_group}")
        except Exception as e:
            if "already exists" in str(e):
                logger.info(f"Consumer group {self.consumer_group} already exists")
            else:
                raise

        self._running = True
        self._consumer_task = asyncio.create_task(self._consume_loop())
        logger.info("Consumer started")

    async def stop(self):
        """Stop the consumer gracefully."""
        logger.info("Stopping consumer...")
        self._running = False

        if self._consumer_task:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task

        if self.redis:
            await self.redis.close()

        logger.info("Consumer stopped")

    async def _consume_loop(self):
        """Run main consumer loop."""
        while self._running:
            try:
                # Read messages from stream
                messages = await self._read_messages()

                if messages:
                    # Process messages
                    await self._process_messages(messages)

                    # Acknowledge processed messages
                    await self._acknowledge_messages(messages)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}", exc_info=True)
                consumer_errors_total.inc()
                await asyncio.sleep(1)  # Back off on error

    async def _read_messages(self) -> List[Tuple[str, Dict]]:
        """Read messages from Redis Stream."""
        try:
            # XREADGROUP to read new messages
            result = await self.redis.xreadgroup(
                self.consumer_group,
                self.consumer_name,
                {self.stream_key: ">"},
                count=self.batch_size,
                block=self.block_ms,
            )

            if not result:
                return []

            # Extract messages from result
            messages = []
            for _stream_name, stream_messages in result:
                for msg_id, data in stream_messages:
                    messages.append((msg_id, data))

            return messages

        except Exception as e:
            logger.error(f"Error reading messages: {e}")
            consumer_errors_total.inc()
            return []

    async def _process_messages(self, messages: List[Tuple[str, Dict]]):
        """Process messages and add frames to buffer."""
        for msg_id, data in messages:
            try:
                # Extract trace context from message
                frame_id = data.get("frame_id", "unknown")

                # Use TraceContext for distributed tracing
                with TraceContext.inject(frame_id) as ctx:
                    ctx.add_event("frame_buffer_consume")

                    # Skip OpenTelemetry span for now since tracer might be None
                    # TODO: Fix tracer initialization for consumer thread

                    # Parse frame data
                    frame_data = self._parse_frame_data(data)

                    # Check if buffer is full
                    if self.frame_buffer.is_full():
                        logger.warning(
                            f"Buffer full, dropping frame {frame_data.get('frame_id')}"
                        )
                        frames_dropped_total.labels(reason="buffer_full").inc()
                        continue

                    # Add to buffer
                    put_success = await self.frame_buffer.put(frame_data)
                    if put_success:
                        frames_consumed_total.inc()
                        frame_id = frame_data.get("frame_id")
                        logger.info(f"✅ Consumer: Added frame {frame_id} to buffer")
                    else:
                        frame_id = frame_data.get("frame_id")
                        logger.warning(
                            f"❌ Consumer: Failed to add frame {frame_id} to buffer"
                        )

                    # Update lag metric
                    if "timestamp" in data:
                        try:
                            timestamp = float(data["timestamp"])
                            lag = asyncio.get_event_loop().time() - timestamp
                            consumer_lag_seconds.set(max(0, lag))
                        except (ValueError, TypeError):
                            pass

                    logger.debug(f"Consumed frame {frame_data.get('frame_id')}")

            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}")
                consumer_errors_total.inc()

    async def _acknowledge_messages(self, messages: List[Tuple[str, Dict]]):
        """Acknowledge processed messages."""
        if not messages:
            return

        try:
            # Get message IDs
            msg_ids = [msg_id for msg_id, _ in messages]

            # XACK to acknowledge messages
            acked = await self.redis.xack(
                self.stream_key, self.consumer_group, *msg_ids
            )

            logger.debug(f"Acknowledged {acked} messages")

        except Exception as e:
            logger.error(f"Error acknowledging messages: {e}")
            consumer_errors_total.inc()

    def _parse_frame_data(self, data: Dict) -> Dict:
        """Parse frame data from Redis message."""
        # Parse resolution if available
        width, height = 0, 0
        if "resolution" in data:
            try:
                # Handle resolution as string like "[640, 360]"
                resolution_str = data["resolution"]
                if isinstance(resolution_str, str):
                    resolution_str = resolution_str.strip("[]")
                    width, height = map(int, resolution_str.split(","))
                elif isinstance(resolution_str, list):
                    width, height = resolution_str[0], resolution_str[1]
            except (ValueError, IndexError, TypeError):
                logger.warning(f"Could not parse resolution: {data.get('resolution')}")

        # Use direct width/height if available (fallback)
        width = int(data.get("width", width))
        height = int(data.get("height", height))

        # Extract frame data
        frame_data = {
            "frame_id": data.get("frame_id"),
            "camera_id": data.get("camera_id"),
            "timestamp": data.get("timestamp"),
            "width": width,
            "height": height,
            "format": data.get(
                "format", "bgr24"
            ),  # Default to bgr24 as seen in Redis data
            "size_bytes": int(data.get("size_bytes", 0)),
        }

        # Add trace context for propagation
        if "traceparent" in data:
            frame_data["traceparent"] = data["traceparent"]

        # Add any additional metadata
        for key, value in data.items():
            if key not in frame_data and not key.startswith("_"):
                frame_data[key] = value

        return frame_data


async def create_consumer_from_env() -> FrameConsumer:
    """Create consumer from environment variables."""
    # Use same Redis configuration as main.py
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    stream_key = os.getenv("REDIS_STREAM_KEY", "frames:metadata")
    consumer_group = os.getenv("CONSUMER_GROUP", "frame-buffer-group")
    consumer_name = os.getenv("CONSUMER_NAME", f"frame-buffer-{os.getpid()}")
    batch_size = int(os.getenv("CONSUMER_BATCH_SIZE", "10"))
    block_ms = int(os.getenv("CONSUMER_BLOCK_MS", "1000"))

    return FrameConsumer(
        redis_url=redis_url,
        stream_key=stream_key,
        consumer_group=consumer_group,
        consumer_name=consumer_name,
        batch_size=batch_size,
        block_ms=block_ms,
    )
