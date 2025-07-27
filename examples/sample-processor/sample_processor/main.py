"""Sample processor implementation demonstrating all base processor features."""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np

# Add base processor to path (in production, install via pip)
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent.parent
        / "services/shared/base-processor/src"
    ),
)

from base_processor import BaseProcessor  # noqa: E402
from base_processor.batch_processor import BatchProcessorMixin  # noqa: E402
from base_processor.exceptions import ValidationError  # noqa: E402
from base_processor.resource_manager import ResourceManagerMixin  # noqa: E402
from base_processor.state_machine import (  # noqa: E402
    StateMachineMixin,
    StateTransition,
)


class SampleProcessor(
    BatchProcessorMixin, ResourceManagerMixin, StateMachineMixin, BaseProcessor
):
    """Sample processor that demonstrates all base processor features.

    This processor implements:
    - Object detection simulation
    - Batch processing support
    - Resource management (CPU/GPU)
    - Frame state tracking
    - Full observability (metrics, tracing, logging)
    """

    def __init__(
        self,
        detection_threshold: float = 0.5,
        simulate_gpu: bool = False,
        processing_delay_ms: int = 10,
        **kwargs,
    ):
        """Initialize sample processor.

        Args:
            detection_threshold: Confidence threshold for detections
            simulate_gpu: Whether to simulate GPU processing
            processing_delay_ms: Simulated processing delay
            **kwargs: Base processor arguments
        """
        # Extract name for BaseProcessor
        name = kwargs.pop("name", "sample-processor")

        # Remove args that BaseProcessor doesn't accept
        kwargs.pop("enable_metrics", None)
        kwargs.pop("enable_tracing", None)
        kwargs.pop("batch_size", None)
        kwargs.pop("cpu_cores", None)
        kwargs.pop("memory_limit_mb", None)
        kwargs.pop("prefer_gpu", None)

        # Initialize all parent classes properly
        # Pass empty kwargs to ensure all mixins initialize
        super().__init__(name=name, **{})

        self.detection_threshold = detection_threshold
        self.simulate_gpu = simulate_gpu
        self.processing_delay_ms = processing_delay_ms
        self.model_loaded = False

    async def _initialize(self):
        """Setup the processor - load model, initialize resources."""  # noqa: D401
        self.log_with_context("info", "Loading detection model...")

        # Simulate model loading
        await asyncio.sleep(0.5)
        self.model_loaded = True

        # Register state callbacks - commented out for now
        # TODO: Fix state machine callback registration
        # self.state_machine.on_state_enter(
        #     StateTransition.COMPLETE, self._on_detection_complete
        # )

        self.log_with_context(
            "info",
            "Model loaded successfully",
            gpu_enabled=self.simulate_gpu,
            batch_size=self.batch_processor.config.batch_size,
        )

    async def validate_frame(self, frame: np.ndarray, metadata: Dict[str, Any]):
        """Validate input frame.

        Args:
            frame: Input frame
            metadata: Frame metadata

        Raises:
            ValidationError: If frame is invalid
        """
        if frame is None:
            raise ValidationError("Frame is None")

        if frame.size == 0:
            raise ValidationError("Frame is empty")

        # Check dimensions
        if len(frame.shape) not in [2, 3]:
            raise ValidationError(f"Invalid frame dimensions: {frame.shape}")

        # Check data type
        if frame.dtype not in [np.uint8, np.uint16, np.float32]:
            raise ValidationError(f"Unsupported frame dtype: {frame.dtype}")

        # Track frame in state machine
        await self.track_frame_lifecycle(metadata.get("frame_id", "unknown"), metadata)

    async def process_frame(
        self, frame: np.ndarray, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single frame - detect objects.

        Args:
            frame: Input frame
            metadata: Frame metadata

        Returns:
            Detection results
        """
        frame_id = metadata.get("frame_id", "unknown")

        # Track frame in state machine first
        await self.track_frame_lifecycle(frame_id, metadata)

        # Allocate resources
        async with self.with_resources(frame_id):
            # Update state to processing
            await self.state_machine.transition(frame_id, StateTransition.START)

            # Simulate processing delay
            await asyncio.sleep(self.processing_delay_ms / 1000.0)

            # Simulate object detection
            detections = self._simulate_detection(frame)

            # Filter by threshold
            filtered_detections = [
                d for d in detections if d["confidence"] >= self.detection_threshold
            ]

            result = {
                "detections": filtered_detections,
                "total_objects": len(filtered_detections),
                "processing_time_ms": self.processing_delay_ms,
                "frame_shape": frame.shape,
                "gpu_used": self.simulate_gpu,
            }

            # Update state to completed
            await self.state_machine.transition(
                frame_id, StateTransition.COMPLETE, result=result
            )

            # Update metrics
            self.count_frames("success")
            # Could also track objects detected as a custom metric if needed

            return result

    def _simulate_detection(self, frame: np.ndarray) -> list:
        """Simulate object detection on frame.

        Args:
            frame: Input frame

        Returns:
            List of detections
        """
        # Generate random detections based on frame
        h, w = frame.shape[:2]

        # Number of objects based on frame intensity
        avg_intensity = np.mean(frame)
        num_objects = int((avg_intensity / 255) * 5)  # 0-5 objects

        detections = []
        for _ in range(num_objects):
            # Random bounding box
            x1 = np.random.randint(0, w - 50)
            y1 = np.random.randint(0, h - 50)
            x2 = x1 + np.random.randint(20, 50)
            y2 = y1 + np.random.randint(20, 50)

            detection = {
                "class": np.random.choice(["person", "car", "bicycle", "dog", "cat"]),
                "confidence": np.random.uniform(0.3, 0.99),
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
            }
            detections.append(detection)

        return detections

    async def _on_detection_complete(self, frame_id: str, metadata: Dict[str, Any]):
        """Callback when detection completes."""  # noqa: D401
        self.log_with_context(
            "debug",
            f"Detection completed for frame {frame_id}",
            frame_id=frame_id,
        )

    async def _cleanup(self):
        """Cleanup resources."""
        self.log_with_context("info", "Unloading model...")
        self.model_loaded = False

        # Clean up state machine
        self.state_machine.cleanup()

    def supports_batch_processing(self) -> bool:
        """This processor supports batch processing."""  # noqa: D401
        return True

    async def prepare_batch(
        self, frames: list[np.ndarray], metadata_list: list[Dict[str, Any]]
    ) -> tuple[list[np.ndarray], list[Dict[str, Any]]]:
        """Prepare frames for batch processing.

        Args:
            frames: List of frames
            metadata_list: List of metadata

        Returns:
            Prepared frames and metadata
        """
        # Normalize frames to same dtype if needed
        normalized_frames = []
        for frame in frames:
            if frame.dtype != np.float32:
                frame = frame.astype(np.float32) / 255.0
            normalized_frames.append(frame)

        return normalized_frames, metadata_list


async def main():
    """Run the sample processor."""
    print("Sample Processor Demo")
    print("=" * 50)

    # Create processor
    processor = SampleProcessor(
        detection_threshold=0.6,
        simulate_gpu=False,
        processing_delay_ms=20,
        enable_metrics=True,
        enable_tracing=True,
    )

    try:
        # Initialize
        print("\n1. Initializing processor...")
        await processor.initialize()
        print("   ✓ Processor initialized")

        # Create test frames
        print("\n2. Creating test frames...")
        frames = []
        metadata_list = []

        for i in range(5):
            # Vary intensity to get different numbers of detections
            intensity = int((i / 4) * 255)
            frame = np.full((480, 640, 3), intensity, dtype=np.uint8)

            metadata = {
                "frame_id": f"demo_frame_{i:03d}",
                "timestamp": datetime.now().isoformat(),
                "camera_id": "demo_camera",
                "frame_number": i,
            }

            frames.append(frame)
            metadata_list.append(metadata)

        print(f"   ✓ Created {len(frames)} test frames")

        # Process individual frames
        print("\n3. Processing individual frames...")
        for frame, metadata in zip(frames[:2], metadata_list[:2]):
            result = await processor.process(frame, metadata)
            print(
                f"   Frame {metadata['frame_id']}: "
                f"{result['total_objects']} objects detected"
            )

        # Process batch
        print("\n4. Processing frames in batch...")
        batch_results = await processor.process_frames_in_batches(frames, metadata_list)

        total_objects = 0
        for batch_result in batch_results:
            for result in batch_result.results:
                if "result" in result and "total_objects" in result["result"]:
                    total_objects += result["result"]["total_objects"]

        print(f"   ✓ Processed {len(frames)} frames in {len(batch_results)} batches")
        print(f"   ✓ Total objects detected: {total_objects}")

        # Show metrics
        print("\n5. Processor metrics:")
        metrics = processor.get_metrics()
        print(f"   Frames processed: {metrics.get('frames_processed', 0)}")
        if "success_rate" in metrics:
            print(f"   Success rate: {metrics['success_rate']:.1%}")
        if "average_latency_ms" in metrics:
            print(f"   Average latency: {metrics['average_latency_ms']:.1f}ms")

        # Show state statistics
        print("\n6. State machine statistics:")
        state_stats = processor.state_machine.get_statistics()
        print(f"   Total frames tracked: {state_stats['total_frames']}")
        for state, count in state_stats["state_counts"].items():
            if count > 0:
                print(f"   {state}: {count}")

        # Show resource usage
        print("\n7. Resource statistics:")
        resource_stats = processor.resource_manager.get_allocation_stats()
        print(f"   Active allocations: {resource_stats['active_allocations']}")
        print(f"   Available CPUs: {resource_stats['available_cpus']}")
        print(f"   Available memory: {resource_stats['available_memory_mb']:.0f} MB")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
    finally:
        # Shutdown
        print("\n8. Shutting down...")
        await processor.cleanup()
        print("   ✓ Processor shut down")

    print("\n" + "=" * 50)
    print("Demo completed successfully!")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
