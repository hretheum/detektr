# Example Frame Processor Service

This is a comprehensive example service demonstrating best practices for distributed tracing and observability with OpenTelemetry in the detektor project.

## Features

- **Full OpenTelemetry Integration**: Traces, metrics, and logs
- **Distributed Tracing**: End-to-end trace correlation with frame ID propagation
- **Custom Metrics**: Business-specific metrics for frame processing
- **Auto-instrumentation**: Automatic tracing for FastAPI, HTTP requests, and databases
- **Health Checks**: Comprehensive health monitoring
- **Docker Ready**: Complete containerization with observability stack
- **Grafana Dashboard**: Pre-built dashboard for monitoring

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│ Frame Processor │────│  Frame Storage  │
│   (REST API)    │    │  (AI Pipeline)  │    │ (In-Memory DB)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   OpenTelemetry │
                    │   (Observability)│
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Jaeger      │    │   Prometheus    │    │     Grafana     │
│   (Tracing)     │    │   (Metrics)     │    │  (Dashboard)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or using the virtual environment
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the Service

```bash
# Start the service directly
python -m src.examples.telemetry_service.main

# Or using Docker Compose (includes observability stack)
docker-compose up -d
```

### 3. Test the Service

```bash
# Health check
curl http://localhost:8080/health

# Process a frame
curl -X POST http://localhost:8080/process \\
  -H "Content-Type: application/json" \\
  -d '{
    "frame_id": "test_001",
    "camera_id": "camera_001",
    "frame_data": {
      "width": 1920,
      "height": 1080,
      "format": "rgb24"
    }
  }'

# Get frame results
curl http://localhost:8080/frames/test_001

# Run simulation
curl -X POST http://localhost:8080/simulate
```

### 4. Access Observability Tools

- **Jaeger UI**: http://localhost:16686
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Service Health**: http://localhost:8080/health
- **Service Metrics**: http://localhost:8080/metrics

## API Endpoints

### Core Endpoints

- `GET /health` - Health check
- `GET /metrics` - Service metrics information
- `POST /process` - Process a frame
- `GET /frames/{frame_id}` - Get frame processing results
- `GET /cameras/{camera_id}/stats` - Get camera statistics
- `POST /simulate` - Simulate frame processing for testing

### Process Frame Example

```bash
curl -X POST http://localhost:8080/process \\
  -H "Content-Type: application/json" \\
  -d '{
    "frame_id": "unique_frame_id",
    "camera_id": "camera_001",
    "frame_data": {
      "width": 1920,
      "height": 1080,
      "format": "rgb24",
      "timestamp": 1672531200
    }
  }'
```

Response:
```json
{
  "status": "success",
  "frame_id": "unique_frame_id",
  "camera_id": "camera_001",
  "result": {
    "frame_id": "unique_frame_id",
    "timestamp": 1672531200.123,
    "faces": {
      "faces_detected": 2,
      "face_locations": [[100, 100], [200, 200]],
      "confidence_scores": [0.95, 0.87]
    },
    "objects": {
      "objects_detected": 3,
      "object_classes": ["person", "car", "bicycle"],
      "confidence_scores": [0.92, 0.88, 0.79]
    },
    "gestures": {
      "gestures_detected": 1,
      "gesture_types": ["wave"],
      "confidence_scores": [0.83]
    },
    "summary": {
      "total_detections": 6,
      "has_faces": true,
      "has_objects": true,
      "has_gestures": true
    }
  }
}
```

## Observability Features

### 1. Distributed Tracing

- **Frame ID Propagation**: Each frame gets a unique ID that's propagated through all processing stages
- **Span Hierarchy**: Clear parent-child relationships between processing stages
- **Custom Attributes**: Frame metadata, camera info, detection results
- **Error Tracking**: Automatic exception recording and error spans

### 2. Metrics

The service exposes the following metrics:

- `detektor_frame_processor_frames_processed_total` - Total frames processed
- `detektor_frame_processor_detections_total` - Total detections by type
- `detektor_frame_processor_processing_duration_seconds` - Processing time by stage
- `detektor_frame_processor_errors_total` - Total errors by type
- `detektor_frame_storage_stored_frames` - Number of frames in storage

### 3. Custom Decorators

```python
from src.shared.telemetry import traced, traced_frame, traced_method

@traced_frame("frame_id")
async def process_frame(frame_id: str, data: dict):
    # Automatically creates span with frame.id attribute
    pass

@traced
def helper_function():
    # Simple tracing decorator
    pass

@traced_method(include_self_attrs=["processor_id"])
def process_method(self, frame_id: str):
    # Method decorator with instance attributes
    pass
```

