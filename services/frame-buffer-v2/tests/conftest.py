"""Pytest configuration and shared fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
import redis.asyncio as aioredis
from asyncpg import Connection, create_pool
from asyncpg.pool import Pool


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    """Provide Redis client for tests."""
    client = await aioredis.from_url(
        "redis://localhost:6379", encoding="utf-8", decode_responses=True
    )

    # Clean up any test data
    await client.flushdb()

    yield client

    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture
async def pg_pool() -> AsyncGenerator[Pool, None]:
    """Provide PostgreSQL connection pool for tests."""
    pool = await create_pool(
        host="localhost",
        port=5432,
        user="test_user",
        password="test_password",
        database="frame_buffer_test",
        min_size=1,
        max_size=5,
    )

    yield pool

    await pool.close()


@pytest.fixture
async def pg_connection(pg_pool: Pool) -> AsyncGenerator[Connection, None]:
    """Provide PostgreSQL connection for tests."""
    async with pg_pool.acquire() as connection:
        # Start transaction
        transaction = connection.transaction()
        await transaction.start()

        yield connection

        # Rollback to keep tests isolated
        await transaction.rollback()


@pytest.fixture
def test_frame_data():
    """Provide sample frame data for tests."""
    return {
        "frame_id": "test_frame_001",
        "camera_id": "camera_01",
        "timestamp": "2024-03-20T10:00:00Z",
        "width": 1920,
        "height": 1080,
        "format": "jpeg",
        "size_bytes": 1024000,
        "trace_context": {
            "trace_id": "1234567890abcdef1234567890abcdef",
            "span_id": "1234567890abcdef",
            "trace_flags": "01",
        },
        "metadata": {"location": "entrance", "quality": "high"},
    }


@pytest.fixture
def mock_processor_info():
    """Provide sample processor info for tests."""
    return {
        "id": "test-processor-1",
        "capabilities": ["face_detection", "object_detection"],
        "capacity": 100,
        "queue": "frames:ready:test-processor-1",
        "endpoint": "http://test-processor:8080",
        "health_endpoint": "http://test-processor:8080/health",
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    # This will be implemented when we have singleton classes
    yield
