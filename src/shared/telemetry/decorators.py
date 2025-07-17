"""OpenTelemetry decorators for custom instrumentation.

Provides easy-to-use decorators for adding tracing to functions.
"""

import functools
import inspect
from typing import Any, Callable, Optional, TypeVar, Union

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

F = TypeVar("F", bound=Callable[..., Any])


def traced(
    _func: Optional[F] = None,
    *,
    span_name: Optional[str] = None,
    attributes: Optional[dict[str, Any]] = None,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
) -> Union[Callable[[F], F], F]:
    """Decorator to automatically create spans for functions.

    Args:
        span_name: Custom span name (defaults to function name)
        attributes: Additional attributes to add to span
        record_exception: Whether to record exceptions as events
        set_status_on_exception: Whether to set span status to ERROR on exception

    Example:
        @traced
        def process_frame(frame_id: str):
            # This creates a span named "process_frame"
            # with attribute "frame_id" = frame_id
            pass

        @traced(span_name="custom_processing", attributes={"version": "1.0"})
        def process():
            # This creates a span named "custom_processing"
            # with attribute "version" = "1.0"
            pass
    """

    def decorator(func: F) -> F:
        # Check if function is async first
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = trace.get_tracer(__name__)
                name = span_name or func.__name__

                with tracer.start_as_current_span(name) as span:
                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                    # Add function arguments as attributes
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    for param_name, param_value in bound_args.arguments.items():
                        # Skip self/cls and complex objects
                        if param_name in ("self", "cls"):
                            continue
                        if isinstance(param_value, (str, int, float, bool)):
                            span.set_attribute(f"arg.{param_name}", param_value)

                    try:
                        result = await func(*args, **kwargs)
                        return result
                    except Exception as e:
                        if record_exception:
                            span.record_exception(e)
                        if set_status_on_exception:
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return async_wrapper  # type: ignore
        else:
            # For sync functions
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = trace.get_tracer(__name__)
                name = span_name or func.__name__

                with tracer.start_as_current_span(name) as span:
                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                    # Add function arguments as attributes
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    for param_name, param_value in bound_args.arguments.items():
                        # Skip self/cls and complex objects
                        if param_name in ("self", "cls"):
                            continue
                        if isinstance(param_value, (str, int, float, bool)):
                            span.set_attribute(f"arg.{param_name}", param_value)

                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        if record_exception:
                            span.record_exception(e)
                        if set_status_on_exception:
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return sync_wrapper  # type: ignore

    # Handle both @traced and @traced(...) patterns
    if _func is None:
        # Called as @traced(...) - return decorator
        return decorator
    else:
        # Called as @traced - apply decorator directly
        return decorator(_func)


def traced_method(
    span_name: Optional[str] = None,
    attributes: Optional[dict[str, Any]] = None,
    include_self_attrs: Optional[list[str]] = None,
) -> Callable[[F], F]:
    """Decorator for class methods that includes instance attributes.

    Args:
        span_name: Custom span name (defaults to method name)
        attributes: Additional attributes to add to span
        include_self_attrs: List of instance attributes to include

    Example:
        class FrameProcessor:
            def __init__(self, processor_id: str):
                self.processor_id = processor_id

            @traced_method(include_self_attrs=["processor_id"])
            def process(self, frame_id: str):
                # Creates span with attributes:
                # - "self.processor_id" = self.processor_id
                # - "arg.frame_id" = frame_id
                pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Get attributes from self
            extra_attrs = attributes.copy() if attributes else {}

            if include_self_attrs:
                for attr_name in include_self_attrs:
                    if hasattr(self, attr_name):
                        value = getattr(self, attr_name)
                        if isinstance(value, (str, int, float, bool)):
                            extra_attrs[f"self.{attr_name}"] = value

            # Create the traced function with merged attributes
            traced_func = traced(span_name=span_name, attributes=extra_attrs)(func)
            return traced_func(self, *args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def traced_frame(frame_id_key: str = "frame_id") -> Callable[[F], F]:
    """Decorator for frame processing functions that ensures frame ID propagation.

    This decorator automatically:
    1. Sets frame.id attribute on the span
    2. Propagates frame_id through context
    3. Creates child spans for the frame processing pipeline

    Args:
        frame_id_key: The name of the argument/attribute containing the frame ID

    Example:
        @traced_frame("frame_id")
        def process_frame(frame_id: str, data: bytes):
            # This creates a span with "frame.id" = frame_id
            # All child spans will inherit this frame context
            pass

        @traced_frame("id")  # Different parameter name
        def analyze_frame(id: str, features: dict):
            # This creates a span with "frame.id" = id
            pass
    """

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = trace.get_tracer(__name__)

                # Extract frame ID from arguments
                frame_id = _extract_frame_id(func, frame_id_key, args, kwargs)
                span_name = f"frame.{func.__name__}"

                with tracer.start_as_current_span(span_name) as span:
                    # Always set frame.id attribute
                    if frame_id:
                        span.set_attribute("frame.id", frame_id)
                        span.set_attribute("frame.stage", func.__name__)

                    # Add function arguments as attributes
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    for param_name, param_value in bound_args.arguments.items():
                        if param_name in ("self", "cls"):
                            continue
                        if isinstance(param_value, (str, int, float, bool)):
                            span.set_attribute(f"arg.{param_name}", param_value)

                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(trace.Status(trace.StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        raise

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = trace.get_tracer(__name__)

                # Extract frame ID from arguments
                frame_id = _extract_frame_id(func, frame_id_key, args, kwargs)
                span_name = f"frame.{func.__name__}"

                with tracer.start_as_current_span(span_name) as span:
                    # Always set frame.id attribute
                    if frame_id:
                        span.set_attribute("frame.id", frame_id)
                        span.set_attribute("frame.stage", func.__name__)

                    # Add function arguments as attributes
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    for param_name, param_value in bound_args.arguments.items():
                        if param_name in ("self", "cls"):
                            continue
                        if isinstance(param_value, (str, int, float, bool)):
                            span.set_attribute(f"arg.{param_name}", param_value)

                    try:
                        result = func(*args, **kwargs)
                        span.set_status(trace.Status(trace.StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        raise

            return sync_wrapper  # type: ignore

    return decorator


def _extract_frame_id(
    func: Callable, frame_id_key: str, args: tuple, kwargs: dict
) -> Optional[str]:
    """Extract frame ID from function arguments."""
    try:
        # Try to get from kwargs first
        if frame_id_key in kwargs:
            return str(kwargs[frame_id_key])

        # Try to get from positional args
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        if frame_id_key in bound_args.arguments:
            value = bound_args.arguments[frame_id_key]
            return str(value) if value is not None else None

        return None
    except Exception:
        return None
