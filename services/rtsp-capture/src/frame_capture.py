"""
Frame capture module with integrated frame tracking.

Handles RTSP stream capture with distributed tracing support.
"""

import asyncio
import time
from typing import Optional

import cv2
from frame_buffer import CircularFrameBuffer
from observability import _init_metrics_once, create_frame_span, frame_counter

# Import frame tracking
try:
    from frame_tracking import FrameID, FrameMetadata, TraceContext

    FRAME_TRACKING_AVAILABLE = True
except ImportError:
    FRAME_TRACKING_AVAILABLE = False
    print("Warning: frame-tracking library not available")


class RTSPCapture:
    """RTSP stream capture with frame tracking integration."""

    def __init__(
        self,
        rtsp_url: str,
        camera_id: str = "default",
        buffer_size: int = 100,
        fps_limit: int = 30,
    ):
        """
        Initialize RTSP capture.

        Args:
            rtsp_url: RTSP stream URL
            camera_id: Camera identifier
            buffer_size: Frame buffer size
            fps_limit: Maximum FPS to capture
        """
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self.buffer_size = buffer_size
        self.fps_limit = fps_limit
        self.frame_interval = 1.0 / fps_limit

        self.cap = None
        self.buffer = CircularFrameBuffer(buffer_size)
        self.is_running = False
        self.reconnect_delay = 5.0

        # Initialize metrics
        _init_metrics_once()

    def connect(self) -> bool:
        """
        Connect to RTSP stream.

        Returns:
            True if connection successful
        """
        try:
            print(f"[CONNECT] Creating VideoCapture for {self.rtsp_url}")
            self.cap = cv2.VideoCapture(self.rtsp_url)

            # Set timeout properties for RTSP
            print("[CONNECT] Setting timeouts...")
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)  # 5 second open timeout
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)  # 5 second read timeout
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer

            if not self.cap.isOpened():
                print(f"Failed to open RTSP stream: {self.rtsp_url}")
                return False

            # Get stream properties
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            print(f"Connected to RTSP stream: {self.rtsp_url}")
            print(f"Stream properties: {width}x{height} @ {fps} FPS")

            return True

        except Exception as e:
            print(f"Error connecting to RTSP stream: {e}")
            return False

    def disconnect(self):
        """Disconnect from RTSP stream."""
        if self.cap:
            self.cap.release()
            self.cap = None

    async def capture_frame(self) -> Optional[tuple]:
        """
        Capture single frame with frame tracking.

        Returns:
            Tuple of (frame_id, frame_data, metadata) or None
        """
        if not self.cap or not self.cap.isOpened():
            return None

        # Generate frame ID
        if FRAME_TRACKING_AVAILABLE:
            frame_id = FrameID.generate(camera_id=self.camera_id, source="rtsp-capture")
        else:
            # Fallback ID generation
            frame_id = f"{int(time.time() * 1000)}_{self.camera_id}"

        # Create trace context
        if FRAME_TRACKING_AVAILABLE:
            with TraceContext.inject(frame_id) as ctx:
                return await self._capture_with_trace(frame_id, ctx)
        else:
            # Fallback to basic tracing
            with create_frame_span(frame_id, self.camera_id) as span:
                return await self._capture_with_span(frame_id, span)

    async def _capture_with_trace(
        self, frame_id: str, ctx: "TraceContext"
    ) -> Optional[tuple]:
        """Capture frame with TraceContext."""
        # Create metadata
        metadata = FrameMetadata(
            frame_id=frame_id,
            timestamp=time.time(),
            camera_id=self.camera_id,
            source_url=self.rtsp_url,
        )

        # Apply trace context to metadata
        ctx.apply_to_metadata(metadata)

        # Add processing stage
        metadata.add_processing_stage(
            name="capture", service="rtsp-capture", status="processing"
        )

        # Capture frame
        with ctx.span("frame.capture") as span:
            # Don't spam logs - only log every 100th frame
            if not hasattr(self, "_capture_count"):
                self._capture_count = 0
            self._capture_count += 1

            if self._capture_count % 100 == 1:
                print(f"[CAPTURE] Reading frame {self._capture_count}...")

            # Run synchronous cv2 read in thread pool to not block event loop
            import asyncio

            loop = asyncio.get_event_loop()
            ret, frame = await loop.run_in_executor(None, self.cap.read)

            if self._capture_count % 100 == 1:
                print(f"[CAPTURE] Frame read result: ret={ret}")

            if not ret:
                ctx.add_event("capture_failed")
                metadata.complete_stage(
                    "capture", status="failed", error="Failed to read frame"
                )
                return None

            # Set frame properties
            height, width = frame.shape[:2]
            metadata.resolution = (width, height)
            metadata.size_bytes = frame.nbytes
            metadata.format = "bgr24"  # OpenCV default

            # Update span attributes
            span.set_attributes(
                {
                    "frame.width": width,
                    "frame.height": height,
                    "frame.size_bytes": frame.nbytes,
                    "camera.id": self.camera_id,
                }
            )

        # Complete capture stage
        metadata.complete_stage("capture", status="completed")

        # Update metrics
        if frame_counter:
            frame_counter.labels(camera_id=self.camera_id, status="captured").inc()

        return frame_id, frame, metadata

    async def _capture_with_span(self, frame_id: str, span) -> Optional[tuple]:
        """Capture frame with basic span (fallback)."""
        # Run synchronous cv2 read in thread pool to not block event loop
        import asyncio

        loop = asyncio.get_event_loop()
        ret, frame = await loop.run_in_executor(None, self.cap.read)

        if not ret:
            span.add_event("capture_failed")
            return None

        # Basic metadata
        metadata = {
            "frame_id": frame_id,
            "timestamp": time.time(),
            "camera_id": self.camera_id,
            "source_url": self.rtsp_url,
            "width": frame.shape[1],
            "height": frame.shape[0],
            "size_bytes": frame.nbytes,
        }

        span.set_attributes(
            {
                "frame.width": metadata["width"],
                "frame.height": metadata["height"],
                "frame.size_bytes": metadata["size_bytes"],
            }
        )

        # Update metrics
        if frame_counter:
            frame_counter.labels(camera_id=self.camera_id, status="captured").inc()

        return frame_id, frame, metadata

    async def capture_loop(self):
        """Run main capture loop with reconnection logic."""
        print("[CAPTURE_LOOP] Starting capture loop, setting is_running=True")
        self.is_running = True
        last_frame_time = 0

        while self.is_running:
            # Connect if not connected
            if not self.cap or not self.cap.isOpened():
                print(f"Attempting to connect to {self.rtsp_url}")
                if not self.connect():
                    await asyncio.sleep(self.reconnect_delay)
                    continue

            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - last_frame_time
            if time_since_last < self.frame_interval:
                await asyncio.sleep(self.frame_interval - time_since_last)
                continue

            # Capture frame
            try:
                frame_data = await self.capture_frame()
                if frame_data:
                    frame_id, frame, metadata = frame_data

                    # Put in buffer
                    if FRAME_TRACKING_AVAILABLE and isinstance(metadata, FrameMetadata):
                        # Store with full metadata
                        self.buffer.put(frame_id, (frame, metadata), current_time)
                    else:
                        # Store with basic metadata
                        self.buffer.put(frame_id, (frame, metadata), current_time)

                    last_frame_time = current_time
                else:
                    # Capture failed, reconnect
                    self.disconnect()
                    await asyncio.sleep(self.reconnect_delay)

            except Exception as e:
                print(f"Error in capture loop: {e}")
                self.disconnect()
                await asyncio.sleep(self.reconnect_delay)

    def stop(self):
        """Stop capture loop."""
        self.is_running = False
        self.disconnect()

    def get_frame(self) -> Optional[tuple]:
        """
        Get frame from buffer.

        Returns:
            Tuple of (frame_id, (frame, metadata), timestamp) or None
        """
        return self.buffer.get()

    def get_statistics(self) -> dict:
        """Get capture statistics."""
        stats = self.buffer.get_statistics()
        stats.update(
            {
                "camera_id": self.camera_id,
                "rtsp_url": self.rtsp_url,
                "is_connected": self.cap is not None and self.cap.isOpened(),
                "frame_tracking_enabled": FRAME_TRACKING_AVAILABLE,
            }
        )
        return stats
