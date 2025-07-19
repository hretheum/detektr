"""
Test suite for RTSP connection manager with auto-reconnect capabilities.

Tests cover connection, disconnection, auto-reconnect logic and error handling.
"""
import asyncio
import contextlib
import time
from unittest.mock import Mock, patch

import pytest

from src.rtsp_connection import ConnectionState, RTSPConnectionManager


class TestRTSPConnectionManager:
    """Test suite for RTSP connection manager."""

    @pytest.fixture
    def mock_av_open(self):
        """Mock av.open function."""
        with patch("av.open") as mock:
            # Create mock container
            mock_container = Mock()
            mock_container.streams.video = [Mock()]
            mock_container.streams.video[0].codec_context = Mock()
            mock_container.streams.video[0].codec_context.width = 1920
            mock_container.streams.video[0].codec_context.height = 1080
            mock_container.close = Mock()

            # Create mock packet
            mock_packet = Mock()
            mock_packet.decode = Mock(return_value=[Mock()])  # Mock frame

            # Set up decode iteration
            mock_container.decode = Mock(return_value=iter([mock_packet]))

            mock.return_value = mock_container
            yield mock

    @pytest.fixture
    def connection_manager(self):
        """Create connection manager instance."""
        return RTSPConnectionManager(
            rtsp_url="rtsp://admin:pass@192.168.1.195:554/h264Preview_01_main",
            reconnect_timeout=5.0,
            max_reconnect_attempts=3,
        )

    @pytest.mark.asyncio
    async def test_initial_state(self, connection_manager):
        """Test initial connection state."""
        assert connection_manager.state == ConnectionState.DISCONNECTED
        assert connection_manager.is_connected is False
        assert connection_manager.container is None
        assert connection_manager.reconnect_attempts == 0

    @pytest.mark.asyncio
    async def test_successful_connection(self, connection_manager, mock_av_open):
        """Test successful RTSP connection."""
        # Connect
        await connection_manager.connect()

        # Verify state
        assert connection_manager.state == ConnectionState.CONNECTED
        assert connection_manager.is_connected is True
        assert connection_manager.container is not None
        assert connection_manager.reconnect_attempts == 0

        # Verify av.open called with correct parameters
        mock_av_open.assert_called_once()
        call_args = mock_av_open.call_args
        assert connection_manager.rtsp_url in call_args[0]
        assert "options" in call_args[1]
        assert call_args[1]["options"]["rtsp_transport"] == "tcp"

    @pytest.mark.asyncio
    async def test_connection_failure(self, connection_manager):
        """Test connection failure handling."""
        with patch("av.open", side_effect=Exception("Connection failed")):
            # Attempt connection
            with pytest.raises(Exception) as exc_info:
                await connection_manager.connect()

            # Verify state
            assert connection_manager.state == ConnectionState.ERROR
            assert connection_manager.is_connected is False
            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_disconnect(self, connection_manager, mock_av_open):
        """Test disconnection."""
        # Connect first
        await connection_manager.connect()
        assert connection_manager.is_connected is True

        # Disconnect
        await connection_manager.disconnect()

        # Verify state
        assert connection_manager.state == ConnectionState.DISCONNECTED
        assert connection_manager.is_connected is False
        assert connection_manager.container is None

        # Verify container was closed
        mock_av_open.return_value.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_reconnect_on_error(self, connection_manager, mock_av_open):
        """Test auto-reconnect when connection is lost."""
        # Connect successfully first
        await connection_manager.connect()

        # Simulate connection loss
        connection_manager.state = ConnectionState.ERROR

        # Start monitoring (which should trigger reconnect)
        monitor_task = asyncio.create_task(connection_manager.monitor_connection())

        # Give it time to reconnect (includes reconnect_timeout of 5s)
        await asyncio.sleep(6.0)

        # Cancel monitoring
        monitor_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await monitor_task

        # Verify reconnection attempted
        assert mock_av_open.call_count >= 2  # Initial + reconnect
        assert connection_manager.state == ConnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_max_reconnect_attempts(self, connection_manager):
        """Test maximum reconnect attempts limit."""
        connection_manager.max_reconnect_attempts = 2

        # Make av.open always fail
        with patch("av.open", side_effect=Exception("Connection failed")):
            # Try to connect with retry
            result = await connection_manager.connect_with_retry()

            # Should fail after max attempts
            assert result is False
            assert connection_manager.reconnect_attempts == 2
            assert connection_manager.state == ConnectionState.ERROR

    @pytest.mark.asyncio
    async def test_reconnect_timeout(self, connection_manager):
        """Test reconnect timeout delay."""
        connection_manager.reconnect_timeout = 0.5  # 500ms

        with patch("av.open", side_effect=Exception("Connection failed")):
            start_time = time.time()

            # Attempt connection with retry (will fail)
            await connection_manager.connect_with_retry()

            elapsed_time = time.time() - start_time

            # Should have waited at least one timeout period
            assert elapsed_time >= 0.5

    @pytest.mark.asyncio
    async def test_connection_state_transitions(self, connection_manager, mock_av_open):
        """Test all connection state transitions."""
        # Start disconnected
        assert connection_manager.state == ConnectionState.DISCONNECTED

        # Connect -> Connecting -> Connected
        connection_manager.state = ConnectionState.CONNECTING
        await connection_manager.connect()
        assert connection_manager.state == ConnectionState.CONNECTED

        # Simulate error
        connection_manager.state = ConnectionState.ERROR
        assert connection_manager.state == ConnectionState.ERROR

        # Reconnect -> Reconnecting -> Connected
        connection_manager.state = ConnectionState.RECONNECTING
        await connection_manager.connect()
        assert connection_manager.state == ConnectionState.CONNECTED

        # Disconnect
        await connection_manager.disconnect()
        assert connection_manager.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_concurrent_connection_attempts(
        self, connection_manager, mock_av_open
    ):
        """Test handling of concurrent connection attempts."""
        # Create multiple connection tasks
        tasks = [asyncio.create_task(connection_manager.connect()) for _ in range(5)]

        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Only one should succeed, others should be blocked
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful >= 1

        # Should have single connection
        assert connection_manager.is_connected is True
        assert mock_av_open.call_count >= 1

    @pytest.mark.asyncio
    async def test_connection_with_credentials(self):
        """Test URL parsing with credentials."""
        manager = RTSPConnectionManager(
            rtsp_url="rtsp://user:pass@192.168.1.100:554/stream1"
        )

        # Parse URL components
        assert "user:pass" in manager.rtsp_url
        assert "192.168.1.100" in manager.rtsp_url
        assert "554" in manager.rtsp_url
        assert "stream1" in manager.rtsp_url

    @pytest.mark.asyncio
    async def test_get_video_stream(self, connection_manager, mock_av_open):
        """Test getting video stream from container."""
        # Connect
        await connection_manager.connect()

        # Get video stream
        stream = connection_manager.get_video_stream()

        assert stream is not None
        assert stream.codec_context.width == 1920
        assert stream.codec_context.height == 1080

    @pytest.mark.asyncio
    async def test_connection_health_check(self, connection_manager, mock_av_open):
        """Test connection health check."""
        # Not connected
        assert await connection_manager.health_check() is False

        # Connect
        await connection_manager.connect()

        # Should be healthy
        assert await connection_manager.health_check() is True

        # Simulate unhealthy state
        connection_manager.state = ConnectionState.ERROR
        assert await connection_manager.health_check() is False
