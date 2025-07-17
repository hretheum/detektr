"""Common test fixtures and configuration for all tests."""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# Import domain models and services
# These will be imported when needed to avoid circular imports


# Event loop configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Tracing fixtures
@pytest.fixture
def tracer_provider() -> TracerProvider:
    """Create a tracer provider for testing."""
    provider = TracerProvider()
    return provider


@pytest.fixture
def memory_exporter() -> InMemorySpanExporter:
    """Create an in-memory span exporter for testing."""
    return InMemorySpanExporter()


@pytest.fixture
def tracer(
    tracer_provider: TracerProvider, memory_exporter: InMemorySpanExporter
) -> trace.Tracer:
    """Create a tracer with in-memory exporter for testing."""
    tracer_provider.add_span_processor(SimpleSpanProcessor(memory_exporter))
    trace.set_tracer_provider(tracer_provider)
    return trace.get_tracer(__name__)


# Database fixtures
@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Create a PostgreSQL container for testing."""
    container = PostgresContainer("postgres:15-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def postgres_url(postgres_container: PostgresContainer) -> str:
    """Get PostgreSQL connection URL from container."""
    return postgres_container.get_connection_url().replace("psycopg2", "asyncpg")


@pytest_asyncio.fixture
async def db_engine(postgres_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async database engine."""
    engine = create_async_engine(postgres_url, echo=False)

    # Create tables if needed
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session."""
    async_session_maker = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


# Redis fixtures
@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    """Create a Redis container for testing."""
    container = RedisContainer("redis:7-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture
def redis_url(redis_container: RedisContainer) -> str:
    """Get Redis connection URL from container."""
    return f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}"


@pytest_asyncio.fixture
async def redis_client(redis_url: str):
    """Create Redis client for testing."""
    import aioredis

    client = await aioredis.from_url(redis_url, decode_responses=True)
    yield client
    await client.close()


# Message queue fixtures
@pytest.fixture
def message_queue() -> Mock:
    """Mock message queue for testing."""
    queue = Mock()
    queue.publish = AsyncMock()
    queue.subscribe = AsyncMock()
    queue.ack = AsyncMock()
    return queue


# Domain fixtures
@pytest.fixture
def sample_frame():
    """Create a sample Frame for testing."""
    from datetime import datetime

    from src.shared.kernel.domain import Frame

    return Frame.create(camera_id="test_camera_01", timestamp=datetime.now())


@pytest.fixture
def mock_frame_repository() -> Mock:
    """Mock frame repository for testing."""
    repo = Mock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.find_by_status = AsyncMock()
    return repo


# Service fixtures
@pytest.fixture
def mock_metrics() -> Mock:
    """Mock metrics client for testing."""
    metrics = Mock()
    metrics.increment_frames_processed = Mock()
    metrics.record_processing_time = Mock()
    metrics.increment_errors = Mock()
    return metrics


# Environment fixtures
@pytest.fixture(autouse=True)
def test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OTLP_ENDPOINT", "http://localhost:4317")


# Async helpers
@pytest.fixture
def run_async():
    """Helper to run async functions in tests."""

    def _run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    return _run_async


# Test data fixtures
@pytest.fixture
def test_image_path() -> str:
    """Path to test image."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "test_image.jpg")


@pytest.fixture
def test_video_path() -> str:
    """Path to test video."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "test_video.mp4")


# Benchmark fixtures
@pytest.fixture
def benchmark_data():
    """Data for benchmark tests."""
    return {
        "small": list(range(100)),
        "medium": list(range(1000)),
        "large": list(range(10000)),
    }


# Cleanup fixtures
@pytest.fixture(autouse=True)
async def cleanup():
    """Cleanup after each test."""
    yield
    # Add any cleanup logic here


# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "benchmark: mark test as a benchmark")
    config.addinivalue_line("markers", "gpu: mark test as requiring GPU")
    config.addinivalue_line("markers", "flaky: mark test as potentially flaky")
