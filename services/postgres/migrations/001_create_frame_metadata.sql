-- Migration: 001_create_frame_metadata.sql
-- Description: Create frame metadata tables with TimescaleDB hypertables

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS detektor;

-- Frame metadata table
CREATE TABLE IF NOT EXISTS detektor.frame_metadata (
    frame_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    camera_id VARCHAR(100) NOT NULL,
    sequence_number BIGINT NOT NULL,
    frame_size INTEGER,
    frame_width INTEGER,
    frame_height INTEGER,
    fps FLOAT,
    codec VARCHAR(50),
    processing_status VARCHAR(50) DEFAULT 'captured',
    trace_id VARCHAR(128),
    span_id VARCHAR(64),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (timestamp, frame_id)
);

-- Convert to hypertable
SELECT create_hypertable(
    'detektor.frame_metadata',
    'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_frame_metadata_camera_id
    ON detektor.frame_metadata (camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_frame_metadata_trace_id
    ON detektor.frame_metadata (trace_id);
CREATE INDEX IF NOT EXISTS idx_frame_metadata_status
    ON detektor.frame_metadata (processing_status, timestamp DESC);

-- Detection events table
CREATE TABLE IF NOT EXISTS detektor.detection_events (
    event_id UUID DEFAULT gen_random_uuid(),
    frame_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    detection_type VARCHAR(50) NOT NULL, -- face, object, gesture
    confidence FLOAT NOT NULL,
    bounding_box JSONB,
    attributes JSONB,
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (timestamp, event_id)
);

-- Convert to hypertable
SELECT create_hypertable(
    'detektor.detection_events',
    'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_detection_events_frame_id
    ON detektor.detection_events (frame_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_detection_events_type
    ON detektor.detection_events (detection_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_detection_events_confidence
    ON detektor.detection_events (confidence) WHERE confidence > 0.8;

-- Processing metrics table
CREATE TABLE IF NOT EXISTS detektor.processing_metrics (
    metric_id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    duration_ms INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    metadata JSONB,
    PRIMARY KEY (timestamp, metric_id)
);

-- Convert to hypertable
SELECT create_hypertable(
    'detektor.processing_metrics',
    'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 hour'
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_processing_metrics_service
    ON detektor.processing_metrics (service_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_processing_metrics_success
    ON detektor.processing_metrics (success, timestamp DESC);
