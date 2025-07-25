# Detektor Dashboards

This directory contains Grafana dashboards for monitoring the Detektor system.

## Available Dashboards

### Frame Tracking Dashboard (`frame-tracking.json`)

Comprehensive dashboard for monitoring frame processing pipeline with distributed tracing integration.

**Features:**
- Real-time frame processing rate by camera
- Processing time percentiles (p50, p95, p99)
- Frame drops analysis by reason
- Buffer size monitoring
- Jaeger trace integration for frame journey visualization
- Frame ID search functionality

**Variables:**
- `camera_id`: Filter by specific camera(s)
- `operation`: Filter by processing operation
- `frame_id`: Search for specific frame traces

**Requirements:**
- Prometheus datasource configured
- Jaeger datasource configured
- Services exporting metrics to Prometheus
- OpenTelemetry traces sent to Jaeger

## Installation

### Manual Import

1. Open Grafana UI (http://localhost:3000)
2. Go to Dashboards → Import
3. Upload the JSON file or paste its contents
4. Select Prometheus and Jaeger datasources
5. Click Import

### Automatic Provisioning

1. Copy dashboard JSON to Grafana dashboards directory:
   ```bash
   cp dashboards/*.json /var/lib/grafana/dashboards/
   ```

2. Copy provisioning config:
   ```bash
   cp configs/grafana/provisioning/dashboards/*.yaml /etc/grafana/provisioning/dashboards/
   ```

3. Restart Grafana:
   ```bash
   docker restart grafana
   ```

## Dashboard URLs

After import, dashboards will be available at:
- Frame Tracking: http://localhost:3000/d/frame-tracking

## Customization

### Adding New Panels

1. Edit dashboard in Grafana UI
2. Add panel with desired query
3. Save and export JSON
4. Update the dashboard file in this repository

### Common Queries

**Frame processing rate:**
```promql
rate(frames_processed_total{camera_id=~"$camera_id"}[5m])
```

**Processing latency percentiles:**
```promql
histogram_quantile(0.95,
  sum(rate(frame_processing_duration_seconds_bucket[5m])) by (le)
) * 1000
```

**Active connections:**
```promql
active_rtsp_connections{camera_id=~"$camera_id"}
```

**Frame drops:**
```promql
sum(rate(frame_drops_total[5m])) by (reason)
```

## Trace Search

The Frame Tracking dashboard includes a Jaeger panel for trace visualization. To search for a specific frame:

1. Enter the frame ID in the `frame_id` variable at the top of the dashboard
2. The Jaeger panel will automatically update to show matching traces
3. Click on a trace to see the full frame journey

## Alerts

Example alert rules based on dashboard metrics:

```yaml
groups:
  - name: frame_tracking
    rules:
      - alert: HighFrameDropRate
        expr: rate(frame_drops_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High frame drop rate detected"

      - alert: SlowFrameProcessing
        expr: histogram_quantile(0.95, rate(frame_processing_duration_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Frame processing is slow (p95 > 1s)"
```

## Troubleshooting

### No Data in Panels

1. Check Prometheus targets: http://localhost:9090/targets
2. Verify services are exporting metrics:
   ```bash
   curl http://localhost:8080/metrics | grep frame_
   ```
3. Check datasource configuration in Grafana

### Traces Not Showing

1. Verify Jaeger is receiving traces: http://localhost:16686
2. Check OTEL configuration in services
3. Ensure frame.id tag is being set in spans

### Performance Issues

1. Reduce time range or increase refresh interval
2. Use recording rules for expensive queries
3. Enable query caching in Grafana
