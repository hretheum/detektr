"""Integration tests for frame processing pipeline."""

import asyncio
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.monitoring.infrastructure import FrameMetadataRepository
from src.examples.frame_processor import FrameProcessor, ProcessingResult
from src.shared.kernel.domain import Frame, ProcessingState


@pytest.mark.integration
class TestFramePipelineIntegration:
    """Integration tests for complete frame pipeline."""

    @pytest.fixture
    async def frame_processor(self, db_session: AsyncSession, redis_client):
        """Create frame processor with real dependencies."""
        # Create repository with real database
        repository = FrameMetadataRepository(db_session)

        # Mock detectors (in real scenario these would be real services)
        class MockDetector:
            async def detect(self, frame):
                # Simulate some processing time
                await asyncio.sleep(0.1)
                return [{"confidence": 0.85, "class": "person"}]

        # Mock event publisher using Redis
        class RedisEventPublisher:
            def __init__(self, redis):
                self.redis = redis

            async def publish(self, event):
                await self.redis.publish("frame_events", str(event))

        processor = FrameProcessor(
            face_detector=MockDetector(),
            object_detector=MockDetector(),
            frame_repository=repository,
            event_publisher=RedisEventPublisher(redis_client),
        )

        return processor

    @pytest.mark.asyncio
    async def test_full_frame_processing_flow(self, frame_processor, redis_client):
        """Test complete frame processing flow with real dependencies."""
        # Create subscription for events
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("frame_events")

        # Create test frame
        frame = Frame.create(camera_id="integration_test_cam", timestamp=datetime.now())

        # Process frame
        result = await frame_processor.process_frame(frame)

        # Verify result
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.frame_id == str(frame.id)
        assert len(result.detections["faces"]) > 0
        assert len(result.detections["objects"]) > 0
        assert result.processing_time_ms > 100  # At least detection time

        # Verify frame was persisted
        saved_frame = await frame_processor.frame_repository.get_by_id(frame.id)
        assert saved_frame is not None
        assert saved_frame.state == ProcessingState.COMPLETED
        assert saved_frame.metadata["face_count"] == 1
        assert saved_frame.metadata["object_count"] == 1

        # Verify event was published
        message = await asyncio.wait_for(
            pubsub.get_message(ignore_subscribe_messages=True), timeout=2
        )
        assert message is not None
        assert "frame.processed" in str(message["data"])

    @pytest.mark.asyncio
    async def test_concurrent_processing_with_database(self, frame_processor):
        """Test processing multiple frames concurrently with database."""
        frames = [
            Frame.create(camera_id=f"cam_{i}", timestamp=datetime.now())
            for i in range(10)
        ]

        # Process all frames concurrently
        results = await asyncio.gather(
            *[frame_processor.process_frame(frame) for frame in frames],
            return_exceptions=True,
        )

        # Verify all succeeded
        assert all(isinstance(r, ProcessingResult) for r in results)
        assert all(r.success for r in results)

        # Verify all frames in database
        for frame, result in zip(frames, results):
            saved = await frame_processor.frame_repository.get_by_id(frame.id)
            assert saved is not None
            assert saved.state == ProcessingState.COMPLETED

    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(self, frame_processor):
        """Test pipeline handles errors gracefully."""
        # Inject error into detector
        original_detect = frame_processor.face_detector.detect

        async def failing_detect(frame):
            if "fail" in frame.camera_id:
                raise Exception("Simulated detection failure")
            return await original_detect(frame)

        frame_processor.face_detector.detect = failing_detect

        # Process frames with some failures
        frames = [
            Frame.create(camera_id="normal_cam", timestamp=datetime.now()),
            Frame.create(camera_id="fail_cam", timestamp=datetime.now()),
            Frame.create(camera_id="normal_cam_2", timestamp=datetime.now()),
        ]

        results = await asyncio.gather(
            *[frame_processor.process_frame(frame) for frame in frames],
            return_exceptions=True,
        )

        # First and third should succeed
        assert results[0].success is True
        assert results[2].success is True

        # Second should have partial success (object detection worked)
        assert results[1].success is True  # Partial success
        assert "face_detection" in results[1].errors
        assert len(results[1].detections["objects"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_performance_under_load(self, frame_processor, benchmark_data):
        """Test pipeline performance with many frames."""
        import time

        frame_count = 50
        frames = [
            Frame.create(camera_id=f"perf_test_cam_{i}", timestamp=datetime.now())
            for i in range(frame_count)
        ]

        start_time = time.time()

        # Process in batches to simulate realistic load
        batch_size = 10
        for i in range(0, frame_count, batch_size):
            batch = frames[i : i + batch_size]
            await asyncio.gather(
                *[frame_processor.process_frame(frame) for frame in batch]
            )

        total_time = time.time() - start_time
        fps = frame_count / total_time

        print(f"\nProcessed {frame_count} frames in {total_time:.2f}s ({fps:.2f} FPS)")

        # Should process at least 5 FPS with mocked detectors
        assert fps >= 5.0
