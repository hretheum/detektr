"""Abstract base processor for frame processing services."""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from .exceptions import InitializationError, ProcessingError, ValidationError
from .logging import LoggingMixin, ProcessingContext
from .metrics import ProcessorMetrics
from .metrics_decorators import MetricsContext, MetricsMixin, timed_method
from .pipeline import ProcessingPipeline
from .retry import ErrorHandler, RetryPolicy, with_retry
from .tracing import ProcessorSpan, TracingMixin


class BaseProcessor(ABC, TracingMixin, MetricsMixin, LoggingMixin):
    """Abstract base class for all frame processors with full observability."""

    def __init__(self, name: Optional[str] = None):
        """Initialize the base processor.

        Args:
            name: Optional processor name, defaults to class name
        """
        # Set name first as mixins need it
        self.name = name or self.__class__.__name__

        # Initialize all mixins after name is set
        super().__init__()

        self.logger = logging.getLogger(self.name)
        self.metrics = ProcessorMetrics()
        self.is_initialized = False

        # Resource management
        self.max_concurrent_frames = 10
        self._semaphore = asyncio.Semaphore(self.max_concurrent_frames)
        self._active_tasks = set()

        # Hooks
        self._hooks: Dict[str, List[Callable]] = {
            "preprocess": [],
            "postprocess": [],
            "error": [],
        }

        # Processing pipeline
        self.pipeline = self._build_pipeline()

        # Error handling
        self.retry_policy = RetryPolicy(
            max_attempts=3, base_delay=1.0, retryable_exceptions=(ProcessingError,)
        )
        self.error_handler = ErrorHandler()

    @property
    def active_frames(self) -> int:
        """Get number of currently processing frames."""
        return self.max_concurrent_frames - self._semaphore._value

    async def initialize(self):
        """Initialize the processor."""
        if self.is_initialized:
            return

        try:
            self.logger.info(f"Initializing {self.name}")
            await self._initialize()
            self.is_initialized = True
            self.logger.info(f"{self.name} initialized successfully")
        except Exception as e:
            raise InitializationError(f"Failed to initialize {self.name}: {e}")

    async def cleanup(self):
        """Cleanup processor resources."""
        if not self.is_initialized:
            return

        self.logger.info(f"Cleaning up {self.name}")

        # Wait for active tasks
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        await self._cleanup()
        self.is_initialized = False
        self.logger.info(f"{self.name} cleaned up successfully")

    @timed_method("process_frame")
    async def process(
        self, frame: np.ndarray, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single frame with full pipeline.

        Args:
            frame: Input frame as numpy array
            metadata: Frame metadata

        Returns:
            Processing result dictionary

        Raises:
            RuntimeError: If processor not initialized
            ValidationError: If input validation fails
            ProcessingError: If processing fails
        """
        if not self.is_initialized:
            raise RuntimeError("Processor not initialized")

        # Extract frame ID for correlation
        frame_id = metadata.get("frame_id", f"frame_{time.time()}")

        # Start processing context for logging
        with ProcessingContext(self.name, frame_id=frame_id):  # noqa: SIM117
            # Start span for tracing
            with ProcessorSpan(
                self.tracer, "process_frame", self.name, frame_id
            ):  # noqa: SIM117
                # Start metrics context
                with MetricsContext(self.name, "process_frame"):
                    start_time = time.time()

                    async with self._semaphore:
                        task = asyncio.current_task()
                        self._active_tasks.add(task)

                        try:
                            # Log processing start
                            self.log_with_context(
                                "info",
                                "Starting frame processing",
                                frame_shape=frame.shape,
                                metadata_keys=list(metadata.keys()),
                            )

                            # Create pipeline context
                            context = {
                                "frame": frame,
                                "metadata": metadata,
                                "start_time": start_time,
                            }

                            # Execute pipeline
                            result_context = await self.pipeline.execute(context)

                            # Extract result
                            result = result_context.get("result", {})

                            # Record metrics
                            processing_time = time.time() - start_time
                            await self.metrics.record_frame_processed(processing_time)

                            # Log success
                            self.log_with_context(
                                "info",
                                "Frame processing completed",
                                processing_time=processing_time,
                                result_keys=list(result.keys())
                                if isinstance(result, dict)
                                else None,
                            )

                            return result

                        except Exception as e:
                            await self.metrics.record_error(type(e).__name__)
                            await self._run_hooks("error", e)

                            # Log error
                            self.log_with_context(
                                "error",
                                "Frame processing failed",
                                error=str(e),
                                error_type=type(e).__name__,
                            )

                            raise

                        finally:
                            self._active_tasks.discard(task)
                            self.set_active_frames(len(self._active_tasks))

    def register_hook(self, hook_type: str, callback: Callable):
        """Register a hook callback.

        Args:
            hook_type: Type of hook (preprocess, postprocess, error)
            callback: Async callback function
        """
        if hook_type not in self._hooks:
            raise ValueError(f"Invalid hook type: {hook_type}")

        self._hooks[hook_type].append(callback)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current processor metrics."""
        return self.metrics.get_stats()

    def _validate_input(self, frame: Any, metadata: Any):
        """Validate input frame and metadata."""
        if frame is None:
            raise ValidationError("Invalid frame: frame is None")

        if not isinstance(frame, np.ndarray):
            raise ValidationError("Invalid frame: must be numpy array")

        if len(frame.shape) not in [2, 3]:
            raise ValidationError(f"Invalid frame shape: {frame.shape}")

        if metadata is None:
            raise ValidationError("Metadata is required")

    async def _run_hooks(self, hook_type: str, *args):
        """Run registered hooks."""
        hooks = self._hooks.get(hook_type, [])

        result = args[0] if len(args) == 1 else args

        for hook in hooks:
            if asyncio.iscoroutinefunction(hook):
                result = await hook(result) if len(args) == 1 else await hook(*result)
            else:
                result = hook(result) if len(args) == 1 else hook(*result)

        return result

    @abstractmethod
    async def process_frame(
        self, frame: np.ndarray, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single frame - must be implemented by subclasses.

        Args:
            frame: Input frame as numpy array
            metadata: Frame metadata

        Returns:
            Processing result dictionary
        """
        pass

    async def _initialize(self):
        """Initialize processor resources - can be overridden."""
        pass

    async def _cleanup(self):
        """Cleanup processor resources - can be overridden."""
        pass

    def _build_pipeline(self) -> ProcessingPipeline:
        """Build the default processing pipeline."""
        pipeline = ProcessingPipeline()

        # Default pipeline stages
        pipeline.add_stage("validate", self._validate_stage)
        pipeline.add_stage("preprocess", self._preprocess_stage)
        pipeline.add_stage("process", self._process_stage)
        pipeline.add_stage("postprocess", self._postprocess_stage)

        return pipeline

    async def _validate_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input in pipeline stage."""  # noqa: D401
        frame = context.get("frame")
        metadata = context.get("metadata")
        self._validate_input(frame, metadata)
        return context

    async def _preprocess_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocessing stage - runs hooks."""
        frame = context["frame"]
        metadata = context["metadata"]

        # Run preprocessing hooks
        result = await self._run_hooks("preprocess", frame, metadata)
        if isinstance(result, tuple):
            context["frame"], context["metadata"] = result

        return context

    async def _process_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process frame with retry logic."""  # noqa: D401
        frame = context["frame"]
        metadata = context["metadata"]

        # Wrap processing with retry logic
        @with_retry(self.retry_policy)
        async def process_with_retry():
            return await self.process_frame(frame, metadata)

        try:
            # Call with retry
            result = await process_with_retry()
            context["result"] = result
        except Exception as e:
            # Try error handler
            try:
                result = await self.error_handler.handle_error(e, context)
                context["result"] = result
                context["error_recovered"] = True
            except Exception:
                # Re-raise if no recovery possible
                raise

        return context

    async def _postprocess_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocessing stage - runs hooks."""
        result = context.get("result", {})

        # Run postprocessing hooks
        processed_result = await self._run_hooks("postprocess", result)
        context["result"] = processed_result

        return context
