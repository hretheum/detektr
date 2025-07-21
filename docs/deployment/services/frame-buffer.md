# Service: Frame Buffer

## 🚀 Quick Deploy (30 seconds)
```bash
git push origin main
# Watch GitHub Actions deploy automatically
```

## 📋 Detailed Steps (5 minutes)

### 1. Prerequisites
- [x] Frame buffer code implemented in Phase 2 ✅
- [x] Redis service configured ✅
- [x] Dockerfile exists for frame-buffer service ✅
- [x] GitHub Actions workflow exists (frame-buffer-deploy.yml) ✅
- [x] SOPS encrypted secrets configured ✅

### 2. Configuration
- **Service Name**: `frame-buffer`
- **Port**: `8002`
- **Health Check**: `http://localhost:8002/health`
- **Metrics**: `http://localhost:8002/metrics`
- **Dependencies**: Redis (port 6379)
- **Tracing**: Jaeger integration via OpenTelemetry

### 3. Deploy {#deploy}
```bash
# 1. Commit your changes
git add .
git commit -m "feat: deploy frame-buffer service with Redis"

# 2. Push to trigger deployment
git push origin main

# 3. Monitor deployment
# Watch GitHub Actions at: https://github.com/hretheum/bezrobocie-detektor/actions
```

### 4. Verify Deployment
```bash
# Check service health
curl http://nebula:8002/health

# Check metrics
curl http://nebula:8002/metrics

# Check Redis connection
ssh nebula "docker exec redis redis-cli ping"

# Check frame queue
ssh nebula "docker exec redis redis-cli XINFO STREAM frame_queue"
```

## 🔧 Configuration {#configuration}

### Redis Configuration
The frame buffer requires Redis with the following settings:

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --maxmemory 4gb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --appendfsync everysec
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Environment Variables
```env
# .env.sops (encrypted)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
FRAME_BUFFER_SIZE=1000
FRAME_QUEUE_NAME=frame_queue
```

## 📊 Monitoring {#monitoring}

### Prometheus Metrics
The frame buffer exposes the following metrics:

```promql
# Frame queue depth
frame_queue_depth{queue="frame_queue"}

# Frame processing rate
rate(frames_processed_total[5m])

# Frame drop rate
rate(frames_dropped_total[5m])

# Buffer utilization
frame_buffer_utilization_ratio
```

### Grafana Dashboard
Import the frame buffer dashboard:
```bash
curl -X POST http://nebula:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @dashboards/frame-buffer.json
```

## 🔍 Tracing {#tracing}

### Jaeger Integration
The service sends traces to Jaeger for every frame operation:

- `frame.enqueue` - Adding frame to buffer
- `frame.dequeue` - Removing frame from buffer
- `frame.process` - Processing frame
- `frame.drop` - Dropping frame due to buffer full

View traces at: http://nebula:16686

## 🚀 Performance Testing {#load-testing}

### Run Load Test
```bash
# Local test
cd services/frame-buffer
python -m pytest tests/performance/test_load.py

# Production test on Nebula
ssh nebula "docker exec frame-buffer python -m frame_buffer.benchmark --duration 60 --rate 1000"
```

### Expected Performance
- **Throughput**: 1000+ frames/second
- **Latency**: <10ms p99
- **Memory**: <500MB for 1000 frame buffer
- **CPU**: <20% single core

## 🐛 Troubleshooting

### Service Not Starting
```bash
# Check logs
ssh nebula "docker logs frame-buffer --tail 100"

# Common issues:
# - Redis not reachable: Check REDIS_HOST
# - Port already in use: Check port 8002
# - Memory limit: Increase Docker memory
```

### High Frame Drop Rate
```bash
# Check buffer size
curl http://nebula:8002/metrics | grep frame_buffer_size

# Increase buffer size
ssh nebula "docker exec frame-buffer curl -X POST http://localhost:8002/admin/buffer-size -d '{\"size\": 2000}'"
```

### Redis Connection Issues
```bash
# Test Redis connection
ssh nebula "docker exec frame-buffer redis-cli -h redis ping"

# Check Redis memory
ssh nebula "docker exec redis redis-cli INFO memory"
```

## 🔄 Rollback Procedure

If deployment fails:

1. **Revert to previous version**:
   ```bash
   # On Nebula
   cd /opt/detektor
   docker-compose stop frame-buffer
   docker pull ghcr.io/hretheum/bezrobocie-detektor/frame-buffer:previous-tag
   docker-compose up -d frame-buffer
   ```

2. **Clear Redis if corrupted**:
   ```bash
   ssh nebula "docker exec redis redis-cli FLUSHDB"
   ```

3. **Restore from backup**:
   ```bash
   ssh nebula "docker exec redis redis-cli --rdb /backup/dump.rdb"
   ```

## 📝 Notes

- Frame buffer uses Redis Streams for reliable message delivery
- Implements backpressure handling to prevent memory overflow
- Dead Letter Queue (DLQ) for failed frames
- Automatic reconnection to Redis with exponential backoff
- Metrics are scraped by Prometheus every 15s
- All frames have unique IDs for end-to-end tracing

## 🚀 Production Status

**✅ DEPLOYED ON NEBULA** (2025-07-21)

- **Service URL**: http://nebula:8002
- **Health Status**: Healthy ✅
- **Redis Connection**: Connected ✅
- **Deployment Method**: GitHub Actions CI/CD
- **Performance**: 80k+ fps, 0.01ms latency
- **API Endpoints**:
  - POST `/frames/enqueue` - Add frames to buffer
  - GET `/frames/dequeue` - Retrieve frames from buffer
  - GET `/frames/status` - Buffer status and utilization
  - POST `/frames/dlq/clear` - Clear Dead Letter Queue
- **Monitoring**:
  - Prometheus metrics: http://nebula:8002/metrics
  - OpenTelemetry traces to Jaeger
- **Last deployment**: Successfully tested with enqueue/dequeue operations
