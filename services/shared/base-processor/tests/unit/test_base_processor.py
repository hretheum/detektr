"""Unit tests for BaseProcessor abstract class."""
import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest
from base_processor import BaseProcessor, ProcessingError, ValidationError


class ConcreteProcessor(BaseProcessor):
    """Concrete implementation for testing."""

    async def process_frame(
        self, frame: np.ndarray, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simple implementation that returns frame shape."""
        return {"shape": frame.shape, "metadata": metadata, "processed": True}


class TestBaseProcessor:
    """Test suite for BaseProcessor functionality."""

    @pytest.fixture
    def processor(self):
        """Create a concrete processor instance."""
        return ConcreteProcessor()

    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame for testing."""
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata."""
        return {
            "frame_id": "test_123",
            "timestamp": 1234567890.0,
            "source": "test_camera",
        }

    @pytest.mark.asyncio
    async def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.name == "ConcreteProcessor"
        assert processor.is_initialized is False
        assert processor.metrics is not None
        assert processor.logger is not None

    @pytest.mark.asyncio
    async def test_processor_lifecycle(self, processor):
        """Test processor initialization and cleanup lifecycle."""
        # Initialize
        await processor.initialize()
        assert processor.is_initialized is True

        # Cleanup
        await processor.cleanup()
        assert processor.is_initialized is False

    @pytest.mark.asyncio
    async def test_process_with_valid_input(
        self, processor, sample_frame, sample_metadata
    ):
        """Test processing with valid input."""
        await processor.initialize()

        result = await processor.process(sample_frame, sample_metadata)

        assert result["processed"] is True
        assert result["shape"] == sample_frame.shape
        assert result["metadata"] == sample_metadata

    @pytest.mark.asyncio
    async def test_process_without_initialization(
        self, processor, sample_frame, sample_metadata
    ):
        """Test processing without initialization raises error."""
        with pytest.raises(RuntimeError, match="Processor not initialized"):
            await processor.process(sample_frame, sample_metadata)

    @pytest.mark.asyncio
    async def test_input_validation(self, processor, sample_frame, sample_metadata):
        """Test input validation."""
        await processor.initialize()

        # Test with invalid frame
        with pytest.raises(ValidationError, match="Invalid frame"):
            await processor.process(None, sample_metadata)

        # Test with invalid frame shape
        invalid_frame = np.array([1, 2, 3])
        with pytest.raises(ValidationError, match="Invalid frame shape"):
            await processor.process(invalid_frame, sample_metadata)

        # Test with missing metadata
        with pytest.raises(ValidationError, match="Metadata is required"):
            await processor.process(sample_frame, None)

    @pytest.mark.asyncio
    async def test_preprocessing_hook(self, processor, sample_frame, sample_metadata):
        """Test preprocessing hook is called."""
        await processor.initialize()

        preprocess_called = False

        async def custom_preprocess(frame, metadata):
            nonlocal preprocess_called
            preprocess_called = True
            return frame, metadata

        processor.register_hook("preprocess", custom_preprocess)

        await processor.process(sample_frame, sample_metadata)
        assert preprocess_called is True

    @pytest.mark.asyncio
    async def test_postprocessing_hook(self, processor, sample_frame, sample_metadata):
        """Test postprocessing hook is called."""
        await processor.initialize()

        postprocess_called = False

        async def custom_postprocess(result):
            nonlocal postprocess_called
            postprocess_called = True
            result["post_processed"] = True
            return result

        processor.register_hook("postprocess", custom_postprocess)

        result = await processor.process(sample_frame, sample_metadata)
        assert postprocess_called is True
        assert result["post_processed"] is True

    @pytest.mark.asyncio
    async def test_error_handling(self, processor, sample_frame, sample_metadata):
        """Test error handling in processing."""
        await processor.initialize()

        # Mock process_frame to raise an error
        async def failing_process(frame, metadata):
            raise ProcessingError("Test processing error")

        processor.process_frame = failing_process

        with pytest.raises(ProcessingError, match="Test processing error"):
            await processor.process(sample_frame, sample_metadata)

    @pytest.mark.asyncio
    async def test_metrics_collection(self, processor, sample_frame, sample_metadata):
        """Test metrics are collected during processing."""
        await processor.initialize()

        # Process a frame
        await processor.process(sample_frame, sample_metadata)

        # Check metrics were updated
        metrics = processor.get_metrics()
        assert metrics["frames_processed"] == 1
        assert metrics["processing_time_avg"] > 0
        assert metrics["errors_total"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_processing(
        self, processor, sample_frame, sample_metadata
    ):
        """Test concurrent processing of multiple frames."""
        await processor.initialize()

        # Process multiple frames concurrently
        tasks = []
        for i in range(10):
            metadata = sample_metadata.copy()
            metadata["frame_id"] = f"test_{i}"
            tasks.append(processor.process(sample_frame, metadata))

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r["processed"] is True for r in results)

        # Check metrics
        metrics = processor.get_metrics()
        assert metrics["frames_processed"] == 10

    @pytest.mark.asyncio
    async def test_resource_limits(self, processor, sample_frame, sample_metadata):
        """Test resource limits are enforced."""
        processor.max_concurrent_frames = 5
        await processor.initialize()

        # Try to process more frames than allowed
        processing_count = 0

        async def slow_process(frame, metadata):
            nonlocal processing_count
            processing_count += 1
            await asyncio.sleep(0.1)
            return {"processed": True}

        processor.process_frame = slow_process

        # Start multiple processing tasks
        tasks = []
        for i in range(10):
            metadata = sample_metadata.copy()
            metadata["frame_id"] = f"test_{i}"
            tasks.append(processor.process(sample_frame, metadata))

        # Check that max concurrent limit is respected
        await asyncio.sleep(0.05)  # Give time for tasks to start
        assert processor.active_frames <= 5

        # Wait for all to complete
        await asyncio.gather(*tasks)

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, processor, sample_frame, sample_metadata):
        """Test graceful shutdown during processing."""
        await processor.initialize()

        # Start a long-running process
        async def slow_process(frame, metadata):
            await asyncio.sleep(1)
            return {"processed": True}

        processor.process_frame = slow_process

        # Start processing
        task = asyncio.create_task(processor.process(sample_frame, sample_metadata))

        # Give it time to start
        await asyncio.sleep(0.1)

        # Shutdown should wait for active processing
        shutdown_task = asyncio.create_task(processor.cleanup())

        # Should not be done immediately
        await asyncio.sleep(0.1)
        assert not shutdown_task.done()

        # Cancel the processing task
        task.cancel()

        # Now shutdown should complete
        await shutdown_task
        assert processor.is_initialized is False
