-- Frame events table (Event Sourcing pattern)
CREATE TABLE IF NOT EXISTS tracking.frame_events (
    id TEXT NOT NULL,
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

-- Detections table for AI results
CREATE TABLE IF NOT EXISTS tracking.detections (
    id TEXT NOT NULL,
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

-- Frame metadata table
CREATE TABLE IF NOT EXISTS metadata.frame_metadata (
    frame_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    camera_id TEXT NOT NULL,
    resolution JSONB,
    format TEXT,
    size_bytes BIGINT,
    storage_path TEXT,
    checksum TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (frame_id, timestamp)
);

-- Convert to hypertable
SELECT create_hypertable(
    'metadata.frame_metadata',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);
