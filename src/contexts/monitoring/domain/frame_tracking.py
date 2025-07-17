"""Frame tracking domain logic and queries."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.shared.kernel.domain import ProcessingState
from src.shared.telemetry import traced_method


@dataclass
class FrameStats:
    """Frame processing statistics."""

    camera_id: str
    hour: datetime
    total_frames: int
    completed_frames: int
    failed_frames: int
    avg_processing_time_ms: Optional[float]
    max_processing_time_ms: Optional[float]
    min_processing_time_ms: Optional[float]

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_frames == 0:
            return 0.0
        return (self.completed_frames / self.total_frames) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_frames == 0:
            return 0.0
        return (self.failed_frames / self.total_frames) * 100


@dataclass
class ProcessingPerformance:
    """Processing performance metrics."""

    camera_id: str
    hour: datetime
    frames_processed: int
    avg_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    p99_time_ms: float

    def is_degraded(self, baseline_p95: float) -> bool:
        """Check if performance is degraded compared to baseline.

        Args:
            baseline_p95: Baseline 95th percentile in ms

        Returns:
            True if current p95 is 2x worse than baseline
        """
        return self.p95_time_ms > (baseline_p95 * 2)


class FrameTrackingQueries:
    """Domain queries for frame tracking."""

    def __init__(self, repository: Any) -> None:
        """Initialize with repository.

        Args:
            repository: Frame metadata repository
        """
        self.repository = repository

    @traced_method()
    async def get_camera_stats(
        self,
        camera_id: str,
        hours: int = 24,
    ) -> List[FrameStats]:
        """Get frame statistics for a camera.

        Args:
            camera_id: Camera to get stats for
            hours: Number of hours to look back

        Returns:
            List of hourly statistics
        """
        # This would typically use the continuous aggregate
        # For now, we'll use a simplified query
        stats = []

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # Get frames in time range
        from ..infrastructure import TimeRange

        time_range = TimeRange(start_time, end_time)

        # Get counts by state
        completed = await self.repository.find_by_status(
            ProcessingState.COMPLETED,
            time_range=time_range,
            camera_id=camera_id,
        )

        failed = await self.repository.find_by_status(
            ProcessingState.FAILED,
            time_range=time_range,
            camera_id=camera_id,
        )

        # Calculate stats (simplified - in production would use DB aggregation)
        total_frames = len(completed) + len(failed)

        if total_frames > 0:
            processing_times = [
                f.total_processing_time_ms
                for f in completed
                if f.total_processing_time_ms
            ]

            avg_time = (
                sum(processing_times) / len(processing_times)
                if processing_times
                else None
            )
            max_time = max(processing_times) if processing_times else None
            min_time = min(processing_times) if processing_times else None

            stats.append(
                FrameStats(
                    camera_id=camera_id,
                    hour=start_time,
                    total_frames=total_frames,
                    completed_frames=len(completed),
                    failed_frames=len(failed),
                    avg_processing_time_ms=avg_time,
                    max_processing_time_ms=max_time,
                    min_processing_time_ms=min_time,
                )
            )

        return stats

    @traced_method()
    async def find_slow_frames(
        self,
        threshold_ms: float = 1000,
        hours: int = 1,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Find frames that took longer than threshold to process.

        Args:
            threshold_ms: Processing time threshold in milliseconds
            hours: Number of hours to look back
            limit: Maximum results

        Returns:
            List of slow frames with details
        """
        # In production, this would be a direct SQL query
        # For now, we'll filter in memory
        from ..infrastructure import TimeRange

        time_range = TimeRange.last_hour() if hours == 1 else TimeRange.last_day()

        completed_frames = await self.repository.find_by_status(
            ProcessingState.COMPLETED,
            time_range=time_range,
            limit=limit * 2,  # Get more to filter
        )

        slow_frames = []
        for frame in completed_frames:
            if (
                frame.total_processing_time_ms
                and frame.total_processing_time_ms > threshold_ms
            ):
                # Get detailed stage info
                full_frame = await self.repository.get_by_id(frame.id)

                if full_frame:
                    slow_frames.append(
                        {
                            "frame_id": str(full_frame.id),
                            "camera_id": full_frame.camera_id,
                            "timestamp": full_frame.timestamp.isoformat(),
                            "total_time_ms": full_frame.total_processing_time_ms,
                            "stages": [
                                {
                                    "name": stage.name,
                                    "duration_ms": stage.duration_ms,
                                    "status": stage.status,
                                }
                                for stage in full_frame.processing_stages
                            ],
                        }
                    )

                if len(slow_frames) >= limit:
                    break

        return slow_frames

    @traced_method()
    async def get_failure_analysis(
        self,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Analyze frame processing failures.

        Args:
            hours: Number of hours to analyze

        Returns:
            Failure analysis with patterns
        """
        from ..infrastructure import TimeRange

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        time_range = TimeRange(start_time, end_time)

        # Get failed frames
        failed_frames = await self.repository.find_by_status(
            ProcessingState.FAILED,
            time_range=time_range,
        )

        # Analyze failures
        failure_by_camera: Dict[str, int] = {}
        failure_by_error: Dict[str, int] = {}
        failure_by_stage: Dict[str, int] = {}

        for frame in failed_frames:
            # Count by camera
            failure_by_camera[frame.camera_id] = (
                failure_by_camera.get(frame.camera_id, 0) + 1
            )

            # Count by error type
            error = frame.metadata.get("error", "unknown")
            failure_by_error[error] = failure_by_error.get(error, 0) + 1

            # Get detailed frame to find failed stage
            full_frame = await self.repository.get_by_id(frame.id)
            if full_frame:
                for stage in full_frame.processing_stages:
                    if stage.status == "failed":
                        failure_by_stage[stage.name] = (
                            failure_by_stage.get(stage.name, 0) + 1
                        )

        return {
            "total_failures": len(failed_frames),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "failures_by_camera": failure_by_camera,
            "failures_by_error": failure_by_error,
            "failures_by_stage": failure_by_stage,
            "top_error": max(failure_by_error.items(), key=lambda x: x[1])[0]
            if failure_by_error
            else None,
            "most_failing_camera": (
                max(failure_by_camera.items(), key=lambda x: x[1])[0]
                if failure_by_camera
                else None
            ),
        }

    @traced_method()
    async def get_frame_journey(self, frame_id: str) -> Optional[Dict[str, Any]]:
        """Get complete journey of a frame through the system.

        Args:
            frame_id: Frame ID to trace

        Returns:
            Complete frame journey with events and stages
        """
        from src.shared.kernel.domain import FrameId

        # Get frame
        frame = await self.repository.get_by_id(FrameId(frame_id))
        if not frame:
            return None

        # Get all events
        events = await self.repository.get_events(frame_id)

        # Build journey
        journey = {
            "frame_id": str(frame.id),
            "camera_id": frame.camera_id,
            "captured_at": frame.timestamp.isoformat(),
            "current_state": frame.state.value,
            "total_duration_ms": frame.total_processing_time_ms,
            "metadata": frame.metadata,
            "stages": [
                {
                    "name": stage.name,
                    "started_at": stage.started_at.isoformat(),
                    "completed_at": stage.completed_at.isoformat()
                    if stage.completed_at
                    else None,
                    "duration_ms": stage.duration_ms,
                    "status": stage.status,
                    "metadata": stage.metadata,
                    "error": stage.error,
                }
                for stage in frame.processing_stages
            ],
            "events": events,
            "timeline": self._build_timeline(frame, events),
        }

        return journey

    def _build_timeline(
        self, frame: Any, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build chronological timeline of frame processing.

        Args:
            frame: Frame object
            events: List of events

        Returns:
            Chronological timeline
        """
        timeline = []

        # Add frame creation
        timeline.append(
            {
                "timestamp": frame.created_at.isoformat(),
                "type": "frame_created",
                "description": f"Frame {frame.id} captured from {frame.camera_id}",
            }
        )

        # Add events
        for event in events:
            timeline.append(
                {
                    "timestamp": event["occurred_at"],
                    "type": event["event_type"],
                    "description": self._describe_event(event),
                    "data": event["data"],
                }
            )

        # Add stage transitions
        for stage in frame.processing_stages:
            timeline.append(
                {
                    "timestamp": stage.started_at.isoformat(),
                    "type": "stage_started",
                    "description": f"Started {stage.name}",
                }
            )

            if stage.completed_at:
                timeline.append(
                    {
                        "timestamp": stage.completed_at.isoformat(),
                        "type": "stage_completed"
                        if stage.status == "completed"
                        else "stage_failed",
                        "description": (
                            f"{stage.name} {stage.status} "
                            f"({stage.duration_ms:.0f}ms)"
                        ),
                    }
                )

        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])

        return timeline

    def _describe_event(self, event: Dict[str, Any]) -> str:
        """Generate human-readable event description.

        Args:
            event: Event data

        Returns:
            Description string
        """
        event_type = event["event_type"]
        data = event["data"]

        descriptions = {
            "frame.captured": f"Frame captured from camera {data.get('camera_id')}",
            "frame.queued": f"Frame queued in {data.get('queue_name', 'default')}",
            "frame.processing_started": (
                f"Processing started by {data.get('processor_id')}"
            ),
            "frame.processing_completed": (
                f"Processing completed in {data.get('duration_ms', 0):.0f}ms"
            ),
            "frame.processing_failed": f"Processing failed: {data.get('error')}",
        }

        return descriptions.get(event_type, f"Event: {event_type}")
