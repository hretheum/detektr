"""Structured logging with correlation context."""
import asyncio
import contextvars
import functools
import logging
import uuid
from typing import Any, Dict, Optional

import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level
from structlog.stdlib import BoundLogger, LoggerFactory

# Context variables for correlation
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)
frame_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "frame_id", default=""
)
processor_name_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "processor_name", default=""
)


def add_correlation_info(logger, method_name, event_dict):
    """Add correlation IDs to log entries."""
    # Add correlation ID
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    # Add frame ID
    frame_id = frame_id_var.get()
    if frame_id:
        event_dict["frame_id"] = frame_id

    # Add processor name
    processor_name = processor_name_var.get()
    if processor_name:
        event_dict["processor_name"] = processor_name

    return event_dict


def setup_structured_logging(
    log_level: str = "INFO",
    json_logs: bool = True,
    additional_processors: Optional[list] = None,
) -> None:
    """Configure structured logging for processors.

    Args:
        log_level: Logging level
        json_logs: Whether to output JSON format
        additional_processors: Additional structlog processors
    """
    # Configure structlog processors
    processors = [
        TimeStamper(fmt="iso"),
        add_log_level,
        add_correlation_info,
    ]

    if additional_processors:
        processors.extend(additional_processors)

    if json_logs:
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
    )


class LoggingMixin:
    """Mixin to add structured logging to processors."""

    def __init__(self, *args, **kwargs):
        """Initialize logging mixin."""  # noqa: D107
        super().__init__(*args, **kwargs)
        self.logger = structlog.get_logger(self.__class__.__name__)
        # Bind processor name permanently
        self.logger = self.logger.bind(processor=self.name)

    def log_with_context(self, level: str, message: str, **kwargs):
        """Log with current context variables.

        Args:
            level: Log level (info, warning, error, etc.)
            message: Log message
            **kwargs: Additional fields to log
        """
        # Get logger method
        log_method = getattr(self.logger, level)

        # Add context
        context = {
            "correlation_id": correlation_id_var.get(),
            "frame_id": frame_id_var.get(),
            **kwargs,
        }

        # Remove empty values
        context = {k: v for k, v in context.items() if v}

        # Log the message
        log_method(message, **context)

    def create_child_logger(self, **bindings) -> BoundLogger:
        """Create a child logger with additional bindings.

        Args:
            **bindings: Additional fields to bind

        Returns:
            Child logger with bindings
        """
        return self.logger.bind(**bindings)


class ProcessingContext:
    """Context manager for processing correlation."""

    def __init__(
        self,
        processor_name: str,
        frame_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        """Initialize processing context."""  # noqa: D107
        self.processor_name = processor_name
        self.frame_id = frame_id or str(uuid.uuid4())
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.tokens = []

    def __enter__(self):
        """Enter processing context."""
        # Set context variables
        self.tokens.append(processor_name_var.set(self.processor_name))
        self.tokens.append(frame_id_var.set(self.frame_id))
        self.tokens.append(correlation_id_var.set(self.correlation_id))

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit processing context."""
        # Reset context variables in reverse order
        if self.tokens:
            correlation_id_var.reset(self.tokens[-1])
            frame_id_var.reset(self.tokens[-2])
            processor_name_var.reset(self.tokens[-3])


def log_method_call(level: str = "info", include_args: bool = False):
    """Log method calls with optional arguments.

    Args:
        level: Log level
        include_args: Whether to include method arguments in logs
    """  # noqa: D401

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # Build log context
            context = {
                "method": func.__name__,
                "processor": getattr(self, "name", "unknown"),
            }

            if include_args:
                context["args"] = str(args)
                context["kwargs"] = str(kwargs)

            # Log method entry
            self.log_with_context(level, f"Calling {func.__name__}", **context)

            try:
                result = await func(self, *args, **kwargs)

                # Log method success
                self.log_with_context(
                    level, f"Completed {func.__name__}", **context, status="success"
                )

                return result

            except Exception as e:
                # Log method failure
                self.log_with_context(
                    "error",
                    f"Failed {func.__name__}",
                    **context,
                    status="error",
                    error=str(e),
                    error_type=e.__class__.__name__,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            # Build log context
            context = {
                "method": func.__name__,
                "processor": getattr(self, "name", "unknown"),
            }

            if include_args:
                context["args"] = str(args)
                context["kwargs"] = str(kwargs)

            # Log method entry
            self.log_with_context(level, f"Calling {func.__name__}", **context)

            try:
                result = func(self, *args, **kwargs)

                # Log method success
                self.log_with_context(
                    level, f"Completed {func.__name__}", **context, status="success"
                )

                return result

            except Exception as e:
                # Log method failure
                self.log_with_context(
                    "error",
                    f"Failed {func.__name__}",
                    **context,
                    status="error",
                    error=str(e),
                    error_type=e.__class__.__name__,
                )
                raise

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def extract_correlation_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    """Extract correlation ID from metadata.

    Args:
        metadata: Frame metadata

    Returns:
        Correlation ID if found
    """
    # Check common correlation ID fields
    for field in ["correlation_id", "correlationId", "x-correlation-id"]:
        if field in metadata:
            return str(metadata[field])

    # Check trace context
    if "traceparent" in metadata:
        # Extract trace ID from traceparent
        parts = metadata["traceparent"].split("-")
        if len(parts) >= 2:
            return parts[1]

    return None


def inject_correlation_to_metadata(
    metadata: Dict[str, Any], correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Inject correlation ID into metadata.

    Args:
        metadata: Frame metadata
        correlation_id: Correlation ID to inject

    Returns:
        Updated metadata
    """
    if not correlation_id:
        correlation_id = correlation_id_var.get()

    if correlation_id:
        metadata["correlation_id"] = correlation_id

    return metadata


class LogBuffer:
    """Buffer for collecting logs during processing."""

    def __init__(self, max_size: int = 1000):
        """Initialize log buffer."""  # noqa: D107
        self.max_size = max_size
        self.logs = []

    def add(self, level: str, message: str, **kwargs):
        """Add a log entry to buffer."""
        entry = {
            "level": level,
            "message": message,
            "timestamp": TimeStamper(fmt="iso").timestamp(),
            **kwargs,
        }

        self.logs.append(entry)

        # Trim if too large
        if len(self.logs) > self.max_size:
            self.logs = self.logs[-self.max_size :]

    def get_logs(self) -> list:
        """Get all buffered logs."""
        return self.logs.copy()

    def clear(self):
        """Clear the buffer."""
        self.logs.clear()

    def flush_to_logger(self, logger: BoundLogger):
        """Flush all logs to a logger."""
        for entry in self.logs:
            level = entry.pop("level", "info")
            message = entry.pop("message", "")
            getattr(logger, level)(message, **entry)

        self.clear()
