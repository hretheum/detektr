# Faza 2 / Zadanie 2: Konfiguracja Redis/RabbitMQ z metrykami Prometheus

## Cel zadania

Skonfigurować wysokowydajny message broker (Redis/RabbitMQ) do kolejkowania klatek z pełnym monitoringiem Prometheus, zapewniając throughput >100 msg/s.

## Blok 0: Prerequisites check NA SERWERZE NEBULA ⚠️

#### Zadania atomowe

1. **[ ] Weryfikacja dostępności portów NA NEBULI**
   - **Metryka**: Porty 6379, 5672, 15672, 15692 wolne
   - **Walidacja NA SERWERZE**:

     ```bash
     ssh nebula "sudo netstat -tuln | grep -E ':(6379|5672|15672|15692)'"
     # Brak output = porty wolne
     ```
   - **Quality Gate**: Żadne konflikty portów
   - **Guardrails**: Firewall rules configured
   - **Czas**: 0.5h

2. **[ ] Weryfikacja zasobów systemowych NA NEBULI**
   - **Metryka**: Min 4GB RAM free, 10GB disk space
   - **Walidacja NA SERWERZE**:

     ```bash
     ssh nebula "free -h | grep Mem | awk '{print $7}'"
     ssh nebula "df -h / | tail -1 | awk '{print $4}'"
     ssh nebula "nvidia-smi --query-gpu=memory.free --format=csv,noheader"
     ```
   - **Quality Gate**: Sufficient resources available
   - **Guardrails**: Alert if <20% free
   - **Czas**: 0.5h

3. **[ ] Weryfikacja Docker network na Nebuli**
   - **Metryka**: detektor-network exists and healthy
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "docker network ls | grep detektor-network"
     # Should exist
     ssh nebula "docker network inspect detektor-network | jq '.Containers | length'"
     # Shows connected containers
     ```
   - **Quality Gate**: Network properly configured
   - **Guardrails**: All services on same network
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Redis setup z persistence

#### Zadania atomowe

1. **[ ] Konfiguracja Redis z AOF i RDB**
   - **Metryka**: Redis persistence enabled, maxmemory-policy set
   - **Walidacja**:

     ```bash
     docker exec redis redis-cli CONFIG GET appendonly
     docker exec redis redis-cli CONFIG GET save
     # appendonly: yes, save: configured

     # Verify persistence files
     docker exec redis ls -la /data/ | grep -E "(dump.rdb|appendonly.aof)"
     # Both files should exist
     ```
   - **Quality Gate**: AOF rewrite completes in <5s
   - **Guardrails**: Max memory set to 8GB with allkeys-lru policy
   - **Czas**: 1.5h

2. **[ ] Redis exporter dla Prometheus**
   - **Metryka**: Metryki Redis dostępne na :9121/metrics
   - **Walidacja**:

     ```bash
     curl -s localhost:9121/metrics | grep redis_up
     # redis_up 1

     # Verify key metrics exposed
     curl -s localhost:9121/metrics | grep -E "redis_(connected_clients|used_memory_bytes|commands_total)"
     # All metrics should be present
     ```
   - **Quality Gate**: Scrape duration <100ms
   - **Guardrails**: Alert if exporter down >1min
   - **Czas**: 1h

3. **[ ] Performance tuning Redis**
   - **Metryka**: >10k ops/sec, latency <1ms
   - **Walidacja**:

     ```bash
     docker exec redis redis-benchmark -q -n 100000
     # SET: >10000 requests per second

     # Latency check
     docker exec redis redis-cli --latency-history
     # avg latency <1ms
     ```
   - **Quality Gate**: No slow queries >10ms
   - **Guardrails**: CPU usage <50% under load
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Redis stabilny pod load
- Persistence bez data loss
- Prometheus scraping działa

### Blok 2: RabbitMQ setup (alternatywa)

#### Zadania atomowe

1. **[ ] Deploy RabbitMQ z management plugin**
   - **Metryka**: RabbitMQ UI dostępne na :15672
   - **Walidacja**:

     ```bash
     curl -u guest:guest http://localhost:15672/api/overview | jq .rabbitmq_version
     # Returns version string
     ```

   - **Czas**: 1h

2. **[ ] Konfiguracja Prometheus plugin**
   - **Metryka**: Metryki na :15692/metrics
   - **Walidacja**:

     ```bash
     curl -s localhost:15692/metrics | grep rabbitmq_build_info
     # rabbitmq_build_info{...} 1
     ```

   - **Czas**: 1h

3. **[ ] Queue configuration i policies**
   - **Metryka**: Queue z TTL, max-length, durability
   - **Walidacja**:

     ```bash
     rabbitmqctl list_queues name durable messages_ready
     # frame_queue true 0
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- RabbitMQ cluster healthy
- Queues configured correctly
- Monitoring operational

