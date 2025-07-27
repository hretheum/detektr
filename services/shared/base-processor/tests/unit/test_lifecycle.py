"""Tests for frame lifecycle management components."""
import asyncio
from datetime import datetime

import numpy as np
import pytest
from base_processor.batch_processor import (
    BatchConfig,
    BatchProcessor,
    BatchResult,
    create_batched_array,
    unbatch_array,
)
from base_processor.exceptions import ResourceError
from base_processor.resource_manager import ResourceManager, ResourceStats
from base_processor.state_machine import (
    FrameState,
    FrameStateMachine,
    InvalidStateTransition,
    StateTransition,
)


class TestFrameStateMachine:
    """Test frame state machine functionality."""

    @pytest.fixture
    def state_machine(self):
        """Create state machine instance."""
        return FrameStateMachine()

    @pytest.mark.asyncio
    async def test_register_frame(self, state_machine):
        """Test frame registration."""
        frame_id = "test_frame_001"
        metadata = await state_machine.register_frame(
            frame_id, camera_id="cam_1", timestamp=datetime.now()
        )

        assert metadata.frame_id == frame_id
        assert metadata.state == FrameState.RECEIVED
        assert metadata.retry_count == 0
        assert "camera_id" in metadata.custom_data

    @pytest.mark.asyncio
    async def test_valid_transitions(self, state_machine):
        """Test valid state transitions."""
        frame_id = "test_frame_002"
        await state_machine.register_frame(frame_id)

        # RECEIVED -> VALIDATED
        new_state = await state_machine.transition(frame_id, StateTransition.VALIDATE)
        assert new_state == FrameState.VALIDATED

        # VALIDATED -> QUEUED
        new_state = await state_machine.transition(frame_id, StateTransition.QUEUE)
        assert new_state == FrameState.QUEUED

        # QUEUED -> PROCESSING
        new_state = await state_machine.transition(frame_id, StateTransition.START)
        assert new_state == FrameState.PROCESSING

        # PROCESSING -> COMPLETED
        new_state = await state_machine.transition(
            frame_id, StateTransition.COMPLETE, result={"detected_objects": 3}
        )
        assert new_state == FrameState.COMPLETED

        # Check result was stored
        metadata = state_machine.get_frame_metadata(frame_id)
        assert metadata.result == {"detected_objects": 3}

    @pytest.mark.asyncio
    async def test_invalid_transitions(self, state_machine):
        """Test invalid state transitions."""
        frame_id = "test_frame_003"
        await state_machine.register_frame(frame_id)

        # Try invalid transition RECEIVED -> COMPLETED
        with pytest.raises(InvalidStateTransition):
            await state_machine.transition(frame_id, StateTransition.COMPLETE)

    @pytest.mark.asyncio
    async def test_failure_and_retry(self, state_machine):
        """Test failure and retry flow."""
        frame_id = "test_frame_004"
        await state_machine.register_frame(frame_id)

        # Move to processing
        await state_machine.transition(frame_id, StateTransition.VALIDATE)
        await state_machine.transition(frame_id, StateTransition.QUEUE)
        await state_machine.transition(frame_id, StateTransition.START)

        # Fail with error
        await state_machine.transition(
            frame_id, StateTransition.FAIL, error="Processing failed"
        )

        metadata = state_machine.get_frame_metadata(frame_id)
        assert metadata.state == FrameState.FAILED
        assert len(metadata.error_history) == 1
        assert metadata.error_history[0]["error"] == "Processing failed"

        # Retry
        await state_machine.transition(frame_id, StateTransition.RETRY)
        assert metadata.retry_count == 1

        # Requeue
        await state_machine.transition(frame_id, StateTransition.REQUEUE)
        assert metadata.state == FrameState.QUEUED

    @pytest.mark.asyncio
    async def test_state_callbacks(self, state_machine):
        """Test state entry callbacks."""
        callback_called = False
        called_frame_id = None

        async def on_processing(frame_id, metadata):
            nonlocal callback_called, called_frame_id
            callback_called = True
            called_frame_id = frame_id

        state_machine.on_state_enter(FrameState.PROCESSING, on_processing)

        frame_id = "test_frame_005"
        await state_machine.register_frame(frame_id)
        await state_machine.transition(frame_id, StateTransition.VALIDATE)
        await state_machine.transition(frame_id, StateTransition.QUEUE)
        await state_machine.transition(frame_id, StateTransition.START)

        assert callback_called
        assert called_frame_id == frame_id

    def test_get_frames_by_state(self, state_machine):
        """Test getting frames by state."""
        asyncio.run(state_machine.register_frame("frame_1"))
        asyncio.run(state_machine.register_frame("frame_2"))
        asyncio.run(state_machine.register_frame("frame_3"))

        # Move frame_2 to validated
        asyncio.run(state_machine.transition("frame_2", StateTransition.VALIDATE))

        received_frames = state_machine.get_frames_by_state(FrameState.RECEIVED)
        validated_frames = state_machine.get_frames_by_state(FrameState.VALIDATED)

        assert len(received_frames) == 2
        assert len(validated_frames) == 1
        assert "frame_2" in validated_frames

    def test_statistics(self, state_machine):
        """Test statistics collection."""
        # Register and process some frames
        asyncio.run(state_machine.register_frame("frame_1"))
        asyncio.run(state_machine.register_frame("frame_2"))

        # Move frame_1 through retry
        asyncio.run(state_machine.transition("frame_1", StateTransition.VALIDATE))
        asyncio.run(state_machine.transition("frame_1", StateTransition.QUEUE))
        asyncio.run(state_machine.transition("frame_1", StateTransition.START))
        asyncio.run(state_machine.transition("frame_1", StateTransition.FAIL))
        asyncio.run(state_machine.transition("frame_1", StateTransition.RETRY))

        stats = state_machine.get_statistics()

        assert stats["total_frames"] == 2
        assert stats["retry_stats"]["frames_with_retries"] == 1
        assert stats["retry_stats"]["total_retries"] == 1


