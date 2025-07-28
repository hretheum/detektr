# Faza 5 / Zadanie 3: LLM integration z metrykami API calls i kosztów

<!--
LLM TASK CONTEXT:
To zadanie z Fazy 5 (Advanced AI).
Prerequisites: Voice processing (STT), message queue, HA Bridge
External APIs: OpenAI/Anthropic (requires API keys)

CRITICAL ASPECTS:
1. Cost control - MUST implement budget limits
2. Circuit breaker - prevent API call storms
3. Caching - reduce repeated calls
4. Multi-provider support - failover capability

SECRETS MANAGEMENT:
- Use Docker secrets or env vars
- NEVER commit API keys
- Test with mock API first
-->

## Cel zadania

Zintegrować zewnętrzne LLM (OpenAI/Anthropic) do rozpoznawania intencji użytkownika z naturalnego języka, z monitorowaniem kosztów i circuit breaker pattern dla resilience.

## Dekompozycja na bloki zadań

### Blok 1: Wybór i konfiguracja LLM provider

#### Zadania atomowe

1. **[ ] Analiza porównawcza LLM providers**
   - **Metryka**: Tabela: cost, latency, accuracy, Polish support
   - **Walidacja**: Benchmark na 100 przykładowych intencji
   - **Czas**: 3h

2. **[ ] Setup API keys i environment**
   - **Metryka**: Secure storage w secrets manager
   - **Walidacja**:

     ```bash
     docker run --rm -e LLM_API_KEY=${LLM_API_KEY} test-image python -c "import os; assert len(os.getenv('LLM_API_KEY')) > 20"
     ```

   - **Czas**: 1h

3. **[ ] Implementacja multi-provider abstraction**
   - **Metryka**: Łatwe przełączanie OpenAI ↔ Anthropic
   - **Walidacja**: Same interface, różne implementacje
   - **Czas**: 3h

#### Metryki sukcesu bloku

- Provider wybrany data-driven
- Credentials secure
- Provider agnostic code

### Blok 2: Intent recognition implementation

#### Zadania atomowe

1. **[ ] Integration z ProcessorClient dla voice transcripts**
   - **Metryka**: LLM intent processor konsumuje z voice:transcribed stream
   - **Walidacja**:

     ```python
     # services/llm-intent/src/main.py
     from services.frame_buffer_v2.src.processors.client import ProcessorClient

     class LLMIntentProcessor(ProcessorClient):
         def __init__(self):
             super().__init__(
                 processor_id="llm-intent-1",
                 capabilities=["intent_recognition", "natural_language"],
                 orchestrator_url=os.getenv("ORCHESTRATOR_URL"),
                 capacity=50,  # LLM calls can handle many requests
                 result_stream="intents:recognized"
             )
             self.llm_client = self._init_llm_client()
             self.intent_cache = Redis()

         async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Dict:
             # Process transcribed voice input
             if b"transcript" not in frame_data:
                 return None

             transcript = frame_data[b"transcript"].decode()

             # Check cache first
             cached = await self.intent_cache.get(transcript)
             if cached:
                 return json.loads(cached)

             # Call LLM for intent recognition
             intent = await self.recognize_intent(transcript)

             # Cache result
             await self.intent_cache.setex(
                 transcript,
                 300,  # 5 min TTL
                 json.dumps(intent)
             )

             return {
                 "frame_id": frame_data[b"frame_id"].decode(),
                 "transcript": transcript,
                 "intent": intent["action"],
                 "entities": intent["entities"],
                 "confidence": intent["confidence"],
                 "processor_id": self.processor_id
             }
     ```

   - **Czas**: 2h

2. **[ ] Projektowanie prompt engineering**
   - **Metryka**: Prompt <500 tokens, clear instructions
   - **Walidacja**: Test na 50 przykładach, >95% accuracy
   - **Czas**: 4h

2. **[ ] Mapowanie intencji do akcji HA**
   - **Metryka**: 20+ intencji zmapowanych
   - **Walidacja**:

     ```yaml
     # intents.yaml validation
     intents:
       - pattern: "włącz światło.*"
         action: "light.turn_on"
         entities: ["room_from_context"]
     ```

   - **Czas**: 3h

