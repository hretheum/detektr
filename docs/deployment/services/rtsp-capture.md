# Service: RTSP Capture

## 🚀 Quick Deploy (30 seconds)
```bash
git push origin main
# Watch GitHub Actions deploy automatically
```

## 📋 Detailed Steps (5 minutes)

### 1. Prerequisites
- [x] Service code in `services/rtsp-capture/`
- [x] Dockerfile exists
- [x] GitHub Actions workflow exists (`.github/workflows/rtsp-capture-deploy.yml`)
- [x] SOPS encrypted secrets configured

### 2. Configuration
- **Service Name**: `rtsp-capture`
- **Port**: `8080`
- **Health Check**: `http://localhost:8080/health`
- **Metrics**: `http://localhost:8080/metrics`
- **Tracing**: Jaeger integration via OpenTelemetry

### 3. Deploy
```bash
# 1. Commit your changes
git add .
git commit -m "feat: deploy rtsp-capture service"

# 2. Push to trigger deployment
git push origin main

# 3. Monitor deployment
# Watch GitHub Actions at: https://github.com/hretheum/bezrobocie-detektor/actions
```

### 4. Verify Deployment
```bash
# Check service health
curl http://localhost:8080/health

# Check metrics
curl http://localhost:8080/metrics

# Check RTSP stream status
curl http://localhost:8080/stream/status

# Check logs
docker logs rtsp-capture
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

### Docker Compose Override
```yaml
services:
  rtsp-capture:
    image: ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest
    ports:
      - "8080:8080"
    environment:
      - RTSP_URL=rtsp://user:pass@camera-ip:554/stream
      - SERVICE_NAME=rtsp-capture
      - PORT=8080
    volumes:
      - ./recordings:/app/recordings
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
  ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest
