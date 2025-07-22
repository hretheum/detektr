"""
Redis Sentinel client for High Availability support.

Provides automatic failover detection and master discovery
for Redis Sentinel clusters.
"""

import logging
import os
from typing import Optional

import redis.asyncio as redis
from redis.sentinel import Sentinel

logger = logging.getLogger(__name__)


class RedisSentinelClient:
    """Redis client with Sentinel support for HA."""

    def __init__(self):
        """Initialize Redis Sentinel client."""
        # Configuration from environment
        self.sentinel_hosts = self._parse_sentinel_hosts()
        self.master_name = os.getenv("REDIS_MASTER_NAME", "mymaster")
        self.redis_db = int(os.getenv("REDIS_DB", "0"))

        # Fallback to direct Redis connection
        self.fallback_host = os.getenv("REDIS_HOST", "redis")
        self.fallback_port = int(os.getenv("REDIS_PORT", "6379"))

        # Client instances
        self.sentinel: Optional[Sentinel] = None
        self.redis_client: Optional[redis.Redis] = None

    def _parse_sentinel_hosts(self) -> list:
        """Parse Sentinel hosts from environment."""
        sentinel_hosts_str = os.getenv(
            "REDIS_SENTINEL_HOSTS", "sentinel-1:26379,sentinel-2:26380,sentinel-3:26381"
        )

        hosts = []
        for host_port in sentinel_hosts_str.split(","):
            if ":" in host_port:
                host, port = host_port.strip().split(":")
                hosts.append((host, int(port)))
            else:
                hosts.append((host_port.strip(), 26379))

        return hosts

    async def connect(self) -> redis.Redis:
        """Connect to Redis through Sentinel or fallback to direct connection."""
        if self.sentinel_hosts:
            try:
                # Try Sentinel connection
                logger.info(f"Connecting to Redis via Sentinel: {self.sentinel_hosts}")

                # Create Sentinel instance
                self.sentinel = Sentinel(
                    self.sentinel_hosts,
                    socket_timeout=0.1,
                    sentinel_kwargs={"socket_timeout": 0.1},
                )

                # Discover master
                master_info = self.sentinel.discover_master(self.master_name)
                logger.info(f"Discovered Redis master: {master_info}")

                # Create Redis client to master
                self.redis_client = redis.Redis(
                    host=master_info[0],
                    port=master_info[1],
                    db=self.redis_db,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                )

                # Test connection
                await self.redis_client.ping()
                logger.info("✅ Connected to Redis via Sentinel")
                return self.redis_client

            except Exception as e:
                logger.warning(f"Sentinel connection failed: {e}")
                logger.info("Falling back to direct Redis connection...")

        # Fallback to direct Redis connection
        try:
            msg = f"Connecting directly to Redis: {self.fallback_host}:{self.fallback_port}"
            logger.info(msg)
            self.redis_client = redis.Redis(
                host=self.fallback_host,
                port=self.fallback_port,
                db=self.redis_db,
                decode_responses=True,
            )

            await self.redis_client.ping()
            logger.info("✅ Connected to Redis directly")
            return self.redis_client

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def get_client(self) -> redis.Redis:
        """Get Redis client, reconnecting if needed."""
        if not self.redis_client:
            return await self.connect()

        try:
            # Test current connection
            await self.redis_client.ping()
            return self.redis_client
        except Exception as e:
            logger.warning(f"Redis connection lost: {e}")
            logger.info("Attempting to reconnect...")
            return await self.connect()

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
