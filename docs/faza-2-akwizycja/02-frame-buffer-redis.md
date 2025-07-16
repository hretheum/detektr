# Faza 2 / Zadanie 2: Frame Buffer z Redis/RabbitMQ

## Cel zadania

Zaimplementować wydajny system buforowania klatek wideo wykorzystując Redis Streams lub RabbitMQ, z gwarancją dostarczenia i obsługą backpressure.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites

#### Zadania atomowe

1. **[ ] Analiza Redis Streams vs RabbitMQ**
   - **Metryka**: Decyzja oparta na benchmarkach
   - **Walidacja**: Dokument porównawczy z testami
   - **Czas**: 2h

2. **[ ] Setup środowiska testowego z load generator**
   - **Metryka**: Generator produkuje 1000 msg/s
   - **Walidacja**: `redis-cli XLEN frame_stream`
   - **Czas**: 1h

### Blok 1: Implementacja Frame Queue abstraction

#### Zadania atomowe

1. **[ ] TDD: Interface dla frame queue**
   - **Metryka**: 100% coverage dla queue operations
   - **Walidacja**: `pytest tests/test_frame_queue_interface.py`
   - **Czas**: 2h

2. **[ ] Implementacja Redis Streams adapter**
   - **Metryka**: XADD/XREAD z consumer groups
   - **Walidacja**: Multiple consumers test
   - **Czas**: 3h

3. **[ ] Implementacja RabbitMQ adapter (fallback)**
   - **Metryka**: Topic exchange z persistence
   - **Walidacja**: Message durability test
   - **Czas**: 3h

### Blok 2: Frame serialization i compression

#### Zadania atomowe

1. **[ ] TDD: Frame serializer tests**
   - **Metryka**: Tests dla różnych formatów
   - **Walidacja**: Round-trip serialization test
   - **Czas**: 2h

2. **[ ] Implementacja binary frame serialization**
   - **Metryka**: <5ms dla Full HD frame
   - **Walidacja**: Performance benchmark
   - **Czas**: 2h

3. **[ ] Optional compression (LZ4)**
   - **Metryka**: 50% size reduction, <2ms overhead
   - **Walidacja**: Compression ratio test
   - **Czas**: 2h

### Blok 3: Backpressure i flow control

#### Zadania atomowe

1. **[ ] TDD: Backpressure handling tests**
   - **Metryka**: No frame loss under pressure
   - **Walidacja**: Stress test with slow consumer
   - **Czas**: 2h

2. **[ ] Implementacja adaptive buffering**
   - **Metryka**: Dynamic buffer size 100-10000 frames
   - **Walidacja**: Memory usage monitoring
   - **Czas**: 3h

3. **[ ] Circuit breaker dla overload**
   - **Metryka**: Graceful degradation
   - **Walidacja**: Circuit breaker state transitions
   - **Czas**: 2h

### Blok 4: Monitoring i reliability

#### Zadania atomowe

1. **[ ] Queue metrics export**
   - **Metryka**: Queue depth, throughput, latency
   - **Walidacja**: Prometheus scrape endpoint
   - **Czas**: 1h

2. **[ ] Dead letter queue handling**
   - **Metryka**: Failed frames są reprocessowane
   - **Walidacja**: DLQ consumer test
   - **Czas**: 2h

3. **[ ] Integration tests z RTSP service**
   - **Metryka**: End-to-end frame flow
   - **Walidacja**: 24h stability test
   - **Czas**: 3h

## Całościowe metryki sukcesu zadania

1. **Throughput**: 1000+ frames/second sustained
2. **Latency**: <10ms queue overhead per frame
3. **Reliability**: 0% frame loss z persistence
4. **Scalability**: Horizontal scaling consumers

## Deliverables

1. `src/shared/queue/` - Queue abstraction layer
2. `src/infrastructure/redis/` - Redis Streams implementation
3. `src/infrastructure/rabbitmq/` - RabbitMQ implementation
4. `tests/integration/queue/` - Integration tests
5. `docs/queue-architecture.md` - Architecture decision record

## Narzędzia

- **Redis 7+**: Redis Streams
- **RabbitMQ 3.12+**: Alternative queue
- **msgpack**: Binary serialization
- **lz4**: Fast compression
- **locust**: Load testing

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-metadata-storage.md](./03-metadata-storage.md)