3. **[ ] Context management (room, time, user)**
   - **Metryka**: Context retention 5 min
   - **Walidacja**: Conversational test scenarios
   - **Czas**: 4h

4. **[ ] Fallback handling dla unclear intents**
   - **Metryka**: <5% "nie rozumiem" responses
   - **Walidacja**: Edge cases test suite
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Natural language → correct action
- Context aware responses
- Graceful degradation
- Integrated with voice processing pipeline via ProcessorClient

### Blok 3: Cost monitoring i optimization

#### Zadania atomowe

1. **[ ] Token counting przed wysłaniem**
   - **Metryka**: Accurate pre-flight token count
   - **Walidacja**:

     ```python
     estimated = count_tokens(prompt)
     actual = response['usage']['prompt_tokens']
     assert abs(estimated - actual) < 5
     ```

   - **Czas**: 2h

2. **[ ] Cost tracking per request**
   - **Metryka**: Cents precision, all models
   - **Walidacja**: Daily cost report matches billing
   - **Czas**: 3h

3. **[ ] Implementacja cache dla frequent intents**
   - **Metryka**: 40%+ cache hit rate
   - **Walidacja**: Redis cache metrics
   - **Czas**: 3h

4. **[ ] Budget alerts i limits**
   - **Metryka**: Daily/monthly limits enforced
   - **Walidacja**: Hit limit → requests blocked
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Costs tracked realtime
- Cache reduces API calls
- Never exceed budget

### Blok 4: Resilience i error handling

#### Zadania atomowe

1. **[ ] Circuit breaker implementation**
   - **Metryka**: Opens after 5 failures
   - **Walidacja**:

     ```python
     # Force failures
     for i in range(6):
         try:
             llm_client.complete("test")
         except CircuitOpenError:
             assert i >= 5
     ```

   - **Czas**: 3h

2. **[ ] Retry logic z exponential backoff**
   - **Metryka**: 3 retries, 2x backoff
   - **Walidacja**: Network failure simulation
   - **Czas**: 2h

3. **[ ] Fallback to local intent matching**
   - **Metryka**: Basic intents work offline
   - **Walidacja**: Disconnect API, test basics
   - **Czas**: 3h

4. **[ ] Request queuing dla rate limits**
   - **Metryka**: Queue up to 100 requests
   - **Walidacja**: Burst 200 requests, none lost
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Service degradation not failure
- No lost requests
- Automatic recovery

### Blok 5: Observability i dashboards

#### Zadania atomowe

1. **[ ] Prometheus metrics dla LLM calls**
   - **Metryka**: Latency, tokens, cost, errors
   - **Walidacja**:

     ```bash
     curl localhost:8005/metrics | grep llm_
     # llm_requests_total, llm_tokens_used, llm_cost_dollars
     ```

   - **Czas**: 2h

2. **[ ] Distributed tracing dla intent flow**
   - **Metryka**: Voice → STT → LLM → Action traced
   - **Walidacja**: End-to-end trace in Jaeger
   - **Czas**: 2h

3. **[ ] Cost dashboard w Grafana**
   - **Metryka**: Real-time costs, projections
   - **Walidacja**: Dashboard shows $/hour, $/day, $/month
   - **Czas**: 3h

4. **[ ] Intent analytics dashboard**
   - **Metryka**: Top intents, success rate, patterns
   - **Walidacja**: Actionable insights visible
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Full visibility into LLM usage
- Cost tracking accurate
- Performance bottlenecks visible

## Całościowe metryki sukcesu zadania

1. **Accuracy**: >95% intent recognition
2. **Latency**: <3s p99 including API call
3. **Cost**: <$0.02 per request average
4. **Reliability**: 99.9% success rate

## Deliverables

1. `/services/llm-intent/` - Intent recognition service
2. `/config/intents.yaml` - Intent to action mappings
3. `/dashboards/llm-costs.json` - Cost monitoring dashboard
4. `/docs/prompts/intent-recognition.md` - Prompt documentation
5. `/scripts/llm-cost-report.py` - Daily cost reporter

## Narzędzia

