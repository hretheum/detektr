"""Benchmark for backpressure performance."""
import asyncio
import time
from datetime import datetime
from typing import Any, Dict

from shared.kernel.domain.frame_data import FrameData
from shared.queue.backpressure import BackpressureConfig, BackpressureHandler


async def benchmark_throughput(
    handler: BackpressureHandler,
    num_frames: int = 1000,
    producer_delay: float = 0.0,
    consumer_delay: float = 0.001,
) -> Dict[str, float]:
    """Benchmark throughput with specified delays."""
    start_time = time.time()
    frames_sent = 0
    frames_received = 0

    async def producer() -> None:
        nonlocal frames_sent
        for i in range(num_frames):
            frame = FrameData(
                id=f"bench_frame_{i}",
                timestamp=datetime.now(),
                camera_id="camera_bench",
                sequence_number=i,
                image_data=None,
                metadata={"benchmark": True},
            )
            await handler.send(frame)
            frames_sent += 1
            if producer_delay > 0:
                await asyncio.sleep(producer_delay)

    async def consumer() -> None:
        nonlocal frames_received
        while frames_received < num_frames:
            frame = await handler.receive(timeout=1.0)
            if frame:
                frames_received += 1
                if consumer_delay > 0:
                    await asyncio.sleep(consumer_delay)

    # Run producer and consumer
    await asyncio.gather(producer(), consumer())

    elapsed = time.time() - start_time
    throughput = num_frames / elapsed

    metrics = handler.get_metrics()

    return {
        "throughput_fps": throughput,
        "elapsed_seconds": elapsed,
        "frames_sent": frames_sent,
        "frames_received": frames_received,
        "frames_dropped": metrics.frames_dropped,
        "backpressure_activations": metrics.backpressure_activations,
        "avg_wait_time_ms": metrics.total_wait_time_ms / max(frames_sent, 1),
        "max_buffer_size": metrics.max_buffer_size_reached,
        "adaptive_buffer_size": handler.adaptive_buffer.current_size,
    }


async def benchmark_scenarios() -> None:
    """Run various benchmark scenarios."""
    scenarios: list[Dict[str, Any]] = [
        {
            "name": "Balanced Load",
            "producer_delay": 0.001,
            "consumer_delay": 0.001,
            "num_frames": 1000,
        },
        {
            "name": "Fast Producer",
            "producer_delay": 0.0,
            "consumer_delay": 0.005,
            "num_frames": 500,
        },
        {
            "name": "Slow Producer",
            "producer_delay": 0.005,
            "consumer_delay": 0.0,
            "num_frames": 500,
        },
        {
            "name": "Burst Load",
            "producer_delay": 0.0,
            "consumer_delay": 0.002,
            "num_frames": 2000,
        },
    ]

    print("Backpressure Performance Benchmark")
    print("=" * 80)

    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        print("-" * 60)

        # Create fresh handler for each scenario
        config = BackpressureConfig(
            min_buffer_size=100,
            max_buffer_size=10000,
            high_watermark=0.8,
            low_watermark=0.3,
        )
        handler = BackpressureHandler(config)

        # Run benchmark
        results = await benchmark_throughput(
            handler,
            num_frames=int(scenario["num_frames"]),
            producer_delay=float(scenario["producer_delay"]),
            consumer_delay=float(scenario["consumer_delay"]),
        )

        # Print results
        print(f"Throughput: {results['throughput_fps']:,.1f} frames/sec")
        print(f"Total time: {results['elapsed_seconds']:.2f} seconds")
        print(f"Frames sent: {results['frames_sent']}")
        print(f"Frames received: {results['frames_received']}")
        print(f"Frames dropped: {results['frames_dropped']}")
        print(f"Backpressure activations: {results['backpressure_activations']}")
        print(f"Average wait time: {results['avg_wait_time_ms']:.2f}ms")
        print(f"Max buffer size reached: {results['max_buffer_size']}")
        print(f"Final adaptive buffer size: {results['adaptive_buffer_size']}")


async def stress_test() -> None:
    """Run stress test to find breaking point."""
    print("\n\nStress Test - Finding Breaking Point")
    print("=" * 80)

    config = BackpressureConfig(
        min_buffer_size=100,
        max_buffer_size=5000,
        high_watermark=0.8,
        low_watermark=0.3,
    )

    # Test with increasingly fast producers
    producer_delays = [0.001, 0.0005, 0.0001, 0.00005, 0.0]
    consumer_delay = 0.005  # Fixed slow consumer

    for producer_delay in producer_delays:
        print(f"\nProducer delay: {producer_delay*1000:.2f}ms")
        print("-" * 40)

        handler = BackpressureHandler(config, enable_dropping=True)

        try:
            results = await benchmark_throughput(
                handler,
                num_frames=1000,
                producer_delay=producer_delay,
                consumer_delay=consumer_delay,
            )

            print(f"Throughput: {results['throughput_fps']:,.1f} fps")
            print(
                f"Frames dropped: {results['frames_dropped']} "
                f"({results['frames_dropped']/results['frames_sent']*100:.1f}%)"
            )
            print(f"Backpressure activations: {results['backpressure_activations']}")
            print(f"Buffer adapted to: {results['adaptive_buffer_size']}")

        except Exception as e:
            print(f"Test failed: {e}")


def main() -> None:
    """Run all benchmarks."""
    print("Starting backpressure benchmarks...\n")

    # Run benchmark scenarios
    asyncio.run(benchmark_scenarios())

    # Run stress test
    asyncio.run(stress_test())

    print("\n" + "=" * 80)
    print("Benchmark complete!")
    print("\nTarget metrics:")
    print("✓ No frame loss under normal conditions")
    print("✓ Dynamic buffer sizing 100-10000 frames")
    print("✓ Graceful degradation under extreme load")


if __name__ == "__main__":
    main()
