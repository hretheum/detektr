# Service: Frame Tracking

## 🚀 Quick Deploy (30 seconds)
```bash
git push origin main
# Watch GitHub Actions deploy automatically
```

## 📋 Detailed Steps (5 minutes)

### 1. Prerequisites
- [x] Service code in `services/frame-tracking/`
- [x] Dockerfile exists
- [x] GitHub Actions workflow exists (`.github/workflows/frame-tracking-deploy.yml`)
- [x] SOPS encrypted secrets configured

### 2. Configuration
- **Service Name**: `frame-tracking`
- **Port**: `8081`
- **Health Check**: `http://localhost:8081/health`
- **Metrics**: `http://localhost:8081/metrics`
- **Tracing**: Jaeger integration via OpenTelemetry

### 3. Deploy
```bash
# 1. Commit your changes
git add .
git commit -m "feat: deploy frame-tracking service"

# 2. Push to trigger deployment
git push origin main

# 3. Monitor deployment
# Watch GitHub Actions at: https://github.com/hretheum/detektr/actions
```

### 4. Verify Deployment
```bash
# Check service health
curl http://localhost:8081/health

# Check metrics
curl http://localhost:8081/metrics

# Check processing status
curl http://localhost:8081/processing/status

# Check logs
docker logs frame-tracking
```

## ⚙️ Configuration Options

### Environment Variables
```bash
# Required
SERVICE_NAME=frame-tracking
PORT=8081
ENVIRONMENT=production

# Optional
LOG_LEVEL=info
METRICS_ENABLED=true
TRACING_ENABLED=true
MODEL_PATH=/app/models
BATCH_SIZE=10
PROCESSING_INTERVAL=1s
```

### Docker Compose Override
```yaml
services:
  frame-tracking:
    image: ghcr.io/hretheum/detektr/frame-tracking:latest
    ports:
      - "8081:8081"
    environment:
      - SERVICE_NAME=frame-tracking
      - PORT=8081
    volumes:
      - ./models:/app/models
      - ./uploads:/app/uploads
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Model Loading Failed
**Symptoms**: Service starts but processing fails
**Solution**:
```bash
# Check model files
docker exec frame-tracking ls -la /app/models/

# Verify model permissions
docker exec frame-tracking chmod 644 /app/models/*

# Check model format
docker exec frame-tracking python -c "import tensorflow as tf; print(tf.__version__)"
```

#### 2. Processing Queue Full
**Symptoms**: High memory usage, slow processing
**Solution**:
```bash
# Check queue size
curl http://localhost:8081/processing/queue

# Reduce batch size
# Edit docker-compose.yml:
environment:
  - BATCH_SIZE=5

# Restart service
git add docker-compose.yml
git commit -m "fix: reduce batch size"
git push origin main
```

#### 3. Frame Rate Too Low
**Symptoms**: Processing slower than expected
**Solution**:
```bash
# Check CPU usage
docker stats frame-tracking

# Check processing time
curl http://localhost:8081/processing/metrics

# Optimize processing
# Edit docker-compose.yml:
environment:
  - PROCESSING_INTERVAL=500ms
  - BATCH_SIZE=8
```

#### 4. Memory Usage High
**Symptoms**: Memory usage > 80%
**Solution**:
```bash
# Check memory usage
docker stats frame-tracking

# Reduce model size
# Use smaller model variant
environment:
  - MODEL_TYPE=lightweight

# Restart with new config
git add docker-compose.yml
git commit -m "fix: use lightweight model"
git push origin main
```

#### 5. Metrics Not Showing
**Symptoms**: Prometheus doesn't show service metrics
**Solution**:
```bash
# Verify metrics endpoint
curl http://localhost:8081/metrics

# Check service discovery
# Visit: http://nebula:9090/targets

# Verify service name in metrics
curl http://localhost:8081/metrics | grep frame_tracking_
```

## 🔄 Rollback Procedures

### Quick Rollback
```bash
# Revert last commit
git revert HEAD
git push origin main

# Manual rollback
docker-compose -f docker-compose.frame-tracking.yml down
docker-compose -f docker-compose.frame-tracking.yml up -d [previous-version]
```

### Emergency Procedures
```bash
# Stop service immediately
docker stop frame-tracking

# Rollback to last known good
docker-compose -f docker-compose.frame-tracking.yml up -d [previous-tag]

# Verify rollback
curl http://localhost:8081/health
```

## 📊 Monitoring

### Key Metrics to Watch
- **Service Health**: `http://localhost:8081/health`
- **Processing Status**: `http://localhost:8081/processing/status`
- **Processing Rate**: `frames_processed_per_second`
- **Queue Size**: `processing_queue_size`
- **Memory Usage**: `memory_usage_bytes`
- **Model Load Time**: `model_load_duration_seconds`
- **Prometheus Metrics**: `http://nebula:9090`
- **Jaeger Tracing**: `http://nebula:16686`
- **Grafana Dashboard**: `http://nebula:3000`

### Alerting Rules
```yaml
# Processing queue full
- alert: FrameTrackingQueueFull
  expr: processing_queue_size > 100

# High memory usage
- alert: FrameTrackingHighMemory
  expr: memory_usage_percent{service="frame-tracking"} > 80

# Model loading failed
- alert: FrameTrackingModelLoadFailed
  expr: model_load_status == 0

# Service down
- alert: FrameTrackingServiceDown
  expr: up{service="frame-tracking"} == 0
```

## 🎯 Service-Specific Features

### Processing Management
```bash
# Check current processing
curl http://localhost:8081/processing/info

# Restart processing
curl -X POST http://localhost:8081/processing/restart

# Change processing settings
curl -X POST http://localhost:8081/processing/config \
  -d "batch_size=15&interval=2s"
```

### Model Management
```bash
# List available models
curl http://localhost:8081/models

# Switch model
curl -X POST http://localhost:8081/models/switch \
  -d "model_name=yolov8n.pt"

# Update model
curl -X POST http://localhost:8081/models/update \
  -d "model_url=https://models.example.com/new-model.pt"
```

## 📚 Examples

### Real Deployment Example
```bash
# Deploy with custom model
export MODEL_PATH=/app/models/custom-model.pt
git add .
git commit -m "feat: deploy frame-tracking with custom model"
git push origin main
```

### Testing Different Models
```bash
# Test model before deployment
docker run -it --rm \
  -e MODEL_PATH=/app/models/test-model.pt \
  ghcr.io/hretheum/detektr/frame-tracking:latest
```

### Batch Processing Optimization
```bash
# Optimize for high throughput
# Edit docker-compose.yml:
environment:
  - BATCH_SIZE=20
  - PROCESSING_INTERVAL=500ms
  - WORKER_THREADS=4
