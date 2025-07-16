# Faza 4 / Zadanie 3: Redis Streams Event Bus (eofek/detektor pattern)

<!--
LLM CONTEXT PROMPT:
Event bus design bazuje na proven patterns z eofek/detektor (docs/analysis/eofek-detektor-analysis.md):
- Redis Streams zamiast Kafka (prostsze, proven solution)
- Event acknowledgement dla reliability
- Structured event format z unique IDs
- ADOPTUJEMY: Redis Streams architecture z eofek/detektor
- UNIKAMY: Kafka complexity dla naszego use case
-->

## Cel zadania

Wdrożyć skalowalny event bus oparty na Redis Streams dla niezawodnej komunikacji między serwisami z gwarancją dostarczenia i uporządkowania.

**Pattern Source**: Adoptuje eofek/detektor Redis Streams event-driven architecture.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Analiza Kafka vs NATS**
   - **Metryka**: Wybór technologii na podstawie wymagań
   - **Walidacja**:

     ```bash
     # Document decision
     cat docs/architecture/event-bus-decision.md | grep -E "(Decision|Rationale)"
     # Should show:
     # Decision: Kafka/NATS
     # Rationale: [performance/persistence/ordering requirements]
     ```

   - **Czas**: 1h

2. **[ ] Weryfikacja zasobów**
   - **Metryka**: Minimum 4GB RAM, 20GB disk dla Kafka, lub 1GB RAM dla NATS
   - **Walidacja**:

     ```bash
     # Check resources
     free -h | grep Mem | awk '{print $7}'
     df -h /var/lib/docker | tail -1 | awk '{print $4}'
     # Kafka needs ZooKeeper
     docker network ls | grep detektor
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Event bus infrastructure setup

#### Zadania atomowe

1. **[ ] Deploy Kafka/NATS cluster**
   - **Metryka**: 3-node cluster for HA, <5ms latency
   - **Walidacja**:

     ```bash
     # For Kafka
     docker-compose -f docker-compose.kafka.yml up -d
     kafka-topics.sh --bootstrap-server localhost:9092 --list

     # For NATS
     docker-compose -f docker-compose.nats.yml up -d
     nats-cli --server nats://localhost:4222 server info

     # Test publish/subscribe
     ./scripts/event-bus-test.sh latency
     # Average latency: <5ms
     ```

   - **Czas**: 2.5h

2. **[ ] Topic/Subject architecture**
   - **Metryka**: Organized namespace, partitioning strategy
   - **Walidacja**:

     ```bash
     # Kafka topics
     kafka-topics.sh --bootstrap-server localhost:9092 --list | sort
     # detektor.detection.face
     # detektor.detection.motion
     # detektor.detection.object
     # detektor.automation.triggers
     # detektor.system.health

     # NATS subjects
     nats sub "detektor.>" --count 1
     ```

   - **Czas**: 1.5h

3. **[ ] Schema registry setup**
   - **Metryka**: Protobuf/Avro schemas for all event types
   - **Walidacja**:

     ```python
     from confluent_kafka.schema_registry import SchemaRegistryClient

     sr = SchemaRegistryClient({'url': 'http://localhost:8081'})
     schemas = sr.get_subjects()

     assert 'detektor.PersonDetectedEvent' in schemas
     assert 'detektor.MotionDetectedEvent' in schemas

     # Validate schema evolution
     schema = sr.get_latest_version('detektor.PersonDetectedEvent')
     assert schema.version >= 1
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Event bus cluster operational
- Organized topic structure
- Schema management working

### Blok 2: Client libraries and integration

#### Zadania atomowe

1. **[ ] Python client wrapper**
   - **Metryka**: Async publish/subscribe, automatic reconnection
   - **Walidacja**:

     ```python
     from src.infrastructure.messaging import EventBusClient

     client = EventBusClient()

     # Test async publish
     async def test_publish():
         event = PersonDetectedEvent(
             camera_id="front",
             person_id="person_123",
             confidence=0.95
         )

         result = await client.publish("detektor.detection.face", event)
         assert result.success
         assert result.offset is not None  # Kafka
         # or assert result.seq is not None  # NATS

     # Test subscribe
     messages = []
     async def handler(msg):
         messages.append(msg)

     await client.subscribe("detektor.detection.*", handler)
     await asyncio.sleep(1)
     assert len(messages) > 0
     ```

   - **Czas**: 2.5h

2. **[ ] Event routing and filtering**
   - **Metryka**: Content-based routing, subscription filters
   - **Walidacja**:

     ```python
     # Test filtered subscription
     router = EventRouter()

     # Only high-confidence detections
     router.add_route(
         pattern="detektor.detection.*",
         filter=lambda e: e.confidence > 0.9,
         handler=high_confidence_handler
     )

     # Camera-specific routing
     router.add_route(
         pattern="detektor.detection.motion",
         filter=lambda e: e.camera_id == "entrance",
         handler=entrance_handler
     )

     # Process events
     events_routed = router.process_batch(test_events)
     assert events_routed == len(test_events)
     ```

   - **Czas**: 2h

