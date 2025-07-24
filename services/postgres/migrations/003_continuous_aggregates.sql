-- Migration: 003_continuous_aggregates.sql
-- Description: Create continuous aggregates for performance optimization

-- Hourly frame statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS detektor.frame_stats_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS hour,
    camera_id,
    COUNT(*) AS frame_count,
    AVG(frame_size)::INTEGER AS avg_frame_size,
    AVG(fps)::NUMERIC(5,2) AS avg_fps,
    MIN(timestamp) AS first_frame_time,
    MAX(timestamp) AS last_frame_time
FROM detektor.frame_metadata
GROUP BY hour, camera_id
WITH NO DATA;

-- Add refresh policy for hourly stats
SELECT add_continuous_aggregate_policy(
    'detektor.frame_stats_hourly',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Daily detection statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS detektor.detection_stats_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day,
    detection_type,
    COUNT(*) AS detection_count,
    AVG(confidence)::NUMERIC(4,3) AS avg_confidence,
    MIN(confidence)::NUMERIC(4,3) AS min_confidence,
    MAX(confidence)::NUMERIC(4,3) AS max_confidence,
    AVG(processing_time_ms)::INTEGER AS avg_processing_time_ms
FROM detektor.detection_events
GROUP BY day, detection_type
WITH NO DATA;

-- Add refresh policy for daily stats
SELECT add_continuous_aggregate_policy(
    'detektor.detection_stats_daily',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Service performance metrics (5-minute buckets)
CREATE MATERIALIZED VIEW IF NOT EXISTS detektor.service_performance_5min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', timestamp) AS bucket,
    service_name,
    operation,
    COUNT(*) AS request_count,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) AS success_count,
    AVG(duration_ms)::INTEGER AS avg_duration_ms,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms)::INTEGER AS p50_duration_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms)::INTEGER AS p95_duration_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms)::INTEGER AS p99_duration_ms
FROM detektor.processing_metrics
GROUP BY bucket, service_name, operation
WITH NO DATA;

-- Add refresh policy for 5-minute metrics
SELECT add_continuous_aggregate_policy(
    'detektor.service_performance_5min',
    start_offset => INTERVAL '10 minutes',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);

-- Function to manually refresh all aggregates
CREATE OR REPLACE FUNCTION detektor.refresh_all_aggregates()
RETURNS void AS $$
BEGIN
    CALL refresh_continuous_aggregate('detektor.frame_stats_hourly', NULL, NULL);
    CALL refresh_continuous_aggregate('detektor.detection_stats_daily', NULL, NULL);
    CALL refresh_continuous_aggregate('detektor.service_performance_5min', NULL, NULL);
END;
$$ LANGUAGE plpgsql;
