"""Frame consumer for sample processor - fetches frames from frame-buffer API."""

import asyncio
import contextlib
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp
import numpy as np
from aiohttp import ClientTimeout, TCPConnector

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
        connection_pool_size: int = 10,
        connection_timeout: int = 30,
        read_timeout: int = 60,
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
        self.connection_pool_size = connection_pool_size
        self.connection_timeout = connection_timeout
        self.read_timeout = read_timeout
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._consecutive_errors = 0
        self._total_frames_processed = 0
        self._last_health_check = 0
        self._health_check_interval = 30  # seconds

    async def start(self):
        """Start consuming frames."""
        if self._running:
            print("Consumer already running")
            return

        self._running = True

        # Create connection pool with limits
        connector = TCPConnector(
            limit=self.connection_pool_size,
            limit_per_host=self.connection_pool_size,
            ttl_dns_cache=300,  # DNS cache for 5 minutes
            enable_cleanup_closed=True,
        )

        # Configure timeouts
        timeout = ClientTimeout(
            total=None,  # No total timeout
            connect=self.connection_timeout,
            sock_read=self.read_timeout,
        )

        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "sample-processor/1.0"},
        )

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
            # Allow time for connections to close properly
            await asyncio.sleep(0.25)

        print(
            f"Frame consumer stopped. Total frames processed: {self._total_frames_processed}"
        )

    async def _consume_loop(self):
        """Run the main consumer loop."""
        while self._running:
            try:
                # Periodic health check
                current_time = time.time()
                if current_time - self._last_health_check > self._health_check_interval:
                    await self._perform_health_check()
                    self._last_health_check = current_time

                # Fetch frames from frame-buffer
                frames_data = await self._fetch_frames()

                if frames_data and frames_data.get("count", 0) > 0:
                    # Reset error counter on success
                    self._consecutive_errors = 0

                    # Process fetched frames
                    processed_count = await self._process_frames(frames_data["frames"])
                    self._total_frames_processed += processed_count

                    # Log progress
                    remaining = frames_data.get("remaining", 0)
                    print(
                        f"Processed {processed_count}/{frames_data['count']} frames, "
                        f"{remaining} remaining in buffer, "
                        f"total processed: {self._total_frames_processed}"
                    )
                else:
                    # No frames available, wait before next poll
                    await asyncio.sleep(self.poll_interval_ms / 1000.0)

            except asyncio.CancelledError:
                print("Consumer loop cancelled")
                raise
            except Exception as e:
                self._consecutive_errors += 1
                print(
                    f"Error in consumer loop (attempt {self._consecutive_errors}): {type(e).__name__}: {e}"
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

                    # Recreate session if too many errors
                    if self._session:
                        await self._session.close()
                        await asyncio.sleep(0.25)
                        self._session = await self._create_session()

    async def _fetch_frames(self) -> Optional[Dict[str, Any]]:
        """Fetch frames from frame-buffer API."""
        if not self._session:
            print("Session not initialized")
            return None

        try:
            url = f"{self.frame_buffer_url}/frames/dequeue?count={self.batch_size}"

            # Add retry logic for transient failures
            for attempt in range(2):  # Quick retry once
                try:
                    async with self._session.get(url) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 503:
                            # Service unavailable, buffer might be initializing
                            if attempt == 0:
                                await asyncio.sleep(0.5)
                                continue
                            print("Frame buffer service unavailable")
                            return None
                        else:
                            text = await response.text()
                            print(
                                f"Error fetching frames: {response.status} - {text[:200]}"
                            )
                            return None
                except aiohttp.ClientConnectorError as e:
                    if attempt == 0:
                        await asyncio.sleep(0.5)
                        continue
                    raise

        except aiohttp.ClientError as e:
            print(f"Connection error to frame-buffer: {type(e).__name__}: {e}")
            return None
        except asyncio.TimeoutError:
            print(f"Timeout fetching frames from {url}")
            return None

    async def _process_frames(self, frames: list) -> int:
        """Process fetched frames.

        Returns:
            Number of successfully processed frames
        """
        processed_count = 0
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
                processed_count += 1

            except Exception as e:
                print(
                    f"Error processing frame "
                    f"{frame_data.get('frame_id', 'unknown')}: {e}"
                )

        return processed_count

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

    async def _perform_health_check(self):
        """Perform health check on frame buffer service."""
        if not self._session:
            return

        try:
            health_url = f"{self.frame_buffer_url}/health"
            async with self._session.get(
                health_url, timeout=ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(
                        f"Frame buffer health: {health_data.get('status', 'unknown')}"
                    )
                else:
                    print(f"Frame buffer health check failed: {response.status}")
        except Exception as e:
            print(f"Health check error: {type(e).__name__}: {e}")

    async def _create_session(self) -> aiohttp.ClientSession:
        """Create a new HTTP session with connection pooling."""
        connector = TCPConnector(
            limit=self.connection_pool_size,
            limit_per_host=self.connection_pool_size,
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )

        timeout = ClientTimeout(
            total=None,
            connect=self.connection_timeout,
            sock_read=self.read_timeout,
        )

        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "sample-processor/1.0"},
        )


async def create_consumer_from_env(processor) -> FrameBufferConsumer:
    """Create consumer from environment variables."""
    return FrameBufferConsumer(
        processor=processor,
        frame_buffer_url=os.getenv("FRAME_BUFFER_URL", "http://frame-buffer:8002"),
        batch_size=int(os.getenv("CONSUMER_BATCH_SIZE", "10")),
        poll_interval_ms=int(os.getenv("POLL_INTERVAL_MS", "100")),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        backoff_ms=int(os.getenv("BACKOFF_MS", "1000")),
        connection_pool_size=int(os.getenv("CONNECTION_POOL_SIZE", "10")),
        connection_timeout=int(os.getenv("CONNECTION_TIMEOUT", "30")),
        read_timeout=int(os.getenv("READ_TIMEOUT", "60")),
    )
