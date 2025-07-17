"""Example of frame repository usage."""

import asyncio
import os
from datetime import datetime, timedelta

from src.contexts.monitoring.domain.frame_tracking import FrameTrackingQueries
from src.contexts.monitoring.infrastructure import (
    FrameMetadataRepository,
    TimeRange,
    create_pool,
)
from src.shared.kernel.domain import Frame, ProcessingState
from src.shared.kernel.events import (
    FrameCaptured,
    ProcessingCompleted,
    ProcessingFailed,
)


async def demo_repository():
    """Demonstrate frame repository functionality."""
    # Get database connection from environment
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_name = os.getenv("DB_NAME", "detektor")
    db_user = os.getenv("DB_USER", "detektor_app")
    db_pass = os.getenv("DB_PASS", "")

    print(f"Connecting to database {db_name} at {db_host}:{db_port}...")

    try:
        # Create connection pool
        pool = await create_pool(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass,
        )

        # Create repository
        repo = FrameMetadataRepository(pool)
        queries = FrameTrackingQueries(repo)

        print("\n=== Creating and saving frames ===")

        # Create some test frames
        frames = []
        for i in range(5):
            frame = Frame.create(
                camera_id=f"cam0{i % 3 + 1}",
                timestamp=datetime.now() - timedelta(minutes=i * 5),
            )

            # Simulate processing
            frame.transition_to(ProcessingState.QUEUED)
            frame.transition_to(ProcessingState.PROCESSING)

            # Add processing stages
            stage1 = frame.start_processing_stage("face_detection")
            stage1.complete({"faces_found": i % 3})

            stage2 = frame.start_processing_stage("object_detection")

            # Simulate some failures
            if i % 4 == 0:
                stage2.fail("GPU out of memory")
                frame.mark_as_failed("GPU out of memory")
            else:
                stage2.complete({"objects_found": i + 1})
                frame.mark_as_completed()

            # Save frame
            await repo.save(frame)
            frames.append(frame)

            # Save events
            await repo.save_event(
                FrameCaptured(
                    frame_id=str(frame.id),
                    camera_id=frame.camera_id,
                    timestamp=frame.timestamp,
                ),
                str(frame.id),
            )

            if frame.state == ProcessingState.COMPLETED:
                await repo.save_event(
                    ProcessingCompleted(
                        frame_id=str(frame.id),
                        processor_id="example-processor",
                        processing_type="full",
                        duration_ms=frame.total_processing_time_ms,
                        results={"stages": len(frame.processing_stages)},
                    ),
                    str(frame.id),
                )
            elif frame.state == ProcessingState.FAILED:
                await repo.save_event(
                    ProcessingFailed(
                        frame_id=str(frame.id),
                        processor_id="example-processor",
                        processing_type="full",
                        error="GPU out of memory",
                        duration_ms=frame.total_processing_time_ms,
                        retry_count=0,
                    ),
                    str(frame.id),
                )

            print(f"Saved frame {frame.id} - State: {frame.state.value}")

        print("\n=== Querying frames ===")

        # Find completed frames
        completed = await repo.find_by_status(
            ProcessingState.COMPLETED, time_range=TimeRange.last_hour()
        )
        print(f"Found {len(completed)} completed frames in last hour")

        # Find failed frames
        failed = await repo.find_by_status(
            ProcessingState.FAILED, time_range=TimeRange.last_hour()
        )
        print(f"Found {len(failed)} failed frames in last hour")

        # Get recent frames
        recent = await repo.find_recent(limit=10)
        print("\nRecent frames:")
        for frame_data in recent:
            print(
                f"  - {frame_data['frame_id']}: {frame_data['state']} "
                f"({len(frame_data['stages'])} stages)"
            )

        # Get performance stats
        stats = await repo.get_performance_stats(hours=1)
        if stats:
            print("\nPerformance stats:")
            for stat in stats:
                print(
                    f"  - Camera {stat['camera_id']}: "
                    f"avg={stat['avg_time_ms']:.1f}ms, "
                    f"p95={stat['p95_time_ms']:.1f}ms"
                )

        print("\n=== Frame tracking queries ===")

        # Get camera stats
        for camera_id in ["cam01", "cam02", "cam03"]:
            camera_stats = await queries.get_camera_stats(camera_id, hours=1)
            if camera_stats:
                stat = camera_stats[0]
                print(f"\nCamera {camera_id} stats:")
                print(f"  - Total frames: {stat.total_frames}")
                print(f"  - Success rate: {stat.success_rate:.1f}%")
                print(
                    f"  - Avg time: {stat.avg_processing_time_ms:.1f}ms"
                    if stat.avg_processing_time_ms
                    else "  - Avg time: N/A"
                )

        # Find slow frames
        slow_frames = await queries.find_slow_frames(threshold_ms=50, hours=1)
        if slow_frames:
            print(f"\nFound {len(slow_frames)} slow frames (>50ms):")
            for frame in slow_frames[:3]:
                print(f"  - {frame['frame_id']}: {frame['total_time_ms']:.1f}ms")

        # Get failure analysis
        failure_analysis = await queries.get_failure_analysis(hours=1)
        print("\nFailure analysis:")
        print(f"  - Total failures: {failure_analysis['total_failures']}")
        if failure_analysis["top_error"]:
            print(f"  - Top error: {failure_analysis['top_error']}")
        if failure_analysis["most_failing_camera"]:
            print(f"  - Most failing camera: {failure_analysis['most_failing_camera']}")

        # Get frame journey
        if frames:
            test_frame = frames[0]
            journey = await queries.get_frame_journey(str(test_frame.id))
            if journey:
                print(f"\nFrame journey for {journey['frame_id']}:")
                print(f"  - State: {journey['current_state']}")
                print(f"  - Stages: {len(journey['stages'])}")
                print(f"  - Events: {len(journey['events'])}")
                print(f"  - Timeline entries: {len(journey['timeline'])}")

                print("\n  Timeline:")
                for entry in journey["timeline"][:5]:
                    print(f"    - {entry['timestamp']}: {entry['description']}")

        print("\n=== Cleanup ===")

        # Optional: Clean up test data
        # deleted = await repo.cleanup_old_data(days=0)
        # print(f"Cleaned up {deleted} old frames")

    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure TimescaleDB is running and the schema is created:")
        print("  1. Start TimescaleDB container")
        print(
            "  2. Run migration: "
            "psql -d detektor -f migrations/001_frame_metadata_schema.sql"
        )
        print("  3. Set environment variables: DB_HOST, DB_USER, DB_PASS")

    finally:
        if "pool" in locals():
            await pool.close()


if __name__ == "__main__":
    print("Frame Repository Example")
    print("=" * 50)
    asyncio.run(demo_repository())
