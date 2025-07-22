"""
Repository pattern implementation for metadata storage.

Provides async interface for TimescaleDB operations.
"""

import json
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import asyncpg

from src.domain.models.frame_metadata import (
    FrameMetadata,
    FrameMetadataCreate,
    FrameMetadataQuery,
)

from .retry_decorator import ConnectionPoolManager, with_retry

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Base exception for repository errors."""

    pass


@dataclass
class ConnectionPoolConfig:
    """Configuration for database connection pool."""

    host: str
    port: int
    database: str
    user: str
    password: str
    min_size: int = 5
    max_size: int = 20
    command_timeout: float = 60.0
    max_inactive_connection_lifetime: float = 300.0


class IMetadataRepository(ABC):
    """Interface for metadata repository operations."""

    @abstractmethod
    async def create(self, metadata: FrameMetadataCreate) -> FrameMetadata:
        """Create a single frame metadata record."""
        pass

    @abstractmethod
    async def create_batch(self, metadata_list: List[FrameMetadataCreate]) -> int:
        """Create multiple frame metadata records in batch."""
        pass

    @abstractmethod
    async def get_by_id(self, frame_id: str) -> Optional[FrameMetadata]:
        """Get frame metadata by ID."""
        pass

    @abstractmethod
    async def query(self, query: FrameMetadataQuery) -> List[FrameMetadata]:
        """Query frame metadata with filters."""
        pass

    @abstractmethod
    async def update(
        self, frame_id: str, updates: Dict[str, Any]
    ) -> Optional[FrameMetadata]:
        """Update frame metadata."""
        pass

    @abstractmethod
    async def delete(self, frame_id: str) -> bool:
        """Delete frame metadata."""
        pass

    @abstractmethod
    async def count(self, query: Optional[FrameMetadataQuery] = None) -> int:
        """Count frames matching query."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        pass


