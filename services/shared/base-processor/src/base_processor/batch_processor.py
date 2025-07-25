"""Batch processing support for frame processors."""
import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

import numpy as np

T = TypeVar("T")


@dataclass
class BatchResult:
    """Result of batch processing."""

    batch_id: str
    total_items: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]
    errors: List[Tuple[int, Exception]]
    processing_time: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int = 32
    max_concurrent_batches: int = 2
    timeout_per_item: float = 1.0
    retry_failed_items: bool = True
    preserve_order: bool = False
    error_threshold_percent: float = 50.0


class BatchProcessor:
    """Handles batch processing of frames."""

    def __init__(self, config: Optional[BatchConfig] = None):
        """Initialize batch processor.

        Args:
            config: Batch processing configuration
        """
        self.config = config or BatchConfig()
        self._batch_semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
        self._batch_counter = 0

    async def process_batch(
        self,
        items: List[Tuple[np.ndarray, Dict[str, Any]]],
        process_func: Callable,
        batch_id: Optional[str] = None,
    ) -> BatchResult:
        """Process a batch of items.

        Args:
            items: List of (frame, metadata) tuples
            process_func: Async function to process each item
            batch_id: Optional batch identifier

        Returns:
            BatchResult with processing outcomes
        """
        if not batch_id:
            self._batch_counter += 1
            batch_id = f"batch_{self._batch_counter}"

        start_time = time.time()
        results = []
        errors = []

        async with self._batch_semaphore:
            # Process items concurrently within batch
            tasks = []
            for idx, (frame, metadata) in enumerate(items):
                task = self._process_item_with_timeout(
                    idx, frame, metadata, process_func
                )
                tasks.append(task)

            # Wait for all tasks
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect results and errors
            for idx, outcome in enumerate(outcomes):
                if isinstance(outcome, Exception):
                    errors.append((idx, outcome))
                    results.append({"error": str(outcome), "index": idx})
                else:
                    results.append(outcome)

        processing_time = time.time() - start_time

        return BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            successful=len(items) - len(errors),
            failed=len(errors),
            results=results,
            errors=errors,
            processing_time=processing_time,
        )

    async def _process_item_with_timeout(
        self,
        idx: int,
        frame: np.ndarray,
        metadata: Dict[str, Any],
        process_func: Callable,
    ) -> Dict[str, Any]:
        """Process single item with timeout."""
        try:
            timeout = self.config.timeout_per_item
            result = await asyncio.wait_for(
                process_func(frame, metadata), timeout=timeout
            )
            return {"index": idx, "result": result, "metadata": metadata}
        except asyncio.TimeoutError:
            raise TimeoutError(f"Item {idx} processing timed out after {timeout}s")
        except Exception as e:
            raise

    async def process_in_batches(
        self,
        frames: List[np.ndarray],
        metadata_list: List[Dict[str, Any]],
        process_func: Callable,
    ) -> List[BatchResult]:
        """Process multiple frames in batches.

        Args:
            frames: List of frames to process
            metadata_list: List of metadata for each frame
            process_func: Async function to process each frame

        Returns:
            List of BatchResult objects
        """
        if len(frames) != len(metadata_list):
            raise ValueError("Number of frames must match number of metadata entries")

        # Create batches
        items = list(zip(frames, metadata_list))
        batch_results = []

        for i in range(0, len(items), self.config.batch_size):
            batch = items[i : i + self.config.batch_size]
            batch_id = f"batch_{i // self.config.batch_size}"

            result = await self.process_batch(batch, process_func, batch_id)
            batch_results.append(result)

            # Check error threshold
            error_percent = (result.failed / result.total_items) * 100
            if error_percent > self.config.error_threshold_percent:
                raise BatchProcessingError(
                    f"Batch {batch_id} exceeded error threshold: "
                    f"{error_percent:.1f}% > {self.config.error_threshold_percent}%"
                )

        return batch_results

    def create_optimized_batches(
        self, frames: List[np.ndarray], metadata_list: List[Dict[str, Any]]
    ) -> List[List[Tuple[np.ndarray, Dict[str, Any]]]]:
        """Create optimized batches based on frame characteristics.

        Args:
            frames: List of frames
            metadata_list: List of metadata

        Returns:
            List of batches optimized for processing
        """
        # Group by frame dimensions for better GPU utilization
        dimension_groups = {}

        for idx, (frame, metadata) in enumerate(zip(frames, metadata_list)):
            key = frame.shape
            if key not in dimension_groups:
                dimension_groups[key] = []
            dimension_groups[key].append((idx, frame, metadata))

        # Create batches from groups
        batches = []
        for dimension, group in dimension_groups.items():
            # Sort by original index if order needs to be preserved
            if self.config.preserve_order:
                group.sort(key=lambda x: x[0])

            # Create batches of uniform size
            for i in range(0, len(group), self.config.batch_size):
                batch = [(f, m) for _, f, m in group[i : i + self.config.batch_size]]
                batches.append(batch)

        return batches


