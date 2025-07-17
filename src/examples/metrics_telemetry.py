"""Example usage of custom metrics with OpenTelemetry."""

import asyncio
import os
import random
import sys
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.shared.telemetry import (  # noqa: E402
    DetektorMetrics,
    get_metrics,
    increment_detections,
    increment_frames_processed,
    record_processing_time,
    setup_auto_instrumentation,
    setup_telemetry,
    traced,
)

# Setup telemetry first
tracer, meter, _ = setup_telemetry("metrics-example", "0.1.0")

# Enable auto-instrumentation
setup_auto_instrumentation()

# Get metrics instance
metrics = get_metrics("frame_processor")


@traced
def simulate_frame_processing(frame_id: str, camera_id: str) -> dict:
    """Simulate frame processing with metrics."""
    start_time = time.time()

    # Record frame received
    increment_frames_processed("frame_processor", 1, camera_id=camera_id)

    # Simulate capture stage
    capture_start = time.time()
    time.sleep(random.uniform(0.01, 0.05))  # Random capture time
    capture_duration = time.time() - capture_start
    record_processing_time(
        "frame_processor", "capture", capture_duration, camera_id=camera_id
    )

    # Simulate face detection
    face_start = time.time()
    time.sleep(random.uniform(0.05, 0.15))  # Random face detection time
    face_duration = time.time() - face_start
    record_processing_time(
        "frame_processor", "face_detection", face_duration, camera_id=camera_id
    )

    # Random number of faces detected
    faces_detected = random.randint(0, 3)
    if faces_detected > 0:
        increment_detections(
            "frame_processor", "face", faces_detected, camera_id=camera_id
        )

    # Simulate object detection
    object_start = time.time()
    time.sleep(random.uniform(0.03, 0.12))  # Random object detection time
    object_duration = time.time() - object_start
    record_processing_time(
        "frame_processor", "object_detection", object_duration, camera_id=camera_id
    )

    # Random number of objects detected
    objects_detected = random.randint(0, 5)
    if objects_detected > 0:
        increment_detections(
            "frame_processor", "object", objects_detected, camera_id=camera_id
        )

    # Record frame size
    width, height = random.choice([(1920, 1080), (1280, 720), (640, 480)])
    metrics.record_frame_size(width, height, {"camera_id": camera_id})

    # Record total processing time
    total_duration = time.time() - start_time
    record_processing_time(
        "frame_processor", "total", total_duration, camera_id=camera_id
    )

    # Simulate occasional errors
    if random.random() < 0.05:  # 5% error rate
        metrics.increment_errors("processing_timeout", {"camera_id": camera_id})

    return {
        "frame_id": frame_id,
        "camera_id": camera_id,
        "faces_detected": faces_detected,
        "objects_detected": objects_detected,
        "resolution": f"{width}x{height}",
        "processing_time": total_duration,
    }


@traced
def simulate_system_metrics():
    """Simulate system-level metrics."""
    # GPU utilization
    gpu_util = random.uniform(20, 95)
    metrics.record_gpu_utilization(gpu_util, "0")

    # Memory usage
    memory_mb = random.uniform(500, 2000)
    metrics.record_memory_usage(memory_mb)

    # Queue sizes
    for queue_name in ["incoming_frames", "processing_queue", "results_queue"]:
        queue_size = random.randint(0, 50)
        metrics.record_queue_size(queue_name, queue_size)


def test_basic_metrics():
    """Test basic metrics functionality."""
    print("\\n=== Testing Basic Metrics ===")

    # Process some frames
    for i in range(10):
        frame_id = f"frame_{int(time.time() * 1000)}_{i:03d}"
        camera_id = f"camera_{random.randint(1, 3):03d}"

        result = simulate_frame_processing(frame_id, camera_id)
        print(
            f"Processed {result['frame_id']}: {result['faces_detected']} faces, "
            f"{result['objects_detected']} objects ({result['resolution']})"
        )

    # Record system metrics
    simulate_system_metrics()
    print("System metrics recorded")


