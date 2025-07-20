# Faza 2 / Zadanie 4: Frame tracking z distributed tracing od wejścia

## Cel zadania

Implementować kompleksowy system śledzenia każdej klatki przez cały pipeline z wykorzystaniem OpenTelemetry, zapewniając 100% observability.

## Blok 0: Prerequisites check NA SERWERZE NEBULA ⚠️

#### Zadania atomowe

1. **[ ] Weryfikacja OpenTelemetry setup na Nebuli**
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

2. **[ ] Test trace propagation na Nebuli**
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

3. **[ ] Weryfikacja storage dla traces**
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

### Blok 4: CI/CD Pipeline dla Frame Tracking

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

2. **[ ] Dockerfile dla frame-tracking service**
   - **Metryka**: Service image z OTEL instrumentation
   - **Walidacja**:
     ```bash
     docker build -f services/frame-tracking/Dockerfile -t frame-tracking:test .
     docker run --rm frame-tracking:test python -m frame_tracking.health
     # Health check passed
     ```
   - **Quality Gate**: Image <200MB
   - **Guardrails**: OTEL auto-instrumentation included
   - **Czas**: 1h

3. **[ ] GitHub Actions dla tracking components**
   - **Metryka**: Automated builds and tests
   - **Walidacja**:
     ```bash
     # Check workflow
     cat .github/workflows/frame-tracking-deploy.yml
     git push origin main
     # Monitor build: https://github.com/hretheum/bezrobocie/actions
     ```
   - **Quality Gate**: Build <5min
   - **Guardrails**: Integration tests included
   - **Czas**: 1.5h

### Blok 5: DEPLOYMENT NA NEBULA I WALIDACJA ⚠️

#### Zadania atomowe

1. **[ ] Deploy frame-tracking service na Nebuli**
   - **Metryka**: Service running with tracing enabled
   - **Walidacja NA SERWERZE**:
     ```bash
     # Deploy service
     ssh nebula "cd /opt/detektor && docker-compose -f docker-compose.yml -f docker-compose.tracking.yml pull"
     ssh nebula "cd /opt/detektor && docker-compose -f docker-compose.yml -f docker-compose.tracking.yml up -d frame-tracking"

     # Health check
     curl -s http://nebula:8006/health | jq .status
     # "healthy"
     ```
   - **Quality Gate**: Service healthy
   - **Guardrails**: Connected to Jaeger
   - **Czas**: 1h

2. **[ ] E2E trace validation na produkcji**
   - **Metryka**: Complete traces from capture to storage
   - **Walidacja NA SERWERZE**:
     ```bash
     # Generate test frames
     ssh nebula "docker exec frame-tracking python -m frame_tracking.test_generator --count 100"

     # Verify traces in Jaeger
     curl -s "http://nebula:16686/api/traces?service=frame-tracking&limit=10" | jq '.[].spans | length'
     # Multiple spans per trace

     # Check frame IDs in traces
     curl -s "http://nebula:16686/api/traces?service=frame-tracking&limit=1" | \
       jq '.[0].spans[].tags[] | select(.key=="frame.id")'
     ```
   - **Quality Gate**: 100% traces have frame IDs
   - **Guardrails**: No missing spans
   - **Czas**: 1.5h

3. **[ ] Performance impact assessment**
   - **Metryka**: <1% overhead from tracing
   - **Walidacja NA SERWERZE**:
     ```bash
     # Baseline without tracing
     ssh nebula "OTEL_SDK_DISABLED=true docker exec frame-tracking python -m frame_tracking.benchmark"
     # Record throughput

     # With tracing enabled
     ssh nebula "docker exec frame-tracking python -m frame_tracking.benchmark"
     # Compare throughput (should be within 1%)
     ```
   - **Quality Gate**: Performance degradation <1%
   - **Guardrails**: CPU overhead <5%
   - **Czas**: 2h

4. **[ ] Grafana dashboard deployment**
   - **Metryka**: Frame tracking visualizations live
   - **Walidacja NA SERWERZE**:
     ```bash
     # Import dashboard
     ssh nebula "curl -X POST http://localhost:3000/api/dashboards/db \
       -H 'Content-Type: application/json' \
       -d @/opt/detektor/dashboards/frame-tracking.json"

     # Verify data
     open http://nebula:3000/d/frame-tracking/frame-journey
     # Shows frame processing times and paths
     ```
   - **Quality Gate**: All panels populated
   - **Guardrails**: Query performance <1s
   - **Czas**: 1h

5. **[ ] 24h trace retention test**
   - **Metryka**: Traces searchable for 24h+
   - **Walidacja NA SERWERZE**:
     ```bash
     # Generate frames with known IDs
     ssh nebula "docker exec frame-tracking python -m frame_tracking.generate_test_data"

     # After 24h, search for old frames
     frame_id="test_$(date -d '24 hours ago' +%Y%m%d_%H%M%S)"
     curl -s "http://nebula:16686/api/traces?tags=frame.id:$frame_id"
     # Should return trace
     ```
   - **Quality Gate**: 24h retention working
   - **Guardrails**: Storage growth sustainable
   - **Czas**: 24h

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
ghcr.io/hretheum/bezrobocie-detektor/
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
