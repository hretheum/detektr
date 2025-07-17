"""Storage layer with observability."""

import logging
import time
from collections import defaultdict
from typing import Any, Dict, Optional

from src.shared.telemetry import get_metrics, record_processing_time, traced

logger = logging.getLogger(__name__)


class FrameStorage:
    """In-memory storage for frame processing results with observability."""

    def __init__(self):
        """Initialize storage."""
        self.frames: Dict[str, Dict[str, Any]] = {}
        self.camera_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "frames_processed": 0,
                "total_detections": 0,
                "avg_processing_time": 0.0,
                "last_frame_time": 0.0,
            }
        )
        self.metrics = get_metrics("frame_storage")

        logger.info("Frame storage initialized")

    @traced
    async def store_frame_results(
        self, frame_id: str, camera_id: str, results: Dict[str, Any]
    ) -> None:
        """Store frame processing results.

        Args:
            frame_id: Unique frame identifier
            camera_id: Camera identifier
            results: Processing results to store
        """
        start_time = time.time()

        try:
            # Store frame results
            self.frames[frame_id] = {
                "frame_id": frame_id,
                "camera_id": camera_id,
                "results": results,
                "stored_at": time.time(),
            }

            # Update camera statistics
            self._update_camera_stats(camera_id, results)

            # Record metrics
            duration = time.time() - start_time
            record_processing_time(
                "frame_storage", "store", duration, camera_id=camera_id
            )

            # Record storage size metrics
            self.metrics.record_queue_size("stored_frames", len(self.frames))

            logger.debug(f"Stored results for frame {frame_id} from camera {camera_id}")

        except Exception as e:
            self.metrics.increment_errors(
                "storage_error",
                {
                    "error_type": type(e).__name__,
                    "camera_id": camera_id,
                },
            )
            logger.error(f"Error storing frame {frame_id}: {e}", exc_info=True)
            raise

    @traced
    async def get_frame_results(self, frame_id: str) -> Optional[Dict[str, Any]]:
        """Get processing results for a specific frame.

        Args:
            frame_id: Unique frame identifier

        Returns:
            Frame results or None if not found
        """
        start_time = time.time()

        try:
            result = self.frames.get(frame_id)

            # Record metrics
            duration = time.time() - start_time
            record_processing_time("frame_storage", "retrieve", duration)

            if result:
                logger.debug(f"Retrieved results for frame {frame_id}")
            else:
                logger.debug(f"Frame {frame_id} not found in storage")
                self.metrics.increment_errors("frame_not_found", {"frame_id": frame_id})

            return result

        except Exception as e:
            self.metrics.increment_errors(
                "retrieval_error",
                {
                    "error_type": type(e).__name__,
                    "frame_id": frame_id,
                },
            )
            logger.error(f"Error retrieving frame {frame_id}: {e}", exc_info=True)
            raise

    @traced
    async def get_camera_stats(self, camera_id: str) -> Dict[str, Any]:
        """Get processing statistics for a camera.

        Args:
            camera_id: Camera identifier

        Returns:
            Camera statistics
        """
        start_time = time.time()

        try:
            stats = self.camera_stats.get(
                camera_id,
                {
                    "frames_processed": 0,
                    "total_detections": 0,
                    "avg_processing_time": 0.0,
                    "last_frame_time": 0.0,
                },
            )

            # Add current storage info
            camera_frames = [
                f for f in self.frames.values() if f["camera_id"] == camera_id
            ]
            stats["frames_in_storage"] = len(camera_frames)

            # Record metrics
            duration = time.time() - start_time
            record_processing_time(
                "frame_storage", "stats", duration, camera_id=camera_id
            )

            logger.debug(f"Retrieved stats for camera {camera_id}")

            return stats

        except Exception as e:
            self.metrics.increment_errors(
                "stats_error",
                {
                    "error_type": type(e).__name__,
                    "camera_id": camera_id,
                },
            )
            logger.error(
                f"Error retrieving stats for camera {camera_id}: {e}", exc_info=True
            )
            raise

    def _update_camera_stats(self, camera_id: str, results: Dict[str, Any]) -> None:
        """Update camera statistics."""
        try:
            stats = self.camera_stats[camera_id]
            stats["frames_processed"] += 1
            stats["last_frame_time"] = time.time()

            # Update detection counts
            summary = results.get("summary", {})
            stats["total_detections"] += summary.get("total_detections", 0)

            # Update average processing time (simple moving average)
            if "timestamp" in results:
                processing_time = time.time() - results["timestamp"]
                if stats["avg_processing_time"] == 0:
                    stats["avg_processing_time"] = processing_time
                else:
                    # Simple exponential moving average
                    alpha = 0.1
                    stats["avg_processing_time"] = (
                        alpha * processing_time
                        + (1 - alpha) * stats["avg_processing_time"]
                    )

            logger.debug(f"Updated stats for camera {camera_id}")

        except Exception as e:
            logger.error(f"Error updating camera stats: {e}", exc_info=True)

    @traced
    async def cleanup_old_frames(self, max_age_seconds: int = 3600) -> int:
        """Clean up old frames from storage.

        Args:
            max_age_seconds: Maximum age of frames to keep

        Returns:
            Number of frames removed
        """
        start_time = time.time()
        current_time = time.time()

        try:
            frames_to_remove = []

            for frame_id, frame_data in self.frames.items():
                if current_time - frame_data["stored_at"] > max_age_seconds:
                    frames_to_remove.append(frame_id)

            # Remove old frames
            for frame_id in frames_to_remove:
                del self.frames[frame_id]

            # Record metrics
            duration = time.time() - start_time
            record_processing_time("frame_storage", "cleanup", duration)

            if frames_to_remove:
                self.metrics.record_queue_size("stored_frames", len(self.frames))
                logger.info(f"Cleaned up {len(frames_to_remove)} old frames")

            return len(frames_to_remove)

        except Exception as e:
            self.metrics.increment_errors(
                "cleanup_error",
                {
                    "error_type": type(e).__name__,
                },
            )
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            raise

    async def shutdown(self):
        """Gracefully shutdown storage."""
        logger.info("Shutting down frame storage...")

        # In a real implementation, this would flush data to persistent storage
        frames_count = len(self.frames)
        cameras_count = len(self.camera_stats)

        logger.info(
            f"Frame storage shutdown complete. Had {frames_count} frames from {cameras_count} cameras"
        )

        # Clear data
        self.frames.clear()
        self.camera_stats.clear()
