# Faza 2 / Zadanie 4: Frame tracking z distributed tracing od wejścia

## Cel zadania

Implementować kompleksowy system śledzenia każdej klatki przez cały pipeline z wykorzystaniem OpenTelemetry, zapewniając 100% observability.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja OpenTelemetry SDK**
   - **Metryka**: OTEL SDK zainstalowane, Jaeger dostępny
   - **Walidacja**:

     ```bash
     python -c "import opentelemetry; print(opentelemetry.__version__)"
     curl http://localhost:16686/api/services | jq length
     # >0 services registered
     ```

   - **Czas**: 0.5h

2. **[ ] Test trace propagation**
   - **Metryka**: Context propagation między serwisami działa
   - **Walidacja**:

     ```bash
     python test_trace_propagation.py
     # Trace visible in Jaeger with 2+ services
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Frame ID i metadata model

#### Zadania atomowe

1. **[ ] Implementacja FrameID generator**
   - **Metryka**: Unique IDs, sortable by time
   - **Walidacja**:

     ```python
     from frame_tracking import FrameID
     ids = [FrameID.generate() for _ in range(1000)]
     assert len(set(ids)) == 1000  # all unique
     assert sorted(ids) == ids      # time-ordered
     ```

   - **Czas**: 1.5h

2. **[ ] Frame metadata dataclass**
   - **Metryka**: Serializable, version-compatible
   - **Walidacja**:

     ```python
     meta = FrameMetadata(frame_id="...", timestamp=now())
     json_data = meta.to_json()
     restored = FrameMetadata.from_json(json_data)
     assert meta == restored
     ```

   - **Czas**: 2h

3. **[ ] Trace context injection**
   - **Metryka**: Every frame has trace_id, span_id
   - **Walidacja**:

     ```python
     frame = capture_frame()
     assert frame.trace_context.trace_id is not None
     assert frame.trace_context.is_valid()
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Frame IDs globally unique
- Metadata model complete
- Trace context embedded

### Blok 2: Trace instrumentation

#### Zadania atomowe

1. **[ ] Auto-instrumentation dla capture service**
   - **Metryka**: Every operation creates span
   - **Walidacja**:

     ```bash
     # Capture 10 frames, check Jaeger
     curl "http://localhost:16686/api/traces?service=rtsp-capture&limit=10" | \
       jq '.[].spans | length'
     # Each trace has multiple spans
     ```

   - **Czas**: 2h

2. **[ ] Custom span attributes**
   - **Metryka**: Frame size, camera ID, processing time tracked
   - **Walidacja**:

     ```python
     trace = get_latest_trace("rtsp-capture")
     span = trace.get_span("process_frame")
     assert "frame.size_bytes" in span.attributes
     assert "camera.id" in span.attributes
     ```

   - **Czas**: 1.5h

3. **[ ] Trace propagation przez queue**
   - **Metryka**: Trace context survives Redis/RabbitMQ
   - **Walidacja**:

     ```python
     # Producer side
     producer.send(frame, trace_context)
     # Consumer side
     frame, context = consumer.receive()
     assert context.trace_id == original_trace_id
     ```

   - **Czas**: 2.5h

#### Metryki sukcesu bloku

- All operations traced
- Context propagates correctly
- No orphaned spans

### Blok 3: Tracking dashboard i analytics

#### Zadania atomowe

1. **[ ] Frame journey visualization**
   - **Metryka**: Grafana panel shows frame path
   - **Walidacja**:

     ```bash
     # Query for frame journey
     curl -G http://localhost:3000/api/datasources/proxy/1/api/v1/query \
       --data-urlencode 'query=frame_processing_duration'
     # Returns time series data
     ```

   - **Czas**: 2h

2. **[ ] Trace search by frame ID**
   - **Metryka**: Find any frame's journey in <1s
   - **Walidacja**:

     ```bash
     # Search Jaeger by frame ID
     frame_id="20240315_cam01_000123"
     curl "http://localhost:16686/api/traces?tags=frame.id:$frame_id"
     # Returns complete trace
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Frame tracking operational
- Search/analytics working
- Performance acceptable

## Całościowe metryki sukcesu zadania

1. **Coverage**: 100% frames have complete traces
2. **Performance**: <1% overhead from tracing
3. **Searchability**: Any frame findable by ID in <1s

## Deliverables

1. `/src/shared/frame_tracking/` - Tracking library
2. `/src/shared/telemetry/` - OTEL configuration
3. `/dashboards/frame-tracking.json` - Grafana dashboard
4. `/docs/frame-tracking-guide.md` - Usage documentation
5. `/scripts/trace_analyzer.py` - Trace analysis tool

## Narzędzia

- **OpenTelemetry Python**: Tracing SDK
- **Jaeger**: Trace storage and UI
- **W3C Trace Context**: Standard for propagation
- **contextvars**: Python context management

## Zależności

- **Wymaga**:
  - OpenTelemetry setup (Faza 1)
  - Message broker (poprzednie zadanie)
- **Blokuje**: All downstream services

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Trace data explosion | Wysokie | Średni | Sampling, retention policies | Storage growth >10GB/day |
| Context loss | Średnie | Wysoki | Defensive propagation, validation | Missing spans detected |

## Rollback Plan

1. **Detekcja problemu**:
   - Tracing overhead >5%
   - Missing traces >1%
   - Jaeger unstable

2. **Kroki rollback**:
   - [ ] Disable tracing: Set `OTEL_SDK_DISABLED=true`
   - [ ] Clear trace storage
   - [ ] Restart services without instrumentation
   - [ ] Investigate root cause

3. **Czas rollback**: <5 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-dashboard-frame-pipeline.md](./05-dashboard-frame-pipeline.md)
