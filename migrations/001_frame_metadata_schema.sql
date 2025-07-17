-- Frame metadata schema for TimescaleDB
-- Requires TimescaleDB extension to be installed

-- Create database if not exists (run as superuser)
-- CREATE DATABASE detektor;

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Frame metadata table
CREATE TABLE IF NOT EXISTS frame_metadata (
    -- Primary key
    frame_id VARCHAR(64) PRIMARY KEY,

    -- Frame identification
    camera_id VARCHAR(32) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,

    -- Processing state
    state VARCHAR(16) NOT NULL CHECK (state IN ('captured', 'queued', 'processing', 'completed', 'failed')),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Frame details
    metadata JSONB DEFAULT '{}',

    -- Error tracking
    error_message TEXT,

    -- Performance metrics
    total_processing_time_ms FLOAT,

    -- Indexes for common queries
    INDEX idx_camera_timestamp (camera_id, timestamp DESC),
    INDEX idx_state (state),
    INDEX idx_created_at (created_at DESC)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable(
    'frame_metadata',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Processing stages table
CREATE TABLE IF NOT EXISTS processing_stages (
    -- Composite primary key
    frame_id VARCHAR(64) NOT NULL REFERENCES frame_metadata(frame_id) ON DELETE CASCADE,
    stage_index INTEGER NOT NULL,

    -- Stage details
    stage_name VARCHAR(64) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(16) NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed')),

    -- Stage metadata and error
    metadata JSONB DEFAULT '{}',
    error_message TEXT,

    -- Performance
    duration_ms FLOAT,

    PRIMARY KEY (frame_id, stage_index),
    INDEX idx_stage_name (stage_name),
    INDEX idx_stage_status (status)
);

-- Frame events table for event sourcing
CREATE TABLE IF NOT EXISTS frame_events (
    -- Event identification
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(64) NOT NULL,

    -- Frame reference
    frame_id VARCHAR(64) NOT NULL,

    -- Event details
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',

    -- Indexes
    INDEX idx_frame_events (frame_id, occurred_at DESC),
    INDEX idx_event_type (event_type),
    INDEX idx_occurred_at (occurred_at DESC)
);

-- Convert events to hypertable
SELECT create_hypertable(
    'frame_events',
    'occurred_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Continuous aggregate for frame processing stats by camera and hour
CREATE MATERIALIZED VIEW IF NOT EXISTS frame_stats_hourly
WITH (timescaledb.continuous) AS
SELECT
    camera_id,
    time_bucket('1 hour', timestamp) AS hour,
    COUNT(*) AS total_frames,
    COUNT(*) FILTER (WHERE state = 'completed') AS completed_frames,
    COUNT(*) FILTER (WHERE state = 'failed') AS failed_frames,
    AVG(total_processing_time_ms) FILTER (WHERE state = 'completed') AS avg_processing_time_ms,
    MAX(total_processing_time_ms) FILTER (WHERE state = 'completed') AS max_processing_time_ms,
    MIN(total_processing_time_ms) FILTER (WHERE state = 'completed') AS min_processing_time_ms
FROM frame_metadata
GROUP BY camera_id, hour
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy(
    'frame_stats_hourly',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes',
    if_not_exists => TRUE
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_metadata_gin ON frame_metadata USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_frame_state_camera ON frame_metadata (state, camera_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
CREATE TRIGGER update_frame_metadata_updated_at
    BEFORE UPDATE ON frame_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Compression policy for old data (after 7 days)
SELECT add_compression_policy(
    'frame_metadata',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

SELECT add_compression_policy(
    'frame_events',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Retention policy (optional - keep data for 30 days)
-- Uncomment if you want automatic data deletion
-- SELECT add_retention_policy(
--     'frame_metadata',
--     INTERVAL '30 days',
--     if_not_exists => TRUE
-- );

-- Helper views for common queries

-- Recent frames view
CREATE OR REPLACE VIEW recent_frames AS
SELECT
    f.*,
    COALESCE(
        (SELECT json_agg(
            json_build_object(
                'stage_name', ps.stage_name,
                'status', ps.status,
                'duration_ms', ps.duration_ms
            ) ORDER BY ps.stage_index
        )
        FROM processing_stages ps
        WHERE ps.frame_id = f.frame_id
        ), '[]'::json
    ) AS stages
FROM frame_metadata f
WHERE f.timestamp > NOW() - INTERVAL '1 hour'
ORDER BY f.timestamp DESC;

-- Failed frames view
CREATE OR REPLACE VIEW failed_frames AS
SELECT
    f.*,
    ps.stage_name AS failed_stage,
    ps.error_message AS stage_error
FROM frame_metadata f
LEFT JOIN processing_stages ps ON f.frame_id = ps.frame_id AND ps.status = 'failed'
WHERE f.state = 'failed'
ORDER BY f.timestamp DESC;

-- Performance stats view
CREATE OR REPLACE VIEW performance_stats AS
SELECT
    camera_id,
    DATE_TRUNC('hour', timestamp) AS hour,
    COUNT(*) AS frames_processed,
    AVG(total_processing_time_ms) AS avg_time_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_processing_time_ms) AS median_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_processing_time_ms) AS p95_time_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_processing_time_ms) AS p99_time_ms
FROM frame_metadata
WHERE state = 'completed'
    AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY camera_id, hour
ORDER BY hour DESC, camera_id;

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO detektor_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO detektor_app;
