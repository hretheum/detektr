"""Integration tests using test containers."""

import aioredis
import asyncpg
import pytest

from tests.fixtures.containers import ContainerHealthCheck, TestContainers


@pytest.mark.integration
class TestContainerIntegration:
    """Test integration with real containers."""

    @pytest.mark.asyncio
    async def test_postgres_integration(self):
        """Test PostgreSQL container integration."""
        container = TestContainers.get_postgres_container()

        with container:
            # Wait for container to be ready
            is_ready = await ContainerHealthCheck.wait_for_postgres(container)
            assert is_ready, "PostgreSQL container failed to start"

            # Connect and test
            url = container.get_connection_url().replace("psycopg2", "asyncpg")
            conn = await asyncpg.connect(url)

            try:
                # Create test table
                await conn.execute(
                    """
                    CREATE TABLE test_table (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL
                    )
                """
                )

                # Insert data
                await conn.execute(
                    "INSERT INTO test_table (name) VALUES ($1)", "test_value"
                )

                # Query data
                row = await conn.fetchrow(
                    "SELECT * FROM test_table WHERE name = $1", "test_value"
                )

                assert row is not None
                assert row["name"] == "test_value"

            finally:
                await conn.close()

    @pytest.mark.asyncio
    async def test_redis_integration(self):
        """Test Redis container integration."""
        container = TestContainers.get_redis_container()

        with container:
            # Wait for container to be ready
            is_ready = await ContainerHealthCheck.wait_for_redis(container)
            assert is_ready, "Redis container failed to start"

            # Connect and test
            host = container.get_container_host_ip()
            port = container.get_exposed_port(6379)

            client = await aioredis.from_url(
                f"redis://{host}:{port}", decode_responses=True
            )

            try:
                # Test basic operations
                await client.set("test_key", "test_value")
                value = await client.get("test_key")
                assert value == "test_value"

                # Test list operations
                await client.lpush("test_list", "item1", "item2", "item3")
                items = await client.lrange("test_list", 0, -1)
                assert len(items) == 3

                # Test pub/sub
                pubsub = client.pubsub()
                await pubsub.subscribe("test_channel")

                # Publish message
                await client.publish("test_channel", "test_message")

            finally:
                await client.close()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_timescaledb_features(self):
        """Test TimescaleDB specific features."""
        container = TestContainers.get_postgres_container()

        with container:
            is_ready = await ContainerHealthCheck.wait_for_postgres(container)
            assert is_ready

            url = container.get_connection_url().replace("psycopg2", "asyncpg")
            conn = await asyncpg.connect(url)

            try:
                # Enable TimescaleDB extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

                # Create hypertable
                await conn.execute(
                    """
                    CREATE TABLE sensor_data (
                        time TIMESTAMPTZ NOT NULL,
                        sensor_id INTEGER,
                        temperature DOUBLE PRECISION,
                        humidity DOUBLE PRECISION
                    )
                """
                )

                await conn.execute(
                    """
                    SELECT create_hypertable('sensor_data', 'time')
                """
                )

                # Verify hypertable was created
                result = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM timescaledb_information.hypertables
                    WHERE hypertable_name = 'sensor_data'
                """
                )

                assert result == 1

            finally:
                await conn.close()
