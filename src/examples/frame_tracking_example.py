"""Example demonstrating frame tracking with correlation."""

import asyncio
import logging
import time
from datetime import datetime

from src.shared.kernel.domain import Frame
from src.shared.telemetry import (
    CorrelatedMetrics,
    FrameProcessor,
    configure_correlated_logging,
    configure_stdlib_correlation,
    get_correlated_logger,
    setup_telemetry,
    traced_frame_operation,
    traced_processing_stage,
)

# Setup logging and telemetry
configure_correlated_logging()
configure_stdlib_correlation()
tracer, meter, _ = setup_telemetry("frame-tracking-example")

# Get logger
logger = get_correlated_logger(__name__)
stdlib_logger = logging.getLogger(__name__)


class FaceDetectionProcessor(FrameProcessor):
    """Example face detection processor."""

    def __init__(self):
        """Initialize face detection processor."""
        super().__init__("face-detection")

    @traced_processing_stage("face_detection")
    async def detect_faces(self, frame: Frame) -> dict:
        """Detect faces in frame."""
        logger.info("Starting face detection", frame_id=str(frame.id))

        # Simulate processing
        await asyncio.sleep(0.1)

        # Record metrics
        CorrelatedMetrics.increment_processed(stage="face_detection")
        CorrelatedMetrics.observe_duration(0.1, stage="face_detection")

        return {"faces_found": 2, "confidence": 0.95, "processing_time_ms": 100}


class ObjectDetectionProcessor(FrameProcessor):
    """Example object detection processor."""

    def __init__(self):
        """Initialize object detection processor."""
        super().__init__("object-detection")

    @traced_processing_stage("object_detection", auto_complete=True)
    def detect_objects(self, frame: Frame) -> dict:
        """Detect objects in frame."""
        # Using stdlib logger to show correlation
        stdlib_logger.info("Starting object detection")

        # Simulate processing
        time.sleep(0.05)

        # Simulate occasional errors
        if frame.camera_id == "cam02" and frame.timestamp.second % 10 == 0:
            CorrelatedMetrics.increment_errors(
                stage="object_detection", error_type="gpu_memory"
            )
            raise RuntimeError("GPU out of memory")

        # Record success metrics
        CorrelatedMetrics.increment_processed(stage="object_detection")
        CorrelatedMetrics.observe_duration(0.05, stage="object_detection")

        return {
            "objects": ["person", "car", "bicycle"],
            "count": 3,
            "processing_time_ms": 50,
        }


@traced_frame_operation(span_name="pipeline.process_frame")
async def process_frame_pipeline(frame: Frame) -> dict:
    """Process frame through detection pipeline."""
    logger.info(
        "Starting frame pipeline", camera_id=frame.camera_id, state=frame.state.value
    )

    # Transition states
    frame.transition_to(frame.state.QUEUED)
    logger.info("Frame queued")

    frame.transition_to(frame.state.PROCESSING)
    logger.info("Frame processing started")

    results = {}

    try:
        # Face detection
        face_processor = FaceDetectionProcessor()
        face_results = await face_processor.detect_faces(frame)
        results["faces"] = face_results
        logger.info("Face detection completed", results=face_results)

        # Object detection
        obj_processor = ObjectDetectionProcessor()
        obj_results = obj_processor.detect_objects(frame)
        results["objects"] = obj_results
        logger.info("Object detection completed", results=obj_results)

        # Mark as completed
        frame.mark_as_completed()
        logger.info("Frame processing completed successfully")

        # Record success metric
        CorrelatedMetrics.increment_processed(stage="pipeline", status="success")

    except Exception as e:
        logger.exception("Frame processing failed", error=str(e))
        frame.mark_as_failed(str(e))

        # Record failure metric
        CorrelatedMetrics.increment_processed(stage="pipeline", status="failure")
        raise

    return results


async def simulate_frame_processing():
    """Simulate processing frames from multiple cameras."""
    cameras = ["cam01", "cam02", "cam03"]

    for i in range(5):
        for camera_id in cameras:
            # Create frame
            frame = Frame.create(camera_id=camera_id, timestamp=datetime.now())

            logger.info(
                "Created new frame",
                frame_id=str(frame.id),
                camera_id=camera_id,
                iteration=i,
            )

            try:
                # Process frame
                await process_frame_pipeline(frame)

                # Log total processing time
                total_time = frame.total_processing_time_ms
                logger.info(
                    "Frame pipeline completed",
                    total_processing_time_ms=total_time,
                    stages_completed=len(frame.processing_stages),
                )

            except Exception as e:
                logger.error(
                    "Frame pipeline failed", error=str(e), frame_state=frame.state.value
                )

            # Small delay between frames
            await asyncio.sleep(0.1)


def main():
    """Run frame tracking example."""
    print("Starting frame tracking example...")
    print("Check logs for correlation fields: trace_id, span_id, frame_id")
    print("Metrics will include camera_id labels")
    print("-" * 60)

    # Run simulation
    asyncio.run(simulate_frame_processing())

    print("\nExample completed!")
    print("In production, you would see:")
    print("- Logs in Loki with frame_id for filtering")
    print("- Traces in Jaeger with frame context")
    print("- Metrics in Prometheus with camera labels")


if __name__ == "__main__":
    main()
