"""Tests for processor client library."""

import asyncio
import json
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
import redis.asyncio as aioredis
from aioresponses import aioresponses

from src.processors.client import ProcessorClient

# Enable debug logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestProcessor(ProcessorClient):
    """Test processor implementation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processed_frames = []
        self.processing_error = None

    async def process_frame(self, frame_data: dict) -> dict:
        """Process a frame."""
        if self.processing_error:
            raise self.processing_error

        self.processed_frames.append(frame_data[b"frame_id"])
        return {"result": "processed", "frame_id": frame_data[b"frame_id"].decode()}


@pytest.mark.asyncio
async def test_processor_client():
    """Test processor client library."""
    # Test registration
    processor = TestProcessor(
        processor_id="test-proc",
        capabilities=["test_capability"],
        orchestrator_url="http://localhost:8002",
    )

    # Mock the http client
    mock_response = AsyncMock()
    mock_response.status_code = 201
    mock_response.text = "Created"

    processor.http_client.post = AsyncMock(return_value=mock_response)

    await processor.register()

    # Verify registration request
    processor.http_client.post.assert_called_once()
    call_args = processor.http_client.post.call_args
    assert call_args[0][0] == "http://localhost:8002/processors/register"

    json_data = call_args[1]["json"]
    assert json_data["id"] == "test-proc"
    assert json_data["capabilities"] == ["test_capability"]


@pytest.mark.asyncio
async def test_frame_consumption(redis_client):
    """Test frame consumption and processing."""
    processor = TestProcessor(
        processor_id="test-proc",
        capabilities=["test_capability"],
        orchestrator_url="http://localhost:8002",
        redis_client=redis_client,
    )

    # Check processor group name
    print(f"Processor group name: {processor.group_name}")
    print(f"Processor consumer name: {processor.consumer_name}")
    print(f"Processor queue name: {processor.queue_name}")

    # Add frame to processor queue first (creates the stream)
    await redis_client.xadd(
        "frames:ready:test-proc",
        {
            "frame_id": "test_frame_1",
            "camera_id": "cam1",
            "trace_context": json.dumps({"trace_id": "abc123"}),
            "data": "frame_data",
        },
    )

    # Create consumer group after stream exists
    try:
        await redis_client.xgroup_create(
            "frames:ready:test-proc", processor.group_name, id="0"
        )
    except aioredis.ResponseError as e:
        print(f"Group creation error: {e}")

    # Check if message is in stream
    messages = await redis_client.xrange("frames:ready:test-proc", count=10)
    print(f"Messages in stream: {messages}")

    # Check consumer group info
    groups = await redis_client.xinfo_groups("frames:ready:test-proc")
    print(f"Consumer groups: {groups}")

    # Start processor (with timeout for test)
    processor._running = True  # Set the running flag
    consume_task = asyncio.create_task(processor._consume_frames())
    await asyncio.sleep(2.0)  # Give more time to process
    processor.stop()

    try:
        await asyncio.wait_for(consume_task, timeout=1.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    # Verify processing
    assert b"test_frame_1" in processor.processed_frames


@pytest.mark.asyncio
async def test_health_reporting():
    """Test health endpoint and reporting."""
    processor = TestProcessor(
        processor_id="test-proc",
        capabilities=["test_capability"],
        orchestrator_url="http://localhost:8002",
        health_port=8080,
    )

    # Mock health endpoint
    async def health_handler(request):
        return {
            "status": "healthy",
            "frames_processed": len(processor.processed_frames),
        }

    processor._health_handler = health_handler

    # Start health reporter
    report_task = asyncio.create_task(processor._health_reporter())

    # Give it time to report
    await asyncio.sleep(0.1)

    processor.stop()
    report_task.cancel()

    try:
        await report_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_error_handling(redis_client):
    """Test error handling during processing."""
    processor = TestProcessor(
        processor_id="test-proc",
        capabilities=["test_capability"],
        orchestrator_url="http://localhost:8002",
        redis_client=redis_client,
    )

    # Set processing to fail
    processor.processing_error = ValueError("Test error")

    # Add frame
    await redis_client.xadd(
        "frames:ready:test-proc",
        {
            "frame_id": "error_frame",
            "trace_context": json.dumps({"trace_id": "error123"}),
        },
    )

    # Create consumer group
    try:
        await redis_client.xgroup_create(
            "frames:ready:test-proc", processor.group_name, id="0"
        )
    except aioredis.ResponseError:
        pass

    # Try to process
    processor._running = True
    consume_task = asyncio.create_task(processor._consume_frames())
    await asyncio.sleep(0.5)
    processor.stop()

    try:
        await consume_task
    except asyncio.CancelledError:
        pass

    # Frame should not be processed
    assert b"error_frame" not in processor.processed_frames


@pytest.mark.asyncio
async def test_graceful_shutdown():
    """Test graceful shutdown."""
    processor = TestProcessor(
        processor_id="test-proc",
        capabilities=["test_capability"],
        orchestrator_url="http://localhost:8002",
    )

    # Mock HTTP client methods
    mock_post_response = AsyncMock()
    mock_post_response.status_code = 201
    mock_post_response.text = "Created"

    mock_delete_response = AsyncMock()
    mock_delete_response.status_code = 204

    processor.http_client.post = AsyncMock(return_value=mock_post_response)
    processor.http_client.delete = AsyncMock(return_value=mock_delete_response)
    processor.http_client.aclose = AsyncMock()

    # Mock redis
    processor.redis = AsyncMock()
    processor.redis.xgroup_create = AsyncMock()
    processor.redis.xreadgroup = AsyncMock(return_value=[])  # No messages
    processor.redis.aclose = AsyncMock()

    # Start processor
    start_task = asyncio.create_task(processor.start())

    # Give it time to start
    await asyncio.sleep(0.2)

    # Stop processor
    processor.stop()

    # Wait for task to complete
    try:
        await asyncio.wait_for(start_task, timeout=2.0)
    except asyncio.TimeoutError:
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    # Should have called unregister
    processor.http_client.delete.assert_called_once_with(
        "http://localhost:8002/processors/test-proc"
    )


@pytest.mark.asyncio
async def test_result_publishing(redis_client):
    """Test publishing processing results."""
    processor = TestProcessor(
        processor_id="test-proc",
        capabilities=["test_capability"],
        orchestrator_url="http://localhost:8002",
        redis_client=redis_client,
        result_stream="frames:processed",
    )

    # Manually call publish result
    result = {
        "frame_id": "test_123",
        "processor_id": "test-proc",
        "result": "face_detected",
        "confidence": 0.95,
    }

    msg_id = await processor.publish_result(result)
    assert msg_id is not None

    # Verify in Redis
    messages = await redis_client.xrange("frames:processed", count=1)
    assert len(messages) == 1

    msg_data = messages[0][1]
    assert msg_data[b"frame_id"] == b"test_123"
    assert msg_data[b"processor_id"] == b"test-proc"


@pytest.mark.asyncio
async def test_capacity_management():
    """Test processor capacity reporting."""
    processor = TestProcessor(
        processor_id="test-proc",
        capabilities=["test_capability"],
        orchestrator_url="http://localhost:8002",
        capacity=10,
    )

    # Check initial capacity
    assert processor.capacity == 10
    assert processor.get_available_capacity() == 10

    # Simulate processing
    processor._active_tasks = 5
    assert processor.get_available_capacity() == 5

    # Should reject when at capacity
    processor._active_tasks = 10
    assert processor.get_available_capacity() == 0
    assert processor.is_at_capacity() is True


@pytest.mark.asyncio
async def test_metrics_collection():
    """Test metrics collection."""
    processor = TestProcessor(
        processor_id="test-proc",
        capabilities=["test_capability"],
        orchestrator_url="http://localhost:8002",
    )

    # Process some frames
    processor.processed_frames = [b"frame1", b"frame2", b"frame3"]
    processor._frames_total = 3  # Update the internal counter

    # Get metrics
    metrics = processor.get_metrics()

    assert metrics["processor_id"] == "test-proc"
    assert metrics["frames_processed"] == 3
    assert metrics["capacity"] == processor.capacity
    assert "uptime_seconds" in metrics
    assert "errors_total" in metrics


@pytest.mark.asyncio
async def test_configuration_reload():
    """Test configuration reloading."""
    processor = TestProcessor(
        processor_id="test-proc",
        capabilities=["test_capability"],
        orchestrator_url="http://localhost:8002",
    )

    # Update configuration
    new_config = {"capacity": 20, "capabilities": ["test_capability", "new_capability"]}

    # Mock update endpoint
    mock_response = AsyncMock()
    mock_response.status_code = 200
    processor.http_client.put = AsyncMock(return_value=mock_response)

    await processor.update_configuration(new_config)

    assert processor.capacity == 20
    assert "new_capability" in processor.capabilities
