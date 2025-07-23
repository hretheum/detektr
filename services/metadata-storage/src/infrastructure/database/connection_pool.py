"""Connection pool for database operations."""

import logging
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Async connection pool for PostgreSQL."""

    def __init__(self, dsn: str, min_size: int = 5, max_size: int = 20):
        """Initialize connection pool."""
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self._pool: Optional[asyncpg.Pool] = None

    async def get_connection(self) -> asyncpg.Connection:
        """Get a connection from the pool."""
        if not self._pool:
            await self._create_pool()

        return await self._pool.acquire()

    async def release_connection(self, connection: asyncpg.Connection):
        """Release a connection back to the pool."""
        if self._pool:
            await self._pool.release(connection)

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def _create_pool(self):
        """Create the connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                self.dsn,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=10,
                max_inactive_connection_lifetime=60,
            )
            logger.info(
                f"Connection pool created with "
                f"{self.min_size}-{self.max_size} connections"
            )
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    async def execute(self, query: str, *args):
        """Execute a query using a connection from the pool."""
        async with self._pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetch(self, query: str, *args):
        """Fetch results using a connection from the pool."""
        async with self._pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """Fetch a single row using a connection from the pool."""
        async with self._pool.acquire() as connection:
            return await connection.fetchrow(query, *args)
