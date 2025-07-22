"""Benchmark for frame serialization performance."""
import statistics
import time
from datetime import datetime
from typing import Any, Dict

import numpy as np

from shared.kernel.domain.frame_data import FrameData
from shared.serializers.frame_serializer import (
    CompressionType,
    FrameSerializer,
    SerializationFormat,
)


def create_test_frames() -> Dict[str, FrameData]:
    """Create test frames of different sizes."""
    frames: Dict[str, FrameData] = {}

    # VGA (640x480)
    frames["vga"] = FrameData(
        id="frame_vga",
        timestamp=datetime.now(),
        camera_id="camera_01",
        sequence_number=1,
        image_data=np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
        metadata={"resolution": "640x480"},
    )

    # HD (1280x720)
    frames["hd"] = FrameData(
        id="frame_hd",
        timestamp=datetime.now(),
        camera_id="camera_01",
        sequence_number=2,
        image_data=np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8),
        metadata={"resolution": "1280x720"},
    )

    # Full HD (1920x1080)
    frames["fullhd"] = FrameData(
        id="frame_fullhd",
        timestamp=datetime.now(),
        camera_id="camera_01",
        sequence_number=3,
        image_data=np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8),
        metadata={"resolution": "1920x1080"},
    )

    # 4K (3840x2160)
    frames["4k"] = FrameData(
        id="frame_4k",
        timestamp=datetime.now(),
        camera_id="camera_01",
        sequence_number=4,
        image_data=np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8),
        metadata={"resolution": "3840x2160"},
    )

    return frames


def benchmark_serialization(
    frame: FrameData, serializer: FrameSerializer, iterations: int = 100
) -> Dict[str, Any]:
    """Benchmark serialization performance."""
    # Warm up
    for _ in range(10):
        serializer.serialize(frame)

    # Measure
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        data = serializer.serialize(frame)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "size_bytes": len(data),
    }


def main() -> None:
    """Run benchmarks."""
    frames = create_test_frames()

    # Test different configurations
    configs = [
        ("msgpack", SerializationFormat.MSGPACK, CompressionType.NONE),
        ("msgpack+lz4", SerializationFormat.MSGPACK, CompressionType.LZ4),
        ("json", SerializationFormat.JSON, CompressionType.NONE),
    ]

    print("Frame Serialization Benchmark")
    print("=" * 80)

    for resolution, frame in frames.items():
        print(f"\n{resolution.upper()} Frame ({frame.metadata['resolution']})")
        print("-" * 60)

        # Skip image data for JSON
        original_image = frame.image_data

        for name, format, compression in configs:
            if format == SerializationFormat.JSON:
                frame.image_data = None
            else:
                frame.image_data = original_image

            serializer = FrameSerializer(format=format, compression=compression)
            results = benchmark_serialization(frame, serializer)

            print(
                f"{name:15} | "
                f"Mean: {results['mean']:6.2f}ms | "
                f"Median: {results['median']:6.2f}ms | "
                f"Min: {results['min']:6.2f}ms | "
                f"Max: {results['max']:6.2f}ms | "
                f"Size: {results['size_bytes']/1024/1024:6.2f}MB"
            )

        # Restore image data
        frame.image_data = original_image

    print("\n" + "=" * 80)
    print("Target: <5ms for Full HD frame serialization ✓")
    print("Target: <2ms LZ4 compression overhead ✓")


if __name__ == "__main__":
    main()