class TimescaleMetadataRepository(IMetadataRepository):
    """TimescaleDB implementation of metadata repository."""

    def __init__(
        self,
        pool: Optional[asyncpg.Pool] = None,
        config: Optional[ConnectionPoolConfig] = None,
    ):
        """Initialize repository with connection pool or config."""
        self._pool = pool
        self._config = config
        self._initialized = False
        self._pool_manager: Optional[ConnectionPoolManager] = None

        # If config provided, use pool manager for health checking
        if config and not pool:
            self._pool_manager = ConnectionPoolManager(config)

    async def _ensure_pool(self):
        """Ensure connection pool is initialized."""
        if self._pool is None:
            if self._pool_manager:
                # Use pool manager for health checking
                self._pool = await self._pool_manager.start()
                self._initialized = True
            elif self._config:
                # Direct pool creation without health checking
                self._pool = await asyncpg.create_pool(
                    host=self._config.host,
                    port=self._config.port,
                    database=self._config.database,
                    user=self._config.user,
                    password=self._config.password,
                    min_size=self._config.min_size,
                    max_size=self._config.max_size,
                    command_timeout=self._config.command_timeout,
                    max_inactive_connection_lifetime=(
                        self._config.max_inactive_connection_lifetime
                    ),
                )
                self._initialized = True

    @asynccontextmanager
    async def _get_connection(self):
        """Get database connection from pool."""
        await self._ensure_pool()
        if self._pool is None:
            raise RepositoryError("Connection pool not initialized")

        async with self._pool.acquire() as conn:
            yield conn

    @with_retry(max_attempts=3, initial_delay=0.1, max_delay=1.0)
    async def create(self, metadata: FrameMetadataCreate) -> FrameMetadata:
        """Create a single frame metadata record."""
        frame = metadata.to_frame_metadata()

        query = """
            INSERT INTO metadata.frame_metadata
            (frame_id, timestamp, camera_id, sequence_number, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            RETURNING frame_id, timestamp, camera_id, sequence_number, metadata
        """

        try:
            async with self._get_connection() as conn:
                row = await conn.fetchrow(
                    query,
                    frame.frame_id,
                    frame.timestamp,
                    frame.camera_id,
                    frame.sequence_number,
                    json.dumps(frame.metadata),
                )

                return FrameMetadata(
                    frame_id=row["frame_id"],
                    timestamp=row["timestamp"],
                    camera_id=row["camera_id"],
                    sequence_number=row["sequence_number"],
                    metadata=row["metadata"],
                )
        except asyncpg.PostgresError as e:
            logger.error(f"Failed to create frame metadata: {e}")
            raise RepositoryError(f"Failed to create frame metadata: {e}") from e

    @with_retry(max_attempts=3, initial_delay=0.1, max_delay=1.0)
    async def create_batch(self, metadata_list: List[FrameMetadataCreate]) -> int:
        """Create multiple frame metadata records in batch."""
        if not metadata_list:
            return 0

        # Convert to frame metadata objects
        frames = [m.to_frame_metadata() for m in metadata_list]

        try:
            async with self._get_connection() as conn:
                # Use COPY for better performance with large batches
                if len(frames) > 100:
                    # Prepare data for COPY
                    copy_data = []
                    for f in frames:
                        copy_data.append(
                            (
                                f.frame_id,
                                f.timestamp,
                                f.camera_id,
                                f.sequence_number,
                                json.dumps(f.metadata),
                            )
                        )

                    # Use COPY command for bulk insert
                    await conn.copy_records_to_table(
                        "frame_metadata",
                        schema_name="metadata",
                        records=copy_data,
                        columns=[
                            "frame_id",
                            "timestamp",
                            "camera_id",
                            "sequence_number",
                            "metadata",
                        ],
                    )
                else:
                    # Use executemany for smaller batches
                    data = [
                        (
                            f.frame_id,
                            f.timestamp,
                            f.camera_id,
                            f.sequence_number,
                            json.dumps(f.metadata),
                        )
                        for f in frames
                    ]

                    query = """
                        INSERT INTO metadata.frame_metadata
                        (frame_id, timestamp, camera_id, sequence_number, metadata)
                        VALUES ($1, $2, $3, $4, $5::jsonb)
                    """

                    await conn.executemany(query, data)

                return len(frames)
        except asyncpg.PostgresError as e:
            logger.error(f"Failed to create batch frame metadata: {e}")
            raise RepositoryError(f"Failed to create batch frame metadata: {e}") from e

    @with_retry(max_attempts=3, initial_delay=0.05, max_delay=0.5)
    async def get_by_id(self, frame_id: str) -> Optional[FrameMetadata]:
        """Get frame metadata by ID."""
        query = """
            SELECT frame_id, timestamp, camera_id, sequence_number, metadata
            FROM metadata.frame_metadata
            WHERE frame_id = $1
        """

        try:
            async with self._get_connection() as conn:
                row = await conn.fetchrow(query, frame_id)

                if row is None:
                    return None

                return FrameMetadata(
                    frame_id=row["frame_id"],
                    timestamp=row["timestamp"],
                    camera_id=row["camera_id"],
                    sequence_number=row["sequence_number"],
                    metadata=row["metadata"],
                )
        except asyncpg.PostgresError as e:
            logger.error(f"Failed to get frame metadata by ID: {e}")
            raise RepositoryError(f"Failed to get frame metadata: {e}") from e

    @with_retry(max_attempts=3, initial_delay=0.1, max_delay=1.0)
    async def query(self, query: FrameMetadataQuery) -> List[FrameMetadata]:
        """Query frame metadata with filters."""
        conditions = []
        params = []
        param_count = 0

        # Build WHERE conditions
        if query.camera_id:
            param_count += 1
            conditions.append(f"camera_id = ${param_count}")
            params.append(query.camera_id)

        if query.start_time:
            param_count += 1
            conditions.append(f"timestamp >= ${param_count}")
            params.append(query.start_time)

        if query.end_time:
            param_count += 1
            conditions.append(f"timestamp <= ${param_count}")
            params.append(query.end_time)

        if query.min_motion_score is not None:
            param_count += 1
            conditions.append(
                f"(metadata->'detections'->>'motion_score')::float >= ${param_count}"
            )
            params.append(query.min_motion_score)

        if query.has_faces is not None:
            if query.has_faces:
                conditions.append("(metadata->'detections'->>'faces')::int > 0")
            else:
                conditions.append("(metadata->'detections'->>'faces')::int = 0")

        # Build query
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT frame_id, timestamp, camera_id, sequence_number, metadata
            FROM metadata.frame_metadata
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT {query.limit}
            OFFSET {query.offset}
        """

        try:
            async with self._get_connection() as conn:
                rows = await conn.fetch(sql, *params)

                return [
                    FrameMetadata(
                        frame_id=row["frame_id"],
                        timestamp=row["timestamp"],
                        camera_id=row["camera_id"],
                        sequence_number=row["sequence_number"],
                        metadata=row["metadata"],
                    )
                    for row in rows
                ]
        except asyncpg.PostgresError as e:
            logger.error(f"Failed to query frame metadata: {e}")
            raise RepositoryError(f"Failed to query frame metadata: {e}") from e

    @with_retry(max_attempts=3, initial_delay=0.1, max_delay=1.0)
    async def update(
        self, frame_id: str, updates: Dict[str, Any]
    ) -> Optional[FrameMetadata]:
        """Update frame metadata."""
        # For now, only support updating metadata field
        if "metadata" not in updates:
            return await self.get_by_id(frame_id)

        query = """
            UPDATE metadata.frame_metadata
            SET metadata = $2::jsonb
            WHERE frame_id = $1
            RETURNING frame_id, timestamp, camera_id, sequence_number, metadata
        """

        try:
            async with self._get_connection() as conn:
                row = await conn.fetchrow(
                    query, frame_id, json.dumps(updates["metadata"])
                )

                if row is None:
                    return None

                return FrameMetadata(
                    frame_id=row["frame_id"],
                    timestamp=row["timestamp"],
                    camera_id=row["camera_id"],
                    sequence_number=row["sequence_number"],
                    metadata=row["metadata"],
                )
        except asyncpg.PostgresError as e:
            logger.error(f"Failed to update frame metadata: {e}")
            raise RepositoryError(f"Failed to update frame metadata: {e}") from e

    @with_retry(max_attempts=2, initial_delay=0.1, max_delay=0.5)
    async def delete(self, frame_id: str) -> bool:
        """Delete frame metadata."""
        query = "DELETE FROM metadata.frame_metadata WHERE frame_id = $1"

        try:
            async with self._get_connection() as conn:
                result = await conn.execute(query, frame_id)
                return result.split()[-1] != "0"  # Returns "DELETE n"
        except asyncpg.PostgresError as e:
            logger.error(f"Failed to delete frame metadata: {e}")
            raise RepositoryError(f"Failed to delete frame metadata: {e}") from e

    @with_retry(max_attempts=3, initial_delay=0.05, max_delay=0.5)
    async def count(self, query: Optional[FrameMetadataQuery] = None) -> int:
        """Count frames matching query."""
        if query is None:
            sql = "SELECT COUNT(*) FROM metadata.frame_metadata"
            params = []
        else:
            # Reuse query building logic
            conditions = []
            params = []
            param_count = 0

            if query.camera_id:
                param_count += 1
                conditions.append(f"camera_id = ${param_count}")
                params.append(query.camera_id)

            if query.start_time:
                param_count += 1
                conditions.append(f"timestamp >= ${param_count}")
                params.append(query.start_time)

            if query.end_time:
                param_count += 1
                conditions.append(f"timestamp <= ${param_count}")
                params.append(query.end_time)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = f"SELECT COUNT(*) FROM metadata.frame_metadata WHERE {where_clause}"

        try:
            async with self._get_connection() as conn:
                row = await conn.fetchrow(sql, *params)
                return row["count"]
        except asyncpg.PostgresError as e:
            logger.error(f"Failed to count frame metadata: {e}")
            raise RepositoryError(f"Failed to count frame metadata: {e}") from e

    @with_retry(max_attempts=3, initial_delay=0.1, max_delay=1.0)
    async def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics using continuous aggregates."""
        stats = {}

        try:
            async with self._get_connection() as conn:
                # Total frames
                total_row = await conn.fetchrow(
                    "SELECT COUNT(*) as total FROM metadata.frame_metadata"
                )
                stats["total_frames"] = total_row["total"]

                # Camera statistics from hourly aggregate
                camera_stats = await conn.fetch(
                    """
                    SELECT
                        camera_id,
                        SUM(frame_count) as total_frames,
                        AVG(avg_latency) as avg_latency
                    FROM metadata.frame_stats_hourly
                    WHERE hour >= NOW() - INTERVAL '24 hours'
                    GROUP BY camera_id
                """
                )

                stats["cameras"] = {
                    row["camera_id"]: {
                        "frames": row["total_frames"],
                        "avg_latency": float(row["avg_latency"])
                        if row["avg_latency"]
                        else 0,
                    }
                    for row in camera_stats
                }

                # Last hour statistics from 1-minute aggregate
                hour_stats = await conn.fetchrow(
                    """
                    SELECT
                        SUM(frame_count) as frames,
                        SUM(frames_with_faces) as faces_detected,
                        AVG(avg_motion_score) as avg_motion_score
                    FROM metadata.frame_stats_1min
                    WHERE minute >= NOW() - INTERVAL '1 hour'
                """
                )

                stats["last_hour"] = {
                    "frames": hour_stats["frames"] or 0,
                    "faces_detected": hour_stats["faces_detected"] or 0,
                    "avg_motion_score": float(hour_stats["avg_motion_score"])
                    if hour_stats["avg_motion_score"]
                    else 0,
                }

                return stats
        except asyncpg.PostgresError as e:
            logger.error(f"Failed to get statistics: {e}")
            raise RepositoryError(f"Failed to get statistics: {e}") from e

    async def close(self):
        """Close connection pool."""
        if self._pool_manager:
            await self._pool_manager.stop()
        elif self._pool and self._initialized:
            await self._pool.close()

    def get_pool_stats(self) -> Optional[Dict[str, Any]]:
        """Get connection pool statistics."""
        if self._pool_manager:
            return self._pool_manager.get_stats()
        elif self._pool:
            return {
                "pool_size": self._pool.get_size(),
                "idle_connections": self._pool.get_idle_size(),
                "busy_connections": self._pool.get_size() - self._pool.get_idle_size(),
            }
        return None
