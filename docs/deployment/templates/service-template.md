# Service: [SERVICE_NAME]

## 🚀 Quick Deploy (30 seconds)
```bash
git push origin main
# Watch GitHub Actions deploy automatically
```

## 📋 Detailed Steps (5 minutes)

### 1. Prerequisites
- [ ] Service code in `services/[service-name]/`
- [ ] Dockerfile exists
- [ ] GitHub Actions workflow exists (`.github/workflows/[service-name]-deploy.yml`)
- [ ] SOPS encrypted secrets configured

### 2. Configuration
- **Service Name**: `[SERVICE_NAME]`
- **Port**: `[PORT]`
- **Health Check**: `http://localhost:[PORT]/health`
- **Metrics**: `http://localhost:[PORT]/metrics`
- **Tracing**: Jaeger integration via OpenTelemetry

### 3. Deploy
```bash
# 1. Commit your changes
git add .
git commit -m "feat: deploy [SERVICE_NAME] service"

# 2. Push to trigger deployment
git push origin main

# 3. Monitor deployment
# Watch GitHub Actions logs
```

### 4. Verify Deployment
```bash
# Check service health
curl http://localhost:[PORT]/health

# Check metrics
curl http://localhost:[PORT]/metrics

# Check logs
docker logs [service-name]
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

### Docker Compose Override
```yaml
services:
  [service-name]:
    image: ghcr.io/hretheum/detektr/[service-name]:latest
    ports:
      - "[port]:[port]"
    environment:
      - SERVICE_NAME=[service-name]
      - PORT=[port]
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
# Revert last commit
git revert HEAD
git push origin main

# Manual rollback
docker-compose -f docker-compose.[service-name].yml down
docker-compose -f docker-compose.[service-name].yml up -d [previous-version]
```

### Emergency Procedures
```bash
# Stop service immediately
docker stop [service-name]

# Rollback to last known good
docker-compose -f docker-compose.[service-name].yml up -d [previous-tag]

# Verify rollback
curl http://localhost:[PORT]/health
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
