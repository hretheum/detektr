"""Redis-based backpressure controller implementation."""

import logging
from typing import Dict

import redis.asyncio as aioredis

from .controller import BackpressureController

logger = logging.getLogger(__name__)


class RedisBackpressureController(BackpressureController):
    """Backpressure controller that monitors Redis queues."""

    def __init__(
        self,
        redis_client: aioredis.Redis,
        queue_prefix: str = "frames:ready:",
        **kwargs,
    ):
        """Initialize Redis-based controller.

        Args:
            redis_client: Redis client instance
            queue_prefix: Prefix for processor queues
            **kwargs: Additional arguments for BackpressureController
        """
        super().__init__(**kwargs)
        self.redis = redis_client
        self.queue_prefix = queue_prefix
        self._processor_capacities: Dict[str, int] = {}

    def register_processor(self, processor_id: str, capacity: int = 1000):
        """Register processor with its capacity.

        Args:
            processor_id: Processor identifier
            capacity: Maximum queue capacity
        """
        self._processor_capacities[processor_id] = capacity
        logger.info(f"Registered processor {processor_id} with capacity {capacity}")

    async def get_queue_stats(self) -> Dict[str, Dict]:
        """Get current queue statistics from Redis.

        Returns:
            Dict mapping processor_id to stats
        """
        stats = {}

        # Get all processor queues
        cursor = 0
        queues = []

        while True:
            cursor, keys = await self.redis.scan(
                cursor, match=f"{self.queue_prefix}*", count=100
            )
            queues.extend(keys)
            if cursor == 0:
                break

        # Get stats for each queue
        for queue_name in queues:
            try:
                # Extract processor ID from queue name
                proc_id = queue_name.decode().replace(self.queue_prefix, "")

                # Get queue length
                queue_length = await self.redis.xlen(queue_name)

                # Get capacity (default if not registered)
                capacity = self._processor_capacities.get(proc_id, 10000)

                # Get priority from processor metadata (stored in Redis)
                priority_key = f"processor:{proc_id}:priority"
                priority = await self.redis.get(priority_key)
                priority = int(priority) if priority else 1

                stats[proc_id] = {
                    "size": queue_length,
                    "capacity": capacity,
                    "priority": priority,
                    "queue_name": queue_name.decode(),
                }

            except Exception as e:
                logger.error(f"Error getting stats for queue {queue_name}: {e}")
                continue

        return stats

    async def get_detailed_stats(self) -> Dict:
        """Get detailed statistics including message ages.

        Returns:
            Detailed statistics dictionary
        """
        stats = await self.get_queue_stats()

        # Enhance with additional metrics
        for proc_id, proc_stats in stats.items():
            queue_name = proc_stats["queue_name"]

            try:
                # Get oldest and newest message IDs
                info = await self.redis.xinfo_stream(queue_name)

                proc_stats["first_entry_id"] = info.get("first-entry", [None])[0]
                proc_stats["last_entry_id"] = info.get("last-entry", [None])[0]

                # Get consumer group info if exists
                try:
                    groups = await self.redis.xinfo_groups(queue_name)
                    if groups:
                        group = groups[0]  # Assuming one group per processor
                        proc_stats["pending_count"] = group.get("pending", 0)
                        proc_stats["consumers"] = group.get("consumers", 0)
                except aioredis.ResponseError as e:
                    # Consumer group might not exist yet
                    logger.debug(f"Consumer group not found for {queue_name}: {e}")
                except Exception as e:
                    logger.warning(
                        f"Error getting consumer group info for {queue_name}: {e}"
                    )

            except Exception as e:
                logger.debug(f"Could not get detailed stats for {queue_name}: {e}")

        return stats

    async def clear_stale_messages(self, max_age_seconds: int = 3600):
        """Clear messages older than specified age.

        Args:
            max_age_seconds: Maximum message age in seconds
        """
        stats = await self.get_queue_stats()
        cleared_total = 0

        for proc_id, proc_stats in stats.items():
            queue_name = proc_stats["queue_name"]

            try:
                # Calculate cutoff timestamp
                import time

                cutoff_ms = int((time.time() - max_age_seconds) * 1000)
                cutoff_id = f"{cutoff_ms}-0"

                # Trim old messages
                cleared = await self.redis.xtrim(
                    queue_name, minid=cutoff_id, approximate=False
                )

                if cleared:
                    logger.info(f"Cleared {cleared} stale messages from {queue_name}")
                    cleared_total += cleared

            except Exception as e:
                logger.error(f"Error clearing stale messages from {queue_name}: {e}")

        return cleared_total
