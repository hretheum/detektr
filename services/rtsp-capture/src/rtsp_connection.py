"""
RTSP Connection Manager with auto-reconnect capabilities.

Handles connection lifecycle, automatic reconnection, and connection health monitoring.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from enum import Enum, auto
from typing import Any, Dict, Optional

import av

from src.telemetry.decorators import traced_method
from src.telemetry.metrics import get_metrics

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """RTSP connection states."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    ERROR = auto()


class RTSPConnectionManager:
    """Manages RTSP connection with automatic reconnection."""

    def __init__(
        self,
        rtsp_url: str,
        reconnect_timeout: float = 5.0,
        max_reconnect_attempts: int = 10,
        connection_options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize RTSP connection manager.

        Args:
            rtsp_url: RTSP stream URL
            reconnect_timeout: Seconds to wait between reconnection attempts
            max_reconnect_attempts: Maximum number of reconnection attempts
            connection_options: Additional PyAV connection options
        """
        self.rtsp_url = rtsp_url
        self.reconnect_timeout = reconnect_timeout
        self.max_reconnect_attempts = max_reconnect_attempts

        # Connection state
        self._state = ConnectionState.DISCONNECTED
        self.container: Optional[av.Container] = None
        self.reconnect_attempts = 0
        self._connection_lock = asyncio.Lock()
        self._connection_start_time: Optional[float] = None

        # Default connection options
        self.connection_options = {
            "rtsp_transport": "tcp",
            "rtsp_flags": "prefer_tcp",
            "max_delay": "500000",
            "timeout": "10000000",
            "reorder_queue_size": "1000",
            "buffer_size": "1000000",
        }

        if connection_options:
            self.connection_options.update(connection_options)

        logger.info(
            f"RTSPConnectionManager initialized for {self._sanitize_url_for_log()}"
        )

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @state.setter
    def state(self, value: ConnectionState):
        """Set connection state and update metrics."""
        old_state = self._state
        self._state = value

        # Update metrics
        metrics = get_metrics("rtsp_capture")
        metrics.set_service_info({"connection_state": value.name.lower()})

        logger.info(f"Connection state changed: {old_state.name} -> {value.name}")

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self.state == ConnectionState.CONNECTED and self.container is not None

    def _sanitize_url_for_log(self) -> str:
        """Remove credentials from URL for logging."""
        # Simple credential removal - replace user:pass@ with ***@
        import re

        return re.sub(r"://[^:]+:[^@]+@", "://***:***@", self.rtsp_url)

    @traced_method(span_name="rtsp_connect")
    async def connect(self) -> None:
        """
        Establish RTSP connection.

        Raises:
            Exception: If connection fails
        """
        async with self._connection_lock:
            if self.is_connected:
                logger.debug("Already connected")
                return

            self.state = ConnectionState.CONNECTING
            metrics = get_metrics("rtsp_capture")
            metrics.increment_errors("connection_attempt", service="rtsp_capture")

            try:
                logger.info(f"Connecting to {self._sanitize_url_for_log()}")

                # Open connection with PyAV
                self.container = av.open(
                    self.rtsp_url, options=self.connection_options, timeout=10.0
                )

                # Verify we have video stream
                if not self.container.streams.video:
                    raise ValueError("No video stream found in RTSP source")

                self.state = ConnectionState.CONNECTED
                self.reconnect_attempts = 0
                self._connection_start_time = time.time()

                logger.info("RTSP connection established successfully")

            except Exception as e:
                self.state = ConnectionState.ERROR
                logger.error(f"Failed to connect: {e}")
                raise

    @traced_method(span_name="rtsp_disconnect")
    async def disconnect(self) -> None:
        """Disconnect from RTSP stream."""
        async with self._connection_lock:
            if not self.container:
                logger.debug("Already disconnected")
                return

            try:
                # Record connection duration
                if self._connection_start_time:
                    duration = time.time() - self._connection_start_time
                    metrics = get_metrics("rtsp_capture")
                    metrics.record_processing_time("connection", duration)

                # Close container
                self.container.close()
                self.container = None
                self.state = ConnectionState.DISCONNECTED

                logger.info("RTSP connection closed")

            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
                self.state = ConnectionState.ERROR

    @traced_method(span_name="rtsp_reconnect")
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to RTSP stream.

        Returns:
            bool: True if reconnection successful
        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(
                f"Max reconnection attempts ({self.max_reconnect_attempts}) reached"
            )
            return False

        self.state = ConnectionState.RECONNECTING
        self.reconnect_attempts += 1
        metrics = get_metrics("rtsp_capture")
        metrics.increment_errors("reconnect_attempt", service="rtsp_capture")

        msg = f"Reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}"
        logger.info(msg)

        # Disconnect first - but don't lock since we're already in error state
        if self.container:
            try:
                self.container.close()
                self.container = None
            except Exception:
                pass

        # Wait before reconnecting
        await asyncio.sleep(self.reconnect_timeout)

        try:
            await self.connect()
            return True
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return False

    async def connect_with_retry(self) -> bool:
        """
        Connect with automatic retry on failure.

        Returns:
            bool: True if connection successful
        """
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                await self.connect()
                return True
            except Exception:
                if self.reconnect_attempts < self.max_reconnect_attempts - 1:
                    await asyncio.sleep(self.reconnect_timeout)
                    self.reconnect_attempts += 1
                else:
                    self.reconnect_attempts += 1
                    return False

        return False

    async def monitor_connection(self) -> None:
        """
        Monitor connection health and reconnect if needed.

        Runs continuously until cancelled.
        """
        logger.info("Starting connection monitor")

        while True:
            try:
                if self.state == ConnectionState.ERROR:
                    logger.warning("Connection in error state, attempting reconnect")
                    success = await self.reconnect()

                    if not success:
                        logger.error("Reconnection failed, will retry later")
                        await asyncio.sleep(self.reconnect_timeout * 2)

                elif (
                    self.state == ConnectionState.CONNECTED
                    and not await self.health_check()
                ):
                    self.state = ConnectionState.ERROR

                await asyncio.sleep(1.0)  # Check every second

            except asyncio.CancelledError:
                logger.info("Connection monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
                await asyncio.sleep(self.reconnect_timeout)

    async def health_check(self) -> bool:
        """
        Check if connection is healthy.

        Returns:
            bool: True if connection is healthy
        """
        if not self.is_connected:
            return False

        try:
            # Simple check - verify container is still valid
            if self.container and self.container.streams.video:
                return True
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_video_stream(self) -> Optional[av.video.VideoStream]:
        """
        Get video stream from container.

        Returns:
            Optional[av.video.VideoStream]: Video stream if available
        """
        if not self.container:
            return None

        video_streams = self.container.streams.video
        return video_streams[0] if video_streams else None

    @asynccontextmanager
    async def connection_context(self):
        """Context manager for RTSP connection."""
        try:
            await self.connect()
            yield self
        finally:
            await self.disconnect()
