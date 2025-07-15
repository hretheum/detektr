# Faza 5 / Zadanie 5: End-to-end trace - głos → intent → akcja

## Cel zadania
Implementować kompletny distributed tracing dla przepływu komend głosowych od nagrania audio przez STT, LLM, aż do wykonania akcji w HA.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja trace propagation**
   - **Metryka**: Context flows through all services
   - **Walidacja**: 
     ```python
     # Trigger voice command
     trace = trigger_voice_command("włącz światło")
     services = [s.service_name for s in trace.spans]
     required = ["audio-capture", "whisper", "llm", "ha-bridge"]
     assert all(svc in services for svc in required)
     ```
   - **Czas**: 0.5h

2. **[ ] Audio correlation test**
   - **Metryka**: Audio chunks linked to trace
   - **Walidacja**: 
     ```python
     trace = get_voice_trace()
     audio_spans = [s for s in trace.spans if "audio" in s.name]
     assert all("audio.chunk_id" in s.attributes for s in audio_spans)
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Audio processing tracing

#### Zadania atomowe:
1. **[ ] Audio capture spans**
   - **Metryka**: Each chunk traced
   - **Walidacja**: 
     ```python
     capture_spans = get_spans_by_name("audio_capture")
     for span in capture_spans:
         assert "audio.duration_ms" in span.attributes
         assert "audio.sample_rate" in span.attributes
         assert "audio.format" in span.attributes
     ```
   - **Czas**: 1.5h

2. **[ ] VAD decision spans**
   - **Metryka**: Voice detection traced
   - **Walidacja**: 
     ```python
     vad_spans = get_spans_by_name("voice_activity_detection")
     assert any(s.attributes["vad.speech_detected"] for s in vad_spans)
     assert "vad.confidence" in vad_spans[0].attributes
     ```
   - **Czas**: 1.5h

3. **[ ] STT processing trace**
   - **Metryka**: Whisper internals visible
   - **Walidacja**: 
     ```python
     stt_span = get_span("whisper_transcribe")
     assert "model.name" in stt_span.attributes
     assert "text.length" in stt_span.attributes
     assert "language.detected" in stt_span.attributes
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Audio flow traced
- VAD decisions visible
- STT details captured

### Blok 2: Intent processing tracing

#### Zadania atomowe:
1. **[ ] LLM request spans**
   - **Metryka**: API calls fully traced
   - **Walidacja**: 
     ```python
     llm_span = get_span("llm_intent_recognition")
     assert "llm.model" in llm_span.attributes
     assert "llm.tokens.prompt" in llm_span.attributes
     assert "llm.tokens.completion" in llm_span.attributes
     assert "llm.cost.dollars" in llm_span.attributes
     ```
   - **Czas**: 2h

2. **[ ] Intent parsing trace**
   - **Metryka**: Show intent extraction
   - **Walidacja**: 
     ```python
     parse_span = get_span("parse_intent")
     assert "intent.type" in parse_span.attributes
     assert "intent.confidence" in parse_span.attributes
     assert "intent.entities" in parse_span.attributes
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- LLM calls traced
- Intent extraction visible
- Costs tracked

### Blok 3: Voice command analytics

#### Zadania atomowe:
1. **[ ] E2E latency breakdown**
   - **Metryka**: Show where time spent
   - **Walidacja**: 
     ```python
     breakdown = analyze_voice_trace(trace_id)
     assert "audio_capture" in breakdown
     assert "stt_processing" in breakdown
     assert "llm_inference" in breakdown
     assert sum(breakdown.values()) == trace.duration
     ```
   - **Czas**: 2h

2. **[ ] Voice command dashboard**
   - **Metryka**: Trace-based analytics
   - **Walidacja**: 
     ```promql
     # Latency by stage
     histogram_quantile(0.95, 
       rate(span_duration_bucket{span.name=~"audio.*|stt.*|llm.*"}[5m])
     )
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Analytics automated
- Bottlenecks visible
- Optimization targets clear

## Całościowe metryki sukcesu zadania

1. **Completeness**: 100% voice commands fully traced
2. **Performance**: <5s voice to action for 90% commands
3. **Detail**: Sufficient for debugging any issue

## Deliverables

1. `/src/tracing/voice/` - Voice tracing library
2. `/scripts/voice_trace_analyzer.py` - Analysis tool
3. `/dashboards/voice-command-traces.json` - Trace dashboard
4. `/docs/voice-tracing-guide.md` - Developer guide
5. `/examples/voice-traces/` - Sample traces

## Narzędzia

- **OpenTelemetry**: Tracing framework
- **Jaeger**: Trace storage
- **Python**: Analysis scripts
- **Grafana**: Visualization

## Zależności

- **Wymaga**: 
  - All voice services traced
  - LLM instrumented
- **Blokuje**: Voice optimization

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Audio trace size | Wysokie | Średni | Sample audio spans, compress | >10MB traces |
| LLM latency variance | Wysokie | Niski | Multiple samples, percentiles | High StdDev |

## Rollback Plan

1. **Detekcja problemu**: 
   - Traces too large
   - Performance impact
   - Missing spans

2. **Kroki rollback**:
   - [ ] Reduce audio span detail
   - [ ] Enable sampling (1:10)
   - [ ] Disable LLM token tracking
   - [ ] Basic tracing only

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tej fazy, przejdź do:
→ [Faza 6 - Optymalizacja](../faza-6-optymalizacja/01-bottleneck-analysis.md)