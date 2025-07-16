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
   - **Walidacja**: Circuit breaker test
   - **Czas**: 3h

2. **[ ] Self-healing procedures**
   - **Metryka**: Auto-restart unhealthy services
   - **Walidacja**: Kill service, verify restart
   - **Czas**: 2h

3. **[ ] Alerting integration**
   - **Metryka**: Alerts on health degradation
   - **Walidacja**: Alert delivery test
   - **Czas**: 1h

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

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [../faza-3-detekcja/01-yolo-object-detection.md](../faza-3-detekcja/01-yolo-object-detection.md)
