# Faza 2 / Zadanie 4: Frame tracking z distributed tracing od wejścia

## Cel zadania

Implementować kompleksowy system śledzenia każdej klatki przez cały pipeline z wykorzystaniem OpenTelemetry, zapewniając 100% observability.

## Blok 0: Prerequisites check NA SERWERZE NEBULA ⚠️ ✅

#### Zadania atomowe

1. **[x] Weryfikacja OpenTelemetry setup na Nebuli**
   - **Metryka**: OTEL SDK zainstalowane, Jaeger dostępny
   - **Walidacja NA SERWERZE**:

     ```bash
     # Check Jaeger availability
     curl -s http://nebula:16686/api/services | jq length
     # >0 services registered

     # Verify OTEL collector
     curl -s http://nebula:4318/v1/traces
     # Returns 405 (endpoint active but needs POST)
     ```
   - **Quality Gate**: Jaeger UI accessible
   - **Guardrails**: OTEL collector accepting traces
   - **Czas**: 0.5h

2. **[x] Test trace propagation na Nebuli**
   - **Metryka**: Context propagation między serwisami działa
   - **Walidacja NA SERWERZE**:

     ```bash
     # Run trace test between services
     ssh nebula "docker exec example-otel python /app/test_trace_propagation.py"
     # Trace visible in Jaeger with 2+ services

     # Verify in Jaeger UI
     open http://nebula:16686/search?service=example-otel
     ```
   - **Quality Gate**: Multi-service traces visible
   - **Guardrails**: No orphaned spans
   - **Czas**: 0.5h

3. **[x] Weryfikacja storage dla traces**
   - **Metryka**: Sufficient space for trace data
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "df -h /var/lib/docker/volumes/jaeger_data"
     # >20GB available

     ssh nebula "docker exec jaeger-collector curl -s localhost:14269/metrics | grep jaeger_collector_spans_received_total"
     # Collector operational
     ```
   - **Quality Gate**: Storage configured
   - **Guardrails**: Retention policy set
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Frame ID i metadata model ✅

#### Zadania atomowe

1. **[x] Implementacja FrameID generator**
   - **Metryka**: Unique IDs, sortable by time
   - **Walidacja**:

     ```python
     from frame_tracking import FrameID
     ids = [FrameID.generate() for _ in range(1000)]
     assert len(set(ids)) == 1000  # all unique
     assert sorted(ids) == ids      # time-ordered
     ```

   - **Czas**: 1.5h

2. **[x] Frame metadata dataclass**
   - **Metryka**: Serializable, version-compatible
   - **Walidacja**:

     ```python
     meta = FrameMetadata(frame_id="...", timestamp=now())
     json_data = meta.to_json()
     restored = FrameMetadata.from_json(json_data)
     assert meta == restored
     ```

   - **Czas**: 2h

3. **[x] Trace context injection**
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

### Blok 2: Trace instrumentation ✅

#### Zadania atomowe

1. **[x] Auto-instrumentation dla capture service**
   - **Metryka**: Every operation creates span
   - **Walidacja**:

     ```bash
     # Capture 10 frames, check Jaeger
     curl "http://localhost:16686/api/traces?service=rtsp-capture&limit=10" | \
       jq '.[].spans | length'
     # Each trace has multiple spans
     ```

   - **Czas**: 2h

2. **[x] Custom span attributes**
   - **Metryka**: Frame size, camera ID, processing time tracked
   - **Walidacja**:

     ```python
     trace = get_latest_trace("rtsp-capture")
     span = trace.get_span("process_frame")
     assert "frame.size_bytes" in span.attributes
     assert "camera.id" in span.attributes
     ```

   - **Czas**: 1.5h

3. **[x] Trace propagation przez queue**
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

### Blok 3: Tracking dashboard i analytics ✅

#### Zadania atomowe

1. **[x] Frame journey visualization**
   - **Metryka**: Grafana panel shows frame path
   - **Walidacja**:

     ```bash
     # Query for frame journey
     curl -G http://localhost:3000/api/datasources/proxy/1/api/v1/query \
       --data-urlencode 'query=frame_processing_duration'
     # Returns time series data
     ```

   - **Czas**: 2h

2. **[x] Trace search by frame ID**
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

### Blok 4: CI/CD Pipeline dla Frame Tracking (LIBRARY ONLY) ⚠️

> **UWAGA**: Frame-tracking to biblioteka, nie serwis. Nie potrzebuje własnego deploymentu.

#### Zadania atomowe

1. **[ ] Utworzenie shared library package**
   - **Metryka**: frame-tracking jako reusable package
   - **Walidacja**:
     ```bash
     # Build and test package
     cd services/shared/frame-tracking
     python -m build
     pip install dist/frame_tracking-*.whl
     python -c "from frame_tracking import FrameID; print(FrameID.generate())"
     ```
   - **Quality Gate**: Package installable
   - **Guardrails**: All tests passing
   - **Czas**: 1.5h

2. **[x] ~~Dockerfile dla frame-tracking service~~ SKIPPED**
   - **Powód**: Frame-tracking to biblioteka, nie serwis
   - **Zamiast tego**: Każdy serwis instaluje bibliotekę lokalnie
   - **Przykład**: Zobacz `services/rtsp-capture/Dockerfile`

3. **[ ] Weryfikacja testów biblioteki w CI**
   - **Metryka**: Testy biblioteki uruchamiane przy każdym PR
   - **Walidacja**:
     ```bash
     # Sprawdź czy testy są włączone w pr-checks.yml
     grep -n "frame-tracking" .github/workflows/pr-checks.yml

     # Uruchom testy lokalnie
     cd services/shared/frame-tracking
     pytest tests/ -v
     ```
   - **Quality Gate**: 80%+ code coverage
   - **Guardrails**: Testy przechodzą w CI
   - **Czas**: 0.5h

### Blok 5: WALIDACJA BIBLIOTEKI W SERWISACH 🔄

> **📚 ZMIANA**: Ponieważ frame-tracking to biblioteka, nie ma własnego deploymentu. Zamiast tego walidujemy jej użycie w innych serwisach.

#### Zadania atomowe

1. **[ ] Weryfikacja integracji w rtsp-capture**
   - **Metryka**: rtsp-capture używa frame-tracking poprawnie
   - **Walidacja**:
     ```bash
     # Sprawdź logi rtsp-capture
     curl -s http://nebula:8080/health | jq .
     docker logs rtsp-capture | grep "frame_tracking"

     # Sprawdź czy generowane są frame IDs
     docker exec rtsp-capture python -c "from frame_tracking import FrameID; print(FrameID.generate())"
     ```
   - **Quality Gate**: Frame IDs są generowane
   - **Czas**: 15min

2. **[ ] Weryfikacja trace propagation**
   - **Metryka**: Traces z frame.id widoczne w Jaeger
   - **Walidacja**:
     ```bash
     # Sprawdź czy rtsp-capture wysyła traces
     curl -s "http://nebula:16686/api/services" | jq '. | map(select(. == "rtsp-capture"))'

     # Znajdź trace z frame.id
     curl -s "http://nebula:16686/api/traces?service=rtsp-capture&limit=10" | \
       jq '.[].spans[].tags[] | select(.key == "frame.id")'
     ```
   - **Quality Gate**: Każdy trace ma frame.id
   - **Czas**: 15min

3. **[ ] Test frame search functionality**
   - **Metryka**: Można wyszukać klatkę po ID
   - **Walidacja**:
     ```bash
     # Pobierz przykładowy frame ID
     FRAME_ID=$(curl -s "http://nebula:16686/api/traces?service=rtsp-capture&limit=1" | \
       jq -r '.[0].spans[0].tags[] | select(.key == "frame.id") | .value')

     # Użyj trace_analyzer.py
     ./scripts/trace_analyzer.py search "$FRAME_ID" --jaeger-url http://nebula:16686
     ```
   - **Quality Gate**: Trace znaleziony w <1s
   - **Czas**: 15min

4. **[ ] Performance validation biblioteki**
   - **Metryka**: <1ms overhead na klatkę
   - **Walidacja**:
     ```bash
     # Sprawdź metryki w Grafanie
     open http://nebula:3000/d/frame-tracking

     # Porównaj latency z i bez frame-tracking
     curl -s http://nebula:8080/metrics | grep frame_processing_duration
     ```
   - **Quality Gate**: Overhead <1ms
   - **Czas**: 30min

5. **[x] ~~Dashboard setup~~ JUŻ ZROBIONE**
   - **Status**: Dashboard utworzony w Bloku 3
   - **Dostępny**: http://nebula:3000/d/frame-tracking
   - **Dokumentacja**: dashboards/README.md

6. **[ ] Dokumentacja integracji**
   - **Metryka**: Każdy serwis wie jak użyć biblioteki
   - **Tasks**:
     - [ ] Utwórz `docs/guides/frame-tracking-integration.md`
     - [ ] Dodaj przykłady dla różnych serwisów
     - [ ] Zaktualizuj README główne
   - **Quality Gate**: Dokumentacja kompletna
   - **Czas**: 1h

#### 🚀 Quick Reference

```bash
# Deploy
git push origin main