### Blok 3: Integration testing i dashboards

#### Zadania atomowe

1. **[ ] Load test message broker NA SERWERZE**
   - **Metryka**: 1000 msg/s sustained for 10 min
   - **Walidacja NA SERWERZE**:

     ```bash
     ssh nebula "docker run --rm --network detektor-network load-tester python /app/load_test_broker.py --duration 600 --rate 1000"
     # Success rate: >99.9%
     ```
   - **Quality Gate**: No message loss
   - **Guardrails**: CPU <80% during test
   - **Czas**: 2h

2. **[ ] Grafana dashboard deployment na Nebuli**
   - **Metryka**: Dashboard pokazuje throughput, latency, errors
   - **Walidacja NA SERWERZE**:

     ```bash
     curl -s http://nebula:3000/api/dashboards/uid/broker-metrics | jq .dashboard.title
     # "Message Broker Metrics"
     # Check live data
     curl http://nebula:3000/render/d/broker-metrics/message-broker-metrics?orgId=1&from=now-5m&to=now&panelId=1&width=1000&height=500
     ```
   - **Quality Gate**: All panels show data
   - **Guardrails**: No null values in graphs
   - **Czas**: 1.5h

### Blok 4: CI/CD Pipeline i Docker Images

#### Zadania atomowe

1. **[ ] Utworzenie Dockerfile dla Redis z custom config**
   - **Metryka**: Image builds w <2 min
   - **Walidacja**:
     ```bash
     # Build locally for testing
     docker build -f services/redis-broker/Dockerfile -t redis-broker:test .
     docker run --rm redis-broker:test redis-server --version
     # Redis server v=7.x.x
     ```
   - **Quality Gate**: Image size <100MB
   - **Guardrails**: No security vulnerabilities (trivy scan)
   - **Czas**: 1h

2. **[ ] GitHub Actions workflow dla broker images**
   - **Metryka**: Automated build on push to main
   - **Walidacja**:
     ```bash
     # Check workflow file
     cat .github/workflows/broker-deploy.yml | grep "ghcr.io"
     # Push test
     git push origin main
     # Monitor: https://github.com/hretheum/bezrobocie/actions
     ```
   - **Quality Gate**: Build succeeds in <5 min
   - **Guardrails**: Only builds on main branch
   - **Czas**: 1.5h

3. **[ ] Integration z docker-compose dla Nebula**
   - **Metryka**: docker-compose.broker.yml uses registry images
   - **Walidacja**:
     ```yaml
     # docker-compose.broker.yml should contain:
     services:
       redis:
         image: ghcr.io/hretheum/bezrobocie-detektor/redis-broker:latest
       redis-exporter:
         image: ghcr.io/hretheum/bezrobocie-detektor/redis-exporter:latest
     ```
   - **Quality Gate**: No local build directives
   - **Guardrails**: Images pulled from registry only
   - **Czas**: 1h

### Blok 5: DEPLOYMENT NA SERWERZE NEBULA

#### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/message-broker.md`

#### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/message-broker.md#deploy](docs/deployment/services/message-broker.md#deploy)

