"""Frame metadata repository implementation with TimescaleDB."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import asyncpg
from asyncpg import Pool

from src.shared.kernel.domain import Frame, FrameId, ProcessingState
from src.shared.kernel.events import DomainEvent
from src.shared.telemetry import traced_method


class TimeRange:
    """Time range for queries."""

    def __init__(self, start: datetime, end: datetime):
        """Initialize time range.

        Args:
            start: Start time
            end: End time
        """
        self.start = start
        self.end = end

    @classmethod
    def last_hour(cls) -> "TimeRange":
        """Get last hour time range."""
        now = datetime.now()
        return cls(now - timedelta(hours=1), now)

    @classmethod
    def last_day(cls) -> "TimeRange":
        """Get last day time range."""
        now = datetime.now()
        return cls(now - timedelta(days=1), now)


class FrameMetadataRepository:
    """Repository for frame metadata persistence."""

    def __init__(self, pool: Pool):
        """Initialize repository with connection pool.

        Args:
            pool: AsyncPG connection pool
        """
        self.pool = pool

    @traced_method()
    async def save(self, frame: Frame) -> None:
        """Save frame metadata to database.

        Args:
            frame: Frame to save
        """
        async with self.pool.acquire() as conn:
            # Save frame metadata
            await conn.execute(
                """
                INSERT INTO frame_metadata (
                    frame_id, camera_id, timestamp, state,
                    created_at, updated_at, metadata, error_message,
                    total_processing_time_ms
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (frame_id) DO UPDATE SET
                    state = EXCLUDED.state,
                    updated_at = EXCLUDED.updated_at,
                    metadata = EXCLUDED.metadata,
                    error_message = EXCLUDED.error_message,
                    total_processing_time_ms = EXCLUDED.total_processing_time_ms
                """,
                str(frame.id),
                frame.camera_id,
                frame.timestamp,
                frame.state.value,
                frame.created_at,
                frame.updated_at,
                json.dumps(frame.metadata),
                frame.metadata.get("error"),
                frame.total_processing_time_ms,
            )

            # Save processing stages
            for idx, stage in enumerate(frame.processing_stages):
                await conn.execute(
                    """
                    INSERT INTO processing_stages (
                        frame_id, stage_index, stage_name,
                        started_at, completed_at, status,
                        metadata, error_message, duration_ms
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (frame_id, stage_index) DO UPDATE SET
                        completed_at = EXCLUDED.completed_at,
                        status = EXCLUDED.status,
                        metadata = EXCLUDED.metadata,
                        error_message = EXCLUDED.error_message,
                        duration_ms = EXCLUDED.duration_ms
                    """,
                    str(frame.id),
                    idx,
                    stage.name,
                    stage.started_at,
                    stage.completed_at,
                    stage.status,
                    json.dumps(stage.metadata),
                    stage.error,
                    stage.duration_ms,
                )

    @traced_method()
    async def get_by_id(self, frame_id: FrameId) -> Optional[Frame]:
        """Get frame by ID.

        Args:
            frame_id: Frame ID to retrieve

        Returns:
            Frame if found, None otherwise
        """
        async with self.pool.acquire() as conn:
            # Get frame metadata
            row = await conn.fetchrow(
                """
                SELECT frame_id, camera_id, timestamp, state,
                       created_at, updated_at, metadata, error_message,
                       total_processing_time_ms
                FROM frame_metadata
                WHERE frame_id = $1
                """,
                str(frame_id),
            )

            if not row:
                return None

            # Create frame object
            frame = Frame(
                id=FrameId(row["frame_id"]),
                camera_id=row["camera_id"],
                timestamp=row["timestamp"],
                state=ProcessingState(row["state"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                processing_stages=[],
            )

            # Get processing stages
            stages = await conn.fetch(
                """
                SELECT stage_name, started_at, completed_at,
                       status, metadata, error_message, duration_ms
                FROM processing_stages
                WHERE frame_id = $1
                ORDER BY stage_index
                """,
                str(frame_id),
            )

            # Add stages to frame
            for stage_row in stages:
                from src.shared.kernel.domain import ProcessingStage

                stage = ProcessingStage(
                    name=stage_row["stage_name"],
                    started_at=stage_row["started_at"],
                    completed_at=stage_row["completed_at"],
                    status=stage_row["status"],
                    metadata=json.loads(stage_row["metadata"])
                    if stage_row["metadata"]
                    else {},
                    error=stage_row["error_message"],
                )
                frame.processing_stages.append(stage)

            return frame

    @traced_method()
    async def find_by_status(
        self,
        status: ProcessingState,
        time_range: Optional[TimeRange] = None,
        camera_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Frame]:
        """Find frames by status.

        Args:
            status: Processing state to filter by
            time_range: Optional time range filter
            camera_id: Optional camera ID filter
            limit: Maximum number of results

        Returns:
            List of frames matching criteria
        """
        query = """
            SELECT frame_id, camera_id, timestamp, state,
                   created_at, updated_at, metadata, error_message,
                   total_processing_time_ms
            FROM frame_metadata
            WHERE state = $1
        """
        params: List[Any] = [status.value]
        param_num = 2

        if time_range:
            query += f" AND timestamp BETWEEN ${param_num} AND ${param_num + 1}"
            params.extend([time_range.start, time_range.end])
            param_num += 2

        if camera_id:
            query += f" AND camera_id = ${param_num}"
            params.append(camera_id)
            param_num += 1

        query += f" ORDER BY timestamp DESC LIMIT ${param_num}"
        params.append(limit)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            frames = []
            for row in rows:
                frame = Frame(
                    id=FrameId(row["frame_id"]),
                    camera_id=row["camera_id"],
                    timestamp=row["timestamp"],
                    state=ProcessingState(row["state"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    processing_stages=[],
                )
                frames.append(frame)

            return frames

    @traced_method()
    async def find_recent(
        self,
        camera_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Find recent frames with stages.

        Args:
            camera_id: Optional camera ID filter
            limit: Maximum number of results

        Returns:
            List of frame data with stages
        """
        query = """
            SELECT frame_id, camera_id, timestamp, state,
                   created_at, updated_at, metadata, error_message,
                   total_processing_time_ms, stages
            FROM recent_frames
        """
        params: List[Any] = []

        if camera_id:
            query += " WHERE camera_id = $1"
            params.append(camera_id)

        query += f" LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            return [dict(row) for row in rows]

    @traced_method()
    async def get_performance_stats(
        self,
        camera_id: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get performance statistics.

        Args:
            camera_id: Optional camera ID filter
            hours: Number of hours to look back

        Returns:
            Performance statistics by hour
        """
        query = """
            SELECT camera_id, hour,
                   frames_processed, avg_time_ms,
                   median_time_ms, p95_time_ms, p99_time_ms
            FROM performance_stats
            WHERE hour > NOW() - INTERVAL '%s hours'
        """
        params: List[Any] = [hours]

        if camera_id:
            query += " AND camera_id = $2"
            params.append(camera_id)

        query += " ORDER BY hour DESC, camera_id"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            return [dict(row) for row in rows]

    @traced_method()
    async def save_event(self, event: DomainEvent, frame_id: str) -> None:
        """Save domain event.

        Args:
            event: Domain event to save
            frame_id: Associated frame ID
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO frame_events (
                    event_type, frame_id, occurred_at, data, metadata
                ) VALUES ($1, $2, $3, $4, $5)
                """,
                event.event_type,
                frame_id,
                event.occurred_at,
                json.dumps(event.to_dict()["data"]),
                json.dumps(event.metadata),
            )

    @traced_method()
    async def get_events(
        self,
        frame_id: str,
        event_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get events for a frame.

        Args:
            frame_id: Frame ID
            event_types: Optional filter by event types

        Returns:
            List of events
        """
        query = """
            SELECT event_id, event_type, occurred_at, data, metadata
            FROM frame_events
            WHERE frame_id = $1
        """
        params: List[Any] = [frame_id]

        if event_types:
            placeholders = ",".join(f"${i}" for i in range(2, len(event_types) + 2))
            query += f" AND event_type IN ({placeholders})"
            params.extend(event_types)

        query += " ORDER BY occurred_at"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            return [
                {
                    "event_id": str(row["event_id"]),
                    "event_type": row["event_type"],
                    "occurred_at": row["occurred_at"].isoformat(),
                    "data": json.loads(row["data"]),
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
                for row in rows
            ]

    @traced_method()
    async def cleanup_old_data(self, days: int = 30) -> int:
        """Clean up old frame data.

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted frames
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM frame_metadata
                WHERE timestamp < NOW() - INTERVAL '%s days'
                """,
                days,
            )

            return int(result.split()[-1])


async def create_pool(
    host: str = "localhost",
    port: int = 5432,
    database: str = "detektor",
    user: str = "detektor_app",
    password: str = "",
    min_size: int = 10,
    max_size: int = 20,
) -> Pool:
    """Create connection pool for repository.

    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user
        password: Database password
        min_size: Minimum pool size
        max_size: Maximum pool size

    Returns:
        AsyncPG connection pool
    """
    return await asyncpg.create_pool(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        min_size=min_size,
        max_size=max_size,
    )
