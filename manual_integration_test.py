#!/usr/bin/env python3
"""Manual integration test that can be run from local machine or containers."""

import json
import time

import requests


def test_health_endpoints():
    """Test that both services are healthy."""
    print("🔍 Testing health endpoints...")

    # Test frame-buffer
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        if response.status_code == 200:
            print("✅ Frame-buffer is healthy")
        else:
            print(f"❌ Frame-buffer returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frame-buffer not reachable: {e}")
        return False

    # Test sample-processor
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Sample-processor is healthy: {health_data.get('status')}")

            # Check for consumer info in details
            details = health_data.get("details", {})
            consumer_running = details.get("consumer_running", False)
            print(f"   Consumer running: {consumer_running}")

        else:
            print(f"❌ Sample-processor returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Sample-processor not reachable: {e}")
        return False

    return True


def test_frame_flow():
    """Test the frame flow from buffer to processor."""
    print("\n📤 Testing frame enqueue...")

    # Send test frames
    test_frames = []
    for i in range(3):
        frame_data = {
            "frame_id": f"manual_test_{i:03d}",
            "timestamp": time.time() + i,
            "camera_id": "manual_test_cam",
            "width": 640,
            "height": 480,
            "format": "RGB",
            "metadata": {"test": True, "source": "manual_integration_test"},
        }
        test_frames.append(frame_data)

        try:
            response = requests.post(
                "http://localhost:8002/frames/enqueue", json=frame_data, timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                print(
                    f"✅ Frame {frame_data['frame_id']} enqueued: "
                    f"{result.get('message_id')}"
                )
            else:
                print(
                    f"❌ Failed to enqueue frame {frame_data['frame_id']}: "
                    f"{response.status_code}"
                )
                return False
        except Exception as e:
            print(f"❌ Error enqueuing frame: {e}")
            return False

    # Check buffer status
    print("\n📊 Checking buffer status...")
    try:
        response = requests.get("http://localhost:8002/frames/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Buffer status: {json.dumps(status, indent=2)}")
        else:
            print(f"❌ Failed to get buffer status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting buffer status: {e}")

    # Test dequeue
    print("\n📥 Testing frame dequeue...")
    try:
        response = requests.get(
            "http://localhost:8002/frames/dequeue?count=3", timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print(
                f"✅ Dequeued {result.get('count', 0)} frames, "
                f"{result.get('remaining', 0)} remaining"
            )

            # If we got frames, the integration is working
            if result.get("count", 0) > 0:
                print("✅ Frame flow is working!")
                return True
            else:
                print("⚠️  No frames available for dequeue (consumer issue)")
                return False
        else:
            print(f"❌ Failed to dequeue frames: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error dequeuing frames: {e}")
        return False


def test_sample_processor_processing():
    """Test direct frame processing via API."""
    print("\n🔬 Testing direct frame processing...")

    try:
        test_request = {
            "frame_data": "dGVzdA==",  # Base64 for "test"
            "metadata": {"frame_id": "direct_api_test", "test": True},
        }

        response = requests.post(
            "http://localhost:8000/process", json=test_request, timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(
                f"✅ Direct processing successful: "
                f"{result.get('total_objects', 0)} objects detected"
            )
            return True
        else:
            print(f"❌ Direct processing failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error in direct processing: {e}")
        return False


def test_metrics():
    """Test metrics endpoints."""
    print("\n📈 Testing metrics endpoints...")

    try:
        response = requests.get("http://localhost:8000/metrics", timeout=5)
        if response.status_code == 200:
            metrics = response.json()
            print("✅ Metrics available:")

            proc_metrics = metrics.get("processor_metrics", {})
            print(f"   Frames processed: {proc_metrics.get('frames_processed', 0)}")

            state_stats = metrics.get("state_statistics", {})
            print(f"   Total frames tracked: {state_stats.get('total_frames', 0)}")

            resource_stats = metrics.get("resource_statistics", {})
            print(
                f"   Active allocations: {resource_stats.get('active_allocations', 0)}"
            )

            return True
        else:
            print(f"❌ Failed to get metrics: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting metrics: {e}")
        return False


def main():
    """Run the integration test."""
    print("🧪 Manual Sample Processor Integration Test")
    print("=" * 50)

    # Test 1: Health checks
    if not test_health_endpoints():
        print("\n❌ Health check failed - stopping test")
        return 1

    # Test 2: Frame flow
    if not test_frame_flow():
        print("\n❌ Frame flow test failed")

    # Test 3: Direct processing
    if not test_sample_processor_processing():
        print("\n❌ Direct processing test failed")

    # Test 4: Metrics
    if not test_metrics():
        print("\n❌ Metrics test failed")

    print("\n" + "=" * 50)
    print("🎉 Integration test completed!")
    print("\n💡 Note: If frame flow failed but direct processing works,")
    print("   it means the sample-processor consumer is not running properly.")
    return 0


if __name__ == "__main__":
    exit(main())
