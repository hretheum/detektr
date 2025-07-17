"""
Test service for OpenTelemetry configuration validation.

This script creates traces and metrics to verify that exporters are working.
"""

import os
import sys
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.shared.telemetry import setup_telemetry  # noqa: E402


def main() -> None:
    """Run telemetry test with traces and metrics."""
    # Setup telemetry
    tracer, meter, _ = setup_telemetry("test-service", "0.1.0")

    # Create a counter metric
    frame_counter = meter.create_counter(
        name="frames_processed_total",
        description="Total number of frames processed",
        unit="frame",
    )

    # Create a histogram metric
    processing_time = meter.create_histogram(
        name="frame_processing_duration_seconds",
        description="Time spent processing frames",
        unit="s",
    )

    print("Starting telemetry test...")

    # Create some spans and metrics
    with tracer.start_as_current_span("test_processing") as span:
        span.set_attribute("test.type", "validation")
        span.set_attribute("service.name", "test-service")

        # Simulate some work
        for i in range(5):
            with tracer.start_as_current_span(f"process_frame_{i}") as frame_span:
                frame_span.set_attribute("frame.id", f"frame_{i}")
                frame_span.set_attribute("frame.size", 1920 * 1080)

                # Simulate processing time
                start_time = time.time()
                time.sleep(0.1)  # 100ms
                duration = time.time() - start_time

                # Record metrics
                frame_counter.add(1, {"frame.type": "test"})
                processing_time.record(duration, {"operation": "validation"})

                print(f"Processed frame {i}")

        span.set_attribute("frames.count", 5)

    print("Test completed. Check Jaeger UI at http://localhost:16686")
    print("Check Prometheus metrics at http://localhost:9090/metrics")


if __name__ == "__main__":
    main()
