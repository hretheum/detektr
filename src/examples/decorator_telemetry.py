"""Example usage of custom OpenTelemetry decorators."""

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
    traced_method,
)

# Setup telemetry first
tracer, meter, _ = setup_telemetry("decorator-example", "0.1.0")

# Enable auto-instrumentation
setup_auto_instrumentation()


@traced
def process_frame(frame_id: str) -> dict[str, str]:
    """Process a frame with automatic tracing."""
    time.sleep(0.1)  # Simulate processing
    return {
        "frame_id": frame_id,
        "status": "processed",
        "timestamp": str(time.time()),
    }


@traced(span_name="custom_processing", attributes={"version": "2.0"})
def process_with_custom_name(data: str) -> str:
    """Function with custom span name and attributes."""
    time.sleep(0.05)
    return f"processed_{data}"


@traced
async def async_process_frame(frame_id: str) -> dict[str, str]:
    """Async function with automatic tracing."""
    await asyncio.sleep(0.1)  # Simulate async processing
    return {
        "frame_id": frame_id,
        "status": "async_processed",
        "timestamp": str(time.time()),
    }


@traced(record_exception=True)
def failing_function(should_fail: bool) -> str:
    """Function that can fail to test exception recording."""
    if should_fail:
        raise ValueError("Something went wrong!")
    return "success"


class FrameProcessor:
    """Example class using traced_method decorator."""

    def __init__(self, processor_id: str):
        self.processor_id = processor_id
        self.version = "1.0"

    @traced_method(include_self_attrs=["processor_id", "version"])
    def process(self, frame_id: str, priority: int = 1) -> dict[str, any]:
        """Process frame with instance attributes in span."""
        time.sleep(0.02 * priority)  # Processing time based on priority
        return {
            "frame_id": frame_id,
            "processor_id": self.processor_id,
            "priority": priority,
            "status": "completed",
        }

    @traced_method(span_name="validate_frame_data")
    def validate(self, frame_data: dict[str, any]) -> bool:
        """Validate frame data."""
        time.sleep(0.01)
        return "frame_id" in frame_data


def test_basic_decorator() -> None:
    """Test basic @traced decorator."""
    print("\n=== Testing basic @traced decorator ===")

    # This will create a span named "process_frame"
    result = process_frame("frame_001")
    print(f"Result: {result}")

    # This will create a span with custom name and attributes
    result = process_with_custom_name("test_data")
    print(f"Custom result: {result}")


async def test_async_decorator() -> None:
    """Test @traced decorator with async functions."""
    print("\n=== Testing async @traced decorator ===")

    # This will create a span for async function
    result = await async_process_frame("async_frame_001")
    print(f"Async result: {result}")


def test_exception_handling() -> None:
    """Test exception recording in spans."""
    print("\n=== Testing exception handling ===")

    # Success case
    result = failing_function(False)
    print(f"Success: {result}")

    # Failure case (exception will be recorded in span)
    try:
        failing_function(True)
    except ValueError as e:
        print(f"Expected error: {e}")


def test_method_decorator() -> None:
    """Test @traced_method decorator."""
    print("\n=== Testing @traced_method decorator ===")

    processor = FrameProcessor("processor_123")

    # This will include processor_id and version in span attributes
    result = processor.process("frame_002", priority=3)
    print(f"Method result: {result}")

    # Test validation method
    frame_data = {"frame_id": "frame_003", "size": 1920 * 1080}
    is_valid = processor.validate(frame_data)
    print(f"Validation result: {is_valid}")


def test_nested_spans() -> None:
    """Test nested spans with multiple decorated functions."""
    print("\n=== Testing nested spans ===")

    with tracer.start_as_current_span("pipeline_processing") as span:
        span.set_attribute("pipeline.type", "full_processing")

        # Step 1: Validate
        processor = FrameProcessor("pipeline_processor")
        frame_data = {"frame_id": "pipeline_frame", "data": "test"}

        is_valid = processor.validate(frame_data)
        span.set_attribute("validation.result", is_valid)

        if is_valid:
            # Step 2: Process
            result = processor.process("pipeline_frame", priority=2)
            span.set_attribute("processing.result", "success")

            # Step 3: Final processing
            final_result = process_with_custom_name(result["frame_id"])
            span.set_attribute("final_processing.result", final_result)

            print(f"Pipeline completed: {final_result}")


async def main() -> None:
    """Run all decorator tests."""
    print("Starting custom decorator telemetry examples...")

    # Test basic decorator
    test_basic_decorator()

    # Test async decorator
    await test_async_decorator()

    # Test exception handling
    test_exception_handling()

    # Test method decorator
    test_method_decorator()

    # Test nested spans
    test_nested_spans()

    print("\nDecorator tests completed!")
    print("All functions are automatically traced with @traced decorator")


if __name__ == "__main__":
    asyncio.run(main())
