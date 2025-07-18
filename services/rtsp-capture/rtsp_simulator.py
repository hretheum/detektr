#!/usr/bin/env python3
"""
RTSP Camera Simulator

Tworzy symulator kamery RTSP używając FFmpeg do testowania
bez potrzeby fizycznej kamery.
"""

import asyncio
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


class RTSPSimulator:
    """Symulator kamery RTSP używający FFmpeg"""

    def __init__(
        self,
        port: int = 8554,
        video_file: Optional[str] = None,
        resolution: str = "1920x1080",
        fps: int = 30,
    ):
        self.port = port
        self.video_file = video_file
        self.resolution = resolution
        self.fps = fps
        self.process: Optional[subprocess.Popen] = None
        self.rtsp_url = f"rtsp://localhost:{port}/stream"

    def create_test_video(self, duration: int = 60) -> str:
        """Tworzy test video do streamowania"""
        test_video_path = "/tmp/test_video.mp4"

        # Generuj kolorowe test video z moving pattern
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={self.resolution}:rate={self.fps}",
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-pix_fmt",
            "yuv420p",
            test_video_path,
        ]

        print(f"Generating test video: {test_video_path}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create test video: {result.stderr}")

        return test_video_path

    async def start_server(self) -> bool:
        """Uruchamia RTSP server"""
        try:
            # Sprawdź czy FFmpeg jest dostępny
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ FFmpeg not found. Please install FFmpeg:")
            print("   macOS: brew install ffmpeg")
            print("   Ubuntu: sudo apt install ffmpeg")
            return False

        # Jeśli nie ma pliku video, utwórz test video
        if not self.video_file:
            self.video_file = self.create_test_video()

        # Uruchom RTSP server
        cmd = [
            "ffmpeg",
            "-y",
            "-re",  # Read input at native frame rate
            "-stream_loop",
            "-1",  # Loop indefinitely
            "-i",
            self.video_file,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-g",
            "30",  # GOP size
            "-keyint_min",
            "30",
            "-sc_threshold",
            "0",
            "-b:v",
            "1000k",
            "-maxrate",
            "1000k",
            "-bufsize",
            "2000k",
            "-pix_fmt",
            "yuv420p",
            "-f",
            "rtsp",
            f"rtsp://localhost:{self.port}/stream",
        ]

        print(f"Starting RTSP server on port {self.port}")
        print(f"Stream URL: {self.rtsp_url}")

        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        # Poczekaj chwilę na uruchomienie
        await asyncio.sleep(3)

        # Sprawdź czy proces nadal działa
        if self.process.poll() is None:
            print("✅ RTSP server started successfully")
            return True
        else:
            output = self.process.stdout.read() if self.process.stdout else ""
            print(f"❌ RTSP server failed to start: {output}")
            return False

    def stop_server(self):
        """Zatrzymuje RTSP server"""
        if self.process:
            print("Stopping RTSP server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            print("✅ RTSP server stopped")

    async def test_stream(self) -> bool:
        """Testuje czy stream jest dostępny"""
        try:
            # Użyj ffprobe do sprawdzenia streamu
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                self.rtsp_url,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                print("✅ Stream is accessible")
                return True
            else:
                print(f"❌ Stream test failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Stream test timed out")
            return False
        except Exception as e:
            print(f"❌ Stream test error: {e}")
            return False


async def main():
    """Test główny"""
    print("=== RTSP Camera Simulator ===\n")

    simulator = RTSPSimulator(port=8554)

    def signal_handler(signum, frame):
        print("\nReceived interrupt signal")
        simulator.stop_server()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start server
    if await simulator.start_server():
        print(f"RTSP URL: {simulator.rtsp_url}")

        # Test stream
        await asyncio.sleep(2)
        if await simulator.test_stream():
            print("\n✅ Simulator ready for testing!")
            print(f"Use this URL in your RTSP client: {simulator.rtsp_url}")
            print("Press Ctrl+C to stop...")

            # Keep running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            print("❌ Stream test failed")
    else:
        print("❌ Failed to start simulator")

    simulator.stop_server()


if __name__ == "__main__":
    asyncio.run(main())
