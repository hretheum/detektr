# Sample Processor - Frame Buffer Integration

This document describes the integration between the Sample Processor and Frame Buffer services.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ RTSP Capture│────▶│ Frame Buffer │◀────│ Sample Processor│
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                           ▼
                     ┌──────────┐
                     │  Redis   │
                     └──────────┘
```

## Integration Points

### 1. Frame Consumer
The Sample Processor includes a `FrameBufferConsumer` that:
- Polls the Frame Buffer API for available frames
- Processes frames in batches
- Handles errors with exponential backoff
- Supports distributed tracing

### 2. API Endpoints
- `/health` - Health check with consumer status
- `/process` - Manual frame processing
- `/process-with-tracking` - Processing with distributed tracing
- `/metrics` - Processor and consumer metrics

## Configuration

### Environment Variables

```bash
# Frame Consumer Configuration
ENABLE_FRAME_CONSUMER=true          # Enable/disable frame consumer
FRAME_BUFFER_URL=http://frame-buffer:8002  # Frame buffer API URL
CONSUMER_BATCH_SIZE=10              # Frames to fetch per request
POLL_INTERVAL_MS=100                # Polling interval in milliseconds
MAX_RETRIES=3                       # Max retries on error
BACKOFF_MS=1000                     # Initial backoff time

# Processor Configuration
DETECTION_THRESHOLD=0.5             # Detection confidence threshold
SIMULATE_GPU=false                  # Simulate GPU processing
PROCESSING_DELAY_MS=10              # Simulated processing delay
```

## Running the Integration

### Development Mode

1. Start the services:
```bash
# From project root
cd docker/environments/development
docker-compose up frame-buffer sample-processor redis
```

2. Run the integration test:
```bash
cd examples/sample-processor
python test_integration.py
```

### Production Mode

1. Build and deploy:
```bash
# Build
docker build -f examples/sample-processor/Dockerfile -t ghcr.io/hretheum/detektr/sample-processor:latest .

# Deploy
docker-compose up -d sample-processor
```

2. Monitor health:
```bash
# Check health
curl http://localhost:8099/health

# Check metrics
curl http://localhost:8099/metrics
```

## Monitoring

### Health Check Response
```json
{
  "status": "healthy",
  "timestamp": "2025-07-27T12:00:00",
  "service": "sample-processor",
  "version": "1.0.0",
  "details": {
    "processor_initialized": true,
    "consumer_enabled": true,
    "consumer_running": true,
    "frame_buffer_url": "http://frame-buffer:8002",
    "metrics": {
      "frames_processed": 150,
      "active_frames": 2
    }
  }
}
```

### Metrics
- `frames_processed` - Total frames processed
- `active_frames` - Currently processing frames
- `processing_time_ms` - Average processing time
- `state_statistics` - Processor state machine stats
- `resource_statistics` - Resource usage stats

## Troubleshooting

### Consumer Not Starting
1. Check `ENABLE_FRAME_CONSUMER` is set to `true`
2. Verify Frame Buffer is running: `curl http://localhost:8002/health`
3. Check logs: `docker logs sample-processor`

### No Frames Being Processed
1. Verify frames in buffer: `curl http://localhost:8002/frames/status`
2. Check consumer is running in health endpoint
3. Look for errors in logs

### Connection Errors
1. Ensure services are on same network
2. Check `FRAME_BUFFER_URL` is correct
3. Verify Frame Buffer is accessible from container

## Error Handling

The consumer implements robust error handling:
- Exponential backoff on failures
- Automatic retry with max retries
- Graceful degradation
- Detailed error logging

## Performance Tuning

### Batch Size
- Increase `CONSUMER_BATCH_SIZE` for higher throughput
- Decrease for lower latency

### Polling Interval
- Lower `POLL_INTERVAL_MS` for faster response
- Higher for reduced API calls

### Processing
- Adjust `BATCH_SIZE` for processor batching
- Configure `CPU_CORES` and `MEMORY_LIMIT_MB`
- Enable `PREFER_GPU` if available

## Example Usage

### Send Frames to Buffer
```python
import requests

# Send frame to buffer
frame_data = {
    "frame_id": "test_001",
    "timestamp": 1234567890,
    "camera_id": "camera_01",
    "width": 640,
    "height": 480,
    "format": "RGB"
}

response = requests.post("http://localhost:8002/frames", json=frame_data)
```

### Monitor Processing
```python
# Check processor metrics
metrics = requests.get("http://localhost:8099/metrics").json()
print(f"Frames processed: {metrics['processor_metrics']['frames_processed']}")

# Check buffer status
status = requests.get("http://localhost:8002/frames/status").json()
print(f"Frames in buffer: {status['total_frames']}")
```

## Best Practices

1. **Resource Management**
   - Set appropriate CPU and memory limits
   - Monitor resource usage via metrics

2. **Error Handling**
   - Log all errors with context
   - Implement circuit breakers for external calls
   - Use health checks for monitoring

3. **Performance**
   - Batch processing for efficiency
   - Async processing throughout
   - Connection pooling for HTTP clients

4. **Observability**
   - Enable distributed tracing
   - Export metrics to Prometheus
   - Centralized logging
