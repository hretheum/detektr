# Faza 3 / Zadanie 3: Event bus (Kafka/NATS) z pełnym monitoringiem

## Cel zadania

Wdrożyć skalowalny event bus do komunikacji między serwisami AI z gwarancją dostarczenia i pełną observability.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Porównanie Kafka vs NATS**
   - **Metryka**: Decyzja techniczna z uzasadnieniem
   - **Walidacja**:

     ```bash
     # Test both options
     docker run -d --name test-kafka confluentinc/cp-kafka:latest
     docker run -d --name test-nats nats:latest
     # Document pros/cons
     ```

   - **Czas**: 1h

2. **[ ] Weryfikacja zasobów**
   - **Metryka**: 8GB RAM, 20GB disk dla Kafka/Zookeeper
   - **Walidacja**:

     ```bash
     free -h | grep Mem | awk '{print $7}'
     df -h /var/lib/docker | tail -1 | awk '{print $4}'
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Event bus deployment

#### Zadania atomowe

1. **[ ] Kafka cluster setup (3 brokers)**
   - **Metryka**: Cluster healthy, replication working
   - **Walidacja**:

     ```bash
     kafka-topics --bootstrap-server localhost:9092 --list
     kafka-broker-api-versions --bootstrap-server localhost:9092
     # All 3 brokers responding
     ```

   - **Czas**: 2h

2. **[ ] Topic creation z retention**
   - **Metryka**: Topics dla każdego event type
   - **Walidacja**:

     ```bash
     kafka-topics --describe --topic detection-events
     # Partitions: 6, Replication: 2, Retention: 7d
     ```

   - **Czas**: 1h

3. **[ ] Schema registry setup**
   - **Metryka**: Avro schemas versioned
   - **Walidacja**:

     ```bash
     curl http://localhost:8081/subjects
     # ["detection-events-value", "frame-events-value"]
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Kafka cluster operational
- Topics properly configured
- Schema evolution ready

### Blok 2: Producer/Consumer libraries

#### Zadania atomowe

1. **[ ] Event producer z retry logic**
   - **Metryka**: 99.99% delivery guarantee
   - **Walidacja**:

     ```python
     producer = EventProducer(retry_policy=ExponentialBackoff())
     results = [producer.send(event) for _ in range(10000)]
     assert sum(r.success for r in results) >= 9999
     ```

   - **Czas**: 2h

2. **[ ] Consumer z exactly-once semantics**
   - **Metryka**: No duplicate processing
   - **Walidacja**:

     ```python
     # Process same events twice
     processed = consume_with_dedup(events)
     assert len(set(processed)) == len(events)
     ```

   - **Czas**: 2.5h

3. **[ ] Dead letter queue handling**
   - **Metryka**: Failed events captured
   - **Walidacja**:

     ```bash
     # Send malformed event
     kafka-console-consumer --topic detection-events-dlq
     # Should show failed event
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Reliable messaging achieved
- Error handling robust
- Performance acceptable

### Blok 3: Monitoring integration

#### Zadania atomowe

1. **[ ] Kafka exporter setup**
   - **Metryka**: Lag, throughput, errors in Prometheus
   - **Walidacja**:

     ```bash
     curl localhost:9308/metrics | grep kafka_
     # Shows consumer lag, broker metrics
     ```

   - **Czas**: 1.5h

2. **[ ] Event flow dashboard**
   - **Metryka**: Visualize event flow between services
   - **Walidacja**:

     ```bash
     # Grafana shows event rates
     curl http://localhost:3000/api/dashboards/uid/event-flow
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Complete visibility
- Performance tracked
- Alerts configured

## Całościowe metryki sukcesu zadania

1. **Throughput**: >1000 events/sec sustained
2. **Reliability**: 99.99% delivery rate, <10ms p99 latency
3. **Observability**: All event flows traced and measured

## Deliverables

1. `/docker-compose.kafka.yml` - Kafka cluster config
2. `/src/shared/messaging/` - Producer/consumer libraries
3. `/schemas/` - Avro event schemas
4. `/dashboards/event-bus.json` - Kafka metrics dashboard
5. `/docs/event-catalog.md` - Event documentation

## Narzędzia

- **Apache Kafka**: Primary event bus (or NATS)
- **Schema Registry**: Schema management
- **Kafka Manager**: Cluster management UI
- **kcat**: Kafka CLI tool

## Zależności

- **Wymaga**: Docker infrastructure
- **Blokuje**: Service communication, event sourcing

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Partition rebalancing storms | Średnie | Wysoki | Sticky assignment, gradual scaling | Frequent rebalances |
| Event ordering issues | Niskie | Średni | Partition key strategy | Out-of-order detections |

## Rollback Plan

1. **Detekcja problemu**:
   - Message loss detected
   - Lag growing unbounded
   - Cluster unstable

2. **Kroki rollback**:
   - [ ] Stop producers: Pause all services
   - [ ] Export unprocessed events
   - [ ] Switch to fallback (Redis Streams)
   - [ ] Replay events from backup

3. **Czas rollback**: <20 min

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/event-bus.md`

### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/event-bus.md#deploy](docs/deployment/services/event-bus.md#deploy)

2. **[ ] Konfiguracja Kafka/NATS cluster na Nebuli**
   - **Metryka**: 3-node cluster operational
   - **Walidacja**: `.env.sops` contains cluster configuration
   - **Procedura**: [docs/deployment/services/event-bus.md#configuration](docs/deployment/services/event-bus.md#configuration)

3. **[ ] Weryfikacja metryk w Prometheus**
   - **Metryka**: Event bus metrics visible at http://nebula:9090
   - **Walidacja**: `curl http://nebula:9090/api/v1/query?query=kafka_topic_partition_current_offset`
   - **Procedura**: [docs/deployment/services/event-bus.md#monitoring](docs/deployment/services/event-bus.md#monitoring)

4. **[ ] Grafana dashboard dla event bus**
   - **Metryka**: Lag, throughput, partitions visible
   - **Walidacja**: Dashboard shows all topics and consumer groups
   - **Procedura**: [docs/deployment/services/event-bus.md#dashboard](docs/deployment/services/event-bus.md#dashboard)

5. **[ ] Test event flow AI services**
   - **Metryka**: Events flow between face/object detection
   - **Walidacja**: End-to-end event processing test
   - **Procedura**: [docs/deployment/services/event-bus.md#integration-testing](docs/deployment/services/event-bus.md#integration-testing)

### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

### **📋 Walidacja sukcesu:**
```bash
# Sprawdź Kafka cluster:
ssh nebula "docker exec kafka-1 kafka-broker-api-versions --bootstrap-server localhost:9092"

# List topics:
ssh nebula "docker exec kafka-1 kafka-topics --bootstrap-server localhost:9092 --list"

# Check consumer groups:
ssh nebula "docker exec kafka-1 kafka-consumer-groups --bootstrap-server localhost:9092 --list"
```

### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/event-bus.md](docs/deployment/services/event-bus.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

### **🔍 Metryki sukcesu bloku:**
- ✅ Kafka/NATS cluster healthy (3 nodes)
- ✅ Event flow between AI services working
- ✅ <10ms latency p99
- ✅ Zero message loss
- ✅ Monitoring dashboard operational
- ✅ Zero-downtime deployment via CI/CD

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-dashboard-ai-performance.md](./04-dashboard-ai-performance.md)
