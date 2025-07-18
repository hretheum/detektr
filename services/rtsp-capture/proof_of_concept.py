#!/usr/bin/env python3
"""
Proof of Concept: PyAV RTSP Stream Capture

Test script to validate PyAV can handle RTSP streams with:
- H.264/H.265 support
- Reconnect capability
- Frame extraction
- Error handling
"""

import asyncio
import time
from typing import Optional

import av
import cv2
import numpy as np


class RTSPProofOfConcept:
    """Simple RTSP capture proof of concept using PyAV"""

    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self.container: Optional[av.container.InputContainer] = None
        self.video_stream: Optional[av.VideoStream] = None
        self.is_connected = False

    async def connect(self) -> bool:
        """Connect to RTSP stream"""
        try:
            print(f"Connecting to: {self.rtsp_url}")

            # Run in thread pool to avoid blocking
            self.container = await asyncio.get_event_loop().run_in_executor(
                None, self._connect_sync
            )

            if self.container and self.container.streams.video:
                self.video_stream = self.container.streams.video[0]
                self.is_connected = True

                # Print stream info
                print(f"Connected successfully!")
                print(f"Codec: {self.video_stream.codec.name}")
                print(
                    f"Resolution: {self.video_stream.width}x{self.video_stream.height}"
                )
                print(f"FPS: {self.video_stream.average_rate}")

                return True

        except Exception as e:
            print(f"Connection failed: {e}")
            self.is_connected = False
            return False

    def _connect_sync(self) -> av.container.InputContainer:
        """Synchronous connection to avoid async issues with PyAV"""
        # Configure options for RTSP
        options = {
            "rtsp_transport": "tcp",  # Use TCP for reliability
            "rtsp_flags": "prefer_tcp",
            "max_delay": "500000",  # 500ms max delay
            "timeout": "10000000",  # 10s timeout
        }

        return av.open(self.rtsp_url, options=options)

    async def capture_frames(self, num_frames: int = 10) -> list:
        """Capture specified number of frames"""
        if not self.is_connected:
            raise RuntimeError("Not connected to stream")

        frames = []
        frame_count = 0
        start_time = time.time()

        try:
            # Decode frames in thread pool
            frame_generator = await asyncio.get_event_loop().run_in_executor(
                None, self._capture_frames_sync, num_frames
            )

            for frame_data in frame_generator:
                frames.append(frame_data)
                frame_count += 1

                if frame_count >= num_frames:
                    break

        except Exception as e:
            print(f"Frame capture error: {e}")

        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0

        print(f"Captured {frame_count} frames in {elapsed:.2f}s ({fps:.1f} FPS)")
        return frames

    def _capture_frames_sync(self, num_frames: int):
        """Synchronous frame capture generator"""
        frame_count = 0

        for packet in self.container.demux(self.video_stream):
            for frame in packet.decode():
                if frame_count >= num_frames:
                    return

                # Convert to numpy array
                frame_array = frame.to_ndarray(format="rgb24")

                # Convert to BGR for OpenCV compatibility
                frame_bgr = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)

                yield {
                    "timestamp": time.time(),
                    "frame": frame_bgr,
                    "shape": frame_bgr.shape,
                    "size": frame_bgr.nbytes,
                }

                frame_count += 1

    async def test_reconnect(self) -> bool:
        """Test reconnection capability"""
        print("Testing reconnection...")

        # Close current connection
        if self.container:
            self.container.close()
            self.is_connected = False

        # Wait a bit
        await asyncio.sleep(2)

        # Try to reconnect
        return await self.connect()

    def disconnect(self):
        """Close connection"""
        if self.container:
            self.container.close()
            self.is_connected = False
            print("Disconnected")


async def main():
    """Main test function"""
    # Test with different RTSP URLs
    test_urls = [
        "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4",  # Public test stream
        "rtsp://admin:admin@192.168.1.100:554/stream1",  # Example IP camera
        "rtsp://192.168.1.100:554/stream1",  # Without credentials
    ]

    print("=== RTSP PyAV Proof of Concept ===\n")

    for url in test_urls:
        print(f"Testing URL: {url}")

        rtsp_poc = RTSPProofOfConcept(url)

        # Test connection
        if await rtsp_poc.connect():
            try:
                # Capture some frames
                frames = await rtsp_poc.capture_frames(5)

                if frames:
                    print(f"✅ Successfully captured {len(frames)} frames")

                    # Show frame info
                    first_frame = frames[0]
                    print(f"   Frame shape: {first_frame['shape']}")
                    print(f"   Frame size: {first_frame['size']} bytes")

                    # Test reconnect
                    if await rtsp_poc.test_reconnect():
                        print("✅ Reconnection successful")
                    else:
                        print("❌ Reconnection failed")

                else:
                    print("❌ No frames captured")

            except Exception as e:
                print(f"❌ Error during capture: {e}")

            finally:
                rtsp_poc.disconnect()
        else:
            print("❌ Connection failed")

        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
