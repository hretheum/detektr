-- Metadata Storage Schema for Frame Metadata
-- Designed for 1M records/day with TimescaleDB optimization

-- Create metadata schema
CREATE SCHEMA IF NOT EXISTS metadata;

-- Main hypertable for frame metadata
CREATE TABLE IF NOT EXISTS metadata.frame_metadata (
    frame_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    camera_id TEXT NOT NULL,
    sequence_number BIGINT NOT NULL,
    metadata JSONB NOT NULL,
    PRIMARY KEY (frame_id, timestamp)
);

-- Convert to hypertable with 1-day chunks
SELECT create_hypertable(
    'metadata.frame_metadata',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_metadata_camera_time
    ON metadata.frame_metadata (camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metadata_gin
    ON metadata.frame_metadata USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_metadata_motion
    ON metadata.frame_metadata ((metadata->'detections'->>'motion_score'))
    WHERE (metadata->'detections'->>'motion_score')::float > 0.5;

-- Continuous aggregate for 1-minute statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS metadata.frame_stats_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', timestamp) AS minute,
    camera_id,
    COUNT(*) as frame_count,
    AVG((metadata->'processing'->>'total_latency_ms')::int) as avg_latency,
    MAX((metadata->'processing'->>'total_latency_ms')::int) as max_latency,
    MIN((metadata->'processing'->>'total_latency_ms')::int) as min_latency,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY (metadata->'processing'->>'total_latency_ms')::int) as p99_latency,
    SUM(CASE WHEN (metadata->'detections'->>'faces')::int > 0 THEN 1 ELSE 0 END) as frames_with_faces,
    SUM(CASE WHEN (metadata->'detections'->>'motion_score')::float > 0.5 THEN 1 ELSE 0 END) as motion_frames,
    AVG((metadata->'detections'->>'motion_score')::float) as avg_motion_score
FROM metadata.frame_metadata
GROUP BY minute, camera_id
WITH NO DATA;

-- Continuous aggregate for hourly statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS metadata.frame_stats_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS hour,
    camera_id,
    COUNT(*) as frame_count,
    AVG((metadata->'processing'->>'total_latency_ms')::int) as avg_latency,
    MAX((metadata->'processing'->>'total_latency_ms')::int) as max_latency,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY (metadata->'processing'->>'total_latency_ms')::int) as p99_latency,
    SUM(CASE WHEN (metadata->'detections'->>'faces')::int > 0 THEN 1 ELSE 0 END) as frames_with_faces,
    AVG((metadata->'detections'->>'motion_score')::float) as avg_motion_score,
    COUNT(DISTINCT metadata->'trace_id') as unique_traces
FROM metadata.frame_metadata
GROUP BY hour, camera_id
WITH NO DATA;

-- Continuous aggregate for daily statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS metadata.frame_stats_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day,
    camera_id,
    COUNT(*) as frame_count,
    AVG((metadata->'processing'->>'total_latency_ms')::int) as avg_latency,
    MAX((metadata->'processing'->>'total_latency_ms')::int) as max_latency,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY (metadata->'processing'->>'total_latency_ms')::int) as p99_latency,
    SUM(CASE WHEN (metadata->'detections'->>'faces')::int > 0 THEN 1 ELSE 0 END) as total_faces_detected,
    AVG((metadata->'detections'->>'motion_score')::float) as avg_motion_score
FROM metadata.frame_metadata
GROUP BY day, camera_id
WITH NO DATA;

-- Refresh policies for continuous aggregates
SELECT add_continuous_aggregate_policy(
    'metadata.frame_stats_1min',
    start_offset => INTERVAL '5 minutes',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute'
);

SELECT add_continuous_aggregate_policy(
    'metadata.frame_stats_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

SELECT add_continuous_aggregate_policy(
    'metadata.frame_stats_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day'
);

-- Retention policies
-- Raw data: 7 days
SELECT add_retention_policy('metadata.frame_metadata', INTERVAL '7 days');
-- 1-minute aggregates: 30 days
SELECT add_retention_policy('metadata.frame_stats_1min', INTERVAL '30 days');
-- Hourly aggregates: 1 year
SELECT add_retention_policy('metadata.frame_stats_hourly', INTERVAL '365 days');
-- Daily aggregates: Keep forever (no retention policy)

-- Compression policies (if Enterprise license available)
-- Uncomment if you have TimescaleDB Enterprise:
-- SELECT add_compression_policy('metadata.frame_metadata', INTERVAL '1 day');
-- SELECT add_compression_policy('metadata.frame_stats_1min', INTERVAL '7 days');
-- SELECT add_compression_policy('metadata.frame_stats_hourly', INTERVAL '30 days');

-- Performance optimization settings
ALTER TABLE metadata.frame_metadata SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.01
);

-- Grant permissions to application user
GRANT USAGE ON SCHEMA metadata TO detektor_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA metadata TO detektor_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA metadata TO detektor_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA metadata GRANT ALL ON TABLES TO detektor_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA metadata GRANT ALL ON SEQUENCES TO detektor_app;

-- Create helper functions for common queries
CREATE OR REPLACE FUNCTION metadata.get_recent_frames(
    p_camera_id TEXT,
    p_interval INTERVAL DEFAULT '1 hour'
)
RETURNS TABLE (
    frame_id TEXT,
    "timestamp" TIMESTAMPTZ,
    motion_score FLOAT,
    faces_detected INT,
    processing_latency_ms INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        f.frame_id,
        f.timestamp,
        (f.metadata->'detections'->>'motion_score')::float,
        (f.metadata->'detections'->>'faces')::int,
        (f.metadata->'processing'->>'total_latency_ms')::int
    FROM metadata.frame_metadata f
    WHERE f.camera_id = p_camera_id
      AND f.timestamp > NOW() - p_interval
    ORDER BY f.timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- Performance statistics function
CREATE OR REPLACE FUNCTION metadata.get_performance_stats(
    p_interval INTERVAL DEFAULT '1 hour'
)
RETURNS TABLE (
    camera_id TEXT,
    total_frames BIGINT,
    avg_latency FLOAT,
    p99_latency FLOAT,
    max_latency INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        f.camera_id,
        COUNT(*) as total_frames,
        AVG((f.metadata->'processing'->>'total_latency_ms')::int)::float as avg_latency,
        percentile_cont(0.99) WITHIN GROUP (ORDER BY (f.metadata->'processing'->>'total_latency_ms')::int)::float as p99_latency,
        MAX((f.metadata->'processing'->>'total_latency_ms')::int) as max_latency
    FROM metadata.frame_metadata f
    WHERE f.timestamp > NOW() - p_interval
    GROUP BY f.camera_id;
END;
$$ LANGUAGE plpgsql;
