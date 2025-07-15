# Faza 2 / Zadanie 2: Konfiguracja Redis/RabbitMQ z metrykami Prometheus

## Cel zadania
Skonfigurować wysokowydajny message broker (Redis/RabbitMQ) do kolejkowania klatek z pełnym monitoringiem Prometheus, zapewniając throughput >100 msg/s.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja dostępności portów**
   - **Metryka**: Porty 6379, 5672, 15672, 15692 wolne
   - **Walidacja**: 
     ```bash
     netstat -tuln | grep -E ':(6379|5672|15672|15692)'
     # Brak output = porty wolne
     ```
   - **Czas**: 0.5h

2. **[ ] Weryfikacja zasobów systemowych**
   - **Metryka**: Min 4GB RAM free, 10GB disk space
   - **Walidacja**: 
     ```bash
     free -h | grep Mem | awk '{print $7}'
     df -h / | tail -1 | awk '{print $4}'
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Redis setup z persistence

#### Zadania atomowe:
1. **[ ] Konfiguracja Redis z AOF i RDB**
   - **Metryka**: Redis persistence enabled, maxmemory-policy set
   - **Walidacja**: 
     ```bash
     docker exec redis redis-cli CONFIG GET appendonly
     docker exec redis redis-cli CONFIG GET save
     # appendonly: yes, save: configured
     ```
   - **Czas**: 1.5h

2. **[ ] Redis exporter dla Prometheus**
   - **Metryka**: Metryki Redis dostępne na :9121/metrics
   - **Walidacja**: 
     ```bash
     curl -s localhost:9121/metrics | grep redis_up
     # redis_up 1
     ```
   - **Czas**: 1h

3. **[ ] Performance tuning Redis**
   - **Metryka**: >10k ops/sec, latency <1ms
   - **Walidacja**: 
     ```bash
     docker exec redis redis-benchmark -q -n 100000
     # SET: >10000 requests per second
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Redis stabilny pod load
- Persistence bez data loss
- Prometheus scraping działa

### Blok 2: RabbitMQ setup (alternatywa)

#### Zadania atomowe:
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

#### Metryki sukcesu bloku:
- RabbitMQ cluster healthy
- Queues configured correctly
- Monitoring operational

### Blok 3: Integration testing i dashboards

#### Zadania atomowe:
1. **[ ] Load test message broker**
   - **Metryka**: 1000 msg/s sustained for 10 min
   - **Walidacja**: 
     ```bash
     python load_test_broker.py --duration 600 --rate 1000
     # Success rate: >99.9%
     ```
   - **Czas**: 2h

2. **[ ] Grafana dashboard dla broker metrics**
   - **Metryka**: Dashboard pokazuje throughput, latency, errors
   - **Walidacja**: 
     ```bash
     curl -s http://admin:admin@localhost:3000/api/dashboards/uid/broker-metrics | jq .dashboard.title
     # "Message Broker Metrics"
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Load test passing
- Dashboard operational
- Alerts configured

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

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-postgresql-timescale.md](./03-postgresql-timescale.md)