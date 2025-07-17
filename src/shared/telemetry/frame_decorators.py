"""Decorators for automatic frame operation tracing."""

import functools
from typing import Any, Callable, Optional, TypeVar, cast

from opentelemetry import trace

from ..kernel.domain import Frame
from .decorators import traced
from .frame_tracking import FrameTracer, with_frame_context

# Type variable for decorators
F = TypeVar("F", bound=Callable[..., Any])

# Get default tracer
_tracer = trace.get_tracer(__name__)
_frame_tracer = FrameTracer(_tracer)


def traced_frame_operation(
    span_name: Optional[str] = None,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
    attributes: Optional[dict[str, Any]] = None,
) -> Callable[[F], F]:
    """Trace frame operations with automatic context extraction.

    Automatically extracts frame from function arguments and adds to trace context.

    Args:
        span_name: Optional span name (defaults to function name)
        record_exception: Whether to record exceptions
        set_status_on_exception: Whether to set span status on exception
        attributes: Additional span attributes

    Returns:
        Decorated function with frame tracing
    """

    def decorator(func: F) -> F:
        # Combine with existing traced decorator and frame context
        traced_func: F = traced(
            span_name=span_name,
            record_exception=record_exception,
            set_status_on_exception=set_status_on_exception,
            attributes=attributes,
        )(func)

        # Add frame context propagation
        return with_frame_context()(traced_func)

    return decorator


def traced_processing_stage(
    stage_name: Optional[str] = None, auto_complete: bool = True
) -> Callable[[F], F]:
    """Trace frame processing stages with automatic lifecycle management.

    Automatically creates ProcessingStage on Frame and manages lifecycle.

    Args:
        stage_name: Name of processing stage (defaults to function name)
        auto_complete: Whether to auto-complete stage on success

    Returns:
        Decorated function with stage tracking
    """

    def decorator(func: F) -> F:
        actual_stage_name = stage_name or func.__name__

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find frame in arguments
            frame = None
            for arg in args:
                if isinstance(arg, Frame):
                    frame = arg
                    break

            if frame is None:
                for key in ["frame", "self"]:
                    if key in kwargs:
                        val = kwargs[key]
                        if isinstance(val, Frame):
                            frame = val
                            break
                        # Check if self has frame attribute
                        elif hasattr(val, "frame") and isinstance(val.frame, Frame):
                            frame = val.frame
                            break

            if frame is None:
                # No frame found, just execute normally
                return func(*args, **kwargs)

            # Start processing stage
            stage = frame.start_processing_stage(actual_stage_name)

            # Create span for this stage
            with _frame_tracer.start_as_current_frame_span(
                f"stage.{actual_stage_name}",
                frame=frame,
                attributes={
                    "stage.name": actual_stage_name,
                    "stage.index": len(frame.processing_stages) - 1,
                },
            ) as span:
                try:
                    result = func(*args, **kwargs)

                    if auto_complete:
                        # Extract metadata from result if dict-like
                        metadata = {}
                        if isinstance(result, dict):
                            metadata = result
                        elif hasattr(result, "__dict__"):
                            metadata = {"result_type": type(result).__name__}

                        stage.complete(metadata)
                        span.set_attribute("stage.status", "completed")

                    return result

                except Exception as e:
                    # Mark stage as failed
                    stage.fail(str(e))
                    span.set_attribute("stage.status", "failed")
                    span.set_attribute("stage.error", str(e))
                    raise

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Same logic but async
            frame = None
            for arg in args:
                if isinstance(arg, Frame):
                    frame = arg
                    break

            if frame is None:
                for key in ["frame", "self"]:
                    if key in kwargs:
                        val = kwargs[key]
                        if isinstance(val, Frame):
                            frame = val
                            break
                        elif hasattr(val, "frame") and isinstance(val.frame, Frame):
                            frame = val.frame
                            break

            if frame is None:
                return await func(*args, **kwargs)

            stage = frame.start_processing_stage(actual_stage_name)

            with _frame_tracer.start_as_current_frame_span(
                f"stage.{actual_stage_name}",
                frame=frame,
                attributes={
                    "stage.name": actual_stage_name,
                    "stage.index": len(frame.processing_stages) - 1,
                },
            ) as span:
                try:
                    result = await func(*args, **kwargs)

                    if auto_complete:
                        metadata = {}
                        if isinstance(result, dict):
                            metadata = result
                        elif hasattr(result, "__dict__"):
                            metadata = {"result_type": type(result).__name__}

                        stage.complete(metadata)
                        span.set_attribute("stage.status", "completed")

                    return result

                except Exception as e:
                    stage.fail(str(e))
                    span.set_attribute("stage.status", "failed")
                    span.set_attribute("stage.error", str(e))
                    raise

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator


class FrameProcessor:
    """Base class for frame processors with automatic tracing."""

    def __init__(self, service_name: str):
        """Initialize frame processor.

        Args:
            service_name: Name of the processing service
        """
        self.service_name = service_name
        self.tracer = trace.get_tracer(service_name)
        self.frame_tracer = FrameTracer(self.tracer)

    @traced_frame_operation()
    def process_frame(self, frame: Frame) -> Any:
        """Process a frame - to be overridden by subclasses.

        Args:
            frame: Frame to process

        Returns:
            Processing result
        """
        raise NotImplementedError("Subclasses must implement process_frame")

    def create_frame_span(self, name: str, frame: Frame) -> Any:
        """Create a span for frame processing.

        Args:
            name: Span name
            frame: Frame being processed

        Returns:
            Span context manager
        """
        return self.frame_tracer.start_as_current_frame_span(
            name,
            frame=frame,
            attributes={
                "processor.service": self.service_name,
                "processor.operation": name,
            },
        )
