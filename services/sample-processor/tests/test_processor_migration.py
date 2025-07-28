"""Tests for sample processor migration to ProcessorClient."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as aioredis


class TestSampleProcessorMigration:
    """Test suite for ProcessorClient migration."""

    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis client."""
        redis_mock = AsyncMock(spec=aioredis.Redis)
        redis_mock.xgroup_create = AsyncMock()
        redis_mock.xreadgroup = AsyncMock(return_value=[])
        redis_mock.xack = AsyncMock()
        redis_mock.xadd = AsyncMock()
        redis_mock.close = AsyncMock()
        return redis_mock

    @pytest.fixture
    async def mock_http_client(self):
        """Mock HTTP client."""
        client_mock = AsyncMock()
        client_mock.post = AsyncMock()
        client_mock.aclose = AsyncMock()
        return client_mock

    @pytest.mark.asyncio
    async def test_sample_processor_with_client(self, mock_redis, mock_http_client):
        """Test sample processor using ProcessorClient."""
        # Import here to avoid import errors if file doesn't exist yet
        from services.sample_processor.src.main import SampleProcessor

        # Mock successful registration
        mock_http_client.post.return_value = AsyncMock(status_code=200)

        with patch("aioredis.create_redis", return_value=mock_redis):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                processor = SampleProcessor(
                    processor_id="sample-processor-1",
                    orchestrator_url="http://localhost:8002",
                    capabilities=["sample_processing"],
                )

                # Test registration
                registered = await processor.register()
                assert registered

                # Verify registration call
                mock_http_client.post.assert_called_with(
                    "http://localhost:8002/processors/register",
                    json={
                        "processor_id": "sample-processor-1",
                        "capabilities": ["sample_processing"],
                        "queue": "frames:ready:sample-processor-1",
                    },
                )

                # Test frame processing
                frame_data = {
                    b"frame_id": b"test_123",
                    b"camera_id": b"cam01",
                    b"metadata": b'{"test": true}',
                }

                result = await processor.process_frame(frame_data)

                assert result["frame_id"] == "test_123"
                assert result["camera_id"] == "cam01"
                assert result["processed"] is True
                assert "processing_time" in result
                assert result["processor_id"] == "sample-processor-1"

    @pytest.mark.asyncio
    async def test_processor_client_reconnection(self, mock_redis, mock_http_client):
        """Test automatic reconnection on orchestrator failure."""
        from services.sample_processor.src.main import SampleProcessor

        # First attempt fails, second succeeds
        mock_http_client.post.side_effect = [
            ConnectionError("Connection refused"),
            AsyncMock(status_code=200),
        ]

        with patch("aioredis.create_redis", return_value=mock_redis):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                processor = SampleProcessor(
                    processor_id="test-proc", orchestrator_url="http://localhost:8002"
                )

                # Should retry and succeed
                registered = await processor.register()
                assert registered

                # Verify retry happened
                assert mock_http_client.post.call_count == 2
                assert processor._retry_count == 0  # Reset after success

    @pytest.mark.asyncio
    async def test_processor_consumes_from_stream(self, mock_redis, mock_http_client):
        """Test processor consumes frames from dedicated stream."""
        from services.sample_processor.src.main import SampleProcessor

        # Mock registration success
        mock_http_client.post.return_value = AsyncMock(status_code=200)

        # Mock stream messages
        test_frame = {
            b"frame_id": b"stream_test_1",
            b"camera_id": b"cam01",
            b"timestamp": b"1234567890",
        }

        mock_redis.xreadgroup.return_value = [
            (b"frames:ready:test-proc", [(b"123-0", test_frame)])
        ]

        with patch("aioredis.create_redis", return_value=mock_redis):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                processor = SampleProcessor(
                    processor_id="test-proc", orchestrator_url="http://localhost:8002"
                )

                # Start processor
                await processor.start()

                # Give consumer loop time to run
                await asyncio.sleep(0.1)

                # Verify stream consumption
                mock_redis.xreadgroup.assert_called()
                call_args = mock_redis.xreadgroup.call_args

                # Check consumer group and stream
                assert call_args[0][0] == "frame-processors"  # consumer group
                assert call_args[0][1] == "test-proc"  # consumer name
                assert "frames:ready:test-proc" in call_args[0][2]  # stream key

                # Stop processor
                await processor.stop()

    @pytest.mark.asyncio
    async def test_processor_heartbeat(self, mock_redis, mock_http_client):
        """Test processor sends heartbeats."""
        from services.sample_processor.src.main import SampleProcessor

        # Mock registration success
        mock_http_client.post.return_value = AsyncMock(status_code=200)

        with patch("aioredis.create_redis", return_value=mock_redis):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                processor = SampleProcessor(
                    processor_id="heartbeat-test",
                    orchestrator_url="http://localhost:8002",
                    heartbeat_interval=1,  # 1 second for test
                )

                await processor.start()

                # Wait for heartbeat
                await asyncio.sleep(1.5)

                # Check heartbeat was sent
                heartbeat_calls = [
                    call
                    for call in mock_http_client.post.call_args_list
                    if "heartbeat" in str(call)
                ]

                assert len(heartbeat_calls) >= 1

                # Verify heartbeat payload
                for call in heartbeat_calls:
                    if "/processors/heartbeat" in call[0][0]:
                        payload = call[1]["json"]
                        assert payload["processor_id"] == "heartbeat-test"
                        assert payload["status"] == "healthy"
                        assert "timestamp" in payload

                await processor.stop()

    @pytest.mark.asyncio
    async def test_no_polling_behavior(self, mock_redis, mock_http_client):
        """Verify processor doesn't use old polling pattern."""
        from services.sample_processor.src.main import SampleProcessor

        # Mock registration
        mock_http_client.post.return_value = AsyncMock(status_code=200)
        mock_http_client.get = AsyncMock()  # Should not be called

        with patch("aioredis.create_redis", return_value=mock_redis):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                processor = SampleProcessor(
                    processor_id="no-polling-test",
                    orchestrator_url="http://localhost:8002",
                )

                await processor.start()
                await asyncio.sleep(0.5)

                # Verify no GET requests (polling)
                mock_http_client.get.assert_not_called()

                # Verify only POST requests (registration/heartbeat)
                assert all(
                    call[0][0].endswith(("/register", "/heartbeat", "/unregister"))
                    for call in mock_http_client.post.call_args_list
                )

                await processor.stop()

    @pytest.mark.asyncio
    async def test_result_publishing(self, mock_redis, mock_http_client):
        """Test processor publishes results to result stream."""
        from services.sample_processor.src.main import SampleProcessor

        mock_http_client.post.return_value = AsyncMock(status_code=200)

        with patch("aioredis.create_redis", return_value=mock_redis):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                processor = SampleProcessor(
                    processor_id="result-test",
                    orchestrator_url="http://localhost:8002",
                    result_stream="sample:results",
                )

                # Process frame directly
                frame_data = {b"frame_id": b"result_test_1", b"camera_id": b"cam01"}

                # Process and publish result
                await processor._process_frame_wrapper(
                    b"msg-123", frame_data, "frames:ready:result-test"
                )

                # Verify result was published
                mock_redis.xadd.assert_called_once()
                call_args = mock_redis.xadd.call_args

                assert call_args[0][0] == "sample:results"  # stream name
                result_data = call_args[0][1]
                assert result_data["frame_id"] == "result_test_1"
                assert result_data["processor_id"] == "result-test"
                assert "result" in result_data
