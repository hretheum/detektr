# Faza 2 / Zadanie 5: Health Checks i Service Discovery

## Cel zadania

Zaimplementować kompleksowy system health checks dla wszystkich serwisów, z integracją service discovery i automated recovery.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites

#### Zadania atomowe

1. **[ ] Analiza health check patterns**
   - **Metryka**: Best practices research
   - **Walidacja**: Decision document
   - **Czas**: 1h

2. **[ ] Setup Consul dla service discovery**
   - **Metryka**: Consul cluster running
   - **Walidacja**: `consul members` shows nodes
   - **Czas**: 2h

### Blok 1: Health check framework

#### Zadania atomowe

1. **[ ] TDD: Health check interface**
   - **Metryka**: Liveness, readiness, startup probes
   - **Walidacja**: `pytest tests/test_health_checks.py`
   - **Czas**: 2h

2. **[ ] Implementacja health check registry**
   - **Metryka**: Dynamic check registration
   - **Walidacja**: Registry unit tests
   - **Czas**: 2h

3. **[ ] Dependency health checks**
   - **Metryka**: DB, Redis, external services
   - **Walidacja**: Cascade failure test
   - **Czas**: 3h

### Blok 2: Service-specific health checks

#### Zadania atomowe

1. **[ ] RTSP stream health validation**
   - **Metryka**: Frame rate, quality checks
   - **Walidacja**: Degraded stream detection
   - **Czas**: 2h

2. **[ ] Queue depth monitoring**
   - **Metryka**: Backpressure detection
   - **Walidacja**: Queue overflow test
   - **Czas**: 2h

3. **[ ] GPU/CPU resource checks**
   - **Metryka**: Resource exhaustion detection
   - **Walidacja**: Load test validation
   - **Czas**: 2h

### Blok 3: Service discovery integration

#### Zadania atomowe

1. **[ ] Consul service registration**
   - **Metryka**: Auto-registration on startup
   - **Walidacja**: `consul catalog services`
   - **Czas**: 2h

2. **[ ] Health check sync z Consul**
   - **Metryka**: Real-time status updates
   - **Walidacja**: Consul UI shows health
   - **Czas**: 2h

3. **[ ] DNS/HTTP service resolution**
   - **Metryka**: Service discovery working
   - **Walidacja**: `dig @consul service.consul`
   - **Czas**: 2h

### Blok 4: Automated recovery

#### Zadania atomowe

1. **[ ] Circuit breaker integration**
   - **Metryka**: Automatic service isolation
   - **Walidacja**:
     ```python
     # Test circuit breaker
     from health_framework import CircuitBreaker
     cb = CircuitBreaker(failure_threshold=3)
     # Simulate failures and verify opens
     ```
   - **Quality Gate**: Opens after threshold
   - **Guardrails**: Configurable timeouts
   - **Czas**: 3h

2. **[ ] Self-healing procedures**
   - **Metryka**: Auto-restart unhealthy services
   - **Walidacja**:
     ```bash
     # Kill service and verify restart
     docker kill rtsp-capture
     sleep 10
     docker ps | grep rtsp-capture
     # Should be running again
     ```
   - **Quality Gate**: Restart within 30s
   - **Guardrails**: Max restart attempts
   - **Czas**: 2h

3. **[ ] Alerting integration**
   - **Metryka**: Alerts on health degradation
   - **Walidacja**:
     ```bash
     # Trigger health failure
     curl -X POST http://localhost:8001/debug/fail
     # Check alert fired in Prometheus
     ```
   - **Quality Gate**: Alert within 1min
   - **Guardrails**: No alert storms
   - **Czas**: 1h

### Blok 5: DEPLOYMENT NA NEBULA ⚠️

#### Zadania atomowe

1. **[ ] Deploy Consul na Nebuli (jeśli wybrane)**
   - **Metryka**: Consul cluster operational
   - **Walidacja NA SERWERZE**:
     ```bash
     # If using Consul
     ssh nebula "docker-compose -f docker-compose.consul.yml up -d"
     ssh nebula "docker exec consul consul members"
     # Shows cluster members
     ```
   - **Quality Gate**: Cluster healthy
   - **Guardrails**: Data persistence configured
   - **Czas**: 2h

2. **[ ] Integracja health checks we wszystkich serwisach**
   - **Metryka**: All services report health
   - **Walidacja NA SERWERZE**:
     ```bash
     # Check each service health endpoint
     for port in 8001 8002 8003 8004 8005 8006; do
       echo "Checking port $port:"
       curl -s http://nebula:$port/health | jq .
     done
     # All return healthy status
     ```
   - **Quality Gate**: 100% services have health
   - **Guardrails**: Standardized format
   - **Czas**: 2h

