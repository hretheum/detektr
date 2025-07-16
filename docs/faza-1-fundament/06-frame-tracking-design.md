# Faza 1 / Zadanie 6: Frame tracking design i implementacja

<!--
LLM CONTEXT PROMPT:
Frame tracking system bazuje na patterns z eofek/detektor analysis (docs/analysis/eofek-detektor-analysis.md):
- Metrics abstraction layer pattern
- Event-driven architecture z Redis Streams
- GPU monitoring patterns z comprehensive checks
- Ale UNIKAMY: over-engineering, zbyt complex event flows
-->

## Cel zadania

Zaprojektowanie i implementacja systemu śledzenia klatek przez cały pipeline przetwarzania, wykorzystując distributed tracing i event sourcing dla pełnej widoczności każdej klatki.

**Pattern Source**: Inspirowane eofek/detektor metrics architecture z simplifikacjami.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja OpenTelemetry działa poprawnie**
   - **Metryka**: Traces widoczne w Jaeger z example service
   - **Walidacja**:

     ```bash
     # Sprawdź czy są traces z ostatnich 5 minut
     curl -s "http://localhost:16686/api/traces?service=example-service&limit=5" | \
       jq '.data | length'
     # > 0
     ```

   - **Czas**: 0.5h

2. **[ ] Weryfikacja struktury projektu dla domain models**
   - **Metryka**: Domain layer istnieje w strukturze
   - **Walidacja**:

     ```bash
     ls -la src/shared/kernel/domain/ && \
     ls -la src/contexts/monitoring/domain/
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Domain model dla Frame tracking

#### Zadania atomowe

1. **[ ] Implementacja Frame entity i value objects**
   - **Metryka**: Frame model z ID, timestamp, metadata, processing stages
   - **Walidacja**:

     ```python
     from src.shared.kernel.domain.frame import Frame, FrameId, ProcessingStage

     frame = Frame.create(camera_id="cam01", timestamp=datetime.now())
     assert isinstance(frame.id, FrameId)
     assert frame.processing_stages == []
     ```

   - **Czas**: 1.5h

2. **[ ] Implementacja Frame events (Event Sourcing)**
   - **Metryka**: Events: FrameCaptured, ProcessingStarted, ProcessingCompleted, etc.
   - **Walidacja**:

     ```python
     from src.shared.kernel.events import FrameCaptured

     event = FrameCaptured(frame_id="123", camera_id="cam01", timestamp=now)
     assert event.event_type == "frame.captured"
     ```

   - **Czas**: 1h

3. **[ ] Frame lifecycle state machine**
   - **Metryka**: States: captured, queued, processing, completed, failed
   - **Walidacja**:

     ```python
     # Test state transitions
     frame.transition_to(ProcessingState.PROCESSING)
     assert frame.can_transition_to(ProcessingState.COMPLETED)
     assert not frame.can_transition_to(ProcessingState.CAPTURED)
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Domain model captures full frame lifecycle
- Events provide audit trail
- State machine prevents invalid transitions

### Blok 2: Trace context propagation

#### Zadania atomowe

1. **[ ] Frame ID jako baggage w OpenTelemetry context**
   - **Metryka**: Frame ID propagowany automatycznie między serwisami
   - **Walidacja**:

     ```python
     # W każdym span powinien być frame_id
     with tracer.start_as_current_span("process") as span:
         assert span.get_baggage("frame_id") == frame.id
     ```

   - **Czas**: 1h

2. **[ ] Automatic span creation dla frame operations**
   - **Metryka**: Każda operacja na frame tworzy span
   - **Walidacja**:

     ```bash
     # Po przetworzeniu frame
     curl -s "http://localhost:16686/api/traces/{trace_id}" | \
       jq '.data[0].spans | length'
     # Powinno być >5 spans (capture, queue, process, etc.)
     ```

   - **Czas**: 1h

3. **[ ] Correlation między logs, metrics i traces**
   - **Metryka**: Frame ID w logs i jako label w metrics
   - **Walidacja**:

     ```bash
     # Loki query
     curl -G -s "http://localhost:3100/loki/api/v1/query" \
       --data-urlencode 'query={job="detektor"} |= "frame_id=test-123"'
     # Powinien znaleźć logi
     ```

   - **Czas**: 0.5h

#### Metryki sukcesu bloku

- Frame ID widoczny we wszystkich telemetry data
- Automatic context propagation
- Easy correlation między signals

### Blok 3: Frame metadata i storage

#### Zadania atomowe

1. **[ ] TimescaleDB schema dla frame metadata**
   - **Metryka**: Hypertable z automatic partitioning
   - **Walidacja**:

     ```sql
     SELECT * FROM timescaledb_information.hypertables
     WHERE hypertable_name = 'frame_metadata';
     -- Should return 1 row
     ```

   - **Czas**: 1h

2. **[ ] Frame metadata repository implementation**
   - **Metryka**: CRUD operations z tracing
   - **Walidacja**:

     ```python
     # Test repository
     repo = FrameMetadataRepository()
     await repo.save(frame)
     retrieved = await repo.get_by_id(frame.id)
     assert retrieved.id == frame.id
     ```

   - **Czas**: 1.5h

3. **[ ] Processing history queries**
   - **Metryka**: Query frames by time range, status, camera
   - **Walidacja**:

     ```python
     # Find all failed frames in last hour
     failed_frames = await repo.find_by_status(
         status=ProcessingState.FAILED,
         time_range=TimeRange(last_hour, now)
     )
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Efficient storage z time-series optimization
- Rich query capabilities
- Full frame history preserved

### Blok 4: Frame tracking dashboard

#### Zadania atomowe

1. **[ ] Grafana dashboard dla frame pipeline**
   - **Metryka**: Real-time view of frames in each stage
   - **Walidacja**:

     ```bash
     # Check dashboard exists
     curl -s http://localhost:3000/api/dashboards/uid/frame-pipeline | \
       jq '.dashboard.panels | length'
     # Should have >10 panels
     ```

   - **Czas**: 1.5h

2. **[ ] Trace exemplars w Prometheus metrics**
   - **Metryka**: Metrics linked do traces
   - **Walidacja**:

     ```bash
     # Query z exemplars
     curl -s 'http://localhost:9090/api/v1/query?query=frame_processing_duration' | \
       jq '.data.result[0].exemplars | length'
     # > 0
     ```

   - **Czas**: 1h

3. **[ ] Frame search interface w Grafana**
   - **Metryka**: Search by frame ID pokazuje full journey
   - **Walidacja**:

     ```bash
     # Variable w dashboard allows frame ID input
     # Shows logs, metrics, and link to trace
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Single view dla frame journey
- Easy debugging failed frames
- Performance insights per stage

## Całościowe metryki sukcesu zadania

1. **Tracking**: Every frame ma unique ID i full history
2. **Observability**: Frame journey visible w traces, logs, metrics
3. **Performance**: <10ms overhead per frame
4. **Search**: Find any frame w <1s

## Deliverables

1. `/src/shared/kernel/domain/frame.py` - Frame domain model
2. `/src/shared/kernel/events/frame_events.py` - Event definitions
3. `/src/contexts/monitoring/domain/frame_tracking.py` - Tracking logic
4. `/src/contexts/monitoring/infrastructure/frame_repository.py` - Storage
5. `/migrations/001_frame_metadata_schema.sql` - Database schema
6. `/config/grafana/dashboards/frame-pipeline.json` - Dashboard
7. `/docs/frame-tracking-guide.md` - Implementation guide

## Narzędzia

- **Python dataclasses**: Domain models
- **SQLAlchemy + asyncpg**: Database access
- **TimescaleDB**: Time-series storage
- **OpenTelemetry Baggage API**: Context propagation
- **Grafana**: Visualization

## Zależności

- **Wymaga**: OpenTelemetry configured (zadanie 5)
- **Blokuje**: Base service template (zadanie 7)

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| High cardinality w metrics | Wysokie | Średni | Limit frame IDs w metrics, use sampling | Prometheus memory spike |
| Storage growth dla metadata | Średnie | Średni | Retention policy, compression | >1GB/day growth |
| Context propagation overhead | Niskie | Niski | Benchmark, optimize baggage size | Latency increase |

## Rollback Plan

1. **Detekcja problemu**: Performance degradation, storage issues
2. **Kroki rollback**:
   - [ ] Disable frame tracking: `FRAME_TRACKING_ENABLED=false`
   - [ ] Continue z basic logging only
   - [ ] Archive existing data
3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [07-tdd-setup.md](./07-tdd-setup.md)
