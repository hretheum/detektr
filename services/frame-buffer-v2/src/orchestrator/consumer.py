"""Redis Streams consumer for frame events."""

import asyncio
import logging
from typing import AsyncIterator, Dict, List, Optional, Union

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class StreamConsumer:
    """Consumer for Redis Streams with consumer group support."""

    def __init__(
        self,
        stream: str,
        group: str,
        consumer_id: str,
        redis_client: aioredis.Redis,
        block_ms: int = 1000,
    ):
        """Initialize stream consumer.

        Args:
            stream: Redis stream name
            group: Consumer group name
            consumer_id: Unique consumer ID within group
            redis_client: Redis client instance
            block_ms: Block timeout in milliseconds
        """
        # Validate inputs
        if not stream or not stream.strip():
            raise ValueError("Stream name cannot be empty")
        if not group or not group.strip():
            raise ValueError("Group name cannot be empty")
        if not consumer_id or not consumer_id.strip():
            raise ValueError("Consumer ID cannot be empty")
        if block_ms < 0:
            raise ValueError("block_ms cannot be negative")

        self.stream = stream.strip()
        self.group = group.strip()
        self.consumer_id = consumer_id.strip()
        self.redis = redis_client
        self.block_ms = block_ms
        self._running = True

    async def create_group(self, start_id: str = "0") -> bool:
        """Create consumer group if it doesn't exist.

        Args:
            start_id: Starting message ID (0 for beginning, $ for new messages only)

        Returns:
            True if group was created, False if already exists
        """
        try:
            await self.redis.xgroup_create(self.stream, self.group, id=start_id)
            logger.info(
                f"Created consumer group '{self.group}' for stream '{self.stream}'"
            )
            return True
        except aioredis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group '{self.group}' already exists")
                return False
            raise

    async def consume(self, max_count: int = 10) -> AsyncIterator[Dict]:
        """Consume messages from the stream.

        Args:
            max_count: Maximum messages to read per batch

        Yields:
            Message dictionaries with 'id', 'stream', and data fields
        """
        # Validate inputs
        if max_count <= 0:
            raise ValueError("max_count must be positive")

        retry_delay = 1
        max_retry_delay = 60

        while self._running:
            try:
                # Read new messages with timeout
                messages = await asyncio.wait_for(
                    self.redis.xreadgroup(
                        self.group,
                        self.consumer_id,
                        {self.stream: ">"},
                        count=max_count,
                        block=self.block_ms,
                    ),
                    timeout=(self.block_ms / 1000) + 5,  # Add 5s buffer
                )

                if not messages:
                    continue

                # Reset retry delay on success
                retry_delay = 1

                for stream_name, stream_messages in messages:
                    for msg_id, data in stream_messages:
                        yield {"id": msg_id, "stream": stream_name, **data}

            except asyncio.CancelledError:
                logger.info("Consumer cancelled")
                break
            except asyncio.TimeoutError:
                logger.warning(f"Redis operation timed out after {self.block_ms}ms")
                continue
            except aioredis.ConnectionError as e:
                logger.error(
                    f"Redis connection lost: {e}, retrying in {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)
            except aioredis.ResponseError as e:
                logger.error(f"Redis response error: {e}")
                # Don't retry on response errors - they indicate logical issues
                raise
            except Exception as e:
                logger.error(f"Unexpected error consuming messages: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def consume_batch(self, batch_size: int = 10) -> AsyncIterator[List[Dict]]:
        """Consume messages in batches.

        Args:
            batch_size: Number of messages per batch

        Yields:
            Lists of message dictionaries
        """
        batch = []
        async for message in self.consume(max_count=batch_size):
            batch.append(message)
            if len(batch) >= batch_size:
                yield batch
                batch = []

        # Yield remaining messages
        if batch:
            yield batch

    async def ack_frame(self, message_id: str) -> None:
        """Acknowledge a single message.

        Args:
            message_id: Redis stream message ID to acknowledge
        """
        try:
            await self.redis.xack(self.stream, self.group, message_id)
            logger.debug(f"Acknowledged message {message_id}")
        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            raise

    async def ack_frames(self, message_ids: List[str]) -> None:
        """Acknowledge multiple messages.

        Args:
            message_ids: List of Redis stream message IDs to acknowledge
        """
        if not message_ids:
            return

        try:
            count = await self.redis.xack(self.stream, self.group, *message_ids)
            logger.debug(f"Acknowledged {count} messages")
        except Exception as e:
            logger.error(f"Failed to acknowledge messages: {e}")
            raise

    async def claim_pending_messages(
        self, min_idle_time: int = 300000, count: int = 100  # 5 minutes default
    ) -> List[Dict]:
        """Claim pending messages from other consumers.

        Args:
            min_idle_time: Minimum idle time in milliseconds
            count: Maximum messages to claim

        Returns:
            List of claimed messages
        """
        try:
            # Get pending messages
            pending = await self.redis.xpending_range(
                self.stream, self.group, min="-", max="+", count=count
            )

            if not pending:
                return []

            # Extract message IDs
            message_ids = [msg["message_id"] for msg in pending]

            # Claim messages
            claimed = await self.redis.xclaim(
                self.stream,
                self.group,
                self.consumer_id,
                min_idle_time=min_idle_time,
                message_ids=message_ids,
            )

            result = []
            for msg_id, data in claimed:
                result.append({"id": msg_id, "stream": self.stream, **data})

            logger.info(f"Claimed {len(result)} pending messages")
            return result

        except Exception as e:
            logger.error(f"Failed to claim pending messages: {e}")
            return []

    async def get_consumer_info(self) -> Dict:
        """Get information about this consumer.

        Returns:
            Consumer information including pending messages
        """
        try:
            # Get consumer group info
            groups = await self.redis.xinfo_groups(self.stream)

            for group in groups:
                group_name = group["name"]
                if isinstance(group_name, bytes):
                    group_name = group_name.decode()

                if group_name == self.group:
                    # Get consumers in group
                    consumers = await self.redis.xinfo_consumers(
                        self.stream, self.group
                    )

                    for consumer in consumers:
                        consumer_name = consumer["name"]
                        if isinstance(consumer_name, bytes):
                            consumer_name = consumer_name.decode()

                        if consumer_name == self.consumer_id:
                            return {
                                "consumer_id": self.consumer_id,
                                "pending": consumer["pending"],
                                "idle": consumer["idle"],
                            }

            return {"consumer_id": self.consumer_id, "pending": 0, "idle": 0}

        except Exception as e:
            logger.error(f"Failed to get consumer info: {e}")
            return {}

    def stop(self):
        """Stop the consumer."""
        self._running = False
        logger.info(f"Stopping consumer {self.consumer_id}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.create_group()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.stop()
        if exc_type:
            logger.error(f"Consumer exiting with exception: {exc_val}")
