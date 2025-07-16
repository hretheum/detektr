# Faza 4 / Zadanie 4: Trace od detekcji do wykonania automatyzacji

## Cel zadania

Implementować kompletny distributed tracing pokazujący całą ścieżkę od wykrycia obiektu do wykonania akcji w Home Assistant.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja trace continuity**
   - **Metryka**: Trace context propaguje przez wszystkie serwisy
   - **Walidacja**:

     ```python
     # Trigger full automation
     trace = trigger_and_get_trace("motion_detected")
     services = [span.service_name for span in trace.spans]
     assert all(svc in services for svc in
                ["rtsp-capture", "object-detection", "ha-bridge"])
     ```

   - **Czas**: 0.5h

2. **[ ] HA trace integration test**
   - **Metryka**: HA actions appear in traces
   - **Walidacja**:

     ```bash
     # Check if HA spans are captured
     curl "http://localhost:16686/api/services" | jq '.data[]' | grep home-assistant
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Decision tracing

#### Zadania atomowe

1. **[ ] Rule evaluation spans**
   - **Metryka**: Each rule check creates span
   - **Walidacja**:

     ```python
     trace = get_automation_trace()
     rule_spans = [s for s in trace.spans if "rule_eval" in s.name]
     assert len(rule_spans) > 0
     for span in rule_spans:
         assert "rule.name" in span.attributes
         assert "rule.result" in span.attributes
     ```

   - **Czas**: 2h

2. **[ ] Decision tree visualization**
   - **Metryka**: Show why automation triggered
   - **Walidacja**:

     ```python
     decision = extract_decision_tree(trace)
     assert decision.root.name == "automation_trigger"
     assert len(decision.conditions_checked) > 0
     assert decision.final_action is not None
     ```

   - **Czas**: 2.5h

#### Metryki sukcesu bloku

- Decision process visible
- Rule evaluation tracked
- Logic path clear

### Blok 2: Action execution tracing

#### Zadania atomowe

1. **[ ] HA API call spans**
   - **Metryka**: Each HA call fully traced
   - **Walidacja**:

     ```python
     ha_spans = get_spans_by_service("ha-bridge")
     for span in ha_spans:
         assert "ha.service" in span.attributes
         assert "ha.entity_id" in span.attributes
         assert "ha.response_code" in span.attributes
     ```

   - **Czas**: 1.5h

2. **[ ] State verification spans**
   - **Metryka**: Track if action had effect
   - **Walidacja**:

     ```python
     verify_span = get_span("verify_state_change")
     assert verify_span.attributes["state.before"] != \
            verify_span.attributes["state.after"]
     assert verify_span.attributes["change.confirmed"] == True
     ```

   - **Czas**: 2h

3. **[ ] Error propagation**
   - **Metryka**: Failures tracked through trace
   - **Walidacja**:

     ```python
     # Force HA error
     failed_trace = trigger_with_ha_error()
     error_spans = [s for s in failed_trace.spans if s.status.is_error]
     assert len(error_spans) > 0
     assert "home-assistant" in error_spans[-1].attributes["error.source"]
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- HA actions fully traced
- State changes verified
- Errors properly tracked

### Blok 3: Trace analysis tools

#### Zadania atomowe

1. **[ ] Automation trace analyzer**
   - **Metryka**: Extract insights from traces
   - **Walidacja**:

     ```bash
     python analyze_automation_trace.py --trace-id abc123
     # Output:
     # - Total duration: 1.2s
     # - Bottleneck: ha_api_call (800ms)
     # - Rules evaluated: 5
     # - Actions executed: 2
     ```

   - **Czas**: 2h

2. **[ ] Trace comparison for optimization**
   - **Metryka**: Compare fast vs slow automations
   - **Walidacja**:

     ```python
     comparison = compare_automation_traces(fast_id, slow_id)
     print(comparison.largest_diff)  # "ha_api_call: +500ms"
     print(comparison.suggestions)   # ["Cache entity states"]
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Insights extractable
- Optimizations identifiable
- Comparisons easy

## Całościowe metryki sukcesu zadania

1. **Completeness**: 100% automation steps traced
2. **Clarity**: Decision logic visible in traces
3. **Performance**: E2E latency <2s for 95% automations

## Deliverables

1. `/src/tracing/automation/` - Automation tracing library
2. `/scripts/trace_analysis/automation/` - Analysis tools
3. `/dashboards/automation-traces.json` - Trace dashboard
4. `/docs/automation-tracing.md` - Developer guide
5. `/examples/automation-traces/` - Sample traces

## Narzędzia

- **OpenTelemetry**: Tracing framework
- **Jaeger**: Trace storage
- **Python**: Analysis scripts
- **graphviz**: Decision tree viz

## Zależności

- **Wymaga**:
  - All services traced
  - HA bridge instrumented
- **Blokuje**: Performance optimization

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Trace size explosion | Średnie | Średni | Sampling, span limits | >1000 spans per trace |
| HA timing variations | Wysokie | Niski | Multiple samples, percentiles | High variance in traces |

## Rollback Plan

1. **Detekcja problemu**:
   - Traces incomplete
   - Performance degraded
   - Storage full

2. **Kroki rollback**:
   - [ ] Reduce trace verbosity
   - [ ] Enable sampling (1:10)
   - [ ] Clear old traces
   - [ ] Disable decision spans temporarily

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-scenario-testing.md](./05-scenario-testing.md)
