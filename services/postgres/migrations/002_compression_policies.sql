-- Migration: 002_compression_policies.sql
-- Description: Setup compression policies for TimescaleDB hypertables

-- Enable compression on frame_metadata
ALTER TABLE detektor.frame_metadata SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'camera_id',
    timescaledb.compress_orderby = 'timestamp DESC, frame_id'
);

-- Add compression policy: compress chunks older than 7 days
SELECT add_compression_policy(
    'detektor.frame_metadata',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Enable compression on detection_events
ALTER TABLE detektor.detection_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'detection_type',
    timescaledb.compress_orderby = 'timestamp DESC, event_id'
);

-- Add compression policy: compress chunks older than 7 days
SELECT add_compression_policy(
    'detektor.detection_events',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Enable compression on processing_metrics
ALTER TABLE detektor.processing_metrics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'service_name',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Add compression policy: compress chunks older than 3 days
SELECT add_compression_policy(
    'detektor.processing_metrics',
    INTERVAL '3 days',
    if_not_exists => TRUE
);

-- Show compression stats function
CREATE OR REPLACE FUNCTION detektor.show_compression_stats()
RETURNS TABLE (
    hypertable_name TEXT,
    uncompressed_size TEXT,
    compressed_size TEXT,
    compression_ratio NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        hypertable_schema || '.' || hypertable_name,
        pg_size_pretty(before_compression_total_bytes) AS uncompressed_size,
        pg_size_pretty(after_compression_total_bytes) AS compressed_size,
        ROUND((before_compression_total_bytes::numeric /
               NULLIF(after_compression_total_bytes, 0))::numeric, 2) AS compression_ratio
    FROM timescaledb_information.compression_stats
    WHERE hypertable_schema = 'detektor';
END;
$$ LANGUAGE plpgsql;
