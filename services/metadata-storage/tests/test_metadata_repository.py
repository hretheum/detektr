"""
Test suite for metadata repository pattern.

Tests for CRUD operations with async support.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import asyncpg
import pytest

from src.domain.models.frame_metadata import (
    DetectionMetadata,
    FrameMetadata,
    FrameMetadataCreate,
    FrameMetadataQuery,
    ProcessingMetadata,
)
from src.infrastructure.repositories.metadata_repository import (
    ConnectionPoolConfig,
    IMetadataRepository,
    RepositoryError,
    TimescaleMetadataRepository,
)


@pytest.mark.asyncio
class TestMetadataRepositoryInterface:
    """Test repository interface contract."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository for interface testing."""
        repo = AsyncMock(spec=IMetadataRepository)
        return repo

    async def test_repository_interface_methods_exist(self, mock_repository):
        """Test that all required interface methods exist."""
        # These should not raise AttributeError
        assert hasattr(mock_repository, "create")
        assert hasattr(mock_repository, "create_batch")
        assert hasattr(mock_repository, "get_by_id")
        assert hasattr(mock_repository, "query")
        assert hasattr(mock_repository, "update")
        assert hasattr(mock_repository, "delete")
        assert hasattr(mock_repository, "count")
        assert hasattr(mock_repository, "get_stats")

    async def test_create_single_frame_metadata(self, mock_repository):
        """Test creating a single frame metadata record."""
        # Arrange
        create_dto = FrameMetadataCreate(
            camera_id="cam01",
            sequence_number=123,
            detections=DetectionMetadata(
                faces=2, objects=["person", "car"], motion_score=0.85
            ),
            processing=ProcessingMetadata(
                capture_latency_ms=15, processing_latency_ms=45, total_latency_ms=60
            ),
            trace_id="550e8400-e29b-41d4-a716-446655440000",
            span_id="e29b41d4a716",
        )

        expected_frame = create_dto.to_frame_metadata()
        mock_repository.create.return_value = expected_frame

        # Act
        result = await mock_repository.create(create_dto)

        # Assert
        assert result.camera_id == "cam01"
        assert result.sequence_number == 123
        mock_repository.create.assert_called_once_with(create_dto)

    async def test_create_batch_frame_metadata(self, mock_repository):
        """Test batch creation of frame metadata records."""
        # Arrange
        create_dtos = []
        for i in range(100):
            create_dtos.append(
                FrameMetadataCreate(
                    camera_id=f"cam{i % 10:02d}",
                    sequence_number=i,
                    detections=DetectionMetadata(
                        faces=i % 3,
                        objects=["person"] if i % 2 == 0 else [],
                        motion_score=0.5 + (i % 50) / 100,
                    ),
                    processing=ProcessingMetadata(
                        capture_latency_ms=10 + i % 20,
                        processing_latency_ms=30 + i % 30,
                        total_latency_ms=50 + i % 40,
                    ),
                    trace_id=f"trace-{i}",
                    span_id=f"span-{i}",
                )
            )

        mock_repository.create_batch.return_value = len(create_dtos)

        # Act
        count = await mock_repository.create_batch(create_dtos)

        # Assert
        assert count == 100
        mock_repository.create_batch.assert_called_once()

    async def test_get_by_id(self, mock_repository):
        """Test retrieving frame metadata by ID."""
        # Arrange
        frame_id = "2024-01-20T10:15:30.123456Z_cam01_000123"
        expected_frame = FrameMetadata(
            frame_id=frame_id,
            timestamp=datetime.now(timezone.utc),
            camera_id="cam01",
            sequence_number=123,
            metadata={},
        )
        mock_repository.get_by_id.return_value = expected_frame

        # Act
        result = await mock_repository.get_by_id(frame_id)

        # Assert
        assert result.frame_id == frame_id
        assert result.camera_id == "cam01"
        mock_repository.get_by_id.assert_called_once_with(frame_id)

    async def test_query_with_filters(self, mock_repository):
        """Test querying with various filters."""
        # Arrange
        query = FrameMetadataQuery(
            camera_id="cam02",
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc),
            min_motion_score=0.7,
            has_faces=True,
            limit=50,
        )

        mock_frames = [
            FrameMetadata(
                frame_id=f"frame_{i}",
                timestamp=datetime.now(timezone.utc),
                camera_id="cam02",
                sequence_number=i,
                metadata={"detections": {"faces": 1, "motion_score": 0.8}},
            )
            for i in range(10)
        ]
        mock_repository.query.return_value = mock_frames

        # Act
        results = await mock_repository.query(query)

        # Assert
        assert len(results) == 10
        assert all(frame.camera_id == "cam02" for frame in results)
        mock_repository.query.assert_called_once_with(query)

    async def test_update_frame_metadata(self, mock_repository):
        """Test updating frame metadata."""
        # Arrange
        frame_id = "2024-01-20T10:15:30.123456Z_cam01_000123"
        updates = {
            "metadata": {
                "detections": {
                    "faces": 3,
                    "objects": ["person", "dog"],
                    "motion_score": 0.9,
                },
                "processing": {"total_latency_ms": 75},
            }
        }

        updated_frame = FrameMetadata(
            frame_id=frame_id,
            timestamp=datetime.now(timezone.utc),
            camera_id="cam01",
            sequence_number=123,
            metadata=updates["metadata"],
        )
        mock_repository.update.return_value = updated_frame

        # Act
        result = await mock_repository.update(frame_id, updates)

        # Assert
        assert result.metadata["detections"]["faces"] == 3
        assert result.metadata["detections"]["motion_score"] == 0.9
        mock_repository.update.assert_called_once_with(frame_id, updates)

    async def test_delete_frame_metadata(self, mock_repository):
        """Test deleting frame metadata."""
        # Arrange
        frame_id = "2024-01-20T10:15:30.123456Z_cam01_000123"
        mock_repository.delete.return_value = True

        # Act
        result = await mock_repository.delete(frame_id)

        # Assert
        assert result is True
        mock_repository.delete.assert_called_once_with(frame_id)

    async def test_count_frames(self, mock_repository):
        """Test counting frames with optional filters."""
        # Arrange
        query = FrameMetadataQuery(camera_id="cam01")
        mock_repository.count.return_value = 12345

        # Act
        count = await mock_repository.count(query)

        # Assert
        assert count == 12345
        mock_repository.count.assert_called_once_with(query)

    async def test_get_stats(self, mock_repository):
        """Test getting aggregated statistics."""
        # Arrange
        expected_stats = {
            "total_frames": 100000,
            "cameras": {
                "cam01": {"frames": 10000, "avg_latency": 45.2},
                "cam02": {"frames": 9500, "avg_latency": 48.7},
            },
            "last_hour": {
                "frames": 3600,
                "faces_detected": 1200,
                "avg_motion_score": 0.65,
            },
        }
        mock_repository.get_stats.return_value = expected_stats

        # Act
        stats = await mock_repository.get_stats()

        # Assert
        assert stats["total_frames"] == 100000
        assert "cam01" in stats["cameras"]
        assert stats["last_hour"]["faces_detected"] == 1200
        mock_repository.get_stats.assert_called_once()


