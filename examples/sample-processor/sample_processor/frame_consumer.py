"""Frame consumer for sample processor - fetches frames from frame-buffer API."""

import asyncio
import contextlib
import os
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp
import numpy as np

# Frame tracking support
try:
    from frame_tracking import TraceContext

    FRAME_TRACKING_AVAILABLE = True
except ImportError:
    FRAME_TRACKING_AVAILABLE = False


class FrameBufferConsumer:
    """Consumes frames from frame-buffer API and processes them."""

    def __init__(
        self,
        processor,
        frame_buffer_url: str = None,
        batch_size: int = 10,
        poll_interval_ms: int = 100,
        max_retries: int = 3,
        backoff_ms: int = 1000,
    ):
        """Initialize frame consumer.

        Args:
            processor: The sample processor instance
            frame_buffer_url: URL of frame-buffer API
            batch_size: Number of frames to fetch per request
            poll_interval_ms: Polling interval in milliseconds
            max_retries: Max retries on error
            backoff_ms: Backoff time on error in milliseconds
        """
        self.processor = processor
        self.frame_buffer_url = frame_buffer_url or os.getenv(
            "FRAME_BUFFER_URL", "http://frame-buffer:8002"
        )
        self.batch_size = batch_size
        self.poll_interval_ms = poll_interval_ms
        self.max_retries = max_retries
        self.backoff_ms = backoff_ms
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._consecutive_errors = 0

    async def start(self):
        """Start consuming frames."""
        if self._running:
            print("Consumer already running")
            return

        self._running = True
        self._session = aiohttp.ClientSession()
        self._consumer_task = asyncio.create_task(self._consume_loop())
        print(f"Frame consumer started, fetching from {self.frame_buffer_url}")

    async def stop(self):
        """Stop consuming frames."""
        self._running = False

        if self._consumer_task:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task

        if self._session:
            await self._session.close()

        print("Frame consumer stopped")

    async def _consume_loop(self):
        """Run the main consumer loop."""
        while self._running:
            try:
                # Fetch frames from frame-buffer
                frames_data = await self._fetch_frames()

                if frames_data and frames_data.get("count", 0) > 0:
                    # Reset error counter on success
                    self._consecutive_errors = 0

                    # Process fetched frames
                    await self._process_frames(frames_data["frames"])

                    # Log progress
                    remaining = frames_data.get("remaining", 0)
                    print(
                        f"Processed {frames_data['count']} frames, "
                        f"{remaining} remaining in buffer"
                    )
                else:
                    # No frames available, wait before next poll
                    await asyncio.sleep(self.poll_interval_ms / 1000.0)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._consecutive_errors += 1
                print(
                    f"Error in consumer loop (attempt {self._consecutive_errors}): {e}"
                )

                # Exponential backoff on errors
                backoff_time = (
                    min(
                        self.backoff_ms * (2 ** (self._consecutive_errors - 1)),
                        30000,  # Max 30 seconds
                    )
                    / 1000.0
                )

                await asyncio.sleep(backoff_time)

                # Reset errors after max retries
                if self._consecutive_errors >= self.max_retries:
                    print("Max retries reached, resetting error counter")
                    self._consecutive_errors = 0

    async def _fetch_frames(self) -> Optional[Dict[str, Any]]:
        """Fetch frames from frame-buffer API."""
        try:
            url = f"{self.frame_buffer_url}/frames/dequeue?count={self.batch_size}"

            async with self._session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 503:
                    # Service unavailable, buffer might be initializing
                    print("Frame buffer service unavailable")
                    return None
                else:
                    text = await response.text()
                    print(f"Error fetching frames: {response.status} - {text}")
                    return None

        except aiohttp.ClientError as e:
            print(f"Connection error to frame-buffer: {e}")
            return None

    async def _process_frames(self, frames: list):
        """Process fetched frames."""
        for frame_data in frames:
            try:
                # Extract frame info
                frame_id = frame_data.get(
                    "frame_id", f"unknown_{datetime.now().timestamp()}"
                )

                # Convert frame data to numpy array
                # In real implementation, this would decode actual frame data
                # For now, create dummy frame based on metadata
                width = frame_data.get("width", 640)
                height = frame_data.get("height", 480)
                frame = self._create_dummy_frame(width, height, frame_data)

                # Prepare metadata
                metadata = {
                    "frame_id": frame_id,
                    "timestamp": frame_data.get(
                        "timestamp", datetime.now().isoformat()
                    ),
                    "camera_id": frame_data.get("camera_id", "unknown"),
                    **frame_data,  # Include all original metadata
                }

                # Extract and continue trace context if available
                if FRAME_TRACKING_AVAILABLE and "traceparent" in frame_data:
                    with TraceContext.extract_from_carrier(frame_data) as ctx:
                        ctx.add_event("sample_processor_received")
                        ctx.set_attribute("processor.name", "sample-processor")

                        # Process frame with tracing
                        result = await self.processor.process(frame, metadata)

                        ctx.add_event("sample_processor_completed")
                        ctx.set_attribute(
                            "detections.count", result.get("total_objects", 0)
                        )
                else:
                    # Process without tracing
                    result = await self.processor.process(frame, metadata)

                # Log result
                print(
                    f"Frame {frame_id}: detected "
                    f"{result.get('total_objects', 0)} objects"
                )

            except Exception as e:
                print(
                    f"Error processing frame "
                    f"{frame_data.get('frame_id', 'unknown')}: {e}"
                )

    def _create_dummy_frame(
        self, width: int, height: int, metadata: Dict
    ) -> np.ndarray:
        """Create dummy frame for testing.

        In production, this would decode actual frame data from metadata.
        """
        # Create frame with varying intensity based on frame_id hash
        frame_id = metadata.get("frame_id", "")
        intensity = (hash(frame_id) % 200) + 55  # 55-255 range

        frame = np.full((height, width, 3), intensity, dtype=np.uint8)

        # Add some variation
        noise = np.random.randint(-10, 10, size=(height, width, 3))
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        return frame


async def create_consumer_from_env(processor) -> FrameBufferConsumer:
    """Create consumer from environment variables."""
    return FrameBufferConsumer(
        processor=processor,
        frame_buffer_url=os.getenv("FRAME_BUFFER_URL", "http://frame-buffer:8002"),
        batch_size=int(os.getenv("CONSUMER_BATCH_SIZE", "10")),
        poll_interval_ms=int(os.getenv("POLL_INTERVAL_MS", "100")),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        backoff_ms=int(os.getenv("BACKOFF_MS", "1000")),
    )
