"""
Redis queue integration for frame metadata publishing.

Provides high-performance publishing of frame metadata to Redis Streams
with <1ms latency for real-time processing.
"""

import json
from typing import Any, Dict, List, Optional, Union

import aioredis
from aioredis.exceptions import ConnectionError, ResponseError
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class RedisFrameQueue:
    """
    Redis Streams-based queue for frame metadata.

    Uses Redis Streams for reliable, ordered message delivery with
    support for consumer groups and automatic trimming.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        stream_key: str = "frames:metadata",
        max_len: Optional[int] = 10000,
        approximate: bool = True,
    ):
        """
        Initialize Redis queue.

        Args:
            redis_client: Async Redis client instance
            stream_key: Redis stream key for frame metadata
            max_len: Maximum stream length (auto-trim)
            approximate: Use approximate trimming for performance
        """
        self.redis_client = redis_client
        self.stream_key = stream_key
        self.max_len = max_len
        self.approximate = approximate

    async def publish(self, metadata: Dict[str, Any]) -> str:
        """
        Publish frame metadata to Redis stream.

        Args:
            metadata: Frame metadata dictionary

        Returns:
            Message ID from Redis

        Raises:
            ConnectionError: If Redis connection fails
        """
        try:
            # Convert all values to strings for Redis
            fields = {}
            for key, value in metadata.items():
                if isinstance(value, (dict, list)):
                    fields[key] = json.dumps(value)
                else:
                    fields[key] = str(value)

            # Inject trace context for propagation
            propagator = TraceContextTextMapPropagator()
            propagator.inject(fields)

            # Add to stream with automatic trimming
            message_id = await self.redis_client.xadd(
                self.stream_key,
                fields,
                maxlen=self.max_len,
                approximate=self.approximate,
            )

            return message_id.decode() if isinstance(message_id, bytes) else message_id

        except ConnectionError:
            # Connection error handling for aioredis
            raise

    async def publish_batch(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        Publish multiple messages in a batch for efficiency.

        Args:
            messages: List of metadata dictionaries

        Returns:
            List of message IDs
        """
        # Use pipeline for atomic batch operation
        async with self.redis_client.pipeline() as pipe:
            for metadata in messages:
                fields = {}
                for key, value in metadata.items():
                    if isinstance(value, (dict, list)):
                        fields[key] = json.dumps(value)
                    else:
                        fields[key] = str(value)

                pipe.xadd(
                    self.stream_key,
                    fields,
                    maxlen=self.max_len,
                    approximate=self.approximate,
                )

            # Execute pipeline
            results = await pipe.execute()

        # Convert bytes to strings
        return [r.decode() if isinstance(r, bytes) else r for r in results]

    async def create_consumer_group(
        self,
        group_name: str,
        start_id: str = "0",
    ) -> bool:
        """
        Create a consumer group for the stream.

        Args:
            group_name: Name of the consumer group
            start_id: Starting message ID (0 for beginning, $ for new messages only)

        Returns:
            True if created, False if already exists
        """
        try:
            await self.redis_client.xgroup_create(
                self.stream_key,
                group_name,
                id=start_id,
            )
            return True
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                # Group already exists
                return False
            raise

    async def read_as_consumer(
        self,
        group_name: str,
        consumer_name: str,
        count: int = 1,
        block: Optional[int] = None,
    ) -> List[tuple]:
        """
        Read messages as part of a consumer group.

        Args:
            group_name: Consumer group name
            consumer_name: Unique consumer identifier
            count: Maximum messages to read
            block: Block for N milliseconds if no messages

        Returns:
            List of (message_id, fields) tuples
        """
        try:
            messages = await self.redis_client.xreadgroup(
                group_name,
                consumer_name,
                {self.stream_key: ">"},
                count=count,
                block=block,
            )

            if not messages:
                return []

            # Extract messages from response
            result = []
            for stream_messages in messages:
                stream_key, msg_list = stream_messages
                for msg_id, fields in msg_list:
                    # Decode fields
                    decoded_fields = {}
                    for k, v in fields.items():
                        key = k.decode() if isinstance(k, bytes) else k
                        value = v.decode() if isinstance(v, bytes) else v

                        # Try to parse JSON fields
                        try:
                            decoded_fields[key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            decoded_fields[key] = value

                    # Extract trace context from message
                    propagator = TraceContextTextMapPropagator()
                    ctx = propagator.extract(decoded_fields)

                    # Store context for consumer use
                    decoded_fields["_trace_context"] = ctx

                    result.append(
                        (
                            msg_id.decode() if isinstance(msg_id, bytes) else msg_id,
                            decoded_fields,
                        )
                    )

            return result

        except ConnectionError:
            raise

    async def acknowledge(
        self,
        group_name: str,
        message_ids: Union[str, List[str]],
    ) -> int:
        """
        Acknowledge message processing completion.

        Args:
            group_name: Consumer group name
            message_ids: Single ID or list of message IDs to acknowledge

        Returns:
            Number of messages acknowledged
        """
        if isinstance(message_ids, str):
            message_ids = [message_ids]

        return await self.redis_client.xack(self.stream_key, group_name, *message_ids)

    async def get_stream_info(self) -> dict:
        """
        Get information about the stream.

        Returns:
            Dictionary with stream statistics
        """
        info = await self.redis_client.xinfo_stream(self.stream_key)

        # Convert bytes keys to strings
        return {k.decode() if isinstance(k, bytes) else k: v for k, v in info.items()}

    async def trim_stream(self, max_len: int) -> int:
        """
        Manually trim the stream to a specific length.

        Args:
            max_len: Maximum number of messages to keep

        Returns:
            Number of messages removed
        """
        return await self.redis_client.xtrim(
            self.stream_key,
            maxlen=max_len,
            approximate=self.approximate,
        )

    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is active."""
        from contextlib import suppress

        with suppress(Exception):
            await self.redis_client.ping()
            # For aioredis, connection is managed by pool

    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis_client.close()
