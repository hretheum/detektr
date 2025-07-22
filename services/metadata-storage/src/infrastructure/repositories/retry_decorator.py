"""
Retry decorator for database operations.

Provides automatic retry logic with exponential backoff.
"""

import asyncio
import contextlib
import functools
import logging
from typing import TYPE_CHECKING, Callable, Optional, Tuple, Type, TypeVar

import asyncpg

if TYPE_CHECKING:
    from .metadata_repository import ConnectionPoolConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 0.1,
    max_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        asyncpg.PostgresConnectionError,
        asyncpg.InterfaceError,
        asyncio.TimeoutError,
    ),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Add retry logic with exponential backoff to async functions.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each attempt
        retryable_exceptions: Tuple of exceptions that should trigger a retry
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        msg = (
                            f"Attempt {attempt + 1}/{max_attempts} failed for "
                            f"{func.__name__}: {e}. Retrying in {delay:.2f}s..."
                        )
                        logger.warning(msg)
                        await asyncio.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        msg = (
                            f"All {max_attempts} attempts failed for "
                            f"{func.__name__}: {e}"
                        )
                        logger.error(msg)

            # If we get here, all attempts failed
            raise last_exception

        return wrapper

    return decorator


class ConnectionPoolManager:
    """Manage connection pool with health checking and automatic recovery."""

    def __init__(
        self,
        config: "ConnectionPoolConfig",
        health_check_interval: float = 30.0,
        min_pool_size_threshold: float = 0.5,
    ):
        """
        Initialize connection pool manager.

        Args:
            config: Connection pool configuration
            health_check_interval: Interval between health checks in seconds
            min_pool_size_threshold: Threshold for pool size warnings
                (fraction of max_size)
        """
        self.config = config
        self.health_check_interval = health_check_interval
        self.min_pool_size_threshold = min_pool_size_threshold
        self._pool: Optional[asyncpg.Pool] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_healthy = True

    async def start(self) -> asyncpg.Pool:
        """Start the connection pool and health monitoring."""
        if self._pool is None:
            self._pool = await self._create_pool()
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        return self._pool

    async def stop(self):
        """Stop the connection pool and health monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_check_task

        if self._pool:
            await self._pool.close()
            self._pool = None

    @with_retry(max_attempts=5, initial_delay=1.0, max_delay=10.0)
    async def _create_pool(self) -> asyncpg.Pool:
        """Create connection pool with retry logic."""
        logger.info(
            f"Creating connection pool to {self.config.host}:{self.config.port}/"
            f"{self.config.database}"
        )

        return await asyncpg.create_pool(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password,
            min_size=self.config.min_size,
            max_size=self.config.max_size,
            command_timeout=self.config.command_timeout,
            max_inactive_connection_lifetime=(
                self.config.max_inactive_connection_lifetime
            ),
        )

    async def _health_check_loop(self):
        """Continuously monitor pool health."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_pool_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    async def _check_pool_health(self):
        """Check connection pool health and log warnings."""
        if not self._pool:
            return

        try:
            # Get pool statistics
            pool_size = self._pool.get_size()
            idle_size = self._pool.get_idle_size()
            busy_size = pool_size - idle_size

            # Check if pool is healthy
            if pool_size < self.config.min_size:
                logger.warning(
                    f"Pool size ({pool_size}) below minimum ({self.config.min_size})"
                )

            if busy_size / self.config.max_size > 0.8:
                msg = (
                    f"Pool utilization high: {busy_size}/{self.config.max_size} "
                    f"connections busy"
                )
                logger.warning(msg)

            # Test a connection
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            if not self._is_healthy:
                logger.info("Connection pool recovered")
                self._is_healthy = True

        except Exception as e:
            if self._is_healthy:
                logger.error(f"Connection pool unhealthy: {e}")
                self._is_healthy = False

    @property
    def is_healthy(self) -> bool:
        """Check if pool is currently healthy."""
        return self._is_healthy and self._pool is not None

    def get_stats(self) -> dict:
        """Get current pool statistics."""
        if not self._pool:
            return {"status": "not_initialized"}

        pool_size = self._pool.get_size()
        idle_size = self._pool.get_idle_size()

        return {
            "status": "healthy" if self._is_healthy else "unhealthy",
            "pool_size": pool_size,
            "idle_connections": idle_size,
            "busy_connections": pool_size - idle_size,
            "max_size": self.config.max_size,
            "utilization": (pool_size - idle_size) / self.config.max_size
            if self.config.max_size > 0
            else 0,
        }
