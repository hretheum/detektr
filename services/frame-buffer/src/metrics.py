"""Prometheus metrics for frame buffer service."""

from prometheus_client import Counter, Gauge, Histogram

# Frame metrics
frames_processed = Counter(
    "frame_buffer_frames_processed_total",
    "Total number of frames processed",
    ["operation"],
)

frames_dropped = Counter(
    "frame_buffer_frames_dropped_total",
    "Total number of frames dropped",
    ["reason"],
)

# Buffer metrics
buffer_size = Gauge(
    "frame_buffer_size",
    "Current number of frames in buffer",
)

buffer_usage_ratio = Gauge(
    "frame_buffer_usage_ratio",
    "Buffer usage as a ratio (0-1)",
)

# Performance metrics
frame_processing_duration = Histogram(
    "frame_buffer_processing_duration_seconds",
    "Time spent processing frames",
    ["operation"],
)

# DLQ metrics
dlq_size = Gauge(
    "frame_buffer_dlq_size",
    "Current number of frames in DLQ",
)

dlq_reprocessed = Counter(
    "frame_buffer_dlq_reprocessed_total",
    "Total number of frames reprocessed from DLQ",
)

# Consumer metrics
frames_consumed_total = Counter(
    "frame_buffer_consumer_frames_consumed_total",
    "Total number of frames consumed from Redis Stream",
)

frames_dropped_total = Counter(
    "frame_buffer_consumer_frames_dropped_total",
    "Total number of frames dropped by consumer",
    ["reason"],
)

consumer_lag_seconds = Gauge(
    "frame_buffer_consumer_lag_seconds",
    "Consumer lag in seconds",
)

consumer_errors_total = Counter(
    "frame_buffer_consumer_errors_total",
    "Total number of consumer errors",
)
