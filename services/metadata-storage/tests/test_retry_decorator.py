"""
Test suite for retry decorator and connection pool manager.

Tests retry logic and connection pool health monitoring.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
import pytest_asyncio

from src.infrastructure.repositories.metadata_repository import ConnectionPoolConfig
from src.infrastructure.repositories.retry_decorator import (
    ConnectionPoolManager,
    with_retry,
)


@pytest.mark.asyncio
class TestRetryDecorator:
    """Test retry decorator functionality."""

    async def test_successful_call_no_retry(self):
        """Test that successful calls don't retry."""
        mock_func = AsyncMock(return_value="success")

        @with_retry(max_attempts=3)
        async def test_func():
            return await mock_func()

        result = await test_func()

        assert result == "success"
        assert mock_func.call_count == 1

    async def test_retry_on_connection_error(self):
        """Test retry on PostgresConnectionError."""
        mock_func = AsyncMock()
        mock_func.side_effect = [
            asyncpg.PostgresConnectionError("Connection failed"),
            asyncpg.PostgresConnectionError("Connection failed again"),
            "success",
        ]

        @with_retry(max_attempts=3, initial_delay=0.01)
        async def test_func():
            return await mock_func()

        result = await test_func()

        assert result == "success"
        assert mock_func.call_count == 3

    async def test_max_retries_exceeded(self):
        """Test that max retries raises the last exception."""
        mock_func = AsyncMock()
        mock_func.side_effect = asyncpg.PostgresConnectionError("Always fails")

        @with_retry(max_attempts=3, initial_delay=0.01)
        async def test_func():
            return await mock_func()

        with pytest.raises(asyncpg.PostgresConnectionError):
            await test_func()

        assert mock_func.call_count == 3

    async def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        mock_func = AsyncMock()
        mock_func.side_effect = ValueError("Not a connection error")

        @with_retry(max_attempts=3)
        async def test_func():
            return await mock_func()

        with pytest.raises(ValueError):
            await test_func()

        assert mock_func.call_count == 1

    async def test_exponential_backoff(self):
        """Test that delay increases exponentially."""
        delays = []

        async def mock_sleep(delay):
            delays.append(delay)

        mock_func = AsyncMock()
        mock_func.side_effect = [
            asyncpg.PostgresConnectionError("Fail 1"),
            asyncpg.PostgresConnectionError("Fail 2"),
            "success",
        ]

        @with_retry(
            max_attempts=3, initial_delay=0.1, backoff_factor=2.0, max_delay=1.0
        )
        async def test_func():
            return await mock_func()

        with patch("asyncio.sleep", mock_sleep):
            result = await test_func()

        assert result == "success"
        assert len(delays) == 2
        assert delays[0] == 0.1
        assert delays[1] == 0.2  # 0.1 * 2.0

    async def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        delays = []

        async def mock_sleep(delay):
            delays.append(delay)

        mock_func = AsyncMock()
        mock_func.side_effect = [
            asyncpg.PostgresConnectionError("Fail") for _ in range(4)
        ] + ["success"]

        @with_retry(
            max_attempts=5, initial_delay=0.1, backoff_factor=10.0, max_delay=0.5
        )
        async def test_func():
            return await mock_func()

        with patch("asyncio.sleep", mock_sleep):
            result = await test_func()

        assert result == "success"
        assert all(delay <= 0.5 for delay in delays)