## Testing

### Automated Testing

```bash
# Run the test suite
python src/examples/telemetry_service/test_service.py
```

### Manual Testing

```bash
# Test individual endpoints
curl http://localhost:8080/health
curl -X POST http://localhost:8080/simulate

# Load testing
for i in {1..10}; do
  curl -X POST http://localhost:8080/simulate &
done
wait
```

## Development

### Project Structure

```
src/examples/telemetry_service/
├── __init__.py
├── main.py                 # FastAPI application
├── processor.py            # Frame processing logic
├── storage.py              # Storage layer
├── test_service.py         # Test suite
├── Dockerfile              # Container definition
├── docker-compose.yml      # Full stack deployment
├── prometheus.yml          # Prometheus configuration
└── grafana/
    └── provisioning/
        ├── datasources/    # Grafana datasources
        └── dashboards/     # Pre-built dashboards
```

### Key Implementation Patterns

1. **Distributed Tracing**: Using `@traced_frame` for frame ID propagation
2. **Metrics Collection**: Custom metrics for business logic
3. **Error Handling**: Comprehensive error tracking and recovery
4. **Async Processing**: Parallel AI detection tasks
5. **Health Checks**: Proper startup/shutdown lifecycle management

### Environment Variables

- `PORT` - Service port (default: 8080)
- `HOST` - Service host (default: 0.0.0.0)
- `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` - Jaeger endpoint
- `OTEL_EXPORTER_PROMETHEUS_ENDPOINT` - Prometheus endpoint
- `OTEL_SERVICE_NAME` - Service name for telemetry
- `OTEL_SERVICE_VERSION` - Service version

## Deployment

### Docker Compose (Recommended)

```bash
# Start full stack
docker-compose up -d

# View logs
docker-compose logs -f example-service

# Stop
docker-compose down
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example-service
  template:
    metadata:
      labels:
        app: example-service
    spec:
      containers:
      - name: example-service
        image: detektor/example-service:latest
        ports:
        - containerPort: 8080
        env:
        - name: OTEL_EXPORTER_OTLP_TRACES_ENDPOINT
          value: "http://jaeger:4318/v1/traces"
        - name: OTEL_EXPORTER_PROMETHEUS_ENDPOINT
          value: "http://prometheus:9090/metrics"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
```

## Monitoring

### Grafana Dashboard

The service includes a pre-built Grafana dashboard with:

- Frame processing rate
- Processing duration percentiles
- Detection rates by type
- Error rates
- Total statistics

Access: http://localhost:3000/d/example-service

### Alerts

Example Prometheus alerts:

```yaml
groups:
  - name: example-service
    rules:
      - alert: HighErrorRate
        expr: rate(detektor_frame_processor_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in frame processor"

      - alert: SlowProcessing
        expr: histogram_quantile(0.95, rate(detektor_frame_processor_processing_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Frame processing is too slow"
```

## Best Practices Demonstrated

1. **Observability First**: Built-in tracing, metrics, and monitoring
2. **Clean Architecture**: Separation of concerns (API, business logic, storage)
3. **Error Handling**: Comprehensive error tracking and recovery
4. **Testing**: Automated test suite and health checks
5. **Documentation**: Comprehensive API documentation
6. **Containerization**: Production-ready Docker setup
7. **Configuration**: Environment-based configuration
8. **Security**: Non-root user in containers
9. **Performance**: Async processing and parallel execution
10. **Monitoring**: Pre-built dashboards and alerts

## Troubleshooting

### Common Issues

1. **Service won't start**:
   - Check if port 8080 is available
   - Verify OpenTelemetry configuration
   - Check logs: `docker-compose logs example-service`

2. **No traces in Jaeger**:
   - Verify Jaeger is running: `curl http://localhost:16686`
   - Check OTLP endpoint configuration
   - Ensure network connectivity

3. **No metrics in Prometheus**:
   - Check Prometheus config: `curl http://localhost:9090/targets`
   - Verify service `/metrics` endpoint
   - Check scraping interval

4. **Dashboard not loading**:
   - Verify Grafana is running: `curl http://localhost:3000`
   - Check datasource configuration
   - Ensure dashboard is provisioned

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with additional OpenTelemetry debugging
export OTEL_LOG_LEVEL=DEBUG
export OTEL_PYTHON_LOG_CORRELATION=true
```

## Contributing

This example service serves as a template for implementing observability in detektor services. When creating new services:

1. Copy the observability patterns
2. Adapt the business logic
3. Update the metrics and tracing
4. Create appropriate dashboards
5. Add comprehensive tests

## License

This example is part of the detektor project and follows the same licensing terms.
