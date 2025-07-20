"""Repository pattern for database operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from models import EventType, FrameEvent
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class FrameEventRepository:
    """Repository for frame event operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db
        self.logger = structlog.get_logger()

    async def create_event(
        self,
        frame_id: str,
        camera_id: str,
        event_type: EventType,
        data: Dict[str, Any],
        metadata: Dict[str, Any],
        correlation_id: Optional[UUID] = None,
    ) -> FrameEvent:
        """Create a new frame event."""
        event = FrameEvent(
            frame_id=frame_id,
            camera_id=camera_id,
            event_type=event_type,
            data=data,
            metadata=metadata,
            correlation_id=correlation_id,
        )

        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)

        self.logger.info(
            "frame_event_created",
            event_id=str(event.event_id),
            frame_id=frame_id,
            event_type=event_type,
        )

        return event

    async def get_frame_events(
        self, frame_id: str, limit: int = 100, offset: int = 0
    ) -> List[FrameEvent]:
        """Get all events for a frame in chronological order."""
        query = (
            select(FrameEvent)
            .where(FrameEvent.frame_id == frame_id)
            .order_by(FrameEvent.event_timestamp)
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_frame_events(self, frame_id: str) -> int:
        """Count total events for a frame."""
        query = (
            select(func.count())
            .select_from(FrameEvent)
            .where(FrameEvent.frame_id == frame_id)
        )

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_latest_events(
        self, camera_id: Optional[str] = None, limit: int = 10
    ) -> List[FrameEvent]:
        """Get latest events, optionally filtered by camera."""
        query = (
            select(FrameEvent).order_by(desc(FrameEvent.event_timestamp)).limit(limit)
        )

        if camera_id:
            query = query.where(FrameEvent.camera_id == camera_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_events_by_type(
        self,
        event_type: EventType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[FrameEvent]:
        """Get events by type within a time range."""
        conditions = [FrameEvent.event_type == event_type]

        if start_time:
            conditions.append(FrameEvent.event_timestamp >= start_time)
        if end_time:
            conditions.append(FrameEvent.event_timestamp <= end_time)

        query = (
            select(FrameEvent)
            .where(and_(*conditions))
            .order_by(desc(FrameEvent.event_timestamp))
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_camera_activity(
        self, camera_id: str, hours: int = 24
    ) -> Dict[str, Any]:
        """Get camera activity statistics."""
        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Count events by type
        query = (
            select(
                FrameEvent.event_type,
                func.count(FrameEvent.event_id).label("count"),
            )
            .where(
                and_(
                    FrameEvent.camera_id == camera_id,
                    FrameEvent.event_timestamp >= cutoff_time,
                )
            )
            .group_by(FrameEvent.event_type)
        )

        result = await self.db.execute(query)
        event_counts = {row.event_type: row.count for row in result}

        # Get total frames
        total_query = select(func.count(func.distinct(FrameEvent.frame_id))).where(
            and_(
                FrameEvent.camera_id == camera_id,
                FrameEvent.event_timestamp >= cutoff_time,
            )
        )

        total_result = await self.db.execute(total_query)
        total_frames = total_result.scalar() or 0

        return {
            "camera_id": camera_id,
            "period_hours": hours,
            "total_frames": total_frames,
            "event_counts": event_counts,
            "last_activity": await self._get_last_activity(camera_id),
        }

    async def _get_last_activity(self, camera_id: str) -> Optional[datetime]:
        """Get timestamp of last activity for a camera."""
        query = select(func.max(FrameEvent.event_timestamp)).where(
            FrameEvent.camera_id == camera_id
        )

        result = await self.db.execute(query)
        return result.scalar()