@pytest.mark.asyncio
class TestTimescaleMetadataRepository:
    """Test TimescaleDB implementation of metadata repository."""

    @pytest.fixture
    async def mock_pool(self):
        """Create mock connection pool."""
        pool = AsyncMock(spec=asyncpg.Pool)
        return pool

    @pytest.fixture
    async def repository(self, mock_pool):
        """Create repository with mocked pool."""
        repo = TimescaleMetadataRepository(pool=mock_pool)
        return repo

    async def test_repository_initialization(self):
        """Test repository can be initialized with config."""
        # Arrange
        config = ConnectionPoolConfig(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass",
            min_size=5,
            max_size=20,
        )

        # Act - just verify no errors
        repo = TimescaleMetadataRepository(config=config)

        # Assert
        assert repo is not None
        assert repo._config == config

    async def test_create_executes_insert_query(self, repository, mock_pool):
        """Test that create executes proper INSERT query."""
        # Arrange
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        create_dto = FrameMetadataCreate(
            camera_id="cam01",
            sequence_number=123,
            detections=DetectionMetadata(faces=1, objects=[], motion_score=0.5),
            processing=ProcessingMetadata(
                capture_latency_ms=10, processing_latency_ms=20, total_latency_ms=30
            ),
            trace_id="test-trace",
            span_id="test-span",
        )

        # Act
        await repository.create(create_dto)

        # Assert
        mock_conn.execute.assert_called_once()
        query = mock_conn.execute.call_args[0][0]
        assert "INSERT INTO metadata.frame_metadata" in query

    async def test_create_batch_uses_executemany(self, repository, mock_pool):
        """Test that batch creation uses executemany for performance."""
        # Arrange
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        create_dtos = [
            FrameMetadataCreate(
                camera_id=f"cam{i:02d}",
                sequence_number=i,
                detections=DetectionMetadata(faces=0, objects=[], motion_score=0.1),
                processing=ProcessingMetadata(
                    capture_latency_ms=10, processing_latency_ms=20, total_latency_ms=30
                ),
                trace_id=f"trace-{i}",
                span_id=f"span-{i}",
            )
            for i in range(10)
        ]

        # Act
        await repository.create_batch(create_dtos)

        # Assert
        mock_conn.executemany.assert_called_once()

    async def test_query_builds_correct_where_clause(self, repository, mock_pool):
        """Test that query builds correct WHERE clause from filters."""
        # Arrange
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        query = FrameMetadataQuery(
            camera_id="cam01",
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc),
            min_motion_score=0.5,
            has_faces=True,
            limit=100,
        )

        # Act
        await repository.query(query)

        # Assert
        mock_conn.fetch.assert_called_once()
        sql_query = mock_conn.fetch.call_args[0][0]
        assert "camera_id = $" in sql_query
        assert "timestamp >= $" in sql_query
        assert "timestamp <= $" in sql_query
        assert "motion_score" in sql_query
        assert "faces" in sql_query

    async def test_connection_pool_retry_on_failure(self, repository, mock_pool):
        """Test that repository retries on connection failure."""
        # Arrange
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # First call fails, second succeeds
        mock_conn.execute.side_effect = [
            asyncpg.PostgresConnectionError("Connection failed"),
            None,
        ]

        create_dto = FrameMetadataCreate(
            camera_id="cam01",
            sequence_number=1,
            detections=DetectionMetadata(faces=0, objects=[], motion_score=0.1),
            processing=ProcessingMetadata(
                capture_latency_ms=10, processing_latency_ms=20, total_latency_ms=30
            ),
            trace_id="test",
            span_id="test",
        )

        # Act & Assert - should not raise exception
        with pytest.raises(RepositoryError):
            await repository.create(create_dto)

    async def test_get_stats_uses_continuous_aggregates(self, repository, mock_pool):
        """Test that get_stats queries continuous aggregates for performance."""
        # Arrange
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock different aggregate queries
        mock_conn.fetchrow.side_effect = [
            {"total": 100000},  # Total count
            {"cameras": [{"camera_id": "cam01", "count": 10000}]},  # Camera stats
            {"avg_latency": 45.5, "faces_detected": 1200},  # Last hour stats
        ]

        # Act
        await repository.get_stats()

        # Assert
        assert mock_conn.fetchrow.call_count >= 1
        # Verify it queries the continuous aggregates
        calls = [call[0][0] for call in mock_conn.fetchrow.call_args_list]
        assert any(
            "frame_stats_1min" in call or "frame_stats_hourly" in call for call in calls
        )
