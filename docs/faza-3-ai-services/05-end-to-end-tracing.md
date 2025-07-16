# Faza 3 / Zadanie 5: Trace - pełny flow od klatki do wyniku AI

## Cel zadania

Implementować kompletny distributed tracing pokazujący przepływ klatki przez wszystkie serwisy AI z zachowaniem kontekstu i metryk.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja trace propagation**
   - **Metryka**: Context propaguje między serwisami
   - **Walidacja**:

     ```bash
     # Send test frame, check trace
     python send_test_frame.py --with-trace
     sleep 5
     curl "http://localhost:16686/api/traces?service=rtsp-capture&limit=1" | \
       jq '.[0].spans | length'
     # >5 spans (multiple services)
     ```

   - **Czas**: 0.5h

2. **[ ] Trace storage capacity**
   - **Metryka**: Jaeger ma 10GB+ storage
   - **Walidacja**:

     ```bash
     docker exec jaeger df -h /badger
     # Sufficient space available
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Trace instrumentation enhancement

#### Zadania atomowe

1. **[ ] Rich span attributes**
   - **Metryka**: Each span has frame_id, size, timestamps
   - **Walidacja**:

     ```python
     trace = get_latest_trace()
     for span in trace.spans:
         assert "frame.id" in span.attributes
         assert "processing.duration_ms" in span.attributes
     ```

   - **Czas**: 2h

2. **[ ] AI-specific trace data**
   - **Metryka**: Model name, confidence, object count in spans
   - **Walidacja**:

     ```python
     ai_span = get_span_by_name("face_detection")
     assert "model.name" in ai_span.attributes
     assert "detection.count" in ai_span.attributes
     assert "confidence.mean" in ai_span.attributes
     ```

   - **Czas**: 2h

3. **[ ] Error tracking in traces**
   - **Metryka**: Failures marked with error details
   - **Walidacja**:

     ```python
     # Force error, check trace
     failed_trace = trigger_error_scenario()
     error_spans = [s for s in failed_trace.spans if s.status.code == ERROR]
     assert len(error_spans) > 0
     assert error_spans[0].status.message != ""
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Rich trace context
- AI metrics in traces
- Errors properly tracked

### Blok 2: Trace analysis tools

#### Zadania atomowe

1. **[ ] Trace timeline visualization**
   - **Metryka**: Gantt chart of frame processing
   - **Walidacja**:

     ```bash
     python generate_trace_timeline.py --frame-id test123
     # Outputs timeline.html with visualization
     ```

   - **Czas**: 2h

2. **[ ] Bottleneck detection script**
   - **Metryka**: Identify slowest operations
   - **Walidacja**:

     ```bash
     python analyze_bottlenecks.py --service all --period 1h
     # Output: Top 5 slowest operations with stats
     ```

   - **Czas**: 2h

3. **[ ] Trace comparison tool**
   - **Metryka**: Compare fast vs slow traces
   - **Walidacja**:

     ```python
     fast, slow = get_trace_percentiles(50, 95)
     diff = compare_traces(fast, slow)
     print(diff.largest_delta)  # Shows biggest difference
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Analysis automated
- Bottlenecks visible
- Performance patterns clear

### Blok 3: Integration with dashboards

#### Zadania atomowe

1. **[ ] Jaeger links in Grafana**
   - **Metryka**: Click from metric to trace
   - **Walidacja**:

     ```javascript
     // Panel has trace links
     panel.fieldConfig.defaults.links[0].url
       .includes("jaeger/trace/${__value.raw}")
     ```

   - **Czas**: 1.5h

2. **[ ] Trace statistics dashboard**
   - **Metryka**: Span duration percentiles
   - **Walidacja**:

     ```promql
     histogram_quantile(0.95,
       rate(span_duration_bucket{service="object-detection"}[5m]))
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Seamless integration
- Stats accessible
- Navigation smooth

## Całościowe metryki sukcesu zadania

1. **Coverage**: 100% of AI operations traced
2. **Detail**: Sufficient attributes for debugging
3. **Performance**: <5% overhead from tracing

## Deliverables

1. `/src/shared/tracing/` - Enhanced tracing library
2. `/scripts/trace_analysis/` - Analysis tools
3. `/dashboards/trace-analytics.json` - Trace stats dashboard
4. `/docs/tracing-guide.md` - Developer guide
5. `/examples/trace-samples.json` - Example traces

## Narzędzia

- **OpenTelemetry**: Tracing framework
- **Jaeger**: Trace storage/UI
- **Python**: Analysis scripts
- **Grafana**: Trace visualization

## Zależności

- **Wymaga**:
  - All services instrumented
  - Jaeger deployed
- **Blokuje**: Performance optimization

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Trace data volume | Wysokie | Średni | Sampling, retention limits | >1GB/hour traces |
| Context propagation loss | Niskie | Wysoki | Defensive coding, validation | Orphaned spans |

## Rollback Plan

1. **Detekcja problemu**:
   - Tracing overhead >10%
   - Traces incomplete
   - Jaeger unstable

2. **Kroki rollback**:
   - [ ] Increase sampling rate (reduce volume)
   - [ ] Disable detailed attributes
   - [ ] Switch to basic tracing
   - [ ] Clear trace storage if full

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [06-performance-testing.md](./06-performance-testing.md)
