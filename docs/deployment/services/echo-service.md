# Service: Echo Service

## 🚀 Quick Deploy (Unified Pipeline)

### Automatyczny deployment
```bash
# Deploy przy push do main
git push origin main
```

### Manualny deployment
```bash
# Deploy tylko tego serwisu
gh workflow run main-pipeline.yml -f services=echo-service

# Lub użyj skryptu pomocniczego
./scripts/deploy.sh production deploy
```

## 📋 Configuration

### Podstawowe informacje
- **Service Name**: `echo-service`
- **Port**: `8007` (zobacz [PORT_ALLOCATION.md](../PORT_ALLOCATION.md))
- **Registry**: `ghcr.io/hretheum/detektr/echo-service`
- **Health Check**: `http://localhost:8007/health`
- **Metrics**: `http://localhost:8007/metrics`
- **Purpose**: Prosty serwis echo do testowania infrastruktury

### Docker Compose Entry
```yaml
# W pliku docker/base/docker-compose.yml
services:
  echo-service:
    image: ghcr.io/hretheum/detektr/echo-service:latest
    container_name: echo-service
    ports:
      - "8007:8007"
    environment:
      - SERVICE_NAME=echo-service
      - PORT=8007
      - ECHO_DELAY_MS=${ECHO_DELAY_MS:-0}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8007/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - detektor-network
```

### Environment Variables
```bash
# Required
SERVICE_NAME=echo-service
PORT=8007

# Optional
LOG_LEVEL=info
METRICS_ENABLED=true
TRACING_ENABLED=true
ECHO_DELAY_MS=0        # Artificial delay for testing
ECHO_PREFIX=""         # Prefix for echo responses
MAX_ECHO_SIZE=1048576  # Max size of echo payload (1MB)
```

## 🔧 API Endpoints

### Echo endpoint
```bash
# Simple echo
curl -X POST http://localhost:8007/echo \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello World"}'

# Response:
{
  "echo": {
    "message": "Hello World"
  },
  "timestamp": "2024-07-25T10:00:00Z",
  "service": "echo-service"
}
```

### Test endpoints
```bash
# Test latency
curl http://localhost:8007/test/latency?delay=100

# Test error
curl http://localhost:8007/test/error?code=500

# Test timeout
curl http://localhost:8007/test/timeout?seconds=5
```

## 🔧 Deployment Methods

### 1. Production deployment (ZALECANE)
```bash
# Automatyczny deployment przy push do main
git add .
git commit -m "feat: update echo-service configuration"
git push origin main
```

### 2. Manual deployment via workflow
```bash
# Build i deploy
gh workflow run main-pipeline.yml -f services=echo-service

# Tylko build
gh workflow run main-pipeline.yml -f action=build-only -f services=echo-service

# Tylko deploy (używa latest z registry)
gh workflow run main-pipeline.yml -f action=deploy-only -f services=echo-service
```

## 🧪 Testing Infrastructure

### Load testing
```bash
# Test with Apache Bench
ab -n 1000 -c 10 -p payload.json -T application/json \
  http://localhost:8007/echo

# Test with curl in loop
for i in {1..100}; do
  curl -s -X POST http://localhost:8007/echo \
    -d "{\"test\": $i}" \
    -H "Content-Type: application/json"
done
```

### Tracing test
```bash
# Send request with trace header
curl -X POST http://localhost:8007/echo \
  -H "Content-Type: application/json" \
  -H "X-Trace-ID: test-trace-123" \
  -d '{"trace": "test"}'

# Check trace in Jaeger
# http://nebula:16686/search?service=echo-service
```

## 📊 Monitoring

### Metrics
```promql
# Request rate
rate(echo_service_requests_total[5m])

# Echo payload sizes
histogram_quantile(0.95, rate(echo_service_payload_bytes_bucket[5m]))

# Error rate
rate(echo_service_errors_total[5m])
```

### Use Cases
1. **Testing deployment pipeline** - Prosty serwis do weryfikacji CI/CD
2. **Network latency testing** - Pomiar opóźnień między serwisami
3. **Load testing target** - Endpoint do testów obciążeniowych
4. **Tracing verification** - Sprawdzanie propagacji trace headers
5. **Health check testing** - Weryfikacja mechanizmów health check

## 🔧 Troubleshooting

### Service returns 413 Payload Too Large
```bash
# Zwiększ limit
docker exec echo-service \
  sh -c 'export MAX_ECHO_SIZE=10485760 && kill -HUP 1'

# Lub zrestartuj z nową konfiguracją
docker-compose up -d echo-service
```

### High latency
```bash
# Sprawdź czy nie ma ustawionego ECHO_DELAY_MS
docker inspect echo-service | grep ECHO_DELAY_MS

# Sprawdź metryki
curl http://localhost:8007/metrics | grep echo_service_request_duration
```

## 🔗 Related Services
- [Base Template](./base-template.md) - Bazowy template
- [Example OTEL](./example-otel.md) - Przykład z OpenTelemetry
