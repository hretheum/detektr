"""Test environment setup verification."""

import pytest
import redis.asyncio as aioredis
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


@pytest.mark.asyncio
async def test_redis_streams_available():
    """Verify Redis Streams functionality."""
    redis = await aioredis.from_url("redis://localhost:6379")

    try:
        # Test stream creation
        stream_id = await redis.xadd("test:stream", {"data": "test"})
        assert stream_id is not None

        # Test consumer group creation
        await redis.xgroup_create("test:stream", "test-group", "0")

        # Test reading from consumer group
        messages = await redis.xreadgroup(
            "test-group", "consumer-1", {"test:stream": ">"}, count=1, block=100
        )
        assert isinstance(messages, list)

        # Cleanup
        await redis.delete("test:stream")

    finally:
        await redis.close()


@pytest.mark.asyncio
async def test_redis_stream_consumer_groups():
    """Test Redis Streams consumer group functionality."""
    redis = await aioredis.from_url("redis://localhost:6379")

    try:
        stream_key = "test:consumer:stream"
        group_name = "test-consumer-group"

        # Add messages to stream
        msg_ids = []
        for i in range(5):
            msg_id = await redis.xadd(
                stream_key, {"id": str(i), "data": f"message_{i}"}
            )
            msg_ids.append(msg_id)

        # Create consumer group
        await redis.xgroup_create(stream_key, group_name, "0")

        # Read messages as consumer
        messages = await redis.xreadgroup(
            group_name, "consumer-1", {stream_key: ">"}, count=3
        )

        assert len(messages) == 1
        assert len(messages[0][1]) == 3  # 3 messages read

        # Check pending messages
        pending = await redis.xpending(stream_key, group_name)
        assert pending[0] == 3  # 3 messages pending

        # Acknowledge messages
        for msg in messages[0][1]:
            await redis.xack(stream_key, group_name, msg[0])

        # Verify acknowledged
        pending_after = await redis.xpending(stream_key, group_name)
        assert pending_after[0] == 0  # No messages pending

        # Cleanup
        await redis.delete(stream_key)

    finally:
        await redis.close()


def test_trace_context_propagation():
    """Verify OpenTelemetry context propagation."""
    # Set up tracer
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()

    # Add console exporter for testing
    processor = SimpleSpanProcessor(ConsoleSpanExporter())
    tracer_provider.add_span_processor(processor)

    tracer = trace.get_tracer(__name__)

    # Test trace creation
    with tracer.start_as_current_span("test") as span:
        trace_id = span.get_span_context().trace_id
        span_id = span.get_span_context().span_id

        assert trace_id != 0
        assert span_id != 0

        # Test child span
        with tracer.start_as_current_span("child") as child_span:
            child_trace_id = child_span.get_span_context().trace_id
            assert child_trace_id == trace_id  # Same trace
            assert child_span.parent.span_id == span_id


@pytest.mark.asyncio
async def test_postgres_connection():
    """Test PostgreSQL connection for processor registry."""
    import asyncpg

    # Connect to test database
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="test_user",
        password="test_password",
        database="frame_buffer_test",
    )

    try:
        # Test query
        result = await conn.fetchval("SELECT 1")
        assert result == 1

        # Create test table
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                data TEXT
            )
        """
        )

        # Insert test data
        await conn.execute("INSERT INTO test_table (data) VALUES ($1)", "test_data")

        # Query test data
        row = await conn.fetchrow(
            "SELECT * FROM test_table WHERE data = $1", "test_data"
        )
        assert row["data"] == "test_data"

        # Cleanup
        await conn.execute("DROP TABLE IF EXISTS test_table")

    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_all_services_healthy():
    """Verify all test services are healthy."""
    import httpx

    # Check Jaeger
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:16686/api/services")
        assert response.status_code == 200

    # Check Redis
    redis = await aioredis.from_url("redis://localhost:6379")
    try:
        pong = await redis.ping()
        assert pong is True
    finally:
        await redis.close()

    # Check PostgreSQL
    import asyncpg

    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="test_user",
        password="test_password",
        database="frame_buffer_test",
    )
    try:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
    finally:
        await conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
