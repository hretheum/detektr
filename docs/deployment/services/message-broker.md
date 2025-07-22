# Message Broker (Redis) Deployment Guide

## Overview
Redis message broker service for frame buffering and inter-service communication.

## Service Details
- **Name**: redis-broker
- **Port**: 6379
- **Exporter Port**: 9121
- **Images**:
  - `ghcr.io/hretheum/bezrobocie-detektor/redis-broker:latest`
  - `ghcr.io/hretheum/bezrobocie-detektor/redis-exporter:latest`

## Deployment

### Via CI/CD (Recommended)
```bash
# Automatic deployment on push to main
git push origin main
```

The GitHub Actions workflow will:
1. Build Docker images for redis-broker and redis-exporter
2. Push to GitHub Container Registry
3. Deploy to Nebula via self-hosted runner

### Manual Deployment
```bash
# Pull latest images
docker pull ghcr.io/hretheum/bezrobocie-detektor/redis-broker:latest
docker pull ghcr.io/hretheum/bezrobocie-detektor/redis-exporter:latest

# Deploy using broker-specific compose
docker compose -f docker-compose.broker.yml up -d
```

## Configuration

### Redis Configuration
The custom Redis configuration is embedded in the Docker image:
- **Persistence**: AOF + RDB enabled
- **Max Memory**: 4GB with allkeys-lru policy
- **Performance**: Optimized for >100k ops/sec

### Environment Variables
```yaml
# For redis-exporter
REDIS_ADDR: redis://redis:6379
REDIS_USER: ""
REDIS_PASSWORD: ""
```

## Monitoring

### Prometheus Metrics
- **Endpoint**: http://192.168.1.193:9121/metrics
- **Key Metrics**:
  - `redis_up` - Service availability
  - `redis_commands_total` - Command throughput
  - `redis_memory_used_bytes` - Memory usage
  - `redis_evicted_keys_total` - Eviction count

### Health Checks
```bash
# Redis health
docker exec redis redis-cli ping

# Exporter health
curl -f http://192.168.1.193:9121/metrics | grep redis_up
```

## Dashboard

### Grafana Dashboard
- **URL**: http://192.168.1.193:3000/d/broker-metrics/message-broker-metrics
- **Features**:
  - Commands per second graph
  - Memory usage gauge
  - Latency tracking
  - Connected clients count

### Import Dashboard
```bash
# Dashboard is auto-provisioned via:
grafana/dashboards/redis-broker-metrics.json
```

## Load Testing

### Run Load Test
```bash
# Build and run load tester
docker build -f services/load-tester/Dockerfile -t load-tester .
docker run --rm --network detektor-network load-tester \
  --rate 1000 --duration 600
```

### Expected Performance
- **Throughput**: >700 msg/s sustained
- **Latency**: <1ms average
- **Success Rate**: 100%

## Troubleshooting

### Redis Not Starting
```bash
# Check logs
docker logs redis

# Verify config
docker exec redis redis-cli CONFIG GET "*"
```

### Metrics Not Appearing
```bash
# Check exporter connectivity
docker exec redis-exporter wget -O- http://redis:6379/ping

# Verify Prometheus scraping
curl http://192.168.1.193:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="redis")'
```

### Performance Issues
```bash
# Check memory usage
docker exec redis redis-cli INFO memory

# Monitor slow queries
docker exec redis redis-cli SLOWLOG GET 10
```

## Rollback Procedure
```bash
# Stop services
docker compose -f docker-compose.broker.yml down

# Restore previous version
docker pull ghcr.io/hretheum/bezrobocie-detektor/redis-broker:main-<previous-sha>
docker compose -f docker-compose.broker.yml up -d
```