class TestResourceManager:
    """Test resource management functionality."""

    @pytest.fixture
    def resource_manager(self):
        """Create resource manager instance."""
        return ResourceManager(
            max_cpu_percent=80.0,
            max_memory_percent=80.0,
            gpu_devices=[],  # No GPU for tests
        )

    @pytest.mark.asyncio
    async def test_resource_stats(self, resource_manager):
        """Test getting resource statistics."""
        stats = await resource_manager.get_current_stats()

        assert isinstance(stats, ResourceStats)
        assert stats.cpu_percent >= 0
        assert stats.memory_percent >= 0
        assert stats.memory_used_mb > 0

    @pytest.mark.asyncio
    async def test_resource_allocation(self, resource_manager):
        """Test resource allocation and release."""
        allocation_id = "test_alloc_001"

        async with resource_manager.allocate_resources(
            allocation_id=allocation_id, cpu_cores=1, memory_mb=100
        ) as allocation:
            assert allocation.allocation_id == allocation_id
            assert allocation.memory_limit_mb == 100
            assert allocation_id in resource_manager._allocations

        # After context exit, allocation should be released
        assert allocation_id not in resource_manager._allocations

    @pytest.mark.asyncio
    async def test_resource_limits(self, resource_manager):
        """Test resource limit enforcement."""
        # Allocate most available memory
        total_memory = resource_manager.total_memory_mb
        max_allowed = total_memory * 0.8  # 80% limit

        allocation1_id = "test_alloc_002"
        async with resource_manager.allocate_resources(
            allocation_id=allocation1_id, memory_mb=max_allowed * 0.7
        ):
            # Try to allocate more than remaining
            allocation2_id = "test_alloc_003"
            with pytest.raises(ResourceError):
                async with resource_manager.allocate_resources(
                    allocation_id=allocation2_id, memory_mb=max_allowed * 0.5
                ):
                    pass

    @pytest.mark.asyncio
    async def test_check_resources_available(self, resource_manager):
        """Test resource availability checking."""
        # Should have resources available initially
        assert await resource_manager.check_resources_available(
            cpu_cores=1, memory_mb=100
        )

        # Allocate some resources
        async with resource_manager.allocate_resources(
            allocation_id="test_alloc_004", cpu_cores=1, memory_mb=100
        ):
            # Check if more resources are available
            stats = resource_manager.get_allocation_stats()
            assert stats["allocated_cpus"] == 1
            assert stats["allocated_memory_mb"] == 100

    @pytest.mark.asyncio
    async def test_wait_for_resources(self, resource_manager):
        """Test waiting for resources."""
        # This test would need proper timing control
        # For now, just test immediate availability
        available = await resource_manager.wait_for_resources(
            cpu_cores=1, memory_mb=100, timeout=0.1
        )
        assert available


