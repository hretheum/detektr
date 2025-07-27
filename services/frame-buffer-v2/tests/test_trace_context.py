"""Tests for trace context propagation."""

import json
from datetime import datetime
from typing import Dict

import pytest
import redis.asyncio as aioredis

from src.models import FrameReadyEvent
from src.orchestrator.consumer import StreamConsumer
from src.orchestrator.queue_manager import WorkQueueManager
from src.orchestrator.trace_context import TraceContext, TraceContextManager


@pytest.mark.asyncio
async def test_trace_context_creation():
    """Test trace context creation and serialization."""
    # Create new trace context
    ctx = TraceContext.create()

    assert ctx.trace_id is not None
    assert ctx.span_id is not None
    assert ctx.parent_span_id is None
    assert ctx.trace_flags == "01"  # Sampled
    assert ctx.trace_state == {}

    # Test serialization
    serialized = ctx.to_dict()
    assert "trace_id" in serialized
    assert "span_id" in serialized
    assert "trace_flags" in serialized

    # Test deserialization
    ctx2 = TraceContext.from_dict(serialized)
    assert ctx2.trace_id == ctx.trace_id
    assert ctx2.span_id == ctx.span_id
    assert ctx2.trace_flags == ctx.trace_flags


@pytest.mark.asyncio
async def test_trace_context_child_span():
    """Test creating child spans."""
    # Create parent context
    parent = TraceContext.create()

    # Create child span
    child = parent.create_child_span()

    assert child.trace_id == parent.trace_id  # Same trace
    assert child.span_id != parent.span_id  # Different span
    assert child.parent_span_id == parent.span_id  # Parent reference
    assert child.trace_flags == parent.trace_flags  # Inherit flags


@pytest.mark.asyncio
async def test_trace_context_propagation_in_frame_event():
    """Test trace context in frame events."""
    # Create frame with trace context
    ctx = TraceContext.create()

    frame = FrameReadyEvent(
        frame_id="test_frame_1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context=ctx.to_dict(),
    )

    # Verify serialization
    frame_json = frame.to_json()
    assert "trace_context" in frame_json
    assert frame_json["trace_context"]["trace_id"] == ctx.trace_id

    # Verify deserialization
    frame2 = FrameReadyEvent.from_json(frame_json)
    assert frame2.trace_context["trace_id"] == ctx.trace_id


@pytest.mark.asyncio
async def test_trace_context_manager():
    """Test trace context manager functionality."""
    manager = TraceContextManager()

    # Test context creation
    ctx = manager.create_context()
    assert ctx.trace_id is not None

    # Test context extraction from headers
    headers = {"traceparent": f"00-{ctx.trace_id}-{ctx.span_id}-01"}

    extracted = manager.extract_from_headers(headers)
    assert extracted.trace_id == ctx.trace_id
    assert extracted.span_id == ctx.span_id

    # Test context injection to headers
    headers = {}
    manager.inject_to_headers(ctx, headers)
    assert "traceparent" in headers
    assert ctx.trace_id in headers["traceparent"]


@pytest.mark.asyncio
async def test_trace_context_in_stream_consumer(redis_client):
    """Test trace context propagation through stream consumer."""
    # Create consumer with trace context support
    consumer = StreamConsumer(
        redis_client=redis_client,
        stream="test:stream",
        group="test-group",
        consumer_id="test-consumer",
    )

    # Add message with trace context
    ctx = TraceContext.create()
    message_data = {"frame_id": "test_123", "trace_context": json.dumps(ctx.to_dict())}

    await redis_client.xadd("test:stream", message_data)

    # Create consumer group
    try:
        await redis_client.xgroup_create("test:stream", "test-group", id="0")
    except aioredis.ResponseError:
        pass

    # Consume and verify trace context
    messages = []
    async for msg in consumer.consume(max_count=1):
        messages.append(msg)
        if len(messages) >= 1:
            break

    assert len(messages) == 1
    trace_data = json.loads(messages[0][b"trace_context"])
    assert trace_data["trace_id"] == ctx.trace_id


