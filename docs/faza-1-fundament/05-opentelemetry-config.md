# Faza 1 / Zadanie 5: Konfiguracja OpenTelemetry SDK

## Cel zadania

Implementacja OpenTelemetry SDK dla Python z auto-instrumentation, eksporterami do Jaeger i Prometheus oraz przykładowym serwisem demonstrującym distributed tracing.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja observability stack działa**
   - **Metryka**: Jaeger, Prometheus, Grafana responding
   - **Walidacja**:

     ```bash
     for url in http://localhost:16686 http://localhost:9090 http://localhost:3000; do
       curl -s -o /dev/null -w "%{http_code}" $url | grep -E "200|302"
     done
     ```

   - **Czas**: 0.5h

2. **[ ] Python environment z Poetry/pip-tools**
   - **Metryka**: Python 3.11+, dependency management ready
   - **Walidacja**:

     ```bash
     python --version | grep -E "3\.(11|12)"
     poetry --version || pip-compile --version
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: OpenTelemetry SDK setup

#### Zadania atomowe

1. **[ ] Instalacja OpenTelemetry packages**
   - **Metryka**: Core packages + instrumentations zainstalowane
   - **Walidacja**:

     ```bash
     pip list | grep -E "opentelemetry-(api|sdk|instrumentation)" | wc -l
     # Powinno zwrócić >= 10 packages
     ```

   - **Czas**: 1h

2. **[ ] Utworzenie telemetry configuration module**
   - **Metryka**: Centralna konfiguracja dla traces, metrics, logs
   - **Walidacja**:

     ```python
     # Test import
     from src.shared.telemetry import setup_telemetry
     tracer, meter, logger = setup_telemetry("test-service")
     assert tracer is not None
     ```

   - **Czas**: 1.5h

3. **[ ] Konfiguracja exporters (Jaeger, Prometheus)**
   - **Metryka**: Traces idą do Jaeger, metrics do Prometheus
   - **Walidacja**:

     ```bash
     # Run test service
     python -m src.examples.telemetry_test
     # Check Jaeger
     curl -s "http://localhost:16686/api/services" | jq '.data[]' | grep "test-service"
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- OpenTelemetry SDK skonfigurowany dla traces i metrics
- Auto-instrumentation dla common libraries (requests, FastAPI, SQLAlchemy)
- Environment variables control configuration

### Blok 2: Auto-instrumentation setup

#### Zadania atomowe

1. **[ ] Instrumentacja dla FastAPI**
   - **Metryka**: Automatic spans dla wszystkich endpoints
   - **Walidacja**:

     ```python
     # Test endpoint pokazuje span w Jaeger
     # GET /health powinien utworzyć span "GET /health"
     ```

   - **Czas**: 1h

2. **[ ] Instrumentacja dla database (SQLAlchemy/asyncpg)**
   - **Metryka**: Query spans z SQL statements
   - **Walidacja**:

     ```bash
     # Po wykonaniu query
     curl -s "http://localhost:16686/api/traces/{trace_id}" | \
       jq '.data[0].spans[] | select(.operationName | contains("SELECT"))'
     ```

   - **Czas**: 1h

