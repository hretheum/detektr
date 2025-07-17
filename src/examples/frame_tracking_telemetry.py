"""Example usage of frame tracking with OpenTelemetry decorators."""

import asyncio
import os
import sys
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.shared.telemetry import (  # noqa: E402
    setup_auto_instrumentation,
    setup_telemetry,
    traced,
    traced_frame,
)

# Setup telemetry first
tracer, meter, _ = setup_telemetry("frame-tracking-example", "0.1.0")

# Enable auto-instrumentation
setup_auto_instrumentation()


@traced_frame("frame_id")
def capture_frame(frame_id: str, camera_id: str = "camera_001") -> dict[str, any]:
    """Capture frame from camera."""
    time.sleep(0.05)  # Simulate capture time
    return {
        "frame_id": frame_id,
        "camera_id": camera_id,
        "timestamp": time.time(),
        "size": (1920, 1080),
        "format": "rgb24",
    }


@traced_frame("frame_id")
def detect_faces(frame_id: str, frame_data: dict) -> dict[str, any]:
    """Detect faces in frame."""
    time.sleep(0.1)  # Simulate AI processing
    return {
        "frame_id": frame_id,
        "faces_detected": 2,
        "face_locations": [(100, 100, 200, 200), (300, 150, 400, 250)],
        "confidence_scores": [0.95, 0.87],
    }


@traced_frame("frame_id")
def detect_objects(frame_id: str, frame_data: dict) -> dict[str, any]:
    """Detect objects in frame."""
    time.sleep(0.08)  # Simulate AI processing
    return {
        "frame_id": frame_id,
        "objects_detected": 3,
        "object_classes": ["person", "person", "car"],
        "confidence_scores": [0.92, 0.88, 0.79],
    }


@traced_frame("frame_id")
async def analyze_gesture(frame_id: str, face_data: dict) -> dict[str, any]:
    """Analyze gestures in frame (async processing)."""
    await asyncio.sleep(0.12)  # Simulate async AI processing
    return {
        "frame_id": frame_id,
        "gestures_detected": ["wave", "thumbs_up"],
        "gesture_confidence": [0.83, 0.91],
    }


@traced_frame("frame_id")
def store_results(frame_id: str, analysis_results: dict) -> bool:
    """Store analysis results."""
    time.sleep(0.02)  # Simulate database write
    return True


@traced
def create_frame_id() -> str:
    """Generate unique frame ID."""
    timestamp = int(time.time() * 1000)
    return f"frame_{timestamp}"


async def process_frame_pipeline(camera_id: str = "camera_001") -> dict[str, any]:
    """Complete frame processing pipeline with distributed tracing."""
    # Create a parent span for the entire pipeline
    with tracer.start_as_current_span("frame_processing_pipeline") as pipeline_span:
        # Generate frame ID
        frame_id = create_frame_id()
        pipeline_span.set_attribute("frame.id", frame_id)
        pipeline_span.set_attribute("camera.id", camera_id)

        # Step 1: Capture frame
        frame_data = capture_frame(frame_id, camera_id)
        pipeline_span.set_attribute(
            "frame.size", f"{frame_data['size'][0]}x{frame_data['size'][1]}"
        )

        # Step 2: Parallel AI processing
        # Note: These will all have the same frame.id in their spans
        face_task = asyncio.create_task(
            asyncio.to_thread(detect_faces, frame_id, frame_data)
        )
        object_task = asyncio.create_task(
            asyncio.to_thread(detect_objects, frame_id, frame_data)
        )

        # Wait for face detection to complete first
        face_results = await face_task

        # Step 3: Gesture analysis (depends on face detection)
        gesture_task = asyncio.create_task(analyze_gesture(frame_id, face_results))

        # Wait for all AI processing to complete
        object_results = await object_task
        gesture_results = await gesture_task

        # Step 4: Combine results
        analysis_results = {
            "frame_data": frame_data,
            "faces": face_results,
            "objects": object_results,
            "gestures": gesture_results,
        }

        # Step 5: Store results
        stored = store_results(frame_id, analysis_results)

        pipeline_span.set_attribute(
            "processing.faces_count", face_results["faces_detected"]
        )
        pipeline_span.set_attribute(
            "processing.objects_count", object_results["objects_detected"]
        )
        pipeline_span.set_attribute(
            "processing.gestures_count", len(gesture_results["gestures_detected"])
        )
        pipeline_span.set_attribute("storage.success", stored)

        return {
            "frame_id": frame_id,
            "pipeline_success": stored,
            "results": analysis_results,
        }


async def test_frame_tracking() -> None:
    """Test frame tracking with multiple frames."""
    print("\\n=== Testing Frame Tracking ===")

    # Process multiple frames to show distributed tracing
    tasks = []
    for i in range(3):
        camera_id = f"camera_{i+1:03d}"
        task = asyncio.create_task(process_frame_pipeline(camera_id))
        tasks.append(task)

    # Process frames in parallel
    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        print(
            f"Frame {i+1}: {result['frame_id']} - Success: {result['pipeline_success']}"
        )


async def test_nested_frame_processing() -> None:
    """Test nested frame processing with context propagation."""
    print("\\n=== Testing Nested Frame Processing ===")

    with tracer.start_as_current_span("batch_processing") as batch_span:
        batch_span.set_attribute("batch.size", 2)
        batch_span.set_attribute("batch.type", "security_scan")

        # Process frames with shared context
        frame1_result = await process_frame_pipeline("security_cam_001")
        frame2_result = await process_frame_pipeline("security_cam_002")

        # All frames in this batch will be linked through the batch span
        batch_span.set_attribute("batch.frames_processed", 2)
        batch_span.set_attribute(
            "batch.success",
            frame1_result["pipeline_success"] and frame2_result["pipeline_success"],
        )

        print(
            f"Batch processing completed: Frame1={frame1_result['frame_id']}, Frame2={frame2_result['frame_id']}"
        )


async def main() -> None:
    """Run all frame tracking tests."""
    print("Starting frame tracking telemetry examples...")
    print("This demonstrates distributed tracing for video frame processing")

    # Test basic frame tracking
    await test_frame_tracking()

    # Test nested contexts
    await test_nested_frame_processing()

    print("\\nFrame tracking tests completed!")
    print("Check Jaeger UI to see distributed traces with frame.id propagation")
    print("All spans for the same frame will have the same frame.id attribute")


if __name__ == "__main__":
    asyncio.run(main())