# Check deployment
gh run list --workflow=deploy-self-hosted.yml --limit=1

# Verify service
curl http://nebula:8006/health
curl http://nebula:16686/api/services

# View traces
open http://nebula:16686
```

#### 📚 Links
- [Unified Deployment Guide](../../deployment/README.md)
- [Service Deployment Docs](../../deployment/services/frame-tracking.md)
- [Troubleshooting](../../deployment/troubleshooting/common-issues.md)

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

## CI/CD i Deployment Guidelines

### Image Registry Structure
```
ghcr.io/hretheum/detektr/
├── frame-tracking:latest      # Main tracking service
├── frame-tracking:main-SHA    # Tagged versions
└── frame-tracking-lib:latest  # Shared library package
```

### Deployment Checklist
- [ ] Frame tracking library published
- [ ] Service images built with OTEL
- [ ] docker-compose.tracking.yml ready
- [ ] Jaeger configured for retention
- [ ] Grafana dashboards imported
- [ ] Performance baselines established

### Monitoring Endpoints
- Frame tracking health: `http://nebula:8006/health`
- Frame tracking metrics: `http://nebula:8006/metrics`
- Jaeger UI: `http://nebula:16686`
- OTEL collector: `http://nebula:4318/v1/traces`

### Key Configuration
```yaml
# OTEL environment variables
OTEL_SERVICE_NAME: frame-tracking
OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4318
OTEL_TRACES_EXPORTER: otlp
OTEL_METRICS_EXPORTER: prometheus
OTEL_RESOURCE_ATTRIBUTES: deployment.environment=production

# Sampling configuration
OTEL_TRACES_SAMPLER: traceidratio
OTEL_TRACES_SAMPLER_ARG: 0.1  # 10% sampling in production
```

### Trace Search Queries
```bash
# Find frame by ID
curl "http://nebula:16686/api/traces?tags=frame.id:FRAME_ID"

# Find slow frames (>1s processing)
curl "http://nebula:16686/api/traces?minDuration=1000ms&service=frame-tracking"

# Find failed frames
curl "http://nebula:16686/api/traces?tags=error:true&service=frame-tracking"
```

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-dashboard-frame-pipeline.md](./05-dashboard-frame-pipeline.md)
