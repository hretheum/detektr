# Faza 3 / Zadanie 4: Event Aggregation Service

## Cel zadania
Stworzyć serwis agregujący zdarzenia z wszystkich detektorów, deduplikujący i korelujący wydarzenia w czasie i przestrzeni.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites
#### Zadania atomowe:
1. **[ ] Design event schema**
   - **Metryka**: Unified event format
   - **Walidacja**: Schema validation tests
   - **Czas**: 2h

2. **[ ] Analiza event patterns**
   - **Metryka**: Common correlation scenarios
   - **Walidacja**: Pattern catalog created
   - **Czas**: 1h

### Blok 1: Event ingestion pipeline

#### Zadania atomowe:
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

#### Zadania atomowe:
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

#### Zadania atomowe:
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

#### Zadania atomowe:
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

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-gpu-optimization.md](./05-gpu-optimization.md)