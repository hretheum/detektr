-- Indexes for frame_events table
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

-- Indexes for detections table
CREATE INDEX IF NOT EXISTS idx_detections_frame_id
    ON tracking.detections (frame_id, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_detections_type
    ON tracking.detections (detection_type, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_detections_confidence
    ON tracking.detections (confidence)
    WHERE confidence > 0.8;

CREATE INDEX IF NOT EXISTS idx_detections_service
    ON tracking.detections (service_name, detected_at DESC);

-- Indexes for service_metrics table
CREATE INDEX IF NOT EXISTS idx_metrics_service_metric
    ON tracking.service_metrics (service_name, metric_name, time DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_tags
    ON tracking.service_metrics USING GIN (tags);

-- Indexes for frame_metadata table
CREATE INDEX IF NOT EXISTS idx_frame_metadata_camera
    ON metadata.frame_metadata (camera_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_frame_metadata_checksum
    ON metadata.frame_metadata (checksum)
    WHERE checksum IS NOT NULL;
