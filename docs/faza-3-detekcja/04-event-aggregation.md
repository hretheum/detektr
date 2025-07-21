# Faza 3 / Zadanie 4: Event Aggregation Service

## Cel zadania

Stworzyć serwis agregujący zdarzenia z wszystkich detektorów, deduplikujący i korelujący wydarzenia w czasie i przestrzeni.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites

#### Zadania atomowe

1. **[ ] Design event schema**
   - **Metryka**: Unified event format
   - **Walidacja**: Schema validation tests
   - **Czas**: 2h

2. **[ ] Analiza event patterns**
   - **Metryka**: Common correlation scenarios
   - **Walidacja**: Pattern catalog created
   - **Czas**: 1h

### Blok 1: Event ingestion pipeline

#### Zadania atomowe

1. **[ ] TDD: Event aggregator interface**
   - **Metryka**: Pluggable aggregation strategies
   - **Walidacja**: `pytest tests/test_event_aggregator.py`
   - **Czas**: 2h

2. **[ ] Multi-source event consumer**
   - **Metryka**: Consume from N queues
   - **Walidacja**: Multi-source test
   - **Czas**: 3h

3. **[ ] Event validation i normalization**
   - **Metryka**: Schema enforcement
   - **Walidacja**: Invalid event handling
   - **Czas**: 2h

### Blok 2: Deduplication i correlation

#### Zadania atomowe

1. **[ ] Time-window deduplication**
   - **Metryka**: Remove duplicates in 5s window
   - **Walidacja**: Dedup accuracy test
   - **Czas**: 3h

2. **[ ] Spatial correlation**
   - **Metryka**: Group events by proximity
   - **Walidacja**: Multi-camera correlation
   - **Czas**: 3h

3. **[ ] Cross-detector correlation**
   - **Metryka**: Face + gesture = action
   - **Walidacja**: Complex event test
   - **Czas**: 3h

### Blok 3: Complex event processing

#### Zadania atomowe

1. **[ ] Event sequence detection**
   - **Metryka**: Pattern matching rules
   - **Walidacja**: Sequence detection test
   - **Czas**: 3h

2. **[ ] Temporal event fusion**
   - **Metryka**: Merge related events
   - **Walidacja**: Fusion accuracy test
   - **Czas**: 2h

3. **[ ] Event enrichment**
   - **Metryka**: Add context, metadata
   - **Walidacja**: Enrichment pipeline test
   - **Czas**: 2h

### Blok 4: Output i persistence

#### Zadania atomowe

1. **[ ] Aggregated event publisher**
   - **Metryka**: Publish high-level events
   - **Walidacja**: Event flow test
   - **Czas**: 2h

2. **[ ] Event store z replay**
   - **Metryka**: Store 30 days of events
   - **Walidacja**: Event replay test
   - **Czas**: 2h

3. **[ ] Real-time event stream API**
   - **Metryka**: WebSocket/SSE streaming
   - **Walidacja**: Stream latency test
   - **Czas**: 2h

## Całościowe metryki sukcesu zadania

1. **Latency**: <100ms aggregation delay
2. **Accuracy**: 99%+ correct correlations
3. **Throughput**: 1000+ events/second
4. **Deduplication**: 100% duplicate removal

## Deliverables

1. `services/event-aggregator/` - Aggregation service
2. `src/domain/events/` - Event definitions
3. `src/infrastructure/event-store/` - Persistence
4. `config/aggregation-rules.yml` - Rules config
5. `docs/event-patterns.md` - Pattern guide

## Narzędzia

- **Apache Kafka**: Event streaming
- **Redis Streams**: Short-term cache
- **ClickHouse**: Event store
- **FastAPI**: Streaming API
- **Pydantic**: Event validation

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/event-aggregator.md`

### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/event-aggregator.md#deploy](docs/deployment/services/event-aggregator.md#deploy)

2. **[ ] Konfiguracja ClickHouse na Nebuli**
   - **Metryka**: ClickHouse cluster for event storage
   - **Walidacja**: `clickhouse-client --query 'SELECT version()'`
   - **Procedura**: [docs/deployment/services/event-aggregator.md#clickhouse-setup](docs/deployment/services/event-aggregator.md#clickhouse-setup)

3. **[ ] Event aggregation rules**
   - **Metryka**: Custom aggregation rules loaded
   - **Walidacja**: Test deduplication and correlation
   - **Procedura**: [docs/deployment/services/event-aggregator.md#aggregation-rules](docs/deployment/services/event-aggregator.md#aggregation-rules)

4. **[ ] Real-time streaming API**
   - **Metryka**: WebSocket event stream working
   - **Walidacja**: Connect client and receive events
   - **Procedura**: [docs/deployment/services/event-aggregator.md#streaming-api](docs/deployment/services/event-aggregator.md#streaming-api)

5. **[ ] Performance test aggregation**
   - **Metryka**: Handle 10k events/second
   - **Walidacja**: Load test via CI/CD pipeline
   - **Procedura**: [docs/deployment/services/event-aggregator.md#performance-testing](docs/deployment/services/event-aggregator.md#performance-testing)

### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

### **📋 Walidacja sukcesu:**
```bash
# Sprawdź deployment:
curl http://nebula:8014/health

# Test ClickHouse:
ssh nebula "docker exec clickhouse clickhouse-client --query 'SELECT count() FROM events'"

# Test WebSocket stream:
wscat -c ws://nebula:8014/events/stream
```

### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/event-aggregator.md](docs/deployment/services/event-aggregator.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

### **🔍 Metryki sukcesu bloku:**
- ✅ Event aggregator handling 10k events/sec
- ✅ Deduplication working (5s window)
- ✅ Spatial correlation operational
- ✅ ClickHouse storing all events
- ✅ Real-time WebSocket streaming
- ✅ Zero-downtime deployment via CI/CD

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-gpu-optimization.md](./05-gpu-optimization.md)
