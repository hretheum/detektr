"""Test container configurations and helpers."""

import os
from typing import Any, Dict

from testcontainers.compose import DockerCompose
from testcontainers.kafka import KafkaContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer


class TestContainers:
    """Manage test containers for integration testing."""

    @staticmethod
    def get_postgres_container() -> PostgresContainer:
        """Create configured PostgreSQL container."""
        container = PostgresContainer(
            image="timescale/timescaledb:latest-pg15",
            user="test_user",
            password="test_pass",
            dbname="test_detektor",
        )
        container.with_env("POSTGRES_INITDB_ARGS", "--encoding=UTF8")
        return container

    @staticmethod
    def get_redis_container() -> RedisContainer:
        """Create configured Redis container."""
        container = RedisContainer(image="redis:7-alpine")
        container.with_command("redis-server --appendonly yes")
        return container

    @staticmethod
    def get_kafka_container() -> KafkaContainer:
        """Create configured Kafka container."""
        container = KafkaContainer(image="confluentinc/cp-kafka:7.5.0")
        return container

    @staticmethod
    def get_observability_stack() -> DockerCompose:
        """Create observability stack for integration tests."""
        compose_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docker-compose.observability.yml"
        )

        return DockerCompose(
            filepath=os.path.dirname(compose_path),
            compose_file_name=os.path.basename(compose_path),
            pull=True,
            build=False,
        )


class ContainerHealthCheck:
    """Health check utilities for containers."""

    @staticmethod
    async def wait_for_postgres(
        container: PostgresContainer, timeout: int = 30
    ) -> bool:
        """Wait for PostgreSQL to be ready."""
        import asyncio

        import asyncpg

        url = container.get_connection_url().replace("psycopg2", "asyncpg")

        for _ in range(timeout):
            try:
                conn = await asyncpg.connect(url)
                await conn.fetchval("SELECT 1")
                await conn.close()
                return True
            except Exception:
                await asyncio.sleep(1)

        return False

    @staticmethod
    async def wait_for_redis(container: RedisContainer, timeout: int = 30) -> bool:
        """Wait for Redis to be ready."""
        import asyncio

        import aioredis

        host = container.get_container_host_ip()
        port = container.get_exposed_port(6379)

        for _ in range(timeout):
            try:
                client = await aioredis.from_url(f"redis://{host}:{port}")
                await client.ping()
                await client.close()
                return True
            except Exception:
                await asyncio.sleep(1)

        return False


def get_container_env_vars(container_name: str) -> Dict[str, str]:
    """Get environment variables for a specific container."""
    env_vars = {
        "postgres": {
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": "test_detektor",
            "DB_USER": "test_user",
            "DB_PASS": "test_pass",
        },
        "redis": {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "0",
        },
        "kafka": {
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "KAFKA_TOPIC_PREFIX": "test_",
        },
    }

    return env_vars.get(container_name, {})
