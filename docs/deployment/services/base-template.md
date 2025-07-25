# Service: Base Template

## 🚀 Quick Deploy (Unified Pipeline)

### Automatyczny deployment
```bash
# Deploy przy push do main
git push origin main
```

### Manualny deployment
```bash
# Deploy tylko tego serwisu
gh workflow run main-pipeline.yml -f services=base-template

# Lub użyj skryptu pomocniczego
./scripts/deploy.sh production deploy
```

## 📋 Configuration

### Podstawowe informacje
- **Service Name**: `base-template`
- **Port**: `8000` (zobacz [PORT_ALLOCATION.md](../PORT_ALLOCATION.md))
- **Registry**: `ghcr.io/hretheum/detektr/base-template`
- **Health Check**: `http://localhost:8000/health`
- **Metrics**: `http://localhost:8000/metrics`
- **Purpose**: Template/przykład dla nowych serwisów

### Docker Compose Entry
```yaml
# W pliku docker/base/docker-compose.yml
services:
  base-template:
    image: ghcr.io/hretheum/detektr/base-template:latest
    container_name: base-template
    ports:
      - "8000:8000"
    environment:
      - SERVICE_NAME=base-template
      - PORT=8000
      - LOG_LEVEL=${LOG_LEVEL:-info}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
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
SERVICE_NAME=base-template
PORT=8000

# Optional
LOG_LEVEL=info
METRICS_ENABLED=true
TRACING_ENABLED=true
ENVIRONMENT=production
```

## 🔧 Deployment Methods

### 1. Production deployment (ZALECANE)
```bash
# Automatyczny deployment przy push do main
git add .
git commit -m "feat: update base-template"
git push origin main
```

### 2. Manual deployment via workflow
```bash
# Build i deploy
gh workflow run main-pipeline.yml -f services=base-template

# Tylko build
gh workflow run main-pipeline.yml -f action=build-only -f services=base-template

# Tylko deploy (używa latest z registry)
gh workflow run main-pipeline.yml -f action=deploy-only -f services=base-template
```

### 3. Jako template dla nowego serwisu
```bash
# Skopiuj strukturę
cp -r services/base-template services/my-new-service

# Dostosuj konfigurację
cd services/my-new-service
# ... edytuj pliki ...

# Deploy nowego serwisu
git add .
git commit -m "feat: add my-new-service based on template"
git push origin main
```

## 🔧 Troubleshooting

### Service nie startuje
```bash
# Sprawdź logi
docker logs base-template --tail 50

# Sprawdź konfigurację
docker inspect base-template | jq '.[0].Config'

# Test ręczny
docker run -it --rm \
  -e SERVICE_NAME=base-template \
  -e PORT=8000 \
  ghcr.io/hretheum/detektr/base-template:latest
```

## 📊 Monitoring

### Basic Metrics
```promql
# Service health
up{job="base-template"}

# HTTP requests
rate(http_requests_total{service="base-template"}[5m])

# Response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="base-template"}[5m]))
```

### Template Features
- ✅ Health checks (`/health`)
- ✅ Prometheus metrics (`/metrics`)
- ✅ OpenTelemetry tracing
- ✅ Structured logging
- ✅ Graceful shutdown
- ✅ Configuration via env vars

## 🎯 Użycie jako template

### 1. Struktura katalogów
```
services/base-template/
├── Dockerfile
├── requirements.txt
├── main.py
├── health.py
├── metrics.py
└── config.py
```

### 2. Minimalne zmiany dla nowego serwisu
1. Zmień `SERVICE_NAME` w config.py
2. Dodaj swoją logikę biznesową w main.py
3. Zaktualizuj requirements.txt
4. Dostosuj Dockerfile jeśli potrzeba

### 3. Przykład rozszerzenia
```python
# main.py
from base_template import app, health, metrics

# Dodaj własne endpointy
@app.route('/api/v1/process', methods=['POST'])
@metrics.track_request
async def process_data(request):
    # Twoja logika
    return {"status": "processed"}
```

## 🔗 Related Documentation
- [Adding New Service Guide](../guides/new-service.md)
- [Service Architecture](../../architecture/services/README.md)
- [Python Service Standards](../../standards/python-services.md)
