# DEPLOYMENT CHECKLIST - NEBULA SERVER

## Critical Requirements
Wszystkie zadania MUSZĄ być wykonane NA SERWERZE NEBULA, nie lokalnie!

## Pre-deployment Validation

### 1. SSH Access Check
```bash
ssh nebula "hostname && docker --version && nvidia-smi"
```
✅ PASS: Możesz kontynuować
❌ FAIL: Napraw dostęp SSH najpierw

### 2. Environment Check
```bash
ssh nebula "cd /opt/detektor && git status"
```
✅ PASS: Repo jest aktualne
❌ FAIL: Pull latest changes

### 3. Resources Check
```bash
ssh nebula "free -h && df -h / && docker system df"
```
✅ PASS: >4GB RAM free, >10GB disk free
❌ FAIL: Cleanup required

## Deployment Steps

### Phase 1: Message Broker (Redis)
```bash
# Deploy Redis stack
ssh nebula "cd /opt/detektor && docker-compose -f docker-compose.broker.yml up -d redis redis-exporter"

# Verify
ssh nebula "docker ps | grep redis"
ssh nebula "docker exec redis redis-cli ping"
curl http://nebula:9121/metrics | grep redis_up
```

### Phase 2: RTSP Capture Service
```bash
# Build image ON SERVER
ssh nebula "cd /opt/detektor && docker build -f services/rtsp-capture/Dockerfile -t rtsp-capture:latest ."

# Deploy
ssh nebula "cd /opt/detektor && docker-compose up -d rtsp-capture"

# Verify
ssh nebula "docker ps | grep rtsp-capture"
curl http://nebula:8001/health
curl http://nebula:9090/api/v1/query?query=rtsp_frames_captured_total
```

### Phase 3: Integration Verification
```bash
# Check all services
ssh nebula "docker-compose ps"

# Check metrics
curl http://nebula:9090/api/v1/targets | jq '.data.activeTargets[].labels.job' | sort -u

# Check traces
curl http://nebula:16686/api/services | jq '.data[]'

# Check logs aggregation
curl http://nebula:3100/loki/api/v1/labels
```

## Quality Gates

### 1. Service Health
All services must show "healthy" status:
```bash
ssh nebula "docker-compose ps --format json | jq -r '.[] | select(.Health != \"healthy\") | .Name'"
```
Expected: Empty output

### 2. Metrics Collection
All services exporting metrics:
```bash
for service in redis rtsp-capture frame-buffer; do
  echo "Checking $service metrics..."
  curl -s http://nebula:9090/api/v1/query?query=up{job=\"$service\"} | jq '.data.result[0].value[1]'
done
```
Expected: "1" for each service

### 3. Resource Usage
No service exceeding limits:
```bash
ssh nebula "docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}'"
```
Expected: CPU <80%, Memory <specified limits

## Rollback Procedure

### If deployment fails:
```bash
# Stop new services
ssh nebula "docker-compose down"

# Restore previous state
ssh nebula "cd /opt/detektor && git checkout HEAD~1"
ssh nebula "docker-compose up -d"

# Verify rollback
ssh nebula "docker-compose ps"
```

## Post-deployment Monitoring

### Setup alerts:
```bash
# CPU Alert
curl -X POST http://nebula:9090/api/v1/rules -d '{
  "name": "HighCPU",
  "query": "rate(process_cpu_seconds_total[5m]) > 0.8",
  "duration": "5m",
  "labels": {"severity": "warning"}
}'

# Memory Alert
curl -X POST http://nebula:9090/api/v1/rules -d '{
  "name": "HighMemory",
  "query": "process_resident_memory_bytes > 1e9",
  "duration": "5m",
  "labels": {"severity": "warning"}
}'
```

## Success Criteria

✅ All containers running on Nebula
✅ All health checks passing
✅ Metrics visible in Prometheus
✅ Traces visible in Jaeger
✅ No errors in logs for 30 minutes
✅ Load test passing (1000 msg/s)

## DO NOT PROCEED IF ANY CHECK FAILS!
