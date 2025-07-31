"""Work queue manager for processor-specific queues."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as aioredis
from prometheus_client import Counter, Gauge

from src.models import FrameReadyEvent

logger = logging.getLogger(__name__)

# Metrics
queue_depth = Gauge(
    "frame_buffer_queue_depth", "Current depth of processor queues", ["processor_id"]
)

frames_enqueued = Counter(
    "frame_buffer_frames_enqueued_total",
    "Total frames enqueued to processors",
    ["processor_id", "camera_id"],
)

frames_dropped = Counter(
    "frame_buffer_frames_dropped_total",
    "Frames dropped due to queue overflow",
    ["processor_id", "reason"],
)


class WorkQueueManager:
    """Manages processor-specific work queues in Redis Streams."""

    def __init__(self, redis_client: aioredis.Redis, max_queue_size: int = 10000):
        """Initialize work queue manager.

        Args:
            redis_client: Redis client instance
            max_queue_size: Maximum messages per queue (FIFO eviction)
        """
        self.redis = redis_client
        self.max_queue_size = max_queue_size
        self.queue_prefix = "frames:ready:"

    def _get_queue_name(self, processor_id: str) -> str:
        """Get Redis stream name for processor queue."""
        return f"{self.queue_prefix}{processor_id}"

    async def create_queue(self, processor_id: str) -> bool:
        """Create a processor queue.

        Args:
            processor_id: Processor identifier

        Returns:
            True if created, False if already exists
        """
        queue_name = self._get_queue_name(processor_id)

        # Check if stream exists
        try:
            length = await self.redis.xlen(queue_name)
            if length >= 0:
                logger.debug(
                    f"Queue {queue_name} already exists with {length} messages"
                )
                return False
        except Exception:
            pass

        # Create empty stream using MKSTREAM option
        try:
            await self.redis.xgroup_create(
                queue_name, "__init__", id="0", mkstream=True
            )
            await self.redis.xgroup_destroy(queue_name, "__init__")
        except aioredis.ResponseError:
            # Fallback for older Redis versions
            dummy_id = await self.redis.xadd(queue_name, {"__init__": "1"})
            await self.redis.xdel(queue_name, dummy_id)

        logger.info(f"Created queue {queue_name}")
        return True

    async def delete_queue(self, processor_id: str) -> bool:
        """Delete a processor queue.

        Args:
            processor_id: Processor identifier

        Returns:
            True if deleted, False if didn't exist
        """
        queue_name = self._get_queue_name(processor_id)

        try:
            # Delete the stream
            result = await self.redis.delete(queue_name)

            # Also delete consumer groups
            try:
                groups = await self.redis.xinfo_groups(queue_name)
                for group in groups:
                    group_name = group.get("name", group.get(b"name"))
                    if isinstance(group_name, bytes):
                        group_name = group_name.decode()
                    await self.redis.xgroup_destroy(queue_name, group_name)
            except Exception:
                pass

            logger.info(f"Deleted queue {queue_name}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete queue {queue_name}: {e}")
            return False

    async def enqueue(self, processor_id: str, frame: FrameReadyEvent) -> Optional[str]:
        """Enqueue a frame to processor queue.

        Args:
            processor_id: Target processor ID
            frame: Frame event to enqueue

        Returns:
            Message ID if enqueued, None if dropped
        """
        queue_name = self._get_queue_name(processor_id)

        # Add timestamp and serialize
        data = frame.to_json()
        data["enqueued_at"] = datetime.now().isoformat()

        # Convert to Redis-compatible format
        redis_data = {}
        for key, value in data.items():
            if value is None:
                redis_data[key] = ""  # Convert None to empty string
            elif isinstance(value, (dict, list)):
                redis_data[key] = json.dumps(value)
            else:
                redis_data[key] = str(value)

        try:
            # Add with maxlen to prevent unbounded growth
            msg_id = await self.redis.xadd(
                queue_name, redis_data, maxlen=self.max_queue_size, approximate=True
            )

            # Update metrics
            frames_enqueued.labels(
                processor_id=processor_id, camera_id=frame.camera_id
            ).inc()

            # Update gauge
            length = await self.redis.xlen(queue_name)
            queue_depth.labels(processor_id=processor_id).set(length)

            logger.debug(f"Enqueued frame {frame.frame_id} to {queue_name}")
            return msg_id

        except Exception as e:
            logger.error(f"Failed to enqueue frame to {queue_name}: {e}")
            frames_dropped.labels(
                processor_id=processor_id, reason="enqueue_error"
            ).inc()
            return None

    async def enqueue_batch(
        self, processor_id: str, frames: List[FrameReadyEvent]
    ) -> List[Optional[str]]:
        """Enqueue multiple frames in a batch.

        Args:
            processor_id: Target processor ID
            frames: List of frames to enqueue

        Returns:
            List of message IDs (None for dropped frames)
        """
        if not frames:
            return []

        queue_name = self._get_queue_name(processor_id)
        msg_ids = []

        # Use pipeline for efficiency
        pipe = self.redis.pipeline()

        for frame in frames:
            data = frame.to_json()
            data["enqueued_at"] = datetime.now().isoformat()

            # Convert to Redis format
            redis_data = {}
            for key, value in data.items():
                if value is None:
                    redis_data[key] = ""  # Convert None to empty string
                elif isinstance(value, (dict, list)):
                    redis_data[key] = json.dumps(value)
                else:
                    redis_data[key] = str(value)

            pipe.xadd(
                queue_name, redis_data, maxlen=self.max_queue_size, approximate=True
            )

        try:
            # Execute pipeline
            results = await pipe.execute()
            msg_ids = results

            # Update metrics
            for frame, msg_id in zip(frames, msg_ids):
                if msg_id:
                    frames_enqueued.labels(
                        processor_id=processor_id, camera_id=frame.camera_id
                    ).inc()
                else:
                    frames_dropped.labels(
                        processor_id=processor_id, reason="batch_overflow"
                    ).inc()

            # Update gauge
            length = await self.redis.xlen(queue_name)
            queue_depth.labels(processor_id=processor_id).set(length)

            logger.debug(f"Batch enqueued {len(msg_ids)} frames to {queue_name}")
            return msg_ids

        except Exception as e:
            logger.error(f"Failed to batch enqueue to {queue_name}: {e}")
            return [None] * len(frames)

    async def create_consumer_group(
        self, processor_id: str, group_name: str, start_id: str = "0"
    ) -> bool:
        """Create a consumer group for the processor queue.

        Args:
            processor_id: Processor identifier
            group_name: Consumer group name
            start_id: Starting message ID (0 for beginning)

        Returns:
            True if created, False if already exists
        """
        queue_name = self._get_queue_name(processor_id)

        try:
            await self.redis.xgroup_create(queue_name, group_name, id=start_id)
            logger.info(f"Created consumer group '{group_name}' for {queue_name}")
            return True
        except aioredis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group '{group_name}' already exists")
                return False
            raise

    async def consume(
        self,
        processor_id: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 1000,
        auto_ack: bool = False,
    ) -> List[Dict]:
        """Consume messages from processor queue.

        Args:
            processor_id: Processor identifier
            group_name: Consumer group name
            consumer_name: Consumer instance name
            count: Maximum messages to read
            block_ms: Block timeout in milliseconds (0 = no wait, None = block forever)
            auto_ack: Automatically acknowledge messages after reading

        Returns:
            List of messages with id, stream, and data fields
        """
        queue_name = self._get_queue_name(processor_id)

        # Validate block_ms
        if block_ms is not None and block_ms < 0:
            raise ValueError("block_ms must be non-negative or None")

        try:
            messages = await self.redis.xreadgroup(
                group_name,
                consumer_name,
                {queue_name: ">"},
                count=count,
                block=block_ms,
            )

            if not messages:
                return []

            result = []
            ack_ids = []

            for stream_name, stream_messages in messages:
                for msg_id, data in stream_messages:
                    message = {"id": msg_id, "stream": stream_name, **data}
                    result.append(message)
                    if auto_ack:
                        ack_ids.append(msg_id)

            # Auto-acknowledge if requested
            if auto_ack and ack_ids:
                await self.redis.xack(queue_name, group_name, *ack_ids)

            # Update gauge
            length = await self.redis.xlen(queue_name)
            queue_depth.labels(processor_id=processor_id).set(length)

            return result

        except aioredis.ConnectionError:
            logger.error(f"Redis connection error consuming from {queue_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to consume from {queue_name}: {e}", exc_info=True)
            return []

    async def ack_messages(
        self, processor_id: str, group_name: str, message_ids: List[str]
    ) -> int:
        """Acknowledge consumed messages.

        Args:
            processor_id: Processor identifier
            group_name: Consumer group name
            message_ids: List of message IDs to acknowledge

        Returns:
            Number of messages acknowledged
        """
        if not message_ids:
            return 0

        queue_name = self._get_queue_name(processor_id)

        try:
            count = await self.redis.xack(queue_name, group_name, *message_ids)
            logger.debug(f"Acknowledged {count} messages in {queue_name}")
            return count
        except Exception as e:
            logger.error(f"Failed to ack messages in {queue_name}: {e}")
            return 0

    async def get_queue_stats(self, processor_id: str) -> Dict:
        """Get statistics for a processor queue.

        Args:
            processor_id: Processor identifier

        Returns:
            Queue statistics dictionary
        """
        queue_name = self._get_queue_name(processor_id)

        try:
            # Get basic info
            length = await self.redis.xlen(queue_name)

            # Check if queue really exists by trying to get info
            exists = True
            try:
                await self.redis.xinfo_stream(queue_name)
            except aioredis.ResponseError as e:
                if "no such key" in str(e).lower():
                    exists = False

            if length == 0 and not exists:
                return {
                    "queue_name": queue_name,
                    "processor_id": processor_id,
                    "length": 0,
                    "pending": 0,
                    "exists": False,
                    "consumers": 0,
                }

            # Get first and last message IDs
            info = await self.redis.xinfo_stream(queue_name)
            first_id = info.get("first-entry", info.get(b"first-entry"))
            last_id = info.get("last-entry", info.get(b"last-entry"))

            # Get consumer group info
            total_pending = 0
            total_consumers = 0

            try:
                groups = await self.redis.xinfo_groups(queue_name)
                for group in groups:
                    pending = group.get("pending", group.get(b"pending", 0))
                    consumers = group.get("consumers", group.get(b"consumers", 0))
                    if isinstance(pending, bytes):
                        pending = int(pending)
                    if isinstance(consumers, bytes):
                        consumers = int(consumers)
                    total_pending += pending
                    total_consumers += consumers
            except Exception:
                pass

            return {
                "queue_name": queue_name,
                "processor_id": processor_id,
                "length": length,
                "pending": total_pending,
                "exists": True,
                "consumers": total_consumers,
                "first_id": first_id[0] if first_id else None,
                "last_id": last_id[0] if last_id else None,
            }

        except Exception as e:
            logger.error(f"Failed to get stats for {queue_name}: {e}")
            return {
                "queue_name": queue_name,
                "processor_id": processor_id,
                "length": 0,
                "pending": 0,
                "exists": False,
                "consumers": 0,
                "error": str(e),
            }
