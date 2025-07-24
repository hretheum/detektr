-- Migration: 004_retention_policies.sql
-- Description: Setup data retention policies

-- Drop old frame metadata after 30 days
SELECT add_retention_policy(
    'detektor.frame_metadata',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- Drop old detection events after 30 days
SELECT add_retention_policy(
    'detektor.detection_events',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- Drop old processing metrics after 7 days (more aggressive for metrics)
SELECT add_retention_policy(
    'detektor.processing_metrics',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Create a summary table for long-term storage (not hypertable)
CREATE TABLE IF NOT EXISTS detektor.monthly_summary (
    month DATE NOT NULL,
    camera_id VARCHAR(100),
    total_frames BIGINT,
    total_detections BIGINT,
    avg_fps NUMERIC(5,2),
    detection_breakdown JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (month, camera_id)
);

-- Function to generate monthly summaries before data is dropped
CREATE OR REPLACE FUNCTION detektor.generate_monthly_summary(target_month DATE)
RETURNS void AS $$
BEGIN
    INSERT INTO detektor.monthly_summary (
        month,
        camera_id,
        total_frames,
        total_detections,
        avg_fps,
        detection_breakdown
    )
    SELECT
        target_month,
        fm.camera_id,
        COUNT(DISTINCT fm.frame_id) AS total_frames,
        COUNT(DISTINCT de.event_id) AS total_detections,
        AVG(fm.fps)::NUMERIC(5,2) AS avg_fps,
        jsonb_object_agg(
            COALESCE(de.detection_type, 'none'),
            COUNT(de.event_id)
        ) AS detection_breakdown
    FROM detektor.frame_metadata fm
    LEFT JOIN detektor.detection_events de ON fm.frame_id = de.frame_id
    WHERE DATE_TRUNC('month', fm.timestamp) = target_month
    GROUP BY fm.camera_id
    ON CONFLICT (month, camera_id)
    DO UPDATE SET
        total_frames = EXCLUDED.total_frames,
        total_detections = EXCLUDED.total_detections,
        avg_fps = EXCLUDED.avg_fps,
        detection_breakdown = EXCLUDED.detection_breakdown,
        created_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Job to run monthly summary generation
CREATE OR REPLACE FUNCTION detektor.monthly_summary_job()
RETURNS void AS $$
DECLARE
    last_month DATE;
BEGIN
    -- Get last month
    last_month := DATE_TRUNC('month', NOW() - INTERVAL '1 month');

    -- Generate summary for last month
    PERFORM detektor.generate_monthly_summary(last_month);

    RAISE NOTICE 'Generated monthly summary for %', last_month;
END;
$$ LANGUAGE plpgsql;

-- View to show retention policy status
CREATE OR REPLACE VIEW detektor.retention_policy_status AS
SELECT
    hypertable_schema || '.' || hypertable_name AS hypertable,
    config->>'drop_after' AS retention_period,
    config->>'schedule_interval' AS schedule_interval,
    next_start AS next_scheduled_drop
FROM timescaledb_information.jobs
WHERE application_name LIKE 'Retention Policy%'
AND hypertable_schema = 'detektor';
