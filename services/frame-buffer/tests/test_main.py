"""
Tests for frame buffer service main functionality.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock Redis before importing app
with patch("redis.asyncio.Redis"):
    from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.xlen = AsyncMock(return_value=10)
    mock.xadd = AsyncMock(return_value="1234567890-0")
    mock.xread = AsyncMock(
        return_value=[
            (
                b"frame_queue",
                [
                    (
                        b"1234567890-0",
                        {
                            b"frame_data": json.dumps(
                                {
                                    "frame_id": "test_frame_1",
                                    "timestamp": datetime.now().isoformat(),
                                    "camera_id": "cam1",
                                    "data": "base64_encoded_frame",
                                }
                            ).encode()
                        },
                    )
                ],
            )
        ]
    )
    mock.xack = AsyncMock(return_value=1)
    return mock


class TestHealthCheck:
    """Test health check endpoints."""

    def test_health_endpoint(self, client):
        """Test /health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "uptime" in data

    def test_metrics_endpoint(self, client):
        """Test /metrics endpoint returns Prometheus metrics."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "frame_buffer_frames_total" in response.text
        assert "frame_buffer_queue_size" in response.text


class TestFrameOperations:
    """Test frame enqueue/dequeue operations."""

    @patch("main.redis_client")
    async def test_enqueue_frame_success(self, mock_redis_client, client):
        """Test successful frame enqueue."""
        mock_redis_client.xlen = AsyncMock(return_value=50)
        mock_redis_client.xadd = AsyncMock(return_value="1234567890-0")

        frame_data = {
            "frame_id": "test_123",
            "timestamp": datetime.now().isoformat(),
            "camera_id": "cam1",
            "data": "base64_frame_data",
        }

        response = client.post("/frames/enqueue", json=frame_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "enqueued"
        assert data["frame_id"] == "test_123"
        assert "queue_size" in data

    @patch("main.redis_client")
    async def test_enqueue_frame_buffer_full(self, mock_redis_client, client):
        """Test enqueue when buffer is full."""
        mock_redis_client.xlen = AsyncMock(return_value=1001)  # Over max size

        frame_data = {
            "frame_id": "test_456",
            "timestamp": datetime.now().isoformat(),
            "camera_id": "cam1",
            "data": "base64_frame_data",
        }

        response = client.post("/frames/enqueue", json=frame_data)
        assert response.status_code == 503
        data = response.json()
        assert "Buffer full" in data["detail"]

    @patch("main.redis_client")
    async def test_dequeue_frames_success(self, mock_redis_client, client):
        """Test successful frame dequeue."""
        mock_redis_client.xread = AsyncMock(
            return_value=[
                (
                    b"frame_queue",
                    [
                        (
                            b"1234567890-0",
                            {
                                b"frame_data": json.dumps(
                                    {
                                        "frame_id": "frame_1",
                                        "timestamp": datetime.now().isoformat(),
                                        "camera_id": "cam1",
                                        "data": "base64_data_1",
                                    }
                                ).encode()
                            },
                        ),
                        (
                            b"1234567891-0",
                            {
                                b"frame_data": json.dumps(
                                    {
                                        "frame_id": "frame_2",
                                        "timestamp": datetime.now().isoformat(),
                                        "camera_id": "cam1",
                                        "data": "base64_data_2",
                                    }
                                ).encode()
                            },
                        ),
                    ],
                )
            ]
        )
        mock_redis_client.xack = AsyncMock(return_value=2)

        response = client.get("/frames/dequeue?count=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["frames"]) == 2
        assert data["frames"][0]["frame_id"] == "frame_1"
        assert data["frames"][1]["frame_id"] == "frame_2"

    @patch("main.redis_client")
    async def test_dequeue_frames_empty(self, mock_redis_client, client):
        """Test dequeue when queue is empty."""
        mock_redis_client.xread = AsyncMock(return_value=[])

        response = client.get("/frames/dequeue")
        assert response.status_code == 200
        data = response.json()
        assert data["frames"] == []
        assert data["count"] == 0


class TestBufferStatus:
    """Test buffer status endpoints."""

    @patch("main.redis_client")
    async def test_buffer_status(self, mock_redis_client, client):
        """Test buffer status endpoint."""
        mock_redis_client.xlen = AsyncMock(side_effect=[75, 5])  # queue, dlq
        mock_redis_client.memory_usage = AsyncMock(return_value=1024000)

        response = client.get("/frames/status")
        assert response.status_code == 200
        data = response.json()
        assert data["size"] == 75
        assert data["dlq_size"] == 5
        assert data["max_size"] == 1000
        assert data["usage_percent"] == 7.5

    @patch("main.redis_client")
    async def test_clear_dlq(self, mock_redis_client, client):
        """Test clearing DLQ."""
        mock_redis_client.delete = AsyncMock(return_value=1)

        response = client.post("/frames/dlq/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
        assert data["message"] == "DLQ cleared successfully"


class TestRedisConnection:
    """Test Redis connection handling."""

    @patch("main.redis_client")
    async def test_redis_connection_failure(self, mock_redis_client, client):
        """Test handling of Redis connection failure."""
        mock_redis_client.xlen = AsyncMock(side_effect=Exception("Connection refused"))

        frame_data = {
            "frame_id": "test_789",
            "timestamp": datetime.now().isoformat(),
            "camera_id": "cam1",
            "data": "base64_frame_data",
        }

        response = client.post("/frames/enqueue", json=frame_data)
        assert response.status_code == 500


@pytest.mark.asyncio
async def test_frame_compression():
    """Test frame data compression."""
    from main import compress_frame, decompress_frame

    test_data = {"large": "x" * 10000}
    compressed = compress_frame(test_data)
    decompressed = decompress_frame(compressed)

    assert decompressed == test_data
    assert len(compressed) < len(json.dumps(test_data))