@pytest.mark.asyncio
async def test_trace_context_in_work_queue(redis_client):
    """Test trace context propagation through work queues."""
    manager = WorkQueueManager(redis_client)

    # Create trace context
    ctx = TraceContext.create()

    # Create frame with trace context
    frame = FrameReadyEvent(
        frame_id="test_frame",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context=ctx.to_dict(),
    )

    # Enqueue frame
    msg_id = await manager.enqueue("test-processor", frame)
    assert msg_id is not None

    # Create consumer group
    await manager.create_consumer_group("test-processor", "test-group")

    # Consume and verify trace context
    messages = await manager.consume(
        "test-processor", "test-group", "consumer-1", count=1
    )

    assert len(messages) == 1
    trace_data = json.loads(messages[0][b"trace_context"])
    assert trace_data["trace_id"] == ctx.trace_id


@pytest.mark.asyncio
async def test_trace_context_metrics():
    """Test trace context with metrics collection."""
    manager = TraceContextManager()

    # Create context with custom attributes
    ctx = manager.create_context()
    ctx.add_attribute("service.name", "frame-buffer")
    ctx.add_attribute("camera.id", "cam1")

    # Verify attributes
    assert ctx.attributes["service.name"] == "frame-buffer"
    assert ctx.attributes["camera.id"] == "cam1"

    # Test context with timing
    import time

    start = time.time()

    # Simulate processing
    await asyncio.sleep(0.1)

    ctx.add_attribute("duration_ms", int((time.time() - start) * 1000))
    assert ctx.attributes["duration_ms"] >= 100


@pytest.mark.asyncio
async def test_trace_context_baggage():
    """Test trace context baggage propagation."""
    manager = TraceContextManager()

    # Create context with baggage
    ctx = manager.create_context()
    ctx.set_baggage("user_id", "12345")
    ctx.set_baggage("session_id", "abc-123")

    # Verify baggage
    assert ctx.get_baggage("user_id") == "12345"
    assert ctx.get_baggage("session_id") == "abc-123"

    # Test baggage in child span
    child = ctx.create_child_span()
    assert child.get_baggage("user_id") == "12345"  # Inherited

    # Test baggage serialization
    headers = {}
    manager.inject_to_headers(ctx, headers)
    assert "baggage" in headers
    assert "user_id=12345" in headers["baggage"]


@pytest.mark.asyncio
async def test_trace_context_sampling():
    """Test trace context sampling decisions."""
    manager = TraceContextManager(sampling_rate=0.5)

    # Create multiple contexts
    sampled_count = 0
    total = 100

    for _ in range(total):
        ctx = manager.create_context()
        if ctx.is_sampled():
            sampled_count += 1

    # Should be approximately 50% sampled (with tolerance for randomness)
    assert 30 <= sampled_count <= 70


@pytest.mark.asyncio
async def test_distributed_tracing_flow():
    """Test complete distributed tracing flow."""
    # 1. RTSP capture creates initial trace
    capture_ctx = TraceContext.create()
    capture_ctx.add_attribute("service.name", "rtsp-capture")
    capture_ctx.add_attribute("camera.id", "cam1")

    # 2. Frame buffer receives trace and creates child span
    buffer_ctx = capture_ctx.create_child_span()
    buffer_ctx.add_attribute("service.name", "frame-buffer")
    buffer_ctx.add_attribute("buffer.size", 1024)

    # 3. Processor receives trace and creates another child
    processor_ctx = buffer_ctx.create_child_span()
    processor_ctx.add_attribute("service.name", "face-detector")
    processor_ctx.add_attribute("faces.detected", 3)

    # Verify trace continuity
    assert capture_ctx.trace_id == buffer_ctx.trace_id == processor_ctx.trace_id
    assert processor_ctx.parent_span_id == buffer_ctx.span_id
    assert buffer_ctx.parent_span_id == capture_ctx.span_id

    # Verify all contexts are sampled
    assert capture_ctx.is_sampled()
    assert buffer_ctx.is_sampled()
    assert processor_ctx.is_sampled()


import asyncio
