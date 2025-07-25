"""Prometheus metrics decorators for automatic instrumentation."""
import asyncio
import functools
import time
from typing import Any, Callable, Dict, Optional

from prometheus_client import Counter, Gauge, Histogram, Summary

# Global metrics registry
PROCESSOR_METRICS = {
    "frames_processed": Counter(
        "processor_frames_processed_total",
        "Total number of frames processed",
        ["processor", "status"],
    ),
    "processing_time": Histogram(
        "processor_processing_time_seconds",
        "Frame processing time in seconds",
        ["processor", "method"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    ),
    "errors": Counter(
        "processor_errors_total",
        "Total number of processing errors",
        ["processor", "error_type"],
    ),
    "active_frames": Gauge(
        "processor_active_frames",
        "Number of frames currently being processed",
        ["processor"],
    ),
    "queue_size": Gauge(
        "processor_queue_size",
        "Current size of processing queue",
        ["processor", "queue_type"],
    ),
    "memory_usage": Gauge(
        "processor_memory_usage_bytes", "Current memory usage in bytes", ["processor"]
    ),
    "method_duration": Summary(
        "processor_method_duration_seconds",
        "Duration of processor methods",
        ["processor", "method"],
    ),
}


class MetricsMixin:
    """Mixin to add automatic Prometheus metrics to processors."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize processor-specific labels
        self._metric_labels = {"processor": self.name}

    def count_frames(self, status: str = "success"):
        """Increment frame counter with status."""
        PROCESSOR_METRICS["frames_processed"].labels(
            processor=self.name, status=status
        ).inc()

    def record_error(self, error_type: str):
        """Record an error occurrence."""
        PROCESSOR_METRICS["errors"].labels(
            processor=self.name, error_type=error_type
        ).inc()

    def set_active_frames(self, count: int):
        """Set current number of active frames."""
        PROCESSOR_METRICS["active_frames"].labels(processor=self.name).set(count)

    def set_queue_size(self, size: int, queue_type: str = "input"):
        """Set current queue size."""
        PROCESSOR_METRICS["queue_size"].labels(
            processor=self.name, queue_type=queue_type
        ).set(size)

    def set_memory_usage(self, bytes_used: int):
        """Set current memory usage."""
        PROCESSOR_METRICS["memory_usage"].labels(processor=self.name).set(bytes_used)


def timed_method(metric_name: Optional[str] = None):
    """Decorator to measure method execution time.

    Args:
        metric_name: Custom metric name, defaults to method name
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            method_name = metric_name or func.__name__

            # Record with histogram
            with PROCESSOR_METRICS["processing_time"].labels(
                processor=self.name, method=method_name
            ).time():
                # Also record with summary
                start_time = time.time()
                try:
                    result = await func(self, *args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    PROCESSOR_METRICS["method_duration"].labels(
                        processor=self.name, method=method_name
                    ).observe(duration)

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            method_name = metric_name or func.__name__

            # Record with histogram
            with PROCESSOR_METRICS["processing_time"].labels(
                processor=self.name, method=method_name
            ).time():
                # Also record with summary
                start_time = time.time()
                try:
                    result = func(self, *args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    PROCESSOR_METRICS["method_duration"].labels(
                        processor=self.name, method=method_name
                    ).observe(duration)

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def counted_method(counter_name: str, labels: Optional[Dict[str, Any]] = None):
    """Decorator to count method invocations.

    Args:
        counter_name: Name of the counter metric
        labels: Additional labels for the metric
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # Increment counter
            counter_labels = {"processor": self.name}
            if labels:
                counter_labels.update(labels)

            PROCESSOR_METRICS.get(
                counter_name, PROCESSOR_METRICS["frames_processed"]
            ).labels(**counter_labels).inc()

            return await func(self, *args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            # Increment counter
            counter_labels = {"processor": self.name}
            if labels:
                counter_labels.update(labels)

            PROCESSOR_METRICS.get(
                counter_name, PROCESSOR_METRICS["frames_processed"]
            ).labels(**counter_labels).inc()

            return func(self, *args, **kwargs)

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def gauge_method(gauge_name: str, value_func: Callable[[Any], float]):
    """Decorator to update gauge based on method result.

    Args:
        gauge_name: Name of the gauge metric
        value_func: Function to extract gauge value from result
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            result = await func(self, *args, **kwargs)

            # Update gauge with extracted value
            value = value_func(result)
            PROCESSOR_METRICS[gauge_name].labels(processor=self.name).set(value)

            return result

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)

            # Update gauge with extracted value
            value = value_func(result)
            PROCESSOR_METRICS[gauge_name].labels(processor=self.name).set(value)

            return result

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def error_counted(error_mapping: Optional[Dict[type, str]] = None):
    """Decorator to count errors by type.

    Args:
        error_mapping: Mapping of exception types to error labels
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                # Determine error type
                error_type = "unknown"
                if error_mapping:
                    for exc_type, label in error_mapping.items():
                        if isinstance(e, exc_type):
                            error_type = label
                            break
                else:
                    error_type = e.__class__.__name__

                # Record error
                PROCESSOR_METRICS["errors"].labels(
                    processor=self.name, error_type=error_type
                ).inc()

                raise

        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                # Determine error type
                error_type = "unknown"
                if error_mapping:
                    for exc_type, label in error_mapping.items():
                        if isinstance(e, exc_type):
                            error_type = label
                            break
                else:
                    error_type = e.__class__.__name__

                # Record error
                PROCESSOR_METRICS["errors"].labels(
                    processor=self.name, error_type=error_type
                ).inc()

                raise

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class MetricsContext:
    """Context manager for tracking metrics during processing."""

    def __init__(self, processor_name: str, operation: str):
        self.processor_name = processor_name
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        """Enter metrics context."""
        self.start_time = time.time()

        # Increment active operations
        PROCESSOR_METRICS["active_frames"].labels(processor=self.processor_name).inc()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit metrics context."""
        # Decrement active operations
        PROCESSOR_METRICS["active_frames"].labels(processor=self.processor_name).dec()

        # Record duration
        if self.start_time:
            duration = time.time() - self.start_time
            PROCESSOR_METRICS["processing_time"].labels(
                processor=self.processor_name, method=self.operation
            ).observe(duration)

        # Record success/failure
        if exc_type is None:
            PROCESSOR_METRICS["frames_processed"].labels(
                processor=self.processor_name, status="success"
            ).inc()
        else:
            PROCESSOR_METRICS["frames_processed"].labels(
                processor=self.processor_name, status="error"
            ).inc()

            # Record error type
            error_type = exc_type.__name__ if exc_type else "unknown"
            PROCESSOR_METRICS["errors"].labels(
                processor=self.processor_name, error_type=error_type
            ).inc()
