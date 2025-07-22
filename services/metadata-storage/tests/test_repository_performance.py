"""
Performance tests for metadata repository.

Tests batch insert performance to achieve 10k records/s.
"""

import asyncio
import time
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from src.domain.models.frame_metadata import (
    DetectionMetadata,
    FrameMetadataCreate,
    ProcessingMetadata,
)
from src.infrastructure.repositories.metadata_repository import (
    ConnectionPoolConfig,
    TimescaleMetadataRepository,
)


@pytest.mark.asyncio
@pytest.mark.integration
class TestRepositoryPerformance:
    """Performance tests for repository implementation."""

    @pytest_asyncio.fixture
    async def repository(self):
        """Create repository with real connection for performance testing."""
        config = ConnectionPoolConfig(
            host="192.168.1.193",  # Nebula server
            port=5432,
            database="detektor_db",
            user="detektor",
            password="detektor_pass",
            min_size=10,
            max_size=30,
        )
        repo = TimescaleMetadataRepository(config=config)
        yield repo
        await repo.close()

    async def test_batch_insert_performance(self, repository):
        """Test that batch inserts achieve 10k records/s."""
        # Generate test data
        batch_size = 5000  # Larger batch size for better performance
        num_batches = 4  # Less batches to reduce overhead
        total_records = batch_size * num_batches

        batches = []
        for batch_idx in range(num_batches):
            batch = []
            for i in range(batch_size):
                idx = batch_idx * batch_size + i
                capture_ms = 10 + idx % 20
                processing_ms = 30 + idx % 30
                create_dto = FrameMetadataCreate(
                    camera_id=f"cam{idx % 10:02d}",
                    sequence_number=idx,
                    detections=DetectionMetadata(
                        faces=idx % 4,
                        objects=["person"] if idx % 2 == 0 else [],
                        motion_score=0.5 + (idx % 50) / 100,
                    ),
                    processing=ProcessingMetadata(
                        capture_latency_ms=capture_ms,
                        processing_latency_ms=processing_ms,
                        total_latency_ms=capture_ms + processing_ms,
                    ),
                    trace_id=f"perf-test-{idx}",
                    span_id=f"span-{idx}",
                )
                batch.append(create_dto)
            batches.append(batch)

        # Measure insert performance
        start_time = time.time()

        for batch in batches:
            count = await repository.create_batch(batch)
            assert count == batch_size

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate metrics
        records_per_second = total_records / total_time

        print("\nPerformance Results:")
        print(f"Total records: {total_records}")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Records per second: {records_per_second:.1f}")
        print(f"Batch size: {batch_size}")

        # Assert performance requirement
        assert (
            records_per_second >= 10000
        ), f"Performance {records_per_second:.1f} records/s is below 10k requirement"

    async def test_query_performance_with_data(self, repository):
        """Test query performance with realistic data volume."""
        # First insert some test data
        batch_size = 1000
        create_dtos = []

        base_time = datetime.now(timezone.utc)
        for i in range(batch_size):
            create_dto = FrameMetadataCreate(
                camera_id="cam01",
                sequence_number=i,
                detections=DetectionMetadata(
                    faces=i % 3,
                    objects=["person", "car"] if i % 5 == 0 else ["person"],
                    motion_score=0.3 + (i % 70) / 100,
                ),
                processing=ProcessingMetadata(
                    capture_latency_ms=15, processing_latency_ms=35, total_latency_ms=50
                ),
                trace_id=f"query-test-{i}",
                span_id=f"span-{i}",
            )
            create_dtos.append(create_dto)

        # Insert test data
        await repository.create_batch(create_dtos)

        # Test point query performance
        frame_id = create_dtos[0].generate_frame_id(base_time)

        start_time = time.time()
        await repository.get_by_id(frame_id)
        query_time = (time.time() - start_time) * 1000

        print(f"\nPoint query time: {query_time:.2f}ms")
        assert query_time < 10, f"Point query {query_time:.2f}ms exceeds 10ms limit"

        # Test range query performance
        from src.domain.models.frame_metadata import FrameMetadataQuery

        query = FrameMetadataQuery(camera_id="cam01", min_motion_score=0.5, limit=100)

        start_time = time.time()
        results = await repository.query(query)
        range_query_time = (time.time() - start_time) * 1000

        print(f"Range query time: {range_query_time:.2f}ms ({len(results)} results)")
        assert (
            range_query_time < 50
        ), f"Range query {range_query_time:.2f}ms exceeds 50ms limit"

    async def test_connection_pool_performance(self, repository):
        """Test connection pool handles concurrent operations efficiently."""
        # Create multiple concurrent operations
        num_concurrent = 20
        operations_per_task = 50

        async def perform_operations(task_id: int):
            """Perform multiple operations."""
            times = []

            for i in range(operations_per_task):
                create_dto = FrameMetadataCreate(
                    camera_id=f"cam{task_id % 10:02d}",
                    sequence_number=task_id * 1000 + i,
                    detections=DetectionMetadata(
                        faces=1, objects=["person"], motion_score=0.75
                    ),
                    processing=ProcessingMetadata(
                        capture_latency_ms=20,
                        processing_latency_ms=40,
                        total_latency_ms=60,
                    ),
                    trace_id=f"concurrent-{task_id}-{i}",
                    span_id=f"span-{i}",
                )

                start = time.time()
                await repository.create(create_dto)
                times.append(time.time() - start)

            return times

        # Run concurrent tasks
        start_time = time.time()

        tasks = [perform_operations(i) for i in range(num_concurrent)]
        all_times = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # Calculate statistics
        all_operation_times = [t for times in all_times for t in times]
        avg_time = sum(all_operation_times) / len(all_operation_times)
        max_time = max(all_operation_times)

        total_operations = num_concurrent * operations_per_task
        ops_per_second = total_operations / total_time

        print("\nConcurrency Results:")
        print(f"Concurrent tasks: {num_concurrent}")
        print(f"Total operations: {total_operations}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Operations/second: {ops_per_second:.1f}")
        print(f"Avg operation time: {avg_time*1000:.2f}ms")
        print(f"Max operation time: {max_time*1000:.2f}ms")

        # Pool should handle concurrency efficiently
        assert ops_per_second > 100, f"Concurrent ops {ops_per_second:.1f}/s too low"
        assert max_time < 1.0, f"Max operation time {max_time:.2f}s too high"
