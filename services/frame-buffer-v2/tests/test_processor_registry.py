"""Tests for processor registry with Redis persistence."""

import pytest

from src.orchestrator.processor_registry import ProcessorInfo, ProcessorRegistry


@pytest.mark.asyncio
async def test_processor_registration(redis_client):
    """Test basic processor registration."""
    registry = ProcessorRegistry(redis_client)

    # Register processor
    processor = ProcessorInfo(
        id="test-proc-1",
        capabilities=["face_detection", "emotion_detection"],
        capacity=100,
        queue="frames:ready:test-proc-1",
    )

    success = await registry.register(processor)
    assert success is True

    # Get processor
    retrieved = await registry.get_processor("test-proc-1")
    assert retrieved is not None
    assert retrieved.id == "test-proc-1"
    assert retrieved.capabilities == ["face_detection", "emotion_detection"]


@pytest.mark.asyncio
async def test_duplicate_registration(redis_client):
    """Test duplicate processor registration fails."""
    registry = ProcessorRegistry(redis_client)

    processor = ProcessorInfo(
        id="duplicate-proc", capabilities=["detection"], capacity=50
    )

    # First registration succeeds
    assert await registry.register(processor) is True

    # Duplicate registration fails
    assert await registry.register(processor) is False


@pytest.mark.asyncio
async def test_persistence_across_instances(redis_client):
    """Test registry persists across instances."""
    registry1 = ProcessorRegistry(redis_client)

    # Register with first instance
    processor = ProcessorInfo(
        id="persistent-proc",
        capabilities=["object_detection"],
        capacity=75,
        metadata={"version": "1.0", "gpu": True},
    )
    await registry1.register(processor)

    # Create new instance and verify
    registry2 = ProcessorRegistry(redis_client)
    retrieved = await registry2.get_processor("persistent-proc")

    assert retrieved is not None
    assert retrieved.capabilities == ["object_detection"]
    assert retrieved.metadata["gpu"] is True


@pytest.mark.asyncio
async def test_find_by_capability(redis_client):
    """Test finding processors by capability."""
    registry = ProcessorRegistry(redis_client)

    # Register processors with different capabilities
    await registry.register(
        ProcessorInfo(id="face-proc-1", capabilities=["face_detection"], capacity=100)
    )
    await registry.register(
        ProcessorInfo(
            id="face-proc-2",
            capabilities=["face_detection", "emotion_detection"],
            capacity=100,
        )
    )
    await registry.register(
        ProcessorInfo(
            id="object-proc-1", capabilities=["object_detection"], capacity=100
        )
    )

    # Find face detection processors
    face_procs = await registry.find_by_capability("face_detection")
    assert len(face_procs) == 2
    assert "face-proc-1" in [p.id for p in face_procs]
    assert "face-proc-2" in [p.id for p in face_procs]

    # Find emotion detection processors
    emotion_procs = await registry.find_by_capability("emotion_detection")
    assert len(emotion_procs) == 1
    assert emotion_procs[0].id == "face-proc-2"


@pytest.mark.asyncio
async def test_unregister_processor(redis_client):
    """Test processor unregistration."""
    registry = ProcessorRegistry(redis_client)

    # Register processor
    processor = ProcessorInfo(id="temp-proc", capabilities=["detection"], capacity=50)
    await registry.register(processor)

    # Verify exists
    assert await registry.get_processor("temp-proc") is not None

    # Unregister
    success = await registry.unregister("temp-proc")
    assert success is True

    # Verify removed
    assert await registry.get_processor("temp-proc") is None

    # Unregister non-existent processor
    assert await registry.unregister("non-existent") is False


@pytest.mark.asyncio
async def test_list_all_processors(redis_client):
    """Test listing all registered processors."""
    registry = ProcessorRegistry(redis_client)

    # Register multiple processors
    procs = [
        ProcessorInfo(id=f"list-proc-{i}", capabilities=["test"], capacity=10)
        for i in range(3)
    ]

    for proc in procs:
        await registry.register(proc)

    # List all
    all_procs = await registry.list_all()
    proc_ids = [p.id for p in all_procs]

    for i in range(3):
        assert f"list-proc-{i}" in proc_ids


@pytest.mark.asyncio
async def test_update_processor(redis_client):
    """Test updating processor information."""
    registry = ProcessorRegistry(redis_client)

    # Register processor
    original = ProcessorInfo(
        id="update-proc",
        capabilities=["detection"],
        capacity=50,
        metadata={"version": "1.0"},
    )
    await registry.register(original)

    # Update processor
    updated = ProcessorInfo(
        id="update-proc",
        capabilities=["detection", "tracking"],
        capacity=100,
        metadata={"version": "2.0"},
    )
    success = await registry.update(updated)
    assert success is True

    # Verify update
    retrieved = await registry.get_processor("update-proc")
    assert retrieved.capabilities == ["detection", "tracking"]
    assert retrieved.capacity == 100
    assert retrieved.metadata["version"] == "2.0"


@pytest.mark.asyncio
async def test_concurrent_registration(redis_client):
    """Test concurrent registrations are handled correctly."""
    registry = ProcessorRegistry(redis_client)

    # Simulate concurrent registrations
    import asyncio

    async def register_processor(proc_id: str):
        processor = ProcessorInfo(
            id=proc_id, capabilities=["concurrent_test"], capacity=10
        )
        return await registry.register(processor)

    # Try to register same processor ID concurrently
    results = await asyncio.gather(
        register_processor("concurrent-1"),
        register_processor("concurrent-1"),
        register_processor("concurrent-1"),
        return_exceptions=True,
    )

    # Only one should succeed
    successes = [r for r in results if r is True]
    assert len(successes) == 1

    # Different IDs should all succeed
    results = await asyncio.gather(
        register_processor("concurrent-2"),
        register_processor("concurrent-3"),
        register_processor("concurrent-4"),
    )
    assert all(r is True for r in results)


@pytest.mark.asyncio
async def test_corrupted_data_handling(redis_client):
    """Test handling of corrupted data in Redis."""
    registry = ProcessorRegistry(redis_client)

    # Register a valid processor first
    await registry.register(
        ProcessorInfo(id="good-proc", capabilities=["test"], capacity=10)
    )

    # Manually insert corrupted data
    await redis_client.hset("processors:registry", "corrupted-proc", "invalid-json")

    # Should handle gracefully
    result = await registry.get_processor("corrupted-proc")
    assert result is None

    # Good processor should still work
    good = await registry.get_processor("good-proc")
    assert good is not None
    assert good.id == "good-proc"
