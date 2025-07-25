-- Migration 001: Create frame metadata schema and hypertables
-- Author: AI Assistant
-- Date: 2025-07-24

-- Create schema for tracking data
CREATE SCHEMA IF NOT EXISTS tracking;

-- Enable TimescaleDB extension if not already enabled
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create frame_metadata table
CREATE TABLE IF NOT EXISTS tracking.frame_metadata (
    time TIMESTAMPTZ NOT NULL,
    frame_id VARCHAR(128) NOT NULL,
    camera_id VARCHAR(64) NOT NULL,
    source_url TEXT,
    resolution_width INTEGER,
    resolution_height INTEGER,
    format VARCHAR(32),
    size_bytes BIGINT,
    capture_latency_ms FLOAT,
    processing_stage VARCHAR(64),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create hypertable
SELECT create_hypertable(
    'tracking.frame_metadata',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_frame_metadata_frame_id
    ON tracking.frame_metadata (frame_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_frame_metadata_camera_id
    ON tracking.frame_metadata (camera_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_frame_metadata_stage
    ON tracking.frame_metadata (processing_stage, time DESC);

-- Create detection_events table
CREATE TABLE IF NOT EXISTS tracking.detection_events (
    time TIMESTAMPTZ NOT NULL,
    event_id UUID DEFAULT gen_random_uuid(),
    frame_id VARCHAR(128) NOT NULL,
    camera_id VARCHAR(64) NOT NULL,
    detection_type VARCHAR(64) NOT NULL,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    object_class VARCHAR(128),
    bounding_box JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (event_id, time)
);

-- Create hypertable for detection events
SELECT create_hypertable(
    'tracking.detection_events',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes for detection events
CREATE INDEX IF NOT EXISTS idx_detection_events_frame_id
    ON tracking.detection_events (frame_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_detection_events_camera_id
    ON tracking.detection_events (camera_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_detection_events_type
    ON tracking.detection_events (detection_type, time DESC);

CREATE INDEX IF NOT EXISTS idx_detection_events_confidence
    ON tracking.detection_events (confidence DESC, time DESC)
    WHERE confidence > 0.8;

-- Create GIN index for JSONB metadata
CREATE INDEX IF NOT EXISTS idx_frame_metadata_jsonb
    ON tracking.frame_metadata USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_detection_events_jsonb
    ON tracking.detection_events USING GIN (metadata);

-- Grant permissions to detektor user
GRANT USAGE ON SCHEMA tracking TO detektor;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA tracking TO detektor;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA tracking TO detektor;

-- Add comments
COMMENT ON TABLE tracking.frame_metadata IS 'Time-series data for video frame metadata';
COMMENT ON TABLE tracking.detection_events IS 'Time-series data for object detection events';
COMMENT ON COLUMN tracking.frame_metadata.capture_latency_ms IS 'Time taken to capture frame in milliseconds';
COMMENT ON COLUMN tracking.detection_events.confidence IS 'Detection confidence score between 0 and 1';
