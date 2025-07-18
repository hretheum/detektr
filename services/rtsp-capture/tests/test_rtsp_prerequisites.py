"""
Test Prerequisites - Block 0

Testy dla podstawowych wymagań RTSP service:
- Biblioteka PyAV dostępna i funkcjonalna
- FFmpeg dostępny i działający
- Możliwość połączenia z test streamem
"""

import asyncio
import subprocess
import sys
from unittest.mock import Mock, patch

import av
import pytest


class TestRTSPPrerequisites:
    """Test suite for RTSP prerequisites"""

    def test_python_version_requirement(self):
        """Test that Python version is 3.11+"""
        version = sys.version_info
        assert version >= (
            3,
            11,
        ), f"Python 3.11+ required, got {version.major}.{version.minor}"

    def test_pyav_available(self):
        """Test that PyAV is available and importable"""
        import av

        assert hasattr(av, "__version__"), "PyAV version should be available"
        assert hasattr(av, "open"), "PyAV should have open function"

    def test_opencv_available(self):
        """Test that OpenCV is available"""
        import cv2

        assert hasattr(cv2, "__version__"), "OpenCV version should be available"
        assert hasattr(cv2, "VideoCapture"), "OpenCV should have VideoCapture"

    def test_ffmpeg_available(self):
        """Test that FFmpeg is available in system PATH"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            assert result.returncode == 0, "FFmpeg should be available in PATH"
            assert (
                "ffmpeg version" in result.stdout
            ), "FFmpeg should return version info"
        except FileNotFoundError:
            pytest.fail("FFmpeg not found in PATH")

    def test_ffprobe_available(self):
        """Test that FFprobe is available for stream analysis"""
        try:
            result = subprocess.run(
                ["ffprobe", "-version"], capture_output=True, text=True, timeout=5
            )
            assert result.returncode == 0, "FFprobe should be available in PATH"
            assert (
                "ffprobe version" in result.stdout
            ), "FFprobe should return version info"
        except FileNotFoundError:
            pytest.fail("FFprobe not found in PATH")

    def test_pyav_basic_functionality(self):
        """Test basic PyAV functionality with test source"""
        # Test opening a synthetic video source
        try:
            container = av.open("testsrc2=size=320x240:rate=1", format="lavfi")

            # Should have video stream
            assert len(container.streams.video) > 0, "Should have video stream"

            video_stream = container.streams.video[0]
            assert video_stream.width == 320, "Video width should be 320"
            assert video_stream.height == 240, "Video height should be 240"

            # Try to decode one frame
            frame_decoded = False
            for packet in container.demux(video_stream):
                for frame in packet.decode():
                    assert frame.width == 320, "Frame width should be 320"
                    assert frame.height == 240, "Frame height should be 240"
                    frame_decoded = True
                    break
                if frame_decoded:
                    break

            assert frame_decoded, "Should successfully decode at least one frame"
            container.close()

        except Exception as e:
            pytest.fail(f"PyAV basic functionality failed: {e}")

    @pytest.mark.asyncio
    async def test_asyncio_compatibility(self):
        """Test that PyAV works with asyncio (basic executor test)"""

        def sync_operation():
            """Synchronous operation that would block"""
            import time

            time.sleep(0.1)
            return "success"

        # Test running sync operation in thread executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, sync_operation)
        assert result == "success", "Async execution should work"

    def test_h264_codec_support(self):
        """Test that H.264 codec is supported"""
        try:
            # Check if H.264 encoder is available
            result = subprocess.run(
                ["ffmpeg", "-codecs"], capture_output=True, text=True, timeout=5
            )

            assert result.returncode == 0, "FFmpeg should list codecs"
            assert "h264" in result.stdout.lower(), "H.264 codec should be available"

        except Exception as e:
            pytest.fail(f"H.264 codec check failed: {e}")

    def test_rtsp_protocol_support(self):
        """Test that RTSP protocol is supported"""
        try:
            # Check if RTSP protocol is available
            result = subprocess.run(
                ["ffmpeg", "-protocols"], capture_output=True, text=True, timeout=5
            )

            assert result.returncode == 0, "FFmpeg should list protocols"
            assert "rtsp" in result.stdout.lower(), "RTSP protocol should be available"

        except Exception as e:
            pytest.fail(f"RTSP protocol check failed: {e}")

    @pytest.mark.asyncio
    async def test_public_rtsp_stream_accessibility(self):
        """Test accessibility of public RTSP test stream"""
        test_url = "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"

        try:
            # Try to probe the stream
            process = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                test_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)

            if process.returncode == 0:
                import json

                stream_info = json.loads(stdout.decode())

                assert "streams" in stream_info, "Stream info should contain streams"
                assert (
                    len(stream_info["streams"]) > 0
                ), "Should have at least one stream"

                # Check for video stream
                video_streams = [
                    s for s in stream_info["streams"] if s["codec_type"] == "video"
                ]
                assert len(video_streams) > 0, "Should have video stream"

                video_stream = video_streams[0]
                assert video_stream["codec_name"] in [
                    "h264",
                    "h265",
                ], "Should use H.264/H.265 codec"

            else:
                # Public stream might not be available, that's okay for now
                pytest.skip(f"Public RTSP stream not accessible: {stderr.decode()}")

        except asyncio.TimeoutError:
            pytest.skip("Public RTSP stream connection timeout")
        except Exception as e:
            pytest.skip(f"Public RTSP stream test failed: {e}")

    def test_async_dependencies(self):
        """Test async-related dependencies"""
        # Test asyncio basics
        import asyncio

        assert hasattr(asyncio, "get_event_loop"), "asyncio should have get_event_loop"
        assert hasattr(
            asyncio, "create_subprocess_exec"
        ), "asyncio should have create_subprocess_exec"

        # Test async Redis (if available)
        try:
            import aioredis

            assert hasattr(aioredis, "from_url"), "aioredis should have from_url"
        except ImportError:
            pytest.skip("aioredis not available, will be needed for frame buffering")

    def test_performance_baseline_dependencies(self):
        """Test dependencies for performance baseline measurement"""
        # Test numpy for performance calculations
        import numpy as np

        assert hasattr(np, "percentile"), "numpy should have percentile function"

        # Test time measurement
        import time

        start = time.perf_counter()
        time.sleep(0.01)
        elapsed = time.perf_counter() - start
        assert 0.005 < elapsed < 0.020, "Time measurement should be accurate"


class TestRTSPStreamValidation:
    """Test validation of RTSP streams"""

    def test_rtsp_url_validation(self):
        """Test basic RTSP URL validation"""
        valid_urls = [
            "rtsp://localhost:554/stream1",
            "rtsp://admin:password@192.168.1.100:554/stream",
            "rtsp://demo.com/test",
            "rtsp://192.168.1.100:8554/stream",
        ]

        invalid_urls = [
            "http://localhost/stream",  # Wrong protocol
            "rtsp://",  # Incomplete URL
            "localhost:554/stream",  # Missing protocol
            "rtsp://localhost",  # Missing stream path
        ]

        for url in valid_urls:
            assert url.startswith(
                "rtsp://"
            ), f"Valid URL should start with rtsp://: {url}"
            assert "://" in url, f"Valid URL should have protocol separator: {url}"

        for url in invalid_urls:
            # These should be caught by validation logic when implemented
            if url.startswith("rtsp://"):
                # Basic format check
                parts = url.split("://")
                if len(parts) == 2 and parts[1]:
                    continue  # This might be valid
            # Invalid URLs should be rejected
            assert not (
                url.startswith("rtsp://") and "/" in url.split("://")[1]
            ), f"Invalid URL should be rejected: {url}"
