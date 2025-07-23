-- Compression policies (requires TimescaleDB Enterprise license)
-- NOTE: Community edition users should comment out these lines

-- Compression for frame events after 7 days
SELECT add_compression_policy('tracking.frame_events',
    compress_after => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Compression for detections after 7 days
SELECT add_compression_policy('tracking.detections',
    compress_after => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Compression for metrics after 1 day
SELECT add_compression_policy('tracking.service_metrics',
    compress_after => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Compression for frame metadata after 30 days
SELECT add_compression_policy('metadata.frame_metadata',
    compress_after => INTERVAL '30 days',
    if_not_exists => TRUE
);

-- Retention policies
SELECT add_retention_policy('tracking.frame_events',
    drop_after => INTERVAL '30 days',
    if_not_exists => TRUE
);

SELECT add_retention_policy('tracking.detections',
    drop_after => INTERVAL '30 days',
    if_not_exists => TRUE
);

SELECT add_retention_policy('tracking.service_metrics',
    drop_after => INTERVAL '7 days',
    if_not_exists => TRUE
);

SELECT add_retention_policy('metadata.frame_metadata',
    drop_after => INTERVAL '90 days',
    if_not_exists => TRUE
);

-- Refresh policies for continuous aggregates
SELECT add_continuous_aggregate_policy(
    'tracking.metrics_1min',
    start_offset => INTERVAL '5 minutes',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy(
    'metadata.frame_stats_1min',
    start_offset => INTERVAL '5 minutes',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy(
    'metadata.frame_stats_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy(
    'metadata.frame_stats_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);
