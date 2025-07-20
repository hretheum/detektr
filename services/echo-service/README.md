# Echo Service

A simple service demonstrating request/response patterns with full observability. This service shows how to implement a stateless API with all required patterns.

## Features

- ✅ Full observability (OpenTelemetry tracing, Prometheus metrics, structured logging)
- ✅ Health checks with feature flags
- ✅ Correlation ID propagation
- ✅ Multiple endpoints demonstrating different patterns
- ✅ Proper error handling with correlation IDs
- ✅ Artificial delay support for testing
- ✅ No database dependencies - pure stateless service

## API Endpoints

### Core Endpoints

- `POST /api/v1/echo` - Reverses the input message
- `POST /api/v1/shout` - Returns the message in uppercase
- `GET /api/v1/ping` - Simple ping/pong endpoint

### Monitoring

- `GET /health` - Health check with feature flags
- `GET /metrics` - Prometheus metrics
- `GET /` - Service info and available endpoints

## Request/Response Examples

### Echo
```bash
curl -X POST http://localhost:8007/api/v1/echo \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello World", "delay_ms": 100}'

# Response:
{
  "message": "Hello World",
  "echo_message": "dlroW olleH",
  "timestamp": "2025-01-20T12:00:00",
  "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
  "metadata": {},
  "processing_time_ms": 100.5
}
```

### Shout
```bash
curl -X POST http://localhost:8007/api/v1/shout \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'

# Response:
{
  "message": "hello",
  "echo_message": "HELLO",
  "timestamp": "2025-01-20T12:00:00",
  "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
  "metadata": {"shouted": true},
  "processing_time_ms": 0.5
}
```

## Environment Variables

- `SERVICE_NAME` - Name of the service (default: echo-service)
- `SERVICE_VERSION` - Version (default: 0.1.0)
- `PORT` - HTTP port (default: 8007)
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry collector endpoint
- `LOG_LEVEL` - Logging level (default: info)

## Testing

```bash
# Health check
curl http://localhost:8007/health

# Metrics
curl http://localhost:8007/metrics | grep echo_service

# Load test with delays
for i in {1..100}; do
  curl -X POST http://localhost:8007/api/v1/echo \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"test-$i\", \"delay_ms\": 50}" &
done
```
EOF < /dev/null
