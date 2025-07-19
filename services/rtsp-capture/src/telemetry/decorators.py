"""Simple decorators for telemetry."""
import asyncio
import functools
import logging

logger = logging.getLogger(__name__)


def traced_method(span_name: str = None, include_self_attrs: list = None):
    """Decorate functions with simple tracing."""

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            operation = span_name or func.__name__
            logger.debug(f"Starting {operation}")
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"Completed {operation}")
                return result
            except Exception as e:
                logger.error(f"Error in {operation}: {e}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            operation = span_name or func.__name__
            logger.debug(f"Starting {operation}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Completed {operation}")
                return result
            except Exception as e:
                logger.error(f"Error in {operation}: {e}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
