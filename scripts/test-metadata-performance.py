#!/usr/bin/env python3
"""
Performance test for metadata storage in TimescaleDB.

Tests insertion of 10k records and measures performance.
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from uuid import uuid4

import asyncpg

# Connection parameters
DB_HOST = "192.168.1.193"  # Nebula server
DB_PORT = 5432
DB_NAME = "detektor_db"
DB_USER = "detektor"
DB_PASSWORD = "detektor_pass"

# Test parameters
BATCH_SIZE = 1000
TOTAL_RECORDS = 10000
CAMERAS = [f"cam{i:02d}" for i in range(1, 11)]  # 10 cameras


async def create_pool():
    """Create connection pool."""
    return await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        min_size=5,
        max_size=20,
    )


def generate_frame_data(camera_id: str, sequence: int, timestamp: datetime):
    """Generate realistic frame metadata."""
    return {
        "frame_id": f"{timestamp.isoformat()}_{camera_id}_{sequence:06d}",
        "timestamp": timestamp,
        "camera_id": camera_id,
        "sequence_number": sequence,
        "metadata": json.dumps(
            {
                "detections": {
                    "faces": random.randint(0, 3),
                    "objects": random.choice([["person"], ["person", "car"], []]),
                    "motion_score": round(random.random(), 2),
                },
                "processing": {
                    "capture_latency_ms": random.randint(10, 30),
                    "processing_latency_ms": random.randint(30, 80),
                    "total_latency_ms": random.randint(40, 110),
                },
                "trace_id": str(uuid4()),
                "span_id": str(uuid4())[:16],
            }
        ),
    }


async def insert_batch(pool, frames):
    """Insert batch of frames."""
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO metadata.frame_metadata
            (frame_id, timestamp, camera_id, sequence_number, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            [
                (
                    f["frame_id"],
                    f["timestamp"],
                    f["camera_id"],
                    f["sequence_number"],
                    f["metadata"],
                )
                for f in frames
            ],
        )


async def run_performance_test():
    """Run the performance test."""
    print(
        f"Starting performance test: {TOTAL_RECORDS} records in batches of {BATCH_SIZE}"
    )
    print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME}...")

    pool = await create_pool()

    try:
        # Generate test data
        print("Generating test data...")
        start_time = datetime.now() - timedelta(hours=1)
        frames = []

        for i in range(TOTAL_RECORDS):
            camera = CAMERAS[i % len(CAMERAS)]
            timestamp = start_time + timedelta(seconds=i / 10)  # 10 fps
            frame = generate_frame_data(camera, i, timestamp)
            frames.append(frame)

        # Insert data in batches
        print(f"Inserting {TOTAL_RECORDS} records...")
        insert_start = time.time()

        for i in range(0, len(frames), BATCH_SIZE):
            batch = frames[i : i + BATCH_SIZE]
            await insert_batch(pool, batch)

            if (i + BATCH_SIZE) % 1000 == 0:
                elapsed = time.time() - insert_start
                rate = (i + BATCH_SIZE) / elapsed
                print(
                    f"Progress: {i + BATCH_SIZE}/{TOTAL_RECORDS} "
                    f"({rate:.1f} records/sec)"
                )

        insert_end = time.time()
        total_time = insert_end - insert_start

        print("\n=== Performance Results ===")
        print(f"Total records inserted: {TOTAL_RECORDS}")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Average rate: {TOTAL_RECORDS / total_time:.1f} records/second")
        print(f"Batch size: {BATCH_SIZE}")

        # Test query performance
        print("\n=== Query Performance ===")

        # Point query
        async with pool.acquire() as conn:
            query_start = time.time()
            result = await conn.fetchrow(
                "SELECT * FROM metadata.frame_metadata WHERE frame_id = $1",
                frames[0]["frame_id"],
            )
            query_time = (time.time() - query_start) * 1000
            print(f"Point query by frame_id: {query_time:.2f}ms")

        # Range query
        async with pool.acquire() as conn:
            query_start = time.time()
            results = await conn.fetch(
                """
                SELECT * FROM metadata.frame_metadata
                WHERE camera_id = $1 AND timestamp > NOW() - INTERVAL '10 minutes'
                ORDER BY timestamp DESC
                LIMIT 100
                """,
                CAMERAS[0],
            )
            query_time = (time.time() - query_start) * 1000
            print(
                f"Range query (last 10 min): {query_time:.2f}ms ({len(results)} rows)"
            )

        # Aggregation query
        async with pool.acquire() as conn:
            query_start = time.time()
            results = await conn.fetch(
                """
                SELECT camera_id,
                       COUNT(*) as total_frames,
                       AVG((metadata->>'motion_score')::float) as avg_motion
                FROM metadata.frame_metadata
                WHERE timestamp > NOW() - INTERVAL '1 hour'
                GROUP BY camera_id
                """
            )
            query_time = (time.time() - query_start) * 1000
            print(f"Aggregation query: {query_time:.2f}ms ({len(results)} cameras)")

        # Check continuous aggregates
        async with pool.acquire() as conn:
            result = await conn.fetchrow("SELECT COUNT(*) FROM metadata.frame_metadata")
            print(f"\nTotal records in database: {result['count']}")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_performance_test())
