-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create schema for frame tracking
CREATE SCHEMA IF NOT EXISTS tracking;

-- Frame events table (Event Sourcing pattern)
CREATE TABLE IF NOT EXISTS tracking.frame_events (
    id BIGSERIAL,
    event_id UUID NOT NULL DEFAULT gen_random_uuid(),
    frame_id TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    correlation_id UUID,
    data JSONB NOT NULL DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, event_timestamp)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable(
    'tracking.frame_events',
    'event_timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_frame_events_frame_id
    ON tracking.frame_events (frame_id, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_frame_events_camera_id
    ON tracking.frame_events (camera_id, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_frame_events_event_type
    ON tracking.frame_events (event_type, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_frame_events_correlation_id
    ON tracking.frame_events (correlation_id)
    WHERE correlation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_frame_events_data
    ON tracking.frame_events USING GIN (data);

-- Detections table for AI results
CREATE TABLE IF NOT EXISTS tracking.detections (
    id BIGSERIAL,
    detection_id UUID NOT NULL DEFAULT gen_random_uuid(),
    frame_id TEXT NOT NULL,
    detection_type TEXT NOT NULL, -- 'face', 'object', 'gesture', etc.
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    bbox JSONB, -- Bounding box coordinates
    features JSONB, -- Additional features/embeddings
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_time_ms INTEGER,
    service_name TEXT,
    model_version TEXT,
    PRIMARY KEY (id, detected_at)
);

-- Convert to hypertable
SELECT create_hypertable(
    'tracking.detections',
    'detected_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for detections
CREATE INDEX IF NOT EXISTS idx_detections_frame_id
    ON tracking.detections (frame_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_detections_type
    ON tracking.detections (detection_type, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_detections_confidence
    ON tracking.detections (confidence)
    WHERE confidence > 0.8;

-- Metrics table for performance tracking
CREATE TABLE IF NOT EXISTS tracking.service_metrics (
    time TIMESTAMPTZ NOT NULL,
    service_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    tags JSONB DEFAULT '{}'
);

-- Convert to hypertable
SELECT create_hypertable(
    'tracking.service_metrics',
    'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Compression policy for older data (after 7 days)
-- NOTE: Compression requires TimescaleDB Enterprise license
-- Uncomment if you have Enterprise license:
-- SELECT add_compression_policy('tracking.frame_events', INTERVAL '7 days');
-- SELECT add_compression_policy('tracking.detections', INTERVAL '7 days');
-- SELECT add_compression_policy('tracking.service_metrics', INTERVAL '3 days');

-- Retention policy (keep data for 30 days)
SELECT add_retention_policy('tracking.frame_events', INTERVAL '30 days');
SELECT add_retention_policy('tracking.detections', INTERVAL '30 days');
SELECT add_retention_policy('tracking.service_metrics', INTERVAL '7 days');

-- Continuous aggregates for metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS tracking.metrics_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    service_name,
    metric_name,
    avg(value) as avg_value,
    min(value) as min_value,
    max(value) as max_value,
    count(*) as count
FROM tracking.service_metrics
GROUP BY bucket, service_name, metric_name
WITH NO DATA;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy(
    'tracking.metrics_1min',
    start_offset => INTERVAL '5 minutes',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute'
);

-- Create user for application
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'detektor_app') THEN
        CREATE USER detektor_app WITH PASSWORD 'app_password';
    END IF;
END
$$;

-- Grant permissions
GRANT USAGE ON SCHEMA tracking TO detektor_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA tracking TO detektor_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA tracking TO detektor_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA tracking GRANT ALL ON TABLES TO detektor_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA tracking GRANT ALL ON SEQUENCES TO detektor_app;