3. **[ ] Dead letter queue handling**
   - **Metryka**: Failed messages captured, retry mechanism
   - **Walidacja**:

     ```bash
     # Force processing failure
     docker exec detektor-detection-processor kill -STOP 1

     # Send events
     ./scripts/send-test-events.sh 100

     # Check DLQ
     if [ "$EVENT_BUS" = "kafka" ]; then
         kafka-console-consumer.sh \
             --bootstrap-server localhost:9092 \
             --topic detektor.dlq \
             --from-beginning \
             --max-messages 10
     else
         nats stream view detektor-dlq
     fi
     # Should show failed messages
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Clean client API
- Flexible routing rules
- Robust error handling

### Blok 3: Performance and monitoring

#### Zadania atomowe

1. **[ ] Throughput optimization**
   - **Metryka**: 10,000+ events/second sustained
   - **Walidacja**:

     ```bash
     # Run performance test
     ./scripts/event-bus-perf-test.sh \
         --duration 60 \
         --producers 10 \
         --rate 1000

     # Results should show:
     # Total events: 600,000+
     # Average throughput: 10,000+ msg/s
     # 99th percentile latency: <10ms
     # Message loss: 0%
     ```

   - **Czas**: 2h

2. **[ ] Event bus metrics export**
   - **Metryka**: Prometheus metrics for all aspects
   - **Walidacja**:

     ```bash
     # Check metrics endpoint
     curl http://localhost:8004/metrics | grep -E "event_bus_"

     # Key metrics:
     # event_bus_messages_published_total{topic="..."}
     # event_bus_messages_consumed_total{topic="...",consumer_group="..."}
     # event_bus_consumer_lag{topic="...",partition="..."}
     # event_bus_publish_duration_seconds
     # event_bus_consume_duration_seconds
     ```

   - **Czas**: 1.5h

3. **[ ] Grafana dashboard**
   - **Metryka**: Real-time visibility of event flow
   - **Walidacja**:

     ```bash
     # Import dashboard
     curl -X POST http://admin:admin@localhost:3000/api/dashboards/import \
          -H "Content-Type: application/json" \
          -d @dashboards/event-bus-metrics.json

     # Verify panels
     curl http://localhost:3000/api/dashboards/uid/event-bus | \
          jq '.dashboard.panels[].title'
     # Should include:
     # "Message Rate by Topic"
     # "Consumer Lag"
     # "Error Rate"
     # "E2E Latency Distribution"
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- High throughput achieved
- Complete observability
- Performance baselines established

## Całościowe metryki sukcesu zadania

1. **Throughput**: 10,000+ sustained events/second
2. **Latency**: p99 <10ms end-to-end
3. **Reliability**: 99.99% message delivery guarantee
4. **Scalability**: Horizontal scaling of consumers

## Deliverables

1. `/docker-compose.kafka.yml` or `/docker-compose.nats.yml` - Event bus deployment
2. `/src/infrastructure/messaging/event_bus_client.py` - Client library
3. `/src/infrastructure/messaging/event_router.py` - Routing logic
4. `/config/event-bus/topics.yaml` - Topic configuration
5. `/src/shared/events/schemas/` - Protobuf/Avro schemas
6. `/dashboards/event-bus-metrics.json` - Monitoring dashboard
7. `/docs/event-bus/client-guide.md` - Integration guide

## Narzędzia

- **Apache Kafka 3.x** or **NATS 2.x**: Event bus
- **Schema Registry**: Schema management (Kafka)
- **Kafka Manager/NATS CLI**: Administration
- **kcat/nats-cli**: Debugging tools
- **Prometheus JMX Exporter**: Metrics (Kafka)

## Zależności

- **Wymaga**:
  - Docker infrastructure
  - Network connectivity between services
  - Monitoring stack
- **Blokuje**:
  - Distributed tracing
  - Event sourcing
  - CQRS implementation

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Message ordering issues | Średnie | Wysoki | Single partition per camera, proper keys | Out-of-order detection |
| Consumer lag | Wysokie | Średni | Auto-scaling, parallel processing | Lag metrics >1000 |
| Schema evolution breaks | Średnie | Wysoki | Backward compatibility tests, versioning | Schema registry errors |
| Network partitions | Niskie | Wysoki | Proper replication, ISR settings | Broker disconnect alerts |

## Rollback Plan

1. **Detekcja problemu**:
   - Message loss detected
   - Consumer lag growing
   - Latency spikes

2. **Kroki rollback**:
   - [ ] Switch to fallback Redis pub/sub: `EVENT_BUS_FALLBACK=redis`
   - [ ] Drain in-flight messages: `./scripts/drain-event-bus.sh`
   - [ ] Stop event bus: `docker-compose -f docker-compose.kafka.yml down`
   - [ ] Clear corrupted data: `rm -rf /var/lib/kafka/data/*`
   - [ ] Restart with previous config: `git checkout HEAD~1 -- config/event-bus/`

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-api-gateway.md](./04-api-gateway.md)
