"""
RTSP Frame Extractor with validation and rate limiting.

Handles frame extraction from RTSP stream with automatic validation.
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional

import av
import numpy as np

from src.telemetry.decorators import traced_method
from src.telemetry.metrics import get_metrics

logger = logging.getLogger(__name__)


class FrameValidationError(Exception):
    """Raised when frame validation fails."""

    pass


@dataclass
class Frame:
    """Represents a single video frame."""

    camera_id: str
    timestamp: float
    frame_number: int
    width: int
    height: int
    format: str
    data: np.ndarray

    @property
    def frame_id(self) -> str:
        """Generate unique frame ID."""
        timestamp_ms = int(self.timestamp * 1000)
        return f"{timestamp_ms}_{self.camera_id}_{self.frame_number}"


class FrameExtractor:
    """Extracts and validates frames from RTSP stream."""

    def __init__(
        self,
        connection_manager,
        camera_id: str,
        target_fps: Optional[int] = None,
        validation_enabled: bool = True,
    ):
        """
        Initialize frame extractor.

        Args:
            connection_manager: RTSP connection manager instance
            camera_id: Unique camera identifier
            target_fps: Target frames per second (None for no limit)
            validation_enabled: Enable frame validation
        """
        self.connection_manager = connection_manager
        self.camera_id = camera_id
        self.target_fps = target_fps
        self.validation_enabled = validation_enabled

        self._frame_number = 0
        self._last_frame_time = 0.0
        self._extraction_lock = asyncio.Lock()

        self.metrics = get_metrics("rtsp_capture")

        logger.info(f"FrameExtractor initialized for camera {camera_id}")

    @traced_method(span_name="extract_frame")
    async def extract_frame(self) -> Optional[Frame]:
        """
        Extract a single frame from RTSP stream.

        Returns:
            Frame object or None if extraction fails
        """
        if not self.connection_manager.is_connected:
            raise RuntimeError("Not connected to RTSP stream")

        try:
            async with self._extraction_lock:
                # Get video stream
                video_stream = self.connection_manager.get_video_stream()
                if not video_stream:
                    logger.error("No video stream available")
                    return None

                # Decode next frame
                frame_av = None
                for packet in self.connection_manager.container.decode(video_stream):
                    if hasattr(packet, "decode"):
                        # packet is actually a packet object
                        decoded_frames = packet.decode()
                        for f in decoded_frames:
                            frame_av = f
                            break
                    else:
                        # packet is already a frame
                        frame_av = packet
                        break

                    if frame_av:
                        break

                if not frame_av:
                    logger.warning("No frame decoded")
                    return None

                # Convert to numpy array
                frame_np = frame_av.to_ndarray(format="bgr24")

                # Create Frame object
                timestamp = frame_av.time if frame_av.time else time.time()

                frame = Frame(
                    camera_id=self.camera_id,
                    timestamp=timestamp,
                    frame_number=self._frame_number,
                    width=frame_av.width,
                    height=frame_av.height,
                    format="bgr24",
                    data=frame_np,
                )

                # Validate if enabled
                if self.validation_enabled:
                    self.validate_frame(frame)

                self._frame_number += 1
                self.metrics.increment_frames_processed(1, camera_id=self.camera_id)

                return frame

        except av.FFmpegError as e:
            logger.error(f"AV decode error: {e}")
            self.metrics.increment_errors("decode_error", camera_id=self.camera_id)
            return None
        except Exception as e:
            logger.error(f"Frame extraction error: {e}")
            self.metrics.increment_errors("extraction_error", camera_id=self.camera_id)
            raise

    def validate_frame(self, frame: Frame) -> None:
        """
        Validate frame quality and integrity.

        Args:
            frame: Frame to validate

        Raises:
            FrameValidationError: If validation fails
        """
        # Check dimensions match
        if frame.data.shape[:2] != (frame.height, frame.width):
            raise FrameValidationError(
                f"Frame dimensions mismatch: metadata={frame.width}x{frame.height}, "
                f"actual={frame.data.shape[1]}x{frame.data.shape[0]}"
            )

        # Check for black frame
        if np.mean(frame.data) < 1.0:  # Almost completely black
            raise FrameValidationError("Detected black frame")

        # Check for frozen frame (would need previous frame for comparison)
        # This is a placeholder for more sophisticated validation

        logger.debug(f"Frame {frame.frame_id} validated successfully")

    async def extract_frames(
        self, max_frames: Optional[int] = None
    ) -> AsyncGenerator[Frame, None]:
        """
        Extract frames continuously from RTSP stream.

        Args:
            max_frames: Maximum number of frames to extract (None for infinite)

        Yields:
            Frame objects
        """
        frames_extracted = 0

        while True:
            # Check frame limit
            if max_frames and frames_extracted >= max_frames:
                break

            # Rate limiting
            if self.target_fps:
                current_time = time.time()
                time_since_last = current_time - self._last_frame_time
                target_interval = 1.0 / self.target_fps

                if time_since_last < target_interval:
                    await asyncio.sleep(target_interval - time_since_last)

                self._last_frame_time = time.time()

            # Extract frame
            try:
                frame = await self.extract_frame()
                if frame:
                    yield frame
                    frames_extracted += 1
                else:
                    # Brief pause before retry
                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in frame extraction loop: {e}")
                await asyncio.sleep(1.0)  # Backoff on error

    def calculate_frame_stats(self, frame: Frame) -> Dict[str, Any]:
        """
        Calculate statistics for a frame.

        Args:
            frame: Frame to analyze

        Returns:
            Dictionary of statistics
        """
        # Convert to grayscale for brightness analysis
        gray = np.mean(frame.data, axis=2)

        stats = {
            "mean_brightness": float(np.mean(gray)),
            "std_brightness": float(np.std(gray)),
            "min_brightness": float(np.min(gray)),
            "max_brightness": float(np.max(gray)),
            "is_color": len(frame.data.shape) == 3 and frame.data.shape[2] == 3,
            "width": frame.width,
            "height": frame.height,
            "timestamp": frame.timestamp,
            "frame_id": frame.frame_id,
        }

        # Check if frame is mostly one color (potential issue)
        if stats["std_brightness"] < 5.0:
            stats["is_uniform"] = True
        else:
            stats["is_uniform"] = False

        return stats

    def reset_frame_counter(self) -> None:
        """Reset frame numbering."""
        self._frame_number = 0
        logger.info(f"Frame counter reset for camera {self.camera_id}")
