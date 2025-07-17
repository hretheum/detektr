"""Example showing metrics with trace exemplar support."""

import asyncio
import random
import time
from datetime import datetime

from opentelemetry import trace

from src.shared.kernel.domain import Frame
from src.shared.telemetry import setup_telemetry
from src.shared.telemetry.decorators import traced
from src.shared.telemetry.frame_tracking import set_frame_context
from src.shared.telemetry.metrics import get_metrics


class FrameProcessorWithMetrics:
    """Example frame processor with metrics and traces."""

    def __init__(self, service_name: str = "frame_processor"):
        """Initialize processor.

        Args:
            service_name: Name of the service
        """
        self.service_name = service_name
        self.metrics = get_metrics(service_name)
        self.tracer = trace.get_tracer(__name__)

    @traced(span_name="process_frame")
    async def process_frame(self, frame: Frame) -> None:
        """Process a frame with full telemetry.

        Args:
            frame: Frame to process
        """
        # Set frame context for propagation
        set_frame_context(frame)

        # Record frame received
        self.metrics.increment_frames_processed(
            attributes={"camera_id": frame.camera_id, "frame_id": str(frame.id)}
        )

        # Simulate processing stages
        stages = ["face_detection", "object_detection", "motion_analysis"]

        for stage in stages:
            start_time = time.time()

            with self.tracer.start_as_current_span(f"stage_{stage}") as span:
                span.set_attribute("stage.name", stage)
                span.set_attribute("frame.id", str(frame.id))

                # Simulate processing
                await asyncio.sleep(random.uniform(0.01, 0.1))

                # Random chance of error
                if random.random() < 0.1:
                    error_type = random.choice(["gpu_oom", "timeout", "invalid_input"])
                    self.metrics.increment_errors(
                        error_type,
                        attributes={"stage": stage, "camera_id": frame.camera_id},
                    )
                    span.set_status(trace.Status(trace.StatusCode.ERROR, error_type))
                    raise Exception(f"Processing failed: {error_type}")

                # Simulate detections
                if stage == "face_detection":
                    face_count = random.randint(0, 5)
                    self.metrics.increment_detections(
                        "face",
                        count=face_count,
                        attributes={"camera_id": frame.camera_id},
                    )
                    span.set_attribute("detections.face_count", face_count)

                elif stage == "object_detection":
                    object_count = random.randint(0, 10)
                    self.metrics.increment_detections(
                        "object",
                        count=object_count,
                        attributes={"camera_id": frame.camera_id},
                    )
                    span.set_attribute("detections.object_count", object_count)

                # Record stage duration
                duration = time.time() - start_time
                self.metrics.record_processing_time(
                    stage,
                    duration,
                    attributes={"camera_id": frame.camera_id, "success": "true"},
                )

        # Record total processing time
        total_time = time.time() - frame.created_at.timestamp()
        span = trace.get_current_span()
        span.set_attribute("frame.total_processing_time_ms", total_time * 1000)


async def generate_load(processor: FrameProcessorWithMetrics, camera_id: str):
    """Generate load for testing.

    Args:
        processor: Frame processor instance
        camera_id: Camera ID to simulate
    """
    for i in range(100):
        frame = Frame.create(camera_id=camera_id, timestamp=datetime.now())

        try:
            await processor.process_frame(frame)
            print(f"Processed frame {frame.id} from {camera_id}")
        except Exception as e:
            print(f"Failed to process frame {frame.id}: {e}")

        await asyncio.sleep(random.uniform(0.1, 0.5))


async def main():
    """Run the example."""
    # Setup telemetry
    shutdown = setup_telemetry(
        service_name="metrics_exemplar_example", otlp_endpoint="http://localhost:4317"
    )

    processor = FrameProcessorWithMetrics()

    print("Starting frame processing with metrics and exemplars...")
    print("Metrics will include trace_id and span_id attributes")
    print("Check Prometheus at http://localhost:9090")
    print("Check Jaeger at http://localhost:16686")
    print()

    # Simulate multiple cameras
    cameras = ["cam01", "cam02", "cam03"]
    tasks = []

    for camera_id in cameras:
        task = asyncio.create_task(generate_load(processor, camera_id))
        tasks.append(task)

    # Run for a while
    try:
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Cancel tasks
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        # Shutdown telemetry
        shutdown()

    print("\nExample completed!")
    print("\nTo see exemplars in action:")
    print(
        "1. Query a metric in Prometheus: detektor_frame_processor_processing_duration_seconds"
    )
    print("2. Look for trace_id and span_id labels in the results")
    print("3. Click on a trace_id to jump to Jaeger")


if __name__ == "__main__":
    asyncio.run(main())
