# Service: RTSP Capture

## 🚀 Quick Deploy (Unified Pipeline)

### Automatyczny deployment
```bash
# Deploy przy push do main
git push origin main
```

### Manualny deployment
```bash
# Deploy tylko tego serwisu
gh workflow run main-pipeline.yml -f services=rtsp-capture

# Lub użyj skryptu pomocniczego
./scripts/deploy.sh production deploy
```

## 📋 Configuration

### Podstawowe informacje
- **Service Name**: `rtsp-capture`
- **Port**: `8080` (zobacz [PORT_ALLOCATION.md](../PORT_ALLOCATION.md))
- **Registry**: `ghcr.io/hretheum/detektr/rtsp-capture`
- **Health Check**: `http://localhost:8080/health`
- **Metrics**: `http://localhost:8080/metrics`
- **Specific Endpoints**:
  - Stream status: `http://localhost:8080/stream/status`
  - Stream info: `http://localhost:8080/stream/info`

### Docker Compose Entry
```yaml
# W pliku docker/base/docker-compose.yml
services:
  rtsp-capture:
    image: ghcr.io/hretheum/detektr/rtsp-capture:latest
    container_name: rtsp-capture
    ports:
      - "8080:8080"
    environment:
      - SERVICE_NAME=rtsp-capture
      - PORT=8080
      - RTSP_URL=${RTSP_URL}
      - STREAM_QUALITY=${STREAM_QUALITY:-high}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    volumes:
      - ./recordings:/app/recordings
    networks:
      - detektor-network
```

## ⚙️ Configuration Options

### Environment Variables
```bash
# Required
RTSP_URL=rtsp://user:pass@camera-ip:554/stream
SERVICE_NAME=rtsp-capture
PORT=8080
ENVIRONMENT=production

# Optional
LOG_LEVEL=info
METRICS_ENABLED=true
TRACING_ENABLED=true
RECORDING_ENABLED=false
STREAM_QUALITY=high
```

## 🔧 Deployment Methods

### 1. Production deployment (ZALECANE)
```bash
# Automatyczny deployment przy push do main
git add .
git commit -m "feat: update rtsp-capture configuration"
git push origin main
```

### 2. Manual deployment via workflow
```bash
# Build i deploy
gh workflow run main-pipeline.yml -f services=rtsp-capture

# Tylko build
gh workflow run main-pipeline.yml -f action=build-only -f services=rtsp-capture

# Tylko deploy (używa latest z registry)
gh workflow run main-pipeline.yml -f action=deploy-only -f services=rtsp-capture
```

### 3. Local development
```bash
# Development environment
cd /opt/detektor
./docker/dev.sh up rtsp-capture

# Logi
./docker/dev.sh logs -f rtsp-capture
```

## 🔧 Troubleshooting

### Common Issues

#### 1. RTSP Connection Failed
**Symptoms**: Service starts but stream connection fails
**Solution**:
```bash
# Check RTSP URL format
docker logs rtsp-capture | grep "RTSP connection"

# Test RTSP URL manually
ffmpeg -i rtsp://user:pass@camera-ip:554/stream -t 1 -f null -

# Verify credentials
echo "rtsp://user:pass@camera-ip:554/stream" | base64
```

#### 2. Service Won't Start
**Symptoms**: Deployment fails in GitHub Actions
**Solution**:
```bash
# Check service logs
docker logs rtsp-capture

# Verify configuration
docker inspect rtsp-capture

# Check port availability
netstat -tlnp | grep 8080
```

#### 3. Health Check Fails
**Symptoms**: Service starts but health check fails
**Solution**:
```bash
# Test health endpoint
curl -v http://localhost:8080/health

# Check service logs for errors
docker logs rtsp-capture --tail 50

# Verify RTSP stream is accessible
curl http://localhost:8080/stream/status
```

#### 4. Metrics Not Showing
**Symptoms**: Prometheus doesn't show service metrics
**Solution**:
```bash
# Verify metrics endpoint
curl http://localhost:8080/metrics

# Check service discovery
# Visit: http://nebula:9090/targets

# Verify service name in metrics
curl http://localhost:8080/metrics | grep rtsp_capture_
```

#### 5. Tracing Missing
**Symptoms**: No traces in Jaeger
**Solution**:
```bash
# Verify tracing configuration
docker inspect rtsp-capture | grep JAEGER

# Check service logs for tracing errors
docker logs rtsp-capture | grep jaeger

# Verify Jaeger endpoint is reachable
curl http://nebula:14268/api/traces
```

## 🔄 Rollback Procedures

### Quick Rollback
```bash
# Revert last commit
git revert HEAD
git push origin main

# Manual rollback
docker-compose -f docker-compose.rtsp.yml down
docker-compose -f docker-compose.rtsp.yml up -d [previous-version]
```

### Emergency Procedures
```bash
# Stop service immediately
docker stop rtsp-capture

# Rollback to last known good
docker-compose -f docker-compose.rtsp.yml up -d [previous-tag]

# Verify rollback
curl http://localhost:8080/health
```

## 📊 Monitoring

### Key Metrics to Watch
- **Service Health**: `http://localhost:8080/health`
- **Stream Status**: `http://localhost:8080/stream/status`
- **RTSP Connection**: `rtsp_connection_status`
- **Frame Rate**: `frames_per_second`
- **Memory Usage**: `memory_usage_bytes`
- **Prometheus Metrics**: `http://nebula:9090`
- **Jaeger Tracing**: `http://nebula:16686`
- **Grafana Dashboard**: `http://nebula:3000`

### Alerting Rules
```yaml
# RTSP connection lost
- alert: RTSPConnectionLost
  expr: rtsp_connection_status == 0

# High memory usage
- alert: RTSPHighMemory
  expr: memory_usage_percent{service="rtsp-capture"} > 80

# High CPU usage
- alert: RTSPHighCPU
  expr: cpu_usage_percent{service="rtsp-capture"} > 90

# Service down
- alert: RTSPServiceDown
  expr: up{service="rtsp-capture"} == 0
```

## 🎯 Service-Specific Features

### RTSP Stream Management
```bash
# Check current stream
curl http://localhost:8080/stream/info

# Restart stream
curl -X POST http://localhost:8080/stream/restart

# Change quality
curl -X POST http://localhost:8080/stream/quality -d "quality=medium"
```

### Recording Capabilities
```bash
# Start recording
curl -X POST http://localhost:8080/recording/start

# Stop recording
curl -X POST http://localhost:8080/recording/stop

# List recordings
curl http://localhost:8080/recordings
```

## 📚 Examples

### Real Deployment Example
```bash
# Deploy with custom RTSP URL
export RTSP_URL="rtsp://admin:password@192.168.1.100:554/stream1"
git add .
git commit -m "feat: deploy rtsp-capture with new camera"
git push origin main
```

### Testing Different RTSP URLs
```bash
# Test RTSP URL before deployment
docker run -it --rm \
  -e RTSP_URL="rtsp://user:pass@camera-ip:554/stream" \
  ghcr.io/hretheum/detektr/rtsp-capture:latest
