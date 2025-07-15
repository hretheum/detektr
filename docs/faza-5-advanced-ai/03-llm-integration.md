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

#### Zadania atomowe:
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

#### Metryki sukcesu bloku:
- Provider wybrany data-driven
- Credentials secure
- Provider agnostic code

### Blok 2: Intent recognition implementation

#### Zadania atomowe:
1. **[ ] Projektowanie prompt engineering**
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

#### Metryki sukcesu bloku:
- Natural language → correct action
- Context aware responses
- Graceful degradation

### Blok 3: Cost monitoring i optimization

#### Zadania atomowe:
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

#### Metryki sukcesu bloku:
- Costs tracked realtime
- Cache reduces API calls
- Never exceed budget

### Blok 4: Resilience i error handling

#### Zadania atomowe:
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

#### Metryki sukcesu bloku:
- Service degradation not failure
- No lost requests
- Automatic recovery

### Blok 5: Observability i dashboards

#### Zadania atomowe:
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

#### Metryki sukcesu bloku:
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
- **Blokuje**: Full voice control functionality

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja |
|--------|-------------------|-------|-----------|
| API costs explosion | Średnie | Wysoki | Hard limits, alerts, caching |
| LLM downtime | Niskie | Wysoki | Multi-provider, local fallback |
| Prompt injection | Średnie | Średni | Input sanitization, prompt guards |
| Rate limiting | Wysokie | Średni | Queue, backoff, multiple keys |

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-dashboard-voice-intent.md](./04-dashboard-voice-intent.md)