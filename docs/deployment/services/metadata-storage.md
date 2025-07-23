# Service: Metadata Storage

## 🚀 Quick Deploy (30 seconds)
```bash
git push origin main
# Watch GitHub Actions deploy automatically
```

## 📋 Detailed Steps (5 minutes)

### 1. Prerequisites
- [x] Service code in `services/metadata-storage/`
- [x] Dockerfile exists
- [x] GitHub Actions workflow exists (`.github/workflows/metadata-storage-deploy.yml`)
- [x] TimescaleDB running on Nebula

### 2. Configuration
- **Service Name**: `metadata-storage`
- **Port**: `8005`
- **Health Check**: `http://localhost:8005/health`
- **Metrics**: `http://localhost:8005/metrics`
- **Database**: PostgreSQL/TimescaleDB connection

### 3. Deploy
```bash
# 1. Commit your changes
git add .
git commit -m "feat: deploy metadata-storage service"

# 2. Push to trigger deployment
git push origin main

# 3. Monitor deployment
# Watch GitHub Actions logs
```

### 4. Verify Deployment
```bash
# Check service health
curl http://localhost:8005/health

# Check metrics
curl http://localhost:8005/metrics

# Check logs
docker logs metadata-storage

# Verify database connection
curl -X POST http://localhost:8005/metadata \
  -H "Content-Type: application/json" \
  -d '{"frame_id": "test_001", "timestamp": "2025-07-23T12:00:00", "camera_id": "camera_001"}'
```

## ⚙️ Configuration Options

### Environment Variables
```bash
# Required
SERVICE_NAME=metadata-storage
PORT=8005
DATABASE_URL=postgresql://detektor:detektor_pass@postgres:5432/detektor_db
ENVIRONMENT=production

# Optional
LOG_LEVEL=info
METRICS_ENABLED=true
CONNECTION_POOL_MIN=5
CONNECTION_POOL_MAX=20
```

### Docker Compose Override
```yaml
services:
  metadata-storage:
    image: ghcr.io/hretheum/detektr/metadata-storage:latest
    ports:
      - "8005:8005"
    environment:
      - SERVICE_NAME=metadata-storage
      - PORT=8005
      - DATABASE_URL=postgresql://detektor:detektor_pass@postgres:5432/detektor_db
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Service Won't Start
**Symptoms**: Deployment fails in GitHub Actions
**Solution**:
```bash
# Check service logs
docker logs metadata-storage

# Verify database connection
docker exec metadata-storage curl http://postgres:5432
```

#### 2. Database Connection Fails
**Symptoms**: Service starts but can't connect to TimescaleDB
**Solution**:
```bash
# Test database connection
docker exec metadata-storage psql -h postgres -U detektor -d detektor_db -c "SELECT 1"

# Check network connectivity
docker network inspect detektor-network
```

#### 3. Health Check Fails
**Symptoms**: Service starts but health check fails
**Solution**:
```bash
# Test health endpoint
curl -v http://localhost:8005/health

# Check service logs for errors
docker logs metadata-storage --tail 50
```

#### 4. Metrics Not Showing
**Symptoms**: Prometheus doesn't show service metrics
**Solution**:
```bash
# Verify metrics endpoint
curl http://localhost:8005/metrics | grep metadata_storage

# Check Prometheus targets
# Visit: http://nebula:9090/targets
```

#### 5. Performance Issues
**Symptoms**: Slow queries or high latency
**Solution**:
```bash
# Check connection pool status
docker logs metadata-storage | grep "pool"

# Run performance test
python services/metadata-storage/scripts/optimization/performance_benchmark.py
```

## 🔄 Rollback Procedures

### Quick Rollback
```bash
# Revert last commit
git revert HEAD
git push origin main

# Manual rollback
docker-compose down metadata-storage
docker-compose up -d metadata-storage
```

### Emergency Procedures
```bash
# Stop service immediately
docker stop metadata-storage

# Rollback to last known good
docker pull ghcr.io/hretheum/detektr/metadata-storage:main-[previous-sha]
docker-compose up -d metadata-storage

# Verify rollback
curl http://localhost:8005/health
```

## 📊 Monitoring

### Key Metrics to Watch
- **Service Health**: `http://localhost:8005/health`
- **Prometheus Metrics**: `http://nebula:9090`
- **Database Performance**: Query latency, connection pool
- **Grafana Dashboard**: `http://nebula:3000/d/timescaledb-metadata`

### Alerting Rules
```yaml
# Memory usage > 80%
- alert: MetadataStorageHighMemory
  expr: memory_usage_percent{service="metadata-storage"} > 80

# Query latency > 100ms
- alert: MetadataStorageSlowQueries
  expr: metadata_storage_request_duration_seconds{quantile="0.99"} > 0.1

# Service down
- alert: MetadataStorageDown
  expr: up{service="metadata-storage"} == 0
```

## 📚 Examples

### Store Metadata
```bash
curl -X POST http://localhost:8005/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "frame_id": "2025-07-23_camera001_00001",
    "timestamp": "2025-07-23T12:00:00",
    "camera_id": "camera_001",
    "sequence_number": 1,
    "metadata": {
      "motion_detected": true,
      "objects_count": 3
    }
  }'
```

### Retrieve Metadata
```bash
curl http://localhost:8005/metadata/2025-07-23_camera001_00001
```

### Related Services
- [PostgreSQL/TimescaleDB](../../../docs/faza-2-akwizycja/03-postgresql-timescale.md)
- [Frame Tracking Service](./frame-tracking.md)

### Performance Notes
- Achieves 16,384 inserts/second with batch operations
- Connection pooling with 5-20 connections
- Automatic retry logic with exponential backoff
- TimescaleDB hypertables for time-series optimization
