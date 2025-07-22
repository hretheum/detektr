"""
Queue metrics export for Prometheus.

Exports:
- Queue depth (current size)
- Throughput (frames/second)
- Latency (processing time)
- Backpressure events
- Circuit breaker state
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

from prometheus_client import Counter, Gauge, Histogram, Info

from shared.queue.backpressure import BackpressureHandler, CircuitBreakerState

# Prometheus metrics
queue_depth = Gauge(
    "frame_queue_depth", "Current number of frames in queue", ["queue_name"]
)

queue_throughput = Counter(
    "frame_queue_throughput_total",
    "Total frames processed through queue",
    ["queue_name", "operation"],
)

queue_latency = Histogram(
    "frame_queue_latency_seconds",
    "Time spent in queue operations",
    ["queue_name", "operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

backpressure_events = Counter(
    "frame_queue_backpressure_events_total",
    "Number of backpressure events",
    ["queue_name", "event_type"],
)

circuit_breaker_state = Gauge(
    "frame_queue_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["queue_name"],
)

dropped_frames = Counter(
    "frame_queue_dropped_frames_total",
    "Number of dropped frames",
    ["queue_name", "reason"],
)

queue_info = Info("frame_queue", "Queue configuration information")


@dataclass
class QueueMetricsCollector:
    """
    Collects and exports queue metrics to Prometheus.

    Integrates with BackpressureHandler to provide real-time metrics.
    """

    queue_name: str
    handler: BackpressureHandler

    def __post_init__(self) -> None:
        """Initialize queue info."""
        queue_info.info(
            {
                "queue_name": self.queue_name,
                "min_buffer_size": str(self.handler.config.min_buffer_size),
                "max_buffer_size": str(self.handler.config.max_buffer_size),
                "high_watermark": str(self.handler.config.high_watermark),
                "low_watermark": str(self.handler.config.low_watermark),
            }
        )

    def update_metrics(self) -> None:
        """Update all metrics from handler state."""
        metrics = self.handler.get_metrics()

        # Queue depth
        queue_depth.labels(queue_name=self.queue_name).set(metrics.current_buffer_size)

        # Throughput counters (these are incremental)
        queue_throughput.labels(
            queue_name=self.queue_name, operation="sent"
        )._value._value = metrics.frames_sent

        queue_throughput.labels(
            queue_name=self.queue_name, operation="received"
        )._value._value = metrics.frames_received

        # Dropped frames
        if metrics.frames_dropped > 0:
            dropped_frames.labels(
                queue_name=self.queue_name, reason="backpressure"
            )._value._value = metrics.frames_dropped

        # Backpressure events
        backpressure_events.labels(
            queue_name=self.queue_name, event_type="activation"
        )._value._value = metrics.backpressure_activations

        # Circuit breaker state
        cb_state = self.handler.circuit_breaker.state
        state_value = {
            CircuitBreakerState.CLOSED: 0,
            CircuitBreakerState.OPEN: 1,
            CircuitBreakerState.HALF_OPEN: 2,
        }[cb_state]
        circuit_breaker_state.labels(queue_name=self.queue_name).set(state_value)

        # Average latency (if we have wait time data)
        if metrics.frames_sent > 0 and metrics.total_wait_time_ms > 0:
            avg_wait_seconds = (metrics.total_wait_time_ms / metrics.frames_sent) / 1000
            queue_latency.labels(queue_name=self.queue_name, operation="wait").observe(
                avg_wait_seconds
            )

    def record_send_latency(self, duration_seconds: float) -> None:
        """Record latency for send operation."""
        queue_latency.labels(queue_name=self.queue_name, operation="send").observe(
            duration_seconds
        )

    def record_receive_latency(self, duration_seconds: float) -> None:
        """Record latency for receive operation."""
        queue_latency.labels(queue_name=self.queue_name, operation="receive").observe(
            duration_seconds
        )

    def increment_throughput_sent(self) -> None:
        """Increment sent frames counter."""
        queue_throughput.labels(queue_name=self.queue_name, operation="sent").inc()

    def increment_throughput_received(self) -> None:
        """Increment received frames counter."""
        queue_throughput.labels(queue_name=self.queue_name, operation="received").inc()

    def record_backpressure_event(self, event_type: str) -> None:
        """Record backpressure event."""
        backpressure_events.labels(
            queue_name=self.queue_name, event_type=event_type
        ).inc()

    def record_dropped_frame(self, reason: str = "unknown") -> None:
        """Record dropped frame."""
        dropped_frames.labels(queue_name=self.queue_name, reason=reason).inc()

    def get_current_metrics(self) -> Dict[str, float]:
        """Get current metric values as dictionary."""
        self.update_metrics()

        return {
            "queue_depth": queue_depth.labels(queue_name=self.queue_name)._value.get(),
            "throughput_sent": queue_throughput.labels(
                queue_name=self.queue_name, operation="sent"
            )._value.get(),
            "throughput_received": queue_throughput.labels(
                queue_name=self.queue_name, operation="received"
            )._value.get(),
            "dropped_frames": dropped_frames.labels(
                queue_name=self.queue_name, reason="backpressure"
            )._value.get(),
            "backpressure_activations": backpressure_events.labels(
                queue_name=self.queue_name, event_type="activation"
            )._value.get(),
            "circuit_breaker_state": circuit_breaker_state.labels(
                queue_name=self.queue_name
            )._value.get(),
            "adaptive_buffer_size": self.handler.adaptive_buffer.current_size,
        }


class MetricsEnabledBackpressureHandler(BackpressureHandler):
    """
    BackpressureHandler with integrated metrics collection.

    Automatically records metrics for all queue operations.
    """

    def __init__(self, *args: Any, queue_name: str = "default", **kwargs: Any) -> None:
        """Initialize with metrics collector."""
        super().__init__(*args, **kwargs)
        self.metrics_collector = QueueMetricsCollector(
            queue_name=queue_name, handler=self
        )
        self._last_metrics_update = datetime.now()

    async def send(self, *args: Any, **kwargs: Any) -> bool:
        """Send with metrics recording."""
        start_time = datetime.now()
        result = await super().send(*args, **kwargs)
        duration = (datetime.now() - start_time).total_seconds()

        self.metrics_collector.record_send_latency(duration)
        if result:
            self.metrics_collector.increment_throughput_sent()
        else:
            self.metrics_collector.record_dropped_frame("send_failed")

        self._update_metrics_if_needed()
        return result

    async def receive(self, *args: Any, **kwargs: Any) -> Any:
        """Receive with metrics recording."""
        start_time = datetime.now()
        result = await super().receive(*args, **kwargs)
        duration = (datetime.now() - start_time).total_seconds()

        if result is not None:
            self.metrics_collector.record_receive_latency(duration)
            self.metrics_collector.increment_throughput_received()

        self._update_metrics_if_needed()
        return result

    def _update_metrics_if_needed(self) -> None:
        """Update metrics periodically."""
        now = datetime.now()
        if (now - self._last_metrics_update).total_seconds() > 1.0:
            self.metrics_collector.update_metrics()
            self._last_metrics_update = now
