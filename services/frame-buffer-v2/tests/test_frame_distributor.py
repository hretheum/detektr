"""Tests for frame distributor logic."""

from datetime import datetime

import pytest

from src.models import FrameReadyEvent
from src.orchestrator.distributor import FrameDistributor
from src.orchestrator.processor_registry import ProcessorInfo, ProcessorRegistry


@pytest.mark.asyncio
async def test_frame_distribution(redis_client):
    """Test basic frame distribution logic."""
    registry = ProcessorRegistry(redis_client)
    distributor = FrameDistributor(registry)

    # Register two processors
    await registry.register(
        ProcessorInfo(id="proc1", capabilities=["face_detection"], capacity=10)
    )
    await registry.register(
        ProcessorInfo(id="proc2", capabilities=["object_detection"], capacity=10)
    )

    # Test distribution
    face_frame = FrameReadyEvent(
        frame_id="f1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={},
        metadata={"detection_type": "face_detection"},
    )

    processor = await distributor.select_processor(face_frame)
    assert processor is not None
    assert processor.id == "proc1"


@pytest.mark.asyncio
async def test_capability_based_selection(redis_client):
    """Test processor selection based on capabilities."""
    registry = ProcessorRegistry(redis_client)
    distributor = FrameDistributor(registry)

    # Register processors with different capabilities
    await registry.register(
        ProcessorInfo(
            id="face-proc",
            capabilities=["face_detection", "emotion_detection"],
            capacity=10,
        )
    )
    await registry.register(
        ProcessorInfo(id="object-proc", capabilities=["object_detection"], capacity=10)
    )
    await registry.register(
        ProcessorInfo(
            id="vehicle-proc", capabilities=["vehicle_detection"], capacity=10
        )
    )

    # Test different frame types
    frames = [
        (
            FrameReadyEvent(
                frame_id="f1",
                camera_id="cam1",
                timestamp=datetime.now(),
                size_bytes=1024,
                width=1920,
                height=1080,
                format="jpeg",
                trace_context={},
                metadata={"detection_type": "face_detection"},
            ),
            "face-proc",
        ),
        (
            FrameReadyEvent(
                frame_id="f2",
                camera_id="cam1",
                timestamp=datetime.now(),
                size_bytes=1024,
                width=1920,
                height=1080,
                format="jpeg",
                trace_context={},
                metadata={"detection_type": "object_detection"},
            ),
            "object-proc",
        ),
        (
            FrameReadyEvent(
                frame_id="f3",
                camera_id="cam1",
                timestamp=datetime.now(),
                size_bytes=1024,
                width=1920,
                height=1080,
                format="jpeg",
                trace_context={},
                metadata={"detection_type": "vehicle_detection"},
            ),
            "vehicle-proc",
        ),
    ]

    for frame, expected_proc in frames:
        processor = await distributor.select_processor(frame)
        assert processor is not None
        assert processor.id == expected_proc


@pytest.mark.asyncio
async def test_no_capable_processor(redis_client):
    """Test when no processor can handle the frame."""
    registry = ProcessorRegistry(redis_client)
    distributor = FrameDistributor(registry)

    # Register processor without needed capability
    await registry.register(
        ProcessorInfo(id="proc1", capabilities=["face_detection"], capacity=10)
    )

    # Frame requires different capability
    frame = FrameReadyEvent(
        frame_id="f1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={},
        metadata={"detection_type": "license_plate_detection"},
    )

    processor = await distributor.select_processor(frame)
    assert processor is None


@pytest.mark.asyncio
async def test_load_balancing(redis_client):
    """Test load balancing between multiple capable processors."""
    registry = ProcessorRegistry(redis_client)
    distributor = FrameDistributor(registry)

    # Register multiple processors with same capability
    for i in range(3):
        await registry.register(
            ProcessorInfo(
                id=f"face-proc-{i}", capabilities=["face_detection"], capacity=100
            )
        )

    # Distribute many frames
    results = {}
    for i in range(90):
        frame = FrameReadyEvent(
            frame_id=f"f{i}",
            camera_id="cam1",
            timestamp=datetime.now(),
            size_bytes=1024,
            width=1920,
            height=1080,
            format="jpeg",
            trace_context={},
            metadata={"detection_type": "face_detection"},
        )

        processor = await distributor.select_processor(frame)
        assert processor is not None

        if processor.id not in results:
            results[processor.id] = 0
        results[processor.id] += 1

    # Check distribution is reasonably balanced
    # Each processor should get roughly 30 frames (±10)
    for proc_id, count in results.items():
        assert 20 <= count <= 40, f"Processor {proc_id} got {count} frames"