2. **[ ] Konfiguracja Redis/RabbitMQ na Nebuli**
   - **Metryka**: Message broker running with persistence
   - **Walidacja**: `.env.sops` contains broker configuration
   - **Procedura**: [docs/deployment/services/message-broker.md#configuration](docs/deployment/services/message-broker.md#configuration)

3. **[ ] Weryfikacja metryk w Prometheus**
   - **Metryka**: Broker metrics visible at http://nebula:9090
   - **Walidacja**: `curl http://nebula:9090/api/v1/query?query=redis_up`
   - **Procedura**: [docs/deployment/services/message-broker.md#monitoring](docs/deployment/services/message-broker.md#monitoring)

4. **[ ] Grafana dashboard dla broker**
   - **Metryka**: Message broker dashboard operational
   - **Walidacja**: Dashboard shows throughput and latency
   - **Procedura**: [docs/deployment/services/message-broker.md#dashboard](docs/deployment/services/message-broker.md#dashboard)

5. **[ ] Load test message flow**
   - **Metryka**: >100 msg/s sustained throughput
   - **Walidacja**: Performance tests via CI/CD
   - **Procedura**: [docs/deployment/services/message-broker.md#load-testing](docs/deployment/services/message-broker.md#load-testing)

#### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

#### **📋 Walidacja sukcesu:**
```bash
# Sprawdź deployment:
ssh nebula "docker ps | grep -E 'redis|rabbit'"

# Test Redis:
ssh nebula "docker exec redis redis-cli ping"

# Sprawdź metryki:
curl http://nebula:9121/metrics | grep redis_up
```

#### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/message-broker.md](docs/deployment/services/message-broker.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

#### **🔍 Metryki sukcesu bloku:**
- ✅ Redis/RabbitMQ running with persistence
- ✅ Prometheus exporter operational
- ✅ >100 msg/s throughput verified
- ✅ Grafana dashboard showing metrics
- ✅ 24h stability test passed
- ✅ Zero-downtime deployment via CI/CD

## Całościowe metryki sukcesu zadania

1. **Performance**: >100 msg/s throughput, <10ms latency p99
2. **Reliability**: Zero message loss, automatic failover
3. **Observability**: Full metrics in Prometheus/Grafana

## Deliverables

1. `/docker-compose.yml` - Updated z Redis/RabbitMQ
2. `/config/redis/redis.conf` - Optimized configuration
3. `/config/rabbitmq/` - RabbitMQ config files
4. `/dashboards/message-broker.json` - Grafana dashboard
5. `/scripts/load_test_broker.py` - Performance test script

## Narzędzia

- **Redis 7+**: Primary message broker (alternatywa: RabbitMQ)
- **RabbitMQ 3.12+**: Alternative broker (alternatywa: NATS)
- **redis_exporter**: Prometheus metrics for Redis
- **redis-benchmark**: Performance testing

## Zależności

- **Wymaga**: Docker environment (Faza 1)
- **Blokuje**: Frame tracking (Faza 2), wszystkie AI services

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Memory exhaustion | Średnie | Wysoki | Set maxmemory, eviction policy | Memory usage >80% |
| Message loss | Niskie | Wysoki | Enable persistence, replication | Failed health checks |

## Rollback Plan

1. **Detekcja problemu**:
   - Message loss detected
   - Throughput <50 msg/s
   - Memory >90%

2. **Kroki rollback**:
   - [ ] Stop producers: `docker-compose stop rtsp-capture`
   - [ ] Export queue data: `redis-cli BGSAVE`
   - [ ] Restore previous config
   - [ ] Restart with old version

3. **Czas rollback**: <10 min

## CI/CD i Deployment Guidelines

### Image Registry Structure
```
ghcr.io/hretheum/bezrobocie-detektor/
├── redis-broker:latest       # Redis z custom config
├── redis-broker:main-SHA     # Tagged versions
├── redis-exporter:latest     # Prometheus exporter
└── rabbitmq-broker:latest    # Alternative broker
```

### Deployment Checklist
- [ ] Images built in GitHub Actions
- [ ] Pushed to ghcr.io registry
- [ ] docker-compose.broker.yml references registry images
- [ ] deploy-to-nebula.sh updated for broker services
- [ ] Health checks passing on Nebula
- [ ] Monitoring dashboards showing data
- [ ] 24h stability verified

### Monitoring Endpoints
- Redis metrics: `http://nebula:9121/metrics`
- RabbitMQ metrics: `http://nebula:15692/metrics`
- Grafana dashboard: `http://nebula:3000/d/broker-metrics`

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-postgresql-timescale.md](./03-postgresql-timescale.md)