- **OpenAI/Anthropic SDK**: LLM integration
- **tiktoken**: Token counting
- **Redis**: Response caching
- **Circuit Breaker**: py-breaker lub własna implementacja

## Zależności

- **Wymaga**:
  - Voice processing (Whisper STT)
  - Message queue for requests
  - HA Bridge for action execution
  - Frame-buffer-v2 z ProcessorClient pattern
  - Result stream voice:transcribed z voice-processing
- **Blokuje**: Full voice control functionality
- **Integracja**: Konsumuje transkrypcje z voice-processing poprzez ProcessorClient - zobacz [Processor Client Migration Guide](../processor-client-migration-guide.md)

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja |
|--------|-------------------|-------|-----------|
| API costs explosion | Średnie | Wysoki | Hard limits, alerts, caching |
| LLM downtime | Niskie | Wysoki | Multi-provider, local fallback |
| Prompt injection | Średnie | Średni | Input sanitization, prompt guards |
| Rate limiting | Wysokie | Średni | Queue, backoff, multiple keys |

## Rollback Plan

1. **Detekcja problemu**:
   - API costs >$100/day
   - Latency >5s consistently
   - Error rate >5%

2. **Kroki rollback**:
   - [ ] Switch to cheaper model (GPT-3.5)
   - [ ] Increase cache TTL
   - [ ] Disable non-critical intents
   - [ ] Fall back to rule-based system

3. **Czas rollback**: <5 min

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **UNIFIED CI/CD DEPLOYMENT**

> **📚 Deployment dla tego serwisu jest zautomatyzowany przez zunifikowany workflow CI/CD.**

### Kroki deployment

1. **[ ] Przygotowanie serwisu do deployment**
   - **Metryka**: LLM intent dodany do workflow matrix
   - **Walidacja**:
     ```bash
     # Sprawdź czy serwis jest w .github/workflows/deploy-self-hosted.yml
     grep "llm-intent" .github/workflows/deploy-self-hosted.yml
     ```
   - **Dokumentacja**: [docs/deployment/guides/new-service.md](../../deployment/guides/new-service.md)

2. **[ ] Konfiguracja API keys**
   - **Metryka**: LLM API keys w SOPS
   - **Konfiguracja**:
     ```bash
     # Edytuj sekrety
     make secrets-edit
     # Dodaj: OPENAI_API_KEY, ANTHROPIC_API_KEY
     # Opcjonalnie: LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
     ```

3. **[ ] Deploy przez GitHub Actions**
   - **Metryka**: Automated deployment via git push
   - **Komenda**:
     ```bash
     git add .
     git commit -m "feat: deploy llm-intent service for natural language understanding"
     git push origin main
     ```
   - **Monitorowanie**: https://github.com/hretheum/bezrobocie/actions

### **📋 Walidacja po deployment:**

```bash
# 1. Sprawdź health serwisu
curl http://nebula:8005/health

# 2. Sprawdź metryki
curl http://nebula:8005/metrics | grep llm_

# 3. Test intent recognition
curl -X POST http://nebula:8005/intent \
  -H "Content-Type: application/json" \
  -d '{"text": "włącz światło w salonie"}' \
  | jq .intent

# 4. Sprawdź cache hit rate
curl http://nebula:8005/metrics | grep llm_cache_hit_ratio

# 5. Sprawdź traces w Jaeger
open http://nebula:16686/search?service=llm-intent
```

### **🔗 Dokumentacja:**
- **Unified Deployment Guide**: [docs/deployment/README.md](../../deployment/README.md)
- **New Service Guide**: [docs/deployment/guides/new-service.md](../../deployment/guides/new-service.md)
- **OpenAI API**: https://platform.openai.com/docs
- **Anthropic API**: https://docs.anthropic.com

### **🔍 Metryki sukcesu bloku:**
- ✅ Serwis w workflow matrix `.github/workflows/deploy-self-hosted.yml`
- ✅ LLM API connections working
- ✅ >95% intent recognition accuracy
- ✅ <3s response time p99
- ✅ Cost tracking operational
- ✅ Cache reducing API calls
- ✅ Zero-downtime deployment

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-dashboard-voice-intent.md](./04-dashboard-voice-intent.md)
