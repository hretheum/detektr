"""Frame tracking integration with OpenTelemetry."""

import functools
from typing import Any, Callable, Optional, TypeVar, Union, cast

from opentelemetry import baggage, trace
from opentelemetry.trace import Span

from ..kernel.domain import Frame, FrameId

# Type variables for decorators
F = TypeVar("F", bound=Callable[..., Any])

# Constants for baggage keys
FRAME_ID_KEY = "frame.id"
CAMERA_ID_KEY = "frame.camera_id"
PROCESSING_STAGE_KEY = "frame.processing_stage"


def set_frame_context(frame: Union[Frame, str]) -> None:
    """Set frame information in OpenTelemetry baggage.

    Args:
        frame: Frame object or frame ID string
    """
    if isinstance(frame, Frame):
        baggage.set_baggage(FRAME_ID_KEY, str(frame.id))
        baggage.set_baggage(CAMERA_ID_KEY, frame.camera_id)

        # Add current processing stage if any
        current_stage = frame.get_current_stage()
        if current_stage:
            baggage.set_baggage(PROCESSING_STAGE_KEY, current_stage.name)
    else:
        # Just frame ID string
        baggage.set_baggage(FRAME_ID_KEY, str(frame))


def get_frame_id() -> Optional[str]:
    """Get frame ID from current context."""
    return cast(Optional[str], baggage.get_baggage(FRAME_ID_KEY))


def get_camera_id() -> Optional[str]:
    """Get camera ID from current context."""
    return cast(Optional[str], baggage.get_baggage(CAMERA_ID_KEY))


def clear_frame_context() -> None:
    """Clear frame information from baggage."""
    baggage.remove_baggage(FRAME_ID_KEY)
    baggage.remove_baggage(CAMERA_ID_KEY)
    baggage.remove_baggage(PROCESSING_STAGE_KEY)


def add_frame_attributes(span: Optional[Span] = None) -> None:
    """Add frame attributes to current or provided span.

    Args:
        span: Optional span to add attributes to. If None, uses current span.
    """
    if span is None:
        span = trace.get_current_span()

    if not span or not span.is_recording():
        return

    # Add frame attributes from baggage
    frame_id = get_frame_id()
    if frame_id:
        span.set_attribute("frame.id", frame_id)

    camera_id = get_camera_id()
    if camera_id:
        span.set_attribute("frame.camera_id", camera_id)

    stage = cast(Optional[str], baggage.get_baggage(PROCESSING_STAGE_KEY))
    if stage:
        span.set_attribute("frame.processing_stage", stage)


def with_frame_context(frame: Union[Frame, str, None] = None) -> Callable[[F], F]:
    """Propagate frame context automatically in decorated functions.

    Args:
        frame: Frame object, frame ID string, or None to use from arguments

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Try to find frame in arguments if not provided
            frame_arg = frame
            if frame_arg is None:
                # Look for frame in args
                for arg in args:
                    if isinstance(arg, Frame):
                        frame_arg = arg
                        break
                    elif isinstance(arg, FrameId):
                        frame_arg = str(arg)
                        break

                # Look in kwargs
                if frame_arg is None:
                    for key in ["frame", "frame_id"]:
                        if key in kwargs:
                            val = kwargs[key]
                            if isinstance(val, Frame):
                                frame_arg = val
                                break
                            elif isinstance(val, (str, FrameId)):
                                frame_arg = str(val)
                                break

            # Set context before function
            if frame_arg:
                set_frame_context(frame_arg)

            try:
                # Add attributes to current span
                add_frame_attributes()
                return func(*args, **kwargs)
            finally:
                # Clear context after function
                if frame_arg:
                    clear_frame_context()

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Same logic as sync_wrapper but async
            frame_arg = frame
            if frame_arg is None:
                for arg in args:
                    if isinstance(arg, Frame):
                        frame_arg = arg
                        break
                    elif isinstance(arg, FrameId):
                        frame_arg = str(arg)
                        break

                if frame_arg is None:
                    for key in ["frame", "frame_id"]:
                        if key in kwargs:
                            val = kwargs[key]
                            if isinstance(val, Frame):
                                frame_arg = val
                                break
                            elif isinstance(val, (str, FrameId)):
                                frame_arg = str(val)
                                break

            if frame_arg:
                set_frame_context(frame_arg)

            try:
                add_frame_attributes()
                return await func(*args, **kwargs)
            finally:
                if frame_arg:
                    clear_frame_context()

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator


class FrameTracer:
    """Helper class for frame-aware tracing."""

    def __init__(self, tracer: trace.Tracer):
        """Initialize frame tracer.

        Args:
            tracer: OpenTelemetry tracer instance
        """
        self.tracer = tracer

    def start_frame_span(
        self, name: str, frame: Union[Frame, str, None] = None, **kwargs: Any
    ) -> Span:
        """Start a new span with frame context.

        Args:
            name: Span name
            frame: Frame object or ID to set in context
            **kwargs: Additional span arguments

        Returns:
            Started span with frame attributes
        """
        span = self.tracer.start_span(name, **kwargs)

        # Set frame context if provided
        if frame:
            set_frame_context(frame)

        # Add frame attributes to span
        add_frame_attributes(span)

        return span

    def start_as_current_frame_span(
        self, name: str, frame: Union[Frame, str, None] = None, **kwargs: Any
    ) -> Any:
        """Start a new span as current with frame context.

        Args:
            name: Span name
            frame: Frame object or ID to set in context
            **kwargs: Additional span arguments

        Returns:
            Context manager for the span
        """

        # Create context manager that sets frame context
        class FrameSpanContext:
            def __init__(self, span_cm: Any, frame_to_set: Union[Frame, str, None]):
                self.span_cm = span_cm
                self.frame_to_set = frame_to_set
                self.frame_was_set = False

            def __enter__(self) -> Span:
                if self.frame_to_set:
                    set_frame_context(self.frame_to_set)
                    self.frame_was_set = True

                span = self.span_cm.__enter__()
                add_frame_attributes(span)
                return span

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                try:
                    self.span_cm.__exit__(exc_type, exc_val, exc_tb)
                finally:
                    if self.frame_was_set:
                        clear_frame_context()

        span_cm = self.tracer.start_as_current_span(name, **kwargs)
        return FrameSpanContext(span_cm, frame)
