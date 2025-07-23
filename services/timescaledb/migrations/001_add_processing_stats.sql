-- Migration: Add processing statistics table
-- Date: 2025-07-23
-- Author: Detektor Team

CREATE TABLE IF NOT EXISTS analytics.processing_stats (
    id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    service_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    duration_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable
SELECT create_hypertable(
    'analytics.processing_stats',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Add retention policy
SELECT add_retention_policy('analytics.processing_stats',
    drop_after => INTERVAL '14 days',
    if_not_exists => TRUE
);
