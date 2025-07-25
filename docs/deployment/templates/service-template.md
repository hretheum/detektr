# Service: [SERVICE_NAME]

## 🚀 Quick Deploy (Unified Pipeline)

### Automatyczny deployment
```bash
# Deploy przy push do main
git push origin main
```

### Manualny deployment
```bash
# Deploy tylko tego serwisu
gh workflow run main-pipeline.yml -f services=[service-name]

# Lub użyj skryptu pomocniczego
./scripts/deploy.sh production deploy
```

## 📋 Configuration

### Podstawowe informacje
- **Service Name**: `[service-name]`
- **Port**: `[allocated-port]` (zobacz [PORT_ALLOCATION.md](../PORT_ALLOCATION.md))
- **Registry**: `ghcr.io/hretheum/detektr/[service-name]`
- **Health Check**: `http://localhost:[port]/health`
- **Metrics**: `http://localhost:[port]/metrics`

### Prerequisites
- [ ] Service code in `services/[service-name]/`
- [ ] Dockerfile exists
- [ ] Entry in docker-compose (base lub features)
- [ ] Port allocated in PORT_ALLOCATION.md

### Docker Compose Entry
```yaml
# W pliku docker/base/docker-compose.yml lub odpowiednim feature
services:
  [service-name]:
    image: ghcr.io/hretheum/detektr/[service-name]:latest
    container_name: [service-name]
    ports:
      - "[allocated-port]:[allocated-port]"
    environment:
      - SERVICE_NAME=[service-name]
      - PORT=[allocated-port]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:[port]/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - detektor-network
```

## ⚙️ Configuration Options

### Environment Variables
```bash
# Required
SERVICE_NAME=[service-name]
PORT=[port]
ENVIRONMENT=production

# Optional
LOG_LEVEL=info
METRICS_ENABLED=true
TRACING_ENABLED=true
```

## 🔧 Deployment Methods

### 1. Production deployment (ZALECANE)
```bash
# Automatyczny deployment przy push do main
git add .
git commit -m "feat: update [service-name]"
git push origin main
```

### 2. Manual deployment via workflow
```bash
# Build i deploy
gh workflow run main-pipeline.yml -f services=[service-name]

# Tylko build
gh workflow run main-pipeline.yml -f action=build-only -f services=[service-name]

# Tylko deploy (używa latest z registry)
gh workflow run main-pipeline.yml -f action=deploy-only -f services=[service-name]
```

### 3. Local development
```bash
# Development environment
cd /opt/detektor
./docker/dev.sh up [service-name]

# Logi
./docker/dev.sh logs -f [service-name]
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Service Won't Start
**Symptoms**: Deployment fails in GitHub Actions
**Solution**:
```bash
# Check service logs
docker logs [service-name]

# Verify configuration
docker inspect [service-name]
```

#### 2. Health Check Fails
**Symptoms**: Service starts but health check fails
**Solution**:
```bash
# Test health endpoint
curl -v http://localhost:[PORT]/health

# Check service logs for errors
docker logs [service-name] --tail 50
```

#### 3. Metrics Not Showing
**Symptoms**: Prometheus doesn't show service metrics
**Solution**:
```bash
# Verify metrics endpoint
curl http://localhost:[PORT]/metrics

# Check service discovery
# Visit: http://nebula:9090/targets
```

#### 4. Tracing Missing
**Symptoms**: No traces in Jaeger
**Solution**:
```bash
# Verify tracing configuration
docker inspect [service-name] | grep JAEGER

# Check service logs for tracing errors
docker logs [service-name] | grep jaeger
```

## 🔄 Rollback Procedures

### Quick Rollback
```bash
# Poprzez Git
git revert HEAD
git push origin main

# Poprzez Docker (emergency)
docker pull ghcr.io/hretheum/detektr/[service-name]:[previous-tag]
docker stop [service-name]
docker run -d --name [service-name] ghcr.io/hretheum/detektr/[service-name]:[previous-tag]
```

### Weryfikacja po rollback
```bash
# Health check
curl http://localhost:[PORT]/health

# Logi
docker logs [service-name] --tail 50

# Metryki
curl http://localhost:[PORT]/metrics
```

## 📊 Monitoring

### Key Metrics to Watch
- **Service Health**: `http://localhost:[PORT]/health`
- **Prometheus Metrics**: `http://nebula:9090`
- **Jaeger Tracing**: `http://nebula:16686`
- **Grafana Dashboard**: `http://nebula:3000`

### Alerting Rules
```yaml
# Memory usage > 80%
- alert: [SERVICE_NAME]HighMemory
  expr: memory_usage_percent{service="[service-name]"} > 80

# CPU usage > 90% for 5 minutes
- alert: [SERVICE_NAME]HighCPU
  expr: cpu_usage_percent{service="[service-name]"} > 90

# Service down
- alert: [SERVICE_NAME]Down
  expr: up{service="[service-name]"} == 0
```

## 📚 Examples

### Real Services Using This Template
- [RTSP Capture Service](../services/rtsp-capture.md)
- [Frame Tracking Service](../services/frame-tracking.md)

### Customization Guide
1. **Replace placeholders** with actual values
2. **Add service-specific** configuration
3. **Include service-specific** troubleshooting
4. **Update links** to actual resources
