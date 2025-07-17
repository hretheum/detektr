# BaseService Implementation Guide

## Overview

The `BaseService` class provides a foundation for all microservices in the Detektor system. It includes:

- Built-in health checks and readiness probes
- Automatic telemetry (tracing, metrics)
- Graceful shutdown handling
- Consistent API structure
- Lifecycle management

## Usage

### Creating a Service

```python
from src.shared.base_service import BaseService

class MyService(BaseService):
    def __init__(self):
        super().__init__(
            name="my-service",
            version="1.0.0",
            port=8001,
            description="My awesome service"
        )

    def setup_routes(self):
        """Add custom routes."""
        super().setup_routes()  # Important: call parent

        @self.app.get("/custom")
        async def custom_endpoint():
            return {"hello": "world"}

    async def start(self):
        """Custom startup logic."""
        await super().start()  # Important: call parent
        # Your startup code here

    async def stop(self):
        """Custom shutdown logic."""
        # Your cleanup code here
        await super().stop()  # Important: call parent
```

### Running a Service

```python
import asyncio

async def main():
    service = MyService()
    await service.run()  # Handles signals automatically

if __name__ == "__main__":
    asyncio.run(main())
```

## Built-in Endpoints

Every service automatically provides:

### `/health`
Health check endpoint for container orchestration.

**Response (200 OK)**:
```json
{
    "status": "healthy",
    "service": "my-service",
    "version": "1.0.0",
    "timestamp": "2024-01-01T12:00:00"
}
```

**Response (503 Service Unavailable)**:
```json
{
    "status": "unhealthy",
    "service": "my-service",
    "version": "1.0.0",
    "timestamp": "2024-01-01T12:00:00"
}
```

### `/ready`
Readiness probe for load balancers.

**Response (200 OK)**:
```json
{
    "ready": true,
    "service": "my-service",
    "status": "running"
}
```

### `/metrics`
Prometheus metrics endpoint.

```
# HELP detektor_my_service_frames_processed_total Total frames processed
# TYPE detektor_my_service_frames_processed_total counter
detektor_my_service_frames_processed_total 1234.0
```

### `/info`
Service information endpoint.

```json
{
    "name": "my-service",
    "version": "1.0.0",
    "description": "My awesome service",
    "status": "running",
    "uptime": 3600.5,
    "environment": "production",
    "port": 8001
}
```

## Telemetry

### Tracing

Use the built-in tracer:

```python
async def process_frame(self, frame):
    with self.tracer.start_as_current_span("process_frame") as span:
        span.set_attribute("frame.id", frame.id)
        # Process frame
```

### Metrics

Use the built-in metrics client:

```python
# Increment counter
self.metrics.increment_frames_processed()

# Record duration
self.metrics.record_processing_time("detection", 0.123)

# Record error
self.metrics.increment_errors("timeout")
```

## Lifecycle Management

### Service States

```python
from src.shared.base_service import ServiceStatus

# Available states:
ServiceStatus.STOPPED    # Initial state
ServiceStatus.STARTING   # During startup
ServiceStatus.RUNNING    # Normal operation
ServiceStatus.STOPPING   # During shutdown
ServiceStatus.ERROR      # Error state
```

### Signal Handling

The service automatically handles:
- `SIGTERM`: Graceful shutdown
- `SIGINT` (Ctrl+C): Graceful shutdown

```python
# Signals trigger the stop() method
# Override stop() for custom cleanup
async def stop(self):
    # Close connections
    await self.db.close()

    # Cancel background tasks
    self.task.cancel()

    # Call parent
    await super().stop()
```

## Best Practices

### 1. Always Call Parent Methods

```python
async def start(self):
    await super().start()  # Sets up telemetry, status
    # Your code here

async def stop(self):
    # Your cleanup here
    await super().stop()  # Shuts down properly
```

### 2. Use Built-in Telemetry

```python
@traced(span_name="custom_operation")
async def do_something(self):
    # Automatically traced
    pass
```

### 3. Handle Errors Gracefully

```python
try:
    # Risky operation
    result = await external_api.call()
except Exception as e:
    self.metrics.increment_errors("external_api")
    # Don't crash the service
    return None
```

### 4. Implement Health Checks

Override the health endpoint for custom checks:

```python
def setup_routes(self):
    super().setup_routes()

    @self.app.get("/health")
    async def custom_health():
        # Check dependencies
        db_ok = await self.check_database()
        cache_ok = await self.check_cache()

        if not (db_ok and cache_ok):
            return Response(status_code=503)

        return {"status": "healthy", "db": db_ok, "cache": cache_ok}
```

## Testing

### Unit Testing

```python
from src.shared.base_service import BaseService

def test_service_initialization():
    service = MyService()
    assert service.name == "my-service"
    assert service.status == ServiceStatus.STOPPED
```

### Integration Testing

```python
from fastapi.testclient import TestClient

def test_health_endpoint():
    service = MyService()
    client = TestClient(service.app)

    response = client.get("/health")
    assert response.status_code == 503  # Not running yet
```

## Configuration

### Environment Variables

Services automatically read:
- `ENVIRONMENT`: deployment environment
- `LOG_LEVEL`: logging level
- `OTLP_ENDPOINT`: telemetry endpoint

### Port Configuration

```python
# From environment
port = int(os.getenv("SERVICE_PORT", "8001"))

# Or hardcoded
super().__init__(port=8001)
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run service
CMD ["python", "-m", "src.services.my_service"]
```

### Kubernetes

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  ports:
    - port: 8001
      name: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  template:
    spec:
      containers:
        - name: my-service
          image: my-service:latest
          ports:
            - containerPort: 8001
          livenessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8001
            initialDelaySeconds: 5
            periodSeconds: 5
```

## Troubleshooting

### Service Won't Start
- Check port conflicts
- Verify telemetry endpoint is reachable
- Check logs for startup errors

### Health Check Failing
- Ensure service.status is RUNNING
- Check dependent services
- Verify network connectivity

### Metrics Not Appearing
- Check /metrics endpoint manually
- Verify Prometheus scraping
- Ensure metrics are being recorded