@pytest.mark.asyncio
class TestConnectionPoolManager:
    """Test connection pool manager functionality."""

    @pytest.fixture
    def config(self):
        """Create test connection pool config."""
        return ConnectionPoolConfig(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass",
            min_size=5,
            max_size=20,
        )

    @pytest_asyncio.fixture
    async def mock_pool(self):
        """Create mock connection pool."""
        pool = AsyncMock(spec=asyncpg.Pool)
        pool.get_size.return_value = 10
        pool.get_idle_size.return_value = 7
        return pool

    async def test_pool_creation(self, config):
        """Test connection pool creation."""
        manager = ConnectionPoolManager(config)

        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create:
            mock_pool = MagicMock(spec=asyncpg.Pool)
            mock_create.return_value = mock_pool

            pool = await manager.start()

            assert pool == mock_pool
            mock_create.assert_called_once_with(
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password,
                min_size=config.min_size,
                max_size=config.max_size,
                command_timeout=config.command_timeout,
                max_inactive_connection_lifetime=(
                    config.max_inactive_connection_lifetime
                ),
            )

    async def test_pool_stop(self, config, mock_pool):
        """Test stopping connection pool."""
        manager = ConnectionPoolManager(config)
        manager._pool = mock_pool
        manager._health_check_task = asyncio.create_task(asyncio.sleep(10))

        await manager.stop()

        mock_pool.close.assert_called_once()
        assert manager._pool is None
        assert manager._health_check_task.cancelled()

    async def test_health_check_healthy_pool(self, config, mock_pool):
        """Test health check with healthy pool."""
        manager = ConnectionPoolManager(config)
        manager._pool = mock_pool

        # Mock connection acquisition
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        await manager._check_pool_health()

        assert manager.is_healthy
        mock_conn.fetchval.assert_called_once_with("SELECT 1")

    async def test_health_check_unhealthy_pool(self, config, mock_pool):
        """Test health check with unhealthy pool."""
        manager = ConnectionPoolManager(config)
        manager._pool = mock_pool
        manager._is_healthy = True

        # Mock connection failure
        mock_pool.acquire.side_effect = asyncpg.PostgresConnectionError(
            "Connection failed"
        )

        await manager._check_pool_health()

        assert not manager.is_healthy

    async def test_health_check_warnings(self, config, mock_pool):
        """Test health check warnings for pool size."""
        manager = ConnectionPoolManager(config)
        manager._pool = mock_pool

        # Mock low pool size
        mock_pool.get_size.return_value = 3  # Below min_size of 5

        with patch("logging.Logger.warning") as mock_warning:
            await manager._check_pool_health()

            mock_warning.assert_called()
            assert "below minimum" in mock_warning.call_args[0][0]

    async def test_high_utilization_warning(self, config, mock_pool):
        """Test warning when pool utilization is high."""
        manager = ConnectionPoolManager(config)
        manager._pool = mock_pool

        # Mock high utilization
        mock_pool.get_size.return_value = 20
        mock_pool.get_idle_size.return_value = 2  # 18 busy connections

        # Mock successful connection
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("logging.Logger.warning") as mock_warning:
            await manager._check_pool_health()

            mock_warning.assert_called()
            assert "utilization high" in mock_warning.call_args[0][0]

    async def test_get_stats(self, config, mock_pool):
        """Test getting pool statistics."""
        manager = ConnectionPoolManager(config)
        manager._pool = mock_pool
        manager._is_healthy = True

        stats = manager.get_stats()

        assert stats["status"] == "healthy"
        assert stats["pool_size"] == 10
        assert stats["idle_connections"] == 7
        assert stats["busy_connections"] == 3
        assert stats["max_size"] == 20
        assert stats["utilization"] == 0.15  # 3/20

    async def test_get_stats_not_initialized(self, config):
        """Test getting stats when pool not initialized."""
        manager = ConnectionPoolManager(config)

        stats = manager.get_stats()

        assert stats["status"] == "not_initialized"

    async def test_retry_on_pool_creation_failure(self, config):
        """Test retry logic during pool creation."""
        manager = ConnectionPoolManager(config)

        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create:
            mock_pool = MagicMock(spec=asyncpg.Pool)
            mock_create.side_effect = [
                asyncpg.PostgresConnectionError("First attempt failed"),
                asyncpg.PostgresConnectionError("Second attempt failed"),
                mock_pool,  # Third attempt succeeds
            ]

            pool = await manager.start()

            assert pool is not None
            assert mock_create.call_count == 3
