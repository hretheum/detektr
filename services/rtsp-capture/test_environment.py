#!/usr/bin/env python3
"""
Test Environment Setup

Sprawdza czy środowisko jest gotowe do pracy z RTSP:
- Sprawdza dependencies
- Testuje PyAV
- Testuje FFmpeg
- Sprawdza dostępność kamer
"""

import asyncio
import importlib
import subprocess
import sys
import time
from typing import Any, Dict, List


class EnvironmentChecker:
    """Sprawdza gotowość środowiska"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def check_python_version(self) -> bool:
        """Sprawdza wersję Python"""
        version = sys.version_info
        is_valid = version >= (3, 11)

        self.results.append(
            {
                "test": "Python Version",
                "status": "✅ PASS" if is_valid else "❌ FAIL",
                "details": f"Python {version.major}.{version.minor}.{version.micro}",
                "required": "Python 3.11+",
            }
        )

        return is_valid

    def check_required_packages(self) -> bool:
        """Sprawdza wymagane pakiety Python"""
        required_packages = [
            "av",
            "cv2",
            "numpy",
            "asyncio",
            "fastapi",
            "uvicorn",
            "redis",
            "pytest",
        ]

        all_found = True

        for package in required_packages:
            try:
                if package == "cv2":
                    import cv2

                    version = cv2.__version__
                elif package == "av":
                    import av

                    version = av.__version__
                else:
                    module = importlib.import_module(package)
                    version = getattr(module, "__version__", "unknown")

                self.results.append(
                    {
                        "test": f"Package: {package}",
                        "status": "✅ PASS",
                        "details": f"Version: {version}",
                        "required": "Required",
                    }
                )

            except ImportError:
                self.results.append(
                    {
                        "test": f"Package: {package}",
                        "status": "❌ FAIL",
                        "details": "Not installed",
                        "required": "Required",
                    }
                )
                all_found = False

        return all_found

    def check_ffmpeg(self) -> bool:
        """Sprawdza FFmpeg"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                # Extract version from output
                lines = result.stdout.split("\n")
                version_line = next(
                    (line for line in lines if "ffmpeg version" in line), ""
                )

                self.results.append(
                    {
                        "test": "FFmpeg",
                        "status": "✅ PASS",
                        "details": version_line[:80] + "..."
                        if len(version_line) > 80
                        else version_line,
                        "required": "Required for RTSP",
                    }
                )
                return True
            else:
                self.results.append(
                    {
                        "test": "FFmpeg",
                        "status": "❌ FAIL",
                        "details": f"Exit code: {result.returncode}",
                        "required": "Required for RTSP",
                    }
                )
                return False

        except FileNotFoundError:
            self.results.append(
                {
                    "test": "FFmpeg",
                    "status": "❌ FAIL",
                    "details": "FFmpeg not found in PATH",
                    "required": "Install: brew install ffmpeg",
                }
            )
            return False
        except subprocess.TimeoutExpired:
            self.results.append(
                {
                    "test": "FFmpeg",
                    "status": "❌ FAIL",
                    "details": "FFmpeg command timed out",
                    "required": "Required for RTSP",
                }
            )
            return False

    async def check_pyav_functionality(self) -> bool:
        """Sprawdza czy PyAV działa z testem"""
        try:
            import av

            # Test opening a simple video stream
            test_url = "testsrc2=size=320x240:rate=1"

            container = av.open(f"lavfi:{test_url}")

            if container.streams.video:
                stream = container.streams.video[0]

                # Try to decode one frame
                frame_decoded = False
                for packet in container.demux(stream):
                    for frame in packet.decode():
                        frame_decoded = True
                        break
                    if frame_decoded:
                        break

                container.close()

                self.results.append(
                    {
                        "test": "PyAV Functionality",
                        "status": "✅ PASS",
                        "details": "Successfully decoded test frame",
                        "required": "Required for RTSP",
                    }
                )
                return True
            else:
                self.results.append(
                    {
                        "test": "PyAV Functionality",
                        "status": "❌ FAIL",
                        "details": "No video stream found",
                        "required": "Required for RTSP",
                    }
                )
                return False

        except Exception as e:
            self.results.append(
                {
                    "test": "PyAV Functionality",
                    "status": "❌ FAIL",
                    "details": f"Error: {str(e)}",
                    "required": "Required for RTSP",
                }
            )
            return False

    async def check_test_streams(self) -> bool:
        """Sprawdza dostępność test streamów"""
        test_streams = [
            {
                "name": "Local Test Stream",
                "url": "rtsp://localhost:8554/stream",
                "expected": "May not be running",
            },
            {
                "name": "Public Demo Stream",
                "url": "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4",
                "expected": "Should be available",
            },
        ]

        any_available = False

        for stream in test_streams:
            try:
                result = await asyncio.wait_for(
                    asyncio.create_subprocess_exec(
                        "ffprobe",
                        "-v",
                        "quiet",
                        "-print_format",
                        "json",
                        "-show_streams",
                        stream["url"],
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    ),
                    timeout=10,
                )

                stdout, stderr = await result.communicate()

                if result.returncode == 0:
                    self.results.append(
                        {
                            "test": f"Stream: {stream['name']}",
                            "status": "✅ PASS",
                            "details": f"Accessible: {stream['url']}",
                            "required": "Optional",
                        }
                    )
                    any_available = True
                else:
                    self.results.append(
                        {
                            "test": f"Stream: {stream['name']}",
                            "status": "⚠️ WARN",
                            "details": f"Not accessible: {stream['expected']}",
                            "required": "Optional",
                        }
                    )

            except asyncio.TimeoutError:
                self.results.append(
                    {
                        "test": f"Stream: {stream['name']}",
                        "status": "⚠️ WARN",
                        "details": "Connection timeout",
                        "required": "Optional",
                    }
                )
            except Exception as e:
                self.results.append(
                    {
                        "test": f"Stream: {stream['name']}",
                        "status": "⚠️ WARN",
                        "details": f"Error: {str(e)}",
                        "required": "Optional",
                    }
                )

        return any_available

    def print_results(self):
        """Drukuje wyniki testów"""
        print("=" * 70)
        print("🔍 ENVIRONMENT CHECK RESULTS")
        print("=" * 70)

        for result in self.results:
            print(f"{result['status']} {result['test']}")
            print(f"   Details: {result['details']}")
            print(f"   Required: {result['required']}")
            print()

        # Summary
        passed = sum(1 for r in self.results if r["status"] == "✅ PASS")
        failed = sum(1 for r in self.results if r["status"] == "❌ FAIL")
        warned = sum(1 for r in self.results if r["status"] == "⚠️ WARN")

        print("=" * 70)
        print(f"SUMMARY: {passed} passed, {failed} failed, {warned} warnings")

        if failed == 0:
            print("🎉 Environment ready for RTSP development!")
        else:
            print("❌ Environment needs fixes before proceeding")

        print("=" * 70)


async def main():
    """Main test runner"""
    checker = EnvironmentChecker()

    print("Starting environment check...")

    # Run all checks
    checks = [
        checker.check_python_version(),
        checker.check_required_packages(),
        checker.check_ffmpeg(),
        await checker.check_pyav_functionality(),
        await checker.check_test_streams(),
    ]

    # Print results
    checker.print_results()

    # Exit with appropriate code
    if any(r["status"] == "❌ FAIL" for r in checker.results):
        print("\n🚨 Fix the failed checks before proceeding!")
        sys.exit(1)
    else:
        print("\n✅ Environment check completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
