# RTSP Capture Service API Documentation

## Overview

RTSP Capture Service is responsible for capturing video streams from IP cameras via RTSP protocol, buffering frames, and publishing them to the processing pipeline.

**Base URL**: `http://localhost:8001`
**Version**: 1.0.0
**OpenAPI**: Available at `/docs` and `/redoc`

## Service Architecture

```
RTSP Stream → Connection Manager → Frame Extractor → Frame Buffer → Redis Queue
                     ↓                                     ↓
                Auto-reconnect                    Prometheus Metrics
                     ↓                                     ↓
              OpenTelemetry Traces                  Health Checks
```

## Endpoints

### Health & Monitoring

#### GET /health
Health check endpoint providing detailed service status.

**Response**: `200 OK`
```json
{
  "status": "healthy",  // healthy | degraded | unhealthy
  "service": "rtsp-capture",
  "version": "1.0.0",
  "timestamp": "2025-01-21T00:00:00Z",
  "checks": {
    "redis": "healthy",
    "rtsp_connection": "healthy",
    "frame_buffer": "healthy"
  },
  "metrics": {
    "frames_captured": 1000000,
    "frames_dropped": 0,
    "buffer_size": 50,
    "uptime_seconds": 3600
  }
}
```

#### GET /ready
Kubernetes-style readiness probe.

**Response**:
- `200 OK` - Service is ready to accept traffic
- `503 Service Unavailable` - Service is not ready

#### GET /metrics
Prometheus metrics endpoint.

**Response**: `200 OK` (text/plain)
```
# HELP rtsp_frames_captured_total Total number of frames captured
# TYPE rtsp_frames_captured_total counter
rtsp_frames_captured_total 1000000

# HELP rtsp_frame_processing_duration_seconds Frame processing duration
# TYPE rtsp_frame_processing_duration_seconds histogram
rtsp_frame_processing_duration_seconds_bucket{le="0.005"} 950000
rtsp_frame_processing_duration_seconds_bucket{le="0.01"} 990000
rtsp_frame_processing_duration_seconds_bucket{le="0.025"} 999000

# HELP rtsp_buffer_size_gauge Current frame buffer size
# TYPE rtsp_buffer_size_gauge gauge
rtsp_buffer_size_gauge 50

# HELP rtsp_errors_total Total number of errors
# TYPE rtsp_errors_total counter
rtsp_errors_total{type="connection"} 5
rtsp_errors_total{type="processing"} 0
```

#### GET /ping
Simple liveness check.

**Response**: `200 OK`
```json
{
  "pong": true
}
```

### Frame Operations (Future)

#### POST /frames/capture
Manually trigger frame capture (for testing).

**Request Body**:
```json
{
  "rtsp_url": "rtsp://camera.local:554/stream",
  "count": 10,
  "interval_ms": 100
}
```

**Response**: `202 Accepted`
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing"
}
```

#### GET /frames/buffer/status
Get current frame buffer status.

**Response**: `200 OK`
```json
{
  "buffer_size": 50,
  "max_size": 100,
  "frames": [
    {
      "id": "frame_123",
      "timestamp": "2025-01-21T00:00:00.123Z",
      "size_bytes": 1048576
    }
  ]
}
```

## Configuration

Service configuration via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Service port | `8001` |
| `RTSP_URL` | Camera RTSP URL | `rtsp://localhost:8554/stream` |
| `FRAME_BUFFER_SIZE` | Max frames in buffer | `100` |
| `REDIS_HOST` | Redis hostname | `redis` |
| `REDIS_PORT` | Redis port | `6379` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry endpoint | `http://jaeger:4317` |

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid RTSP URL format",
  "detail": "URL must start with rtsp://"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "detail": "Failed to connect to RTSP stream"
}
```

### 503 Service Unavailable
```json
{
  "error": "Service unavailable",
  "detail": "Redis connection failed"
}
```

## Observability

### Traces
All operations are traced with OpenTelemetry:
- `rtsp.connect` - Connection establishment
- `rtsp.frame.extract` - Frame extraction
- `rtsp.frame.buffer.add` - Buffer operations
- `rtsp.redis.publish` - Redis queue publish

### Metrics
Key metrics to monitor:
- `rtsp_frames_captured_total` - Frame capture rate
- `rtsp_frame_processing_duration_seconds` - Processing latency
- `rtsp_buffer_size_gauge` - Buffer utilization
- `rtsp_errors_total` - Error rate by type

### Logs
Structured JSON logs with correlation IDs:
```json
{
  "timestamp": "2025-01-21T00:00:00Z",
  "level": "INFO",
  "service": "rtsp-capture",
  "trace_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Frame captured successfully",
  "frame_id": "frame_123",
  "duration_ms": 5
}
```

## Docker Image

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest

# Run with environment
docker run -d \
  -p 8001:8001 \
  -e RTSP_URL=rtsp://camera.local:554/stream \
  -e REDIS_HOST=redis \
  ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest
```

## Integration Example

```python
import requests

# Check service health
health = requests.get("http://localhost:8001/health").json()
print(f"Service status: {health['status']}")

# Get metrics
metrics = requests.get("http://localhost:8001/metrics").text
print(f"Frames captured: {metrics}")
```

## Performance Characteristics

- **Frame Rate**: Up to 30 FPS per camera
- **Latency**: <10ms frame processing
- **Buffer Size**: 100 frames default
- **Memory**: ~500MB for 1080p stream
- **CPU**: ~20% single core at 30 FPS

## Security Considerations

- No authentication currently implemented (internal service)
- RTSP credentials should be in URL (basic auth)
- Runs as non-root user in container
- No external ports exposed in production

## Future Enhancements

1. WebSocket endpoint for live frame streaming
2. Multiple camera support
3. Frame filtering/preprocessing
4. S3/MinIO frame archival
5. Motion detection triggers