@pytest.mark.asyncio
async def test_frame_dispatch(redis_client):
    """Test actual frame dispatch to processor queue."""
    registry = ProcessorRegistry(redis_client)
    distributor = FrameDistributor(registry, redis_client)

    # Register processor
    await registry.register(
        ProcessorInfo(
            id="test-proc",
            capabilities=["face_detection"],
            capacity=10,
            queue="frames:ready:test-proc",
        )
    )

    # Create and distribute frame
    frame = FrameReadyEvent(
        frame_id="test-frame-1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={"trace_id": "123"},
        metadata={"detection_type": "face_detection"},
    )

    success = await distributor.distribute_frame(frame)
    assert success is True

    # Verify frame was added to processor queue
    queue_length = await redis_client.xlen("frames:ready:test-proc")
    assert queue_length == 1

    # Read the frame from queue
    messages = await redis_client.xread({"frames:ready:test-proc": 0}, count=1)
    assert len(messages) == 1

    stream_name, stream_messages = messages[0]
    assert stream_name == "frames:ready:test-proc"
    assert len(stream_messages) == 1

    msg_id, data = stream_messages[0]
    assert data["frame_id"] == "test-frame-1"
    assert data["camera_id"] == "cam1"


@pytest.mark.asyncio
async def test_processor_capacity_check(redis_client):
    """Test that distributor respects processor capacity."""
    registry = ProcessorRegistry(redis_client)
    distributor = FrameDistributor(registry, redis_client)

    # Register processor with low capacity
    await registry.register(
        ProcessorInfo(
            id="low-cap-proc",
            capabilities=["face_detection"],
            capacity=2,  # Very low capacity
            queue="frames:ready:low-cap",
        )
    )

    # Also register high capacity processor
    await registry.register(
        ProcessorInfo(
            id="high-cap-proc",
            capabilities=["face_detection"],
            capacity=100,
            queue="frames:ready:high-cap",
        )
    )

    # Simulate low capacity processor being busy
    # Add frames to its queue
    for i in range(3):
        await redis_client.xadd("frames:ready:low-cap", {"frame_id": f"existing-{i}"})

    # Now distribute new frames
    results = {"low-cap-proc": 0, "high-cap-proc": 0}

    for i in range(10):
        frame = FrameReadyEvent(
            frame_id=f"new-frame-{i}",
            camera_id="cam1",
            timestamp=datetime.now(),
            size_bytes=1024,
            width=1920,
            height=1080,
            format="jpeg",
            trace_context={},
            metadata={"detection_type": "face_detection"},
        )

        processor = await distributor.select_processor(frame)
        if processor:
            results[processor.id] += 1

    # Most frames should go to high capacity processor
    assert results["high-cap-proc"] > results["low-cap-proc"]


@pytest.mark.asyncio
async def test_distribute_with_priority(redis_client):
    """Test frame distribution respects priority."""
    registry = ProcessorRegistry(redis_client)
    distributor = FrameDistributor(registry, redis_client)

    await registry.register(
        ProcessorInfo(id="proc1", capabilities=["detection"], capacity=10)
    )

    # High priority frame
    high_priority_frame = FrameReadyEvent(
        frame_id="high-1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={},
        priority=9,  # High priority
        metadata={"detection_type": "detection"},
    )

    # Low priority frame
    low_priority_frame = FrameReadyEvent(
        frame_id="low-1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={},
        priority=1,  # Low priority
        metadata={"detection_type": "detection"},
    )

    # Distribute both
    await distributor.distribute_frame(low_priority_frame)
    await distributor.distribute_frame(high_priority_frame)

    # Verify frames in queue (high priority should be processed first in real system)
    messages = await redis_client.xread({"frames:ready:proc1": 0}, count=2)
    assert len(messages[0][1]) == 2


@pytest.mark.asyncio
async def test_circuit_breaker(redis_client):
    """Test circuit breaker functionality."""
    registry = ProcessorRegistry(redis_client)
    distributor = FrameDistributor(registry, redis_client)

    # Register two processors
    await registry.register(
        ProcessorInfo(id="failing-proc", capabilities=["detection"], capacity=10)
    )
    await registry.register(
        ProcessorInfo(id="healthy-proc", capabilities=["detection"], capacity=10)
    )

    # Simulate failures for one processor
    distributor.processor_failures["failing-proc"] = [
        datetime.now() for _ in range(5)
    ]  # 5 failures

    # Create frame
    frame = FrameReadyEvent(
        frame_id="test-1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={},
        metadata={"detection_type": "detection"},
    )

    # Should not select failing processor
    processor = await distributor.select_processor(frame)
    assert processor is not None
    assert processor.id == "healthy-proc"


@pytest.mark.asyncio
async def test_no_redis_client():
    """Test behavior when Redis is not available."""
    registry = ProcessorRegistry(None)  # Mock registry without Redis
    distributor = FrameDistributor(registry, redis_client=None)

    # Should be able to select processor
    # but fail on distribution
    frame = FrameReadyEvent(
        frame_id="test",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        trace_context={},
        metadata={"detection_type": "detection"},
    )

    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Redis client required"):
        await distributor.dispatch_to_processor(
            ProcessorInfo(id="test", capabilities=["detection"], capacity=10), frame
        )