def test_service_specific_metrics():
    """Test service-specific metrics."""
    print("\\n=== Testing Service-Specific Metrics ===")

    # Different services
    services = ["face_recognition", "object_detection", "gesture_analysis"]

    for service in services:
        service_metrics = get_metrics(service)

        # Each service has different characteristics
        if service == "face_recognition":
            service_metrics.increment_frames_processed(5)
            service_metrics.record_processing_time("inference", 0.08)
            service_metrics.increment_detections("face", 3)

        elif service == "object_detection":
            service_metrics.increment_frames_processed(8)
            service_metrics.record_processing_time("inference", 0.12)
            service_metrics.increment_detections("person", 2)
            service_metrics.increment_detections("car", 1)

        elif service == "gesture_analysis":
            service_metrics.increment_frames_processed(3)
            service_metrics.record_processing_time("inference", 0.15)
            service_metrics.increment_detections("gesture", 1)

        print(f"{service}: metrics recorded")


async def test_concurrent_metrics():
    """Test metrics from concurrent processing."""
    print("\\n=== Testing Concurrent Metrics ===")

    async def process_camera_stream(camera_id: str, frames_count: int):
        """Simulate processing frames from a camera."""
        for i in range(frames_count):
            frame_id = f"camera_{camera_id}_frame_{i:03d}"

            # Simulate async processing
            await asyncio.sleep(random.uniform(0.01, 0.03))

            # Use sync function in async context
            result = await asyncio.to_thread(
                simulate_frame_processing, frame_id, camera_id
            )

        return f"Camera {camera_id}: {frames_count} frames processed"

    # Process multiple camera streams concurrently
    tasks = []
    for camera_num in range(1, 4):  # 3 cameras
        camera_id = f"camera_{camera_num:03d}"
        frames_count = random.randint(5, 10)
        task = asyncio.create_task(process_camera_stream(camera_id, frames_count))
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    for result in results:
        print(result)


def test_custom_metrics():
    """Test custom business metrics."""
    print("\\n=== Testing Custom Business Metrics ===")

    business_metrics = get_metrics("security_alerts")

    # Business-specific metrics
    alert_types = ["intrusion", "loitering", "abandoned_object", "crowd_detection"]

    for _ in range(15):
        alert_type = random.choice(alert_types)
        confidence = random.uniform(0.7, 0.99)
        camera_zone = f"zone_{random.randint(1, 5)}"

        # Custom counter
        counter = business_metrics.get_counter(
            "alerts_generated", "Security alerts generated"
        )
        counter.add(
            1,
            {
                "alert_type": alert_type,
                "camera_zone": camera_zone,
                "confidence_level": "high" if confidence > 0.9 else "medium",
            },
        )

        # Custom histogram for confidence scores
        histogram = business_metrics.get_histogram(
            "alert_confidence", "Alert confidence scores"
        )
        histogram.record(confidence, {"alert_type": alert_type})

        print(f"Alert: {alert_type} in {camera_zone} (confidence: {confidence:.2f})")


def show_metrics_summary():
    """Show summary of what metrics were created."""
    print("\\n=== Metrics Summary ===")
    print("The following detektor metrics were generated:")
    print("- detektor_frame_processor_frames_processed")
    print("- detektor_frame_processor_detections_total")
    print("- detektor_frame_processor_processing_duration_seconds")
    print("- detektor_frame_processor_frame_size_pixels")
    print("- detektor_frame_processor_errors_total")
    print("- detektor_frame_processor_gpu_utilization_percent")
    print("- detektor_frame_processor_memory_usage_mb")
    print("- detektor_frame_processor_queue_size")
    print("- detektor_face_recognition_*")
    print("- detektor_object_detection_*")
    print("- detektor_gesture_analysis_*")
    print("- detektor_security_alerts_*")
    print("\\nCheck Prometheus at http://localhost:9090 to see these metrics")


async def main():
    """Run all metrics tests."""
    print("Starting custom metrics telemetry examples...")

    # Test basic metrics
    test_basic_metrics()

    # Test service-specific metrics
    test_service_specific_metrics()

    # Test concurrent metrics
    await test_concurrent_metrics()

    # Test custom business metrics
    test_custom_metrics()

    # Show summary
    show_metrics_summary()

    print("\\nMetrics tests completed!")
    print("All metrics are automatically exported to Prometheus")


if __name__ == "__main__":
    asyncio.run(main())
