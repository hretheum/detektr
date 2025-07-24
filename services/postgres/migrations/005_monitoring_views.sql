-- Migration: 005_monitoring_views.sql
-- Description: Create monitoring views and functions for operational visibility

-- View for current system health
CREATE OR REPLACE VIEW detektor.system_health AS
WITH recent_metrics AS (
    SELECT
        service_name,
        COUNT(*) AS total_requests,
        SUM(CASE WHEN success THEN 1 ELSE 0 END) AS successful_requests,
        AVG(duration_ms) AS avg_duration_ms,
        MAX(timestamp) AS last_activity
    FROM detektor.processing_metrics
    WHERE timestamp > NOW() - INTERVAL '5 minutes'
    GROUP BY service_name
)
SELECT
    service_name,
    total_requests,
    CASE
        WHEN total_requests = 0 THEN 100.0
        ELSE ROUND((successful_requests::numeric / total_requests) * 100, 2)
    END AS success_rate,
    ROUND(avg_duration_ms::numeric, 2) AS avg_duration_ms,
    last_activity,
    CASE
        WHEN last_activity < NOW() - INTERVAL '2 minutes' THEN 'STALE'
        WHEN total_requests = 0 THEN 'NO_DATA'
        WHEN (successful_requests::numeric / total_requests) < 0.95 THEN 'DEGRADED'
        ELSE 'HEALTHY'
    END AS status
FROM recent_metrics
ORDER BY service_name;

-- View for storage usage
CREATE OR REPLACE VIEW detektor.storage_usage AS
SELECT
    hypertable_schema || '.' || hypertable_name AS table_name,
    pg_size_pretty(hypertable_size) AS total_size,
    pg_size_pretty(compression_total_size) AS compressed_size,
    pg_size_pretty(hypertable_size - COALESCE(compression_total_size, 0)) AS uncompressed_size,
    total_chunks,
    compressed_chunks,
    CASE
        WHEN total_chunks > 0
        THEN ROUND((compressed_chunks::numeric / total_chunks) * 100, 2)
        ELSE 0
    END AS compression_percentage
FROM timescaledb_information.hypertable
WHERE hypertable_schema = 'detektor'
ORDER BY hypertable_size DESC;

-- Function to get frame processing pipeline stats
CREATE OR REPLACE FUNCTION detektor.get_pipeline_stats(
    time_range INTERVAL DEFAULT '1 hour'
)
RETURNS TABLE (
    metric_name TEXT,
    metric_value NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH stats AS (
        SELECT
            COUNT(DISTINCT fm.frame_id) AS total_frames,
            COUNT(DISTINCT de.event_id) AS total_detections,
            AVG(fm.fps) AS avg_fps,
            COUNT(DISTINCT fm.camera_id) AS active_cameras
        FROM detektor.frame_metadata fm
        LEFT JOIN detektor.detection_events de ON fm.frame_id = de.frame_id
        WHERE fm.timestamp > NOW() - time_range
    ),
    performance AS (
        SELECT
            AVG(duration_ms) AS avg_processing_time,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_processing_time
        FROM detektor.processing_metrics
        WHERE timestamp > NOW() - time_range
        AND service_name = 'rtsp-capture'
    )
    SELECT 'total_frames_processed', total_frames::numeric FROM stats
    UNION ALL
    SELECT 'total_detections', total_detections::numeric FROM stats
    UNION ALL
    SELECT 'average_fps', ROUND(avg_fps::numeric, 2) FROM stats
    UNION ALL
    SELECT 'active_cameras', active_cameras::numeric FROM stats
    UNION ALL
    SELECT 'avg_processing_time_ms', ROUND(avg_processing_time::numeric, 2) FROM performance
    UNION ALL
    SELECT 'p95_processing_time_ms', ROUND(p95_processing_time::numeric, 2) FROM performance;
END;
$$ LANGUAGE plpgsql;

-- Alert on high error rates
CREATE OR REPLACE FUNCTION detektor.check_error_rates()
RETURNS TABLE (
    service_name VARCHAR,
    error_rate NUMERIC,
    total_errors BIGINT,
    alert_level TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH error_stats AS (
        SELECT
            pm.service_name,
            COUNT(*) AS total_requests,
            SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) AS error_count
        FROM detektor.processing_metrics pm
        WHERE timestamp > NOW() - INTERVAL '15 minutes'
        GROUP BY pm.service_name
    )
    SELECT
        es.service_name,
        ROUND((error_count::numeric / total_requests) * 100, 2) AS error_rate,
        error_count AS total_errors,
        CASE
            WHEN (error_count::numeric / total_requests) > 0.1 THEN 'CRITICAL'
            WHEN (error_count::numeric / total_requests) > 0.05 THEN 'WARNING'
            ELSE 'OK'
        END AS alert_level
    FROM error_stats es
    WHERE error_count > 0
    ORDER BY error_rate DESC;
END;
$$ LANGUAGE plpgsql;

-- Create a summary dashboard view
CREATE OR REPLACE VIEW detektor.dashboard_summary AS
SELECT
    NOW() AS timestamp,
    (SELECT COUNT(*) FROM detektor.system_health WHERE status = 'HEALTHY') AS healthy_services,
    (SELECT COUNT(*) FROM detektor.system_health WHERE status != 'HEALTHY') AS unhealthy_services,
    (SELECT metric_value FROM detektor.get_pipeline_stats('5 minutes') WHERE metric_name = 'total_frames_processed') AS frames_last_5min,
    (SELECT metric_value FROM detektor.get_pipeline_stats('5 minutes') WHERE metric_name = 'total_detections') AS detections_last_5min,
    (SELECT SUM(pg_size_bytes(total_size)) FROM detektor.storage_usage) AS total_storage_bytes,
    (SELECT COUNT(*) FROM detektor.check_error_rates() WHERE alert_level != 'OK') AS active_alerts;
