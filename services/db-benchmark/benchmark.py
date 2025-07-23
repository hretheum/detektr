#!/usr/bin/env python3
"""Database performance benchmark for TimescaleDB."""

import asyncio
import json
import os
import random
import time
import uuid
from datetime import datetime, timedelta

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://detektor:detektor_pass@postgres:5432/detektor_db"
)
BATCH_SIZE = 1000
NUM_BATCHES = 10


async def create_pool():
    """Create connection pool."""
    return await asyncpg.create_pool(DATABASE_URL, min_size=10, max_size=20)


async def insert_frame_events(pool, batch_num):
    """Insert batch of frame events."""
    async with pool.acquire() as conn:
        start_time = time.time()

        records = []
        base_time = datetime.now() - timedelta(hours=batch_num)

        for i in range(BATCH_SIZE):
            record = (
                f"frame_{batch_num}_{i}",  # id
                str(uuid.uuid4()),  # event_id
                f"frame_{batch_num}_{i}",  # frame_id
                f"camera_{random.randint(1, 5)}",  # camera_id
                random.choice(
                    ["captured", "processed", "stored", "analyzed"]
                ),  # event_type
                base_time + timedelta(seconds=i),  # event_timestamp
                uuid.uuid4() if random.random() > 0.5 else None,  # correlation_id
                json.dumps(
                    {"resolution": "1920x1080", "fps": 30, "codec": "h264"}  # data
                ),
                json.dumps({"batch": batch_num, "index": i}),  # metadata
                base_time + timedelta(seconds=i),  # created_at
            )
            records.append(record)

        await conn.executemany(
            """
            INSERT INTO tracking.frame_events
            (id, event_id, frame_id, camera_id, event_type, event_timestamp,
             correlation_id, data, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            records,
        )

        elapsed = time.time() - start_time
        print(
            f"Batch {batch_num}: Inserted {BATCH_SIZE} records in {elapsed:.2f}s "
            f"({BATCH_SIZE/elapsed:.0f} inserts/sec)"
        )
        return elapsed


async def insert_detections(pool, batch_num):
    """Insert batch of detections."""
    async with pool.acquire() as conn:
        start_time = time.time()

        records = []
        base_time = datetime.now() - timedelta(hours=batch_num)

        for i in range(BATCH_SIZE // 10):  # Less detections than frames
            record = (
                f"detection_{batch_num}_{i}",  # id
                str(uuid.uuid4()),  # detection_id
                f"frame_{batch_num}_{random.randint(0, BATCH_SIZE-1)}",  # frame_id
                random.choice(
                    ["face", "person", "vehicle", "object"]
                ),  # detection_type
                random.uniform(0.7, 0.99),  # confidence
                json.dumps(
                    {  # bbox
                        "x": random.randint(0, 1920),
                        "y": random.randint(0, 1080),
                        "width": random.randint(50, 500),
                        "height": random.randint(50, 500),
                    }
                ),
                json.dumps(
                    {"embedding": [random.random() for _ in range(128)]}  # features
                ),
                base_time + timedelta(seconds=i * 10),  # detected_at
                random.randint(10, 100),  # processing_time_ms
                f"detector_{random.randint(1, 3)}",  # service_name
                "v1.0.0",  # model_version
            )
            records.append(record)

        await conn.executemany(
            """
            INSERT INTO tracking.detections
            (id, detection_id, frame_id, detection_type, confidence, bbox,
             features, detected_at, processing_time_ms, service_name, model_version)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            records,
        )

        elapsed = time.time() - start_time
        print(
            f"Batch {batch_num}: Inserted {len(records)} detections in {elapsed:.2f}s"
        )
        return elapsed


async def query_performance(pool):
    """Test query performance."""
    async with pool.acquire() as conn:
        # Test 1: Recent events query
        start = time.time()
        result = await conn.fetch(
            """
            SELECT COUNT(*), camera_id
            FROM tracking.frame_events
            WHERE event_timestamp > NOW() - INTERVAL '1 hour'
            GROUP BY camera_id
            """
        )
        print(
            f"Query 1 (recent events): {time.time() - start:.3f}s, "
            f"{len(result)} results"
        )

        # Test 2: Time-bucket aggregation
        start = time.time()
        result = await conn.fetch(
            """
            SELECT
                time_bucket('5 minutes', event_timestamp) AS bucket,
                COUNT(*) as event_count
            FROM tracking.frame_events
            WHERE event_timestamp > NOW() - INTERVAL '2 hours'
            GROUP BY bucket
            ORDER BY bucket DESC
            LIMIT 20
            """
        )
        print(
            f"Query 2 (time buckets): {time.time() - start:.3f}s, {len(result)} results"
        )

        # Test 3: Join query
        start = time.time()
        result = await conn.fetch(
            """
            SELECT
                fe.frame_id,
                fe.camera_id,
                COUNT(d.detection_id) as detection_count,
                AVG(d.confidence)::float as avg_confidence
            FROM tracking.frame_events fe
            LEFT JOIN tracking.detections d ON fe.frame_id = d.frame_id
            WHERE fe.event_timestamp > NOW() - INTERVAL '30 minutes'
            GROUP BY fe.frame_id, fe.camera_id
            LIMIT 100
            """
        )
        print(
            f"Query 3 (join with aggregation): {time.time() - start:.3f}s, "
            f"{len(result)} results"
        )


async def main():
    """Run benchmark."""
    print("Starting TimescaleDB benchmark...")
    print(f"Configuration: {BATCH_SIZE} records/batch, {NUM_BATCHES} batches")

    pool = await create_pool()

    try:
        # Insert test data
        print("\n=== INSERT PERFORMANCE ===")
        insert_times = []

        for i in range(NUM_BATCHES):
            elapsed = await insert_frame_events(pool, i)
            insert_times.append(elapsed)
            await insert_detections(pool, i)

        avg_time = sum(insert_times) / len(insert_times)
        total_records = BATCH_SIZE * NUM_BATCHES
        print(f"\nAverage insert time: {avg_time:.2f}s per batch")
        print(f"Average throughput: {BATCH_SIZE/avg_time:.0f} inserts/sec")
        print(f"Total records inserted: {total_records}")

        # Test queries
        print("\n=== QUERY PERFORMANCE ===")
        await query_performance(pool)

        # Check table sizes
        async with pool.acquire() as conn:
            size_result = await conn.fetchrow(
                """
                SELECT
                    pg_size_pretty(pg_total_relation_size(
                        'tracking.frame_events')) as frame_events_size,
                    pg_size_pretty(pg_total_relation_size(
                        'tracking.detections')) as detections_size
                """
            )
            print("\n=== TABLE SIZES ===")
            print(f"frame_events: {size_result['frame_events_size']}")
            print(f"detections: {size_result['detections_size']}")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
