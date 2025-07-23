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

-- Frame stats per minute
CREATE MATERIALIZED VIEW IF NOT EXISTS metadata.frame_stats_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', timestamp) AS bucket,
    camera_id,
    count(*) as frame_count,
    avg(size_bytes) as avg_size_bytes,
    sum(size_bytes) as total_bytes
FROM metadata.frame_metadata
GROUP BY bucket, camera_id
WITH NO DATA;

-- Frame stats per hour
CREATE MATERIALIZED VIEW IF NOT EXISTS metadata.frame_stats_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS bucket,
    camera_id,
    count(*) as frame_count,
    avg(size_bytes) as avg_size_bytes,
    sum(size_bytes) as total_bytes
FROM metadata.frame_metadata
GROUP BY bucket, camera_id
WITH NO DATA;

-- Frame stats per day
CREATE MATERIALIZED VIEW IF NOT EXISTS metadata.frame_stats_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS bucket,
    camera_id,
    count(*) as frame_count,
    avg(size_bytes) as avg_size_bytes,
    sum(size_bytes) as total_bytes
FROM metadata.frame_metadata
GROUP BY bucket, camera_id
WITH NO DATA;