class TestBatchProcessor:
    """Test batch processing functionality."""

    @pytest.fixture
    def batch_processor(self):
        """Create batch processor instance."""
        config = BatchConfig(
            batch_size=3, max_concurrent_batches=2, timeout_per_item=1.0
        )
        return BatchProcessor(config)

    @pytest.fixture
    def sample_frames(self):
        """Create sample frames for testing."""
        return [
            np.random.rand(100, 100, 3).astype(np.float32),
            np.random.rand(100, 100, 3).astype(np.float32),
            np.random.rand(100, 100, 3).astype(np.float32),
            np.random.rand(100, 100, 3).astype(np.float32),
        ]

    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata."""
        return [
            {"frame_id": f"frame_{i}", "timestamp": datetime.now()} for i in range(4)
        ]

    @pytest.mark.asyncio
    async def test_process_batch(self, batch_processor, sample_frames, sample_metadata):
        """Test basic batch processing."""

        async def mock_process(frame, metadata):
            await asyncio.sleep(0.01)  # Simulate processing
            return {"processed": True, "frame_id": metadata["frame_id"]}

        items = list(zip(sample_frames[:3], sample_metadata[:3]))
        result = await batch_processor.process_batch(items, mock_process)

        assert isinstance(result, BatchResult)
        assert result.total_items == 3
        assert result.successful == 3
        assert result.failed == 0
        assert len(result.results) == 3

    @pytest.mark.asyncio
    async def test_batch_with_errors(
        self, batch_processor, sample_frames, sample_metadata
    ):
        """Test batch processing with errors."""

        async def failing_process(frame, metadata):
            if metadata["frame_id"] == "frame_1":
                raise ValueError("Test error")
            return {"processed": True}

        items = list(zip(sample_frames[:3], sample_metadata[:3]))
        result = await batch_processor.process_batch(items, failing_process)

        assert result.failed == 1
        assert result.successful == 2
        assert len(result.errors) == 1
        assert result.errors[0][0] == 1  # Index of failed item

    @pytest.mark.asyncio
    async def test_process_in_batches(
        self, batch_processor, sample_frames, sample_metadata
    ):
        """Test processing multiple batches."""

        async def mock_process(frame, metadata):
            return {"processed": True}

        results = await batch_processor.process_in_batches(
            sample_frames, sample_metadata, mock_process
        )

        # With batch_size=3 and 4 items, should have 2 batches
        assert len(results) == 2
        assert results[0].total_items == 3
        assert results[1].total_items == 1

    def test_create_optimized_batches(self, batch_processor):
        """Test optimized batch creation."""
        frames = [
            np.zeros((100, 100, 3)),
            np.zeros((100, 100, 3)),
            np.zeros((200, 200, 3)),
            np.zeros((200, 200, 3)),
        ]
        metadata = [{"id": i} for i in range(4)]

        batches = batch_processor.create_optimized_batches(frames, metadata)

        # Should group by dimensions
        assert len(batches) == 2
        # Each batch should have frames of same dimensions
        for batch in batches:
            shapes = [f.shape for f, _ in batch]
            assert all(s == shapes[0] for s in shapes)

    def test_batched_array_creation(self):
        """Test creating and unbatching arrays."""
        frames = [
            np.ones((10, 10)),
            np.ones((15, 15)),
            np.ones((12, 12)),
        ]

        batch, original_shapes = create_batched_array(frames)

        assert batch.shape == (3, 15, 15)  # Max dimensions
        assert len(original_shapes) == 3

        # Test unbatching
        unbatched = unbatch_array(batch, original_shapes)
        assert len(unbatched) == 3
        for original, restored in zip(frames, unbatched):
            assert restored.shape == original.shape
            assert np.array_equal(restored, original)
