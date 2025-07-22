# Metadata Storage Requirements - Time Series Analysis

## System Requirements Overview

### Expected Data Volume

**Daily volume**: 1,000,000 records/day
- **Cameras**: 10 cameras
- **FPS**: 1 frame/second per camera (motion detection optimized)
- **Hours**: 24 hours operation
- **Records per day**: 10 cameras × 1 fps × 86,400 seconds = 864,000 records

### Data Model

```json
{
  "frame_id": "2025-01-20T10:15:30.123456_cam01_001234",
  "timestamp": "2025-01-20T10:15:30.123456Z",
  "camera_id": "cam01",
  "sequence_number": 1234,
  "metadata": {
    "detections": {
      "faces": 2,
      "objects": ["person", "car"],
      "motion_score": 0.85
    },
    "processing": {
      "capture_latency_ms": 15,
      "processing_latency_ms": 45,
      "total_latency_ms": 60
    },
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "span_id": "64e8400-e29b-41d4"
  }
}
```

### Storage Calculations

**Raw data storage**:
- Record size: ~500 bytes
- Daily: 864,000 records × 500 bytes = 432 MB
- Monthly: 432 MB × 30 = 12.96 GB
- Yearly: 432 MB × 365 = 157.68 GB

**With TimescaleDB compression (10:1)**:
- Daily: 43.2 MB
- Monthly: 1.3 GB
- Yearly: 15.8 GB

### Performance Requirements

1. **Write Performance**:
   - Sustained: 10 writes/second (normal operation)
   - Burst: 1,000 writes/second (batch processing)
   - Target: 10,000 writes/second (with batching)

2. **Read Performance**:
   - Point queries: <1ms (by frame_id)
   - Range queries: <10ms (last hour of camera)
   - Aggregation queries: <100ms (daily stats)

3. **Query Patterns**:
   ```sql
   -- Most recent frames from camera
   SELECT * FROM frame_metadata
   WHERE camera_id = 'cam01'
   AND timestamp > NOW() - INTERVAL '1 hour'
   ORDER BY timestamp DESC;

   -- Detection statistics
   SELECT camera_id,
          COUNT(*) as total_frames,
          AVG((metadata->>'motion_score')::float) as avg_motion
   FROM frame_metadata
   WHERE timestamp > NOW() - INTERVAL '1 day'
   GROUP BY camera_id;

   -- Performance metrics
   SELECT time_bucket('1 minute', timestamp) as minute,
          AVG((metadata->'processing'->>'total_latency_ms')::int) as avg_latency,
          MAX((metadata->'processing'->>'total_latency_ms')::int) as max_latency
   FROM frame_metadata
   WHERE timestamp > NOW() - INTERVAL '1 hour'
   GROUP BY minute;
   ```

### Data Lifecycle

1. **Retention Policies**:
   - Raw data: 7 days
   - 1-minute aggregates: 30 days
   - 1-hour aggregates: 1 year
   - Daily summaries: Forever

2. **Aggregation Strategy**:
   - Real-time: Raw frames with full metadata
   - Near real-time: 1-minute rollups (counts, averages)
   - Historical: Hourly and daily aggregates

3. **Compression**:
   - Compress chunks older than 1 day
   - Target 10:1 compression ratio
   - Use TimescaleDB native compression

### Schema Design

```sql
-- Main hypertable
CREATE TABLE frame_metadata (
    frame_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    camera_id TEXT NOT NULL,
    sequence_number BIGINT NOT NULL,
    metadata JSONB NOT NULL,
    PRIMARY KEY (frame_id, timestamp)
);

-- Convert to hypertable
SELECT create_hypertable('frame_metadata', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for common queries
CREATE INDEX idx_camera_time ON frame_metadata (camera_id, timestamp DESC);
CREATE INDEX idx_metadata_gin ON frame_metadata USING GIN (metadata);

-- Continuous aggregate for 1-minute stats
CREATE MATERIALIZED VIEW frame_stats_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', timestamp) AS minute,
    camera_id,
    COUNT(*) as frame_count,
    AVG((metadata->'processing'->>'total_latency_ms')::int) as avg_latency,
    MAX((metadata->'processing'->>'total_latency_ms')::int) as max_latency,
    SUM(CASE WHEN metadata->'detections'->>'faces' != '0' THEN 1 ELSE 0 END) as frames_with_faces
FROM frame_metadata
GROUP BY minute, camera_id
WITH NO DATA;

-- Refresh policy
SELECT add_continuous_aggregate_policy('frame_stats_1min',
    start_offset => INTERVAL '2 minutes',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute'
);
```

### Capacity Planning

**For 1M records/day**:
- Chunk size: 1 day = ~432 MB uncompressed
- Compressed chunk: ~43 MB
- Memory for indexes: ~100 MB
- Connection pool: 20 connections
- Shared buffers: 2 GB
- Total RAM needed: 4 GB minimum

**Scaling considerations**:
- Horizontal scaling via read replicas
- Partitioning by camera_id if needed
- Multi-node TimescaleDB for >10M records/day

### Monitoring Requirements

1. **Database Metrics**:
   - Insert rate (records/second)
   - Query latency (p50, p95, p99)
   - Compression ratio
   - Disk usage growth
   - Connection pool utilization

2. **Application Metrics**:
   - Batch size distribution
   - Write errors/retries
   - Query timeouts
   - Cache hit rates

3. **Alerts**:
   - Insert rate drops below threshold
   - Query latency exceeds SLA
   - Disk usage >80%
   - Connection pool exhaustion

## Implementation Checklist

- [ ] Install TimescaleDB 2.13+ with PostgreSQL 15
- [ ] Configure shared_buffers, work_mem, maintenance_work_mem
- [ ] Create hypertable with appropriate chunk interval
- [ ] Set up continuous aggregates
- [ ] Configure compression policies
- [ ] Implement retention policies
- [ ] Create monitoring dashboards
- [ ] Load test with 10k inserts/second
- [ ] Backup and restore procedures
- [ ] Failover testing