class BatchProcessorMixin:
    """Mixin to add batch processing capabilities to processors."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Extract batch configuration
        batch_config = BatchConfig(
            batch_size=kwargs.get("batch_size", 32),
            max_concurrent_batches=kwargs.get("max_concurrent_batches", 2),
            timeout_per_item=kwargs.get("timeout_per_item", 1.0),
            retry_failed_items=kwargs.get("retry_failed_items", True),
            preserve_order=kwargs.get("preserve_order", False),
            error_threshold_percent=kwargs.get("error_threshold_percent", 50.0),
        )

        self.batch_processor = BatchProcessor(batch_config)

    async def process_batch(
        self, frames: List[np.ndarray], metadata_list: List[Dict[str, Any]]
    ) -> BatchResult:
        """Process a batch of frames.

        Args:
            frames: List of frames to process
            metadata_list: List of metadata for each frame

        Returns:
            BatchResult object
        """
        # Log batch start
        self.log_with_context(
            "info",
            f"Starting batch processing of {len(frames)} frames",
            batch_size=len(frames),
        )

        # Create items list
        items = list(zip(frames, metadata_list))

        # Process batch
        result = await self.batch_processor.process_batch(
            items, self.process_frame  # Use the processor's process_frame method
        )

        # Log batch completion
        self.log_with_context(
            "info",
            f"Batch processing completed",
            total=result.total_items,
            successful=result.successful,
            failed=result.failed,
            processing_time=result.processing_time,
        )

        # Update metrics
        self.count_frames("batch_success" if result.failed == 0 else "batch_partial")

        return result

    async def process_frames_in_batches(
        self, frames: List[np.ndarray], metadata_list: List[Dict[str, Any]]
    ) -> List[BatchResult]:
        """Process multiple frames in optimized batches.

        Args:
            frames: List of frames to process
            metadata_list: List of metadata for each frame

        Returns:
            List of BatchResult objects
        """
        # Create optimized batches
        batches = self.batch_processor.create_optimized_batches(frames, metadata_list)

        self.log_with_context(
            "info",
            f"Processing {len(frames)} frames in {len(batches)} batches",
            total_frames=len(frames),
            num_batches=len(batches),
        )

        # Process all batches
        results = []
        for batch_idx, batch in enumerate(batches):
            batch_frames = [f for f, _ in batch]
            batch_metadata = [m for _, m in batch]

            result = await self.process_batch(batch_frames, batch_metadata)
            results.append(result)

        return results

    def supports_batch_processing(self) -> bool:
        """Check if processor supports batch processing.

        Override this method to indicate batch support.
        """
        return True

    async def prepare_batch(
        self, frames: List[np.ndarray], metadata_list: List[Dict[str, Any]]
    ) -> Tuple[List[np.ndarray], List[Dict[str, Any]]]:
        """Prepare frames for batch processing.

        Override this method to implement batch-specific preparation.

        Args:
            frames: Input frames
            metadata_list: Metadata for each frame

        Returns:
            Prepared frames and metadata
        """
        return frames, metadata_list


class BatchProcessingError(Exception):
    """Error during batch processing."""

    pass


def create_batched_array(
    frames: List[np.ndarray], pad_value: float = 0.0
) -> Tuple[np.ndarray, List[Tuple[int, ...]]]:
    """Create a batched array from frames with different sizes.

    Args:
        frames: List of frames to batch
        pad_value: Value to use for padding

    Returns:
        Batched array and original shapes
    """
    if not frames:
        raise ValueError("No frames to batch")

    # Find maximum dimensions
    max_shape = [0] * len(frames[0].shape)
    original_shapes = []

    for frame in frames:
        original_shapes.append(frame.shape)
        for i, dim in enumerate(frame.shape):
            max_shape[i] = max(max_shape[i], dim)

    # Create padded batch
    batch_shape = [len(frames)] + max_shape
    batch = np.full(batch_shape, pad_value, dtype=frames[0].dtype)

    # Fill batch with frames
    for i, frame in enumerate(frames):
        slices = [i] + [slice(0, dim) for dim in frame.shape]
        batch[tuple(slices)] = frame

    return batch, original_shapes


def unbatch_array(
    batch: np.ndarray, original_shapes: List[Tuple[int, ...]]
) -> List[np.ndarray]:
    """Extract original frames from batched array.

    Args:
        batch: Batched array
        original_shapes: Original shapes of frames

    Returns:
        List of frames with original shapes
    """
    frames = []

    for i, shape in enumerate(original_shapes):
        slices = [i] + [slice(0, dim) for dim in shape]
        frame = batch[tuple(slices)].copy()
        frames.append(frame)

    return frames
