"""Test Redis connectivity for integration tests"""

import os
import pytest
import redis
from unittest.mock import patch


def test_redis_connection_params() -> None:
    """Test that Redis connection parameters are properly configured"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    assert isinstance(redis_host, str)
    assert isinstance(redis_port, int)
    assert 0 < redis_port < 65536


@pytest.mark.skipif(
    os.getenv("CI") == "true" and not os.getenv("REDIS_HOST"),
    reason="Redis not available in this CI environment"
)
def test_redis_ping() -> None:
    """Test Redis connectivity with ping command"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    try:
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            socket_connect_timeout=5
        )
        response = client.ping()
        assert response is True
    except redis.ConnectionError:
        # In CI without Redis service, this is expected
        if os.getenv("CI") == "true":
            pytest.skip("Redis not available in CI")
        else:
            raise