3. **[ ] Configure Docker health checks**
   - **Metryka**: Docker-native health monitoring
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "docker ps --format 'table {{.Names}}\t{{.Status}}'"
     # All show (healthy) in status

     # Check docker-compose.yml includes:
     # healthcheck:
     #   test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
     #   interval: 30s
     #   timeout: 10s
     #   retries: 3
     ```
   - **Quality Gate**: All containers monitored
   - **Guardrails**: Proper intervals set
   - **Czas**: 1h

4. **[ ] Prometheus health monitoring**
   - **Metryka**: Health metrics in Prometheus
   - **Walidacja NA SERWERZE**:
     ```bash
     # Query health metrics
     curl -s "http://nebula:9090/api/v1/query?query=up" | jq '.data.result[] | {job: .metric.job, value: .value[1]}'
     # All services show value: "1"

     # Check health dashboard
     open http://nebula:3000/d/health/service-health
     ```
   - **Quality Gate**: All services scraped
   - **Guardrails**: No scrape failures
   - **Czas**: 1h

5. **[ ] End-to-end health validation**
   - **Metryka**: Full system health check
   - **Walidacja NA SERWERZE**:
     ```bash
     # Run system health check script
     ssh nebula "/opt/detektor/scripts/system-health-check.sh"
     # All checks: PASS

     # Simulate service failure
     ssh nebula "docker pause rtsp-capture"
     sleep 35
     ssh nebula "docker ps | grep rtsp-capture"
     # Should be restarted by Docker
     ```
   - **Quality Gate**: Recovery works
   - **Guardrails**: No cascading failures
   - **Czas**: 2h

## Całościowe metryki sukcesu zadania

1. **Detection time**: <5s for unhealthy state
2. **Recovery time**: <30s automatic recovery
3. **False positives**: <1% incorrect health status
4. **Coverage**: 100% services with health checks

## Deliverables

1. `src/shared/health/` - Health check framework
2. `src/infrastructure/consul/` - Service discovery
3. `scripts/health-monitor/` - Monitoring scripts
4. `docs/health-check-guide.md` - Implementation guide
5. `monitoring/alerts/health-rules.yml` - Alert rules

## Narzędzia

- **Consul**: Service discovery and health
- **py-consul2**: Python Consul client
- **tenacity**: Retry/circuit breaker
- **aiohttp**: HTTP health endpoints
- **psutil**: System resource monitoring

## CI/CD i Deployment Guidelines

### Health Check Standards
All services MUST implement these endpoints:
```
/health   - Basic liveness check (is service running?)
/ready    - Readiness check (can service handle requests?)
/metrics  - Prometheus metrics (includes health metrics)
```

### Health Check Response Format
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2024-01-20T10:00:00Z",
  "service": "rtsp-capture",
  "version": "1.0.0",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "disk_space": "healthy"
  },
  "metadata": {
    "uptime_seconds": 3600,
    "last_error": null
  }
}
```

### Docker Compose Health Configuration
```yaml
services:
  rtsp-capture:
    image: ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    deploy:
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
```

### Monitoring Setup
1. **Prometheus scrape config**:
   ```yaml
   - job_name: 'detektor-services'
     static_configs:
     - targets: ['rtsp-capture:8001', 'frame-tracking:8006']
   ```

2. **Alert rules**:
   ```yaml
   - alert: ServiceDown
     expr: up == 0
     for: 2m
     annotations:
       summary: "Service {{ $labels.job }} is down"
   ```

3. **Grafana dashboard**:
   - Import: `/dashboards/service-health.json`
   - Shows: uptime, health status, dependency health

### Service Discovery Options
1. **Docker DNS** (simple):
   - Services accessible by name within network
   - No additional infrastructure

2. **Consul** (advanced):
   - Dynamic service registration
   - Health check sync
   - DNS interface

3. **Kubernetes** (future):
   - Native service discovery
   - Built-in health probes

### Deployment Verification
```bash
# Check all services health
for service in $(docker ps --format '{{.Names}}' | grep detektor); do
  echo "=== $service ==="
  docker exec $service curl -s localhost:8001/health | jq .status
done

# Verify in Prometheus
curl -s http://nebula:9090/api/v1/query?query=up | jq '.data.result[] | {service: .metric.job, up: .value[1]}'

# Test recovery
docker stop rtsp-capture
sleep 40
docker ps | grep rtsp-capture  # Should be running again
```

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [../faza-3-detekcja/01-yolo-object-detection.md](../faza-3-detekcja/01-yolo-object-detection.md)