3. **[ ] Instrumentacja dla HTTP clients i queues**
   - **Metryka**: Outgoing HTTP i queue operations traced
   - **Walidacja**:

     ```python
     # Test pokazuje nested spans
     # parent_span -> http_request -> queue_publish
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Zero-code instrumentation dla major libraries
- Spans zawierają istotne attributes (status code, query, etc.)
- Context propagation działa między serwisami

### Blok 3: Custom instrumentation helpers

#### Zadania atomowe

1. **[ ] Decorator @traced dla custom functions**
   - **Metryka**: Simple decorator automatycznie tworzy spans
   - **Walidacja**:

     ```python
     @traced
     def process_frame(frame_id: str):
         pass

     # Wywołanie tworzy span "process_frame" z frame_id jako attribute
     ```

   - **Czas**: 1h

2. **[ ] Context propagation dla frame tracking**
   - **Metryka**: Frame ID propagowany przez cały pipeline
   - **Walidacja**:

     ```python
     # Wszystkie spans dla frame mają ten sam trace_id
     # i attribute "frame.id" = frame_id
     ```

   - **Czas**: 1h

3. **[ ] Metrics helpers (counters, histograms)**
   - **Metryka**: Łatwe tworzenie custom metrics
   - **Walidacja**:

     ```bash
     # Prometheus pokazuje custom metrics
     curl -s http://localhost:9090/api/v1/label/__name__/values | \
       jq '.data[]' | grep "detektor_"
     ```

   - **Czas**: 0.5h

#### Metryki sukcesu bloku

- Developers mogą łatwo dodać tracing do kodu
- Frame tracking działa end-to-end
- Custom metrics widoczne w Prometheus

### Blok 4: Example service z full observability

#### Zadania atomowe

1. **[ ] Implementacja example frame processor service**
   - **Metryka**: Serwis pokazujący best practices
   - **Walidacja**:

     ```bash
     docker run --rm detektor/example-service:latest
     # Health check przechodzi
     curl http://localhost:8080/health
     ```

   - **Czas**: 1.5h

2. **[ ] End-to-end trace przykład**
   - **Metryka**: Trace pokazuje: API -> processing -> storage -> notification
   - **Walidacja**:

     ```bash
     # Trigger example processing
     curl -X POST http://localhost:8080/process -d '{"frame_id": "test-123"}'
     # Check full trace in Jaeger
     ```

   - **Czas**: 1h

3. **[ ] Dashboard dla example service**
   - **Metryka**: Grafana dashboard z metrics, logs, trace links
   - **Walidacja**:

     ```bash
     # Import dashboard
     curl -s http://localhost:3000/api/dashboards/uid/example-service | \
       jq '.dashboard.title'
     # "Example Service Overview"
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Example service jako template dla nowych serwisów
- Full observability od początku
- Documentation w kodzie

## Całościowe metryki sukcesu zadania

1. **Integration**: OpenTelemetry -> Jaeger + Prometheus działa
2. **Auto-instrumentation**: Major libraries traced automatycznie
3. **Developer Experience**: Simple decorators i helpers
4. **Example**: Working service demonstrating best practices

## Deliverables

1. `/src/shared/telemetry/__init__.py` - Main telemetry module
2. `/src/shared/telemetry/decorators.py` - @traced decorator
3. `/src/shared/telemetry/metrics.py` - Metrics helpers
4. `/src/shared/telemetry/config.py` - Configuration
5. `/src/examples/telemetry_service/` - Example service
6. `/config/otel-collector-config.yml` - Collector config (optional)
7. `/docs/telemetry-guide.md` - Developer guide

## Narzędzia

- **OpenTelemetry Python**: Core SDK
- **opentelemetry-instrumentation-***: Auto instrumentation packages
- **opentelemetry-exporter-jaeger**: Trace exporter
- **opentelemetry-exporter-prometheus**: Metrics exporter
- **pytest + pytest-mock**: Testing

## Zależności

- **Wymaga**: Observability stack running (zadanie 4)
- **Blokuje**: Base service template (zadanie 7)

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Performance overhead from tracing | Średnie | Średni | Sampling strategy, async exporters | Latency increase >10% |
| Context propagation issues | Średnie | Wysoki | Thorough testing, clear examples | Missing spans |
| Version conflicts między OTel packages | Niskie | Średni | Pin versions, test matrix | Import errors |

## Rollback Plan

1. **Detekcja problemu**: High latency, missing traces, import errors
2. **Kroki rollback**:
   - [ ] Disable tracing via env var: `OTEL_SDK_DISABLED=true`
   - [ ] Remove instrumentation decorators
   - [ ] Fallback to basic logging
3. **Czas rollback**: <5 min (env var), <30 min (code changes)

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [06-frame-tracking-design.md](./06-frame-tracking-design.md)
