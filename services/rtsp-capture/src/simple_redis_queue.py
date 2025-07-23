"""
Simple Redis queue integration for frame metadata publishing.

Non-async version for testing and basic integration.
"""

import json
from typing import Any, Dict, List, Optional, Union

import redis


class SimpleRedisFrameQueue:
    """
    Simple Redis Streams-based queue for frame metadata.

    Non-async version using synchronous Redis client.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        stream_key: str = "frames:metadata",
        max_len: Optional[int] = 10000,
        approximate: bool = True,
    ):
        """
        Initialize Redis queue.

        Args:
            redis_client: Redis client instance
            stream_key: Redis stream key for frame metadata
            max_len: Maximum stream length (auto-trim)
            approximate: Use approximate trimming for performance
        """
        self.redis_client = redis_client
        self.stream_key = stream_key
        self.max_len = max_len
        self.approximate = approximate

    def publish(self, metadata: Dict[str, Any]) -> str:
        """
        Publish frame metadata to Redis stream.

        Args:
            metadata: Frame metadata dictionary

        Returns:
            Message ID from Redis
        """
        # Convert all values to strings for Redis
        fields = {}
        for key, value in metadata.items():
            if isinstance(value, (dict, list)):
                fields[key] = json.dumps(value)
            else:
                fields[key] = str(value)

        # Add to stream with automatic trimming
        message_id = self.redis_client.xadd(
            self.stream_key,
            fields,
            maxlen=self.max_len,
            approximate=self.approximate,
        )

        return message_id.decode() if isinstance(message_id, bytes) else message_id

    def publish_batch(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        Publish multiple messages in a batch for efficiency.

        Args:
            messages: List of metadata dictionaries

        Returns:
            List of message IDs
        """
        # Use pipeline for atomic batch operation
        with self.redis_client.pipeline() as pipe:
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
            results = pipe.execute()

        # Convert bytes to strings
        return [r.decode() if isinstance(r, bytes) else r for r in results]

    def create_consumer_group(
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
            self.redis_client.xgroup_create(
                self.stream_key,
                group_name,
                id=start_id,
                mkstream=True,  # Create stream if it doesn't exist
            )
            return True
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                # Group already exists
                return False
            raise

    def read_as_consumer(
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
        messages = self.redis_client.xreadgroup(
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
        for _, msg_list in messages:
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

                result.append(
                    (
                        msg_id.decode() if isinstance(msg_id, bytes) else msg_id,
                        decoded_fields,
                    )
                )

        return result

    def acknowledge(
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

        return self.redis_client.xack(self.stream_key, group_name, *message_ids)

    def get_stream_info(self) -> dict:
        """
        Get information about the stream.

        Returns:
            Dictionary with stream statistics
        """
        info = self.redis_client.xinfo_stream(self.stream_key)

        # Convert bytes keys to strings
        return {k.decode() if isinstance(k, bytes) else k: v for k, v in info.items()}

    def trim_stream(self, max_len: int) -> int:
        """
        Manually trim the stream to a specific length.

        Args:
            max_len: Maximum number of messages to keep

        Returns:
            Number of messages removed
        """
        return self.redis_client.xtrim(
            self.stream_key,
            maxlen=max_len,
            approximate=self.approximate,
        )
