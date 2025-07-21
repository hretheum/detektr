# Faza 5 / Zadanie 1: LLM API Integration (OpenAI/Anthropic)

## Cel zadania

Zintegrować Large Language Models dla zaawansowanej analizy intencji użytkownika, interpretacji złożonych komend i kontekstowego podejmowania decyzji.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites

#### Zadania atomowe

1. **[ ] Analiza API OpenAI vs Anthropic**
   - **Metryka**: Cost/performance comparison
   - **Walidacja**: Decision matrix complete
   - **Czas**: 2h

2. **[ ] Setup API keys i rate limits**
   - **Metryka**: Secure API configuration
   - **Walidacja**: API connectivity test
   - **Czas**: 1h

### Blok 1: LLM abstraction layer

#### Zadania atomowe

1. **[ ] TDD: LLM provider interface**
   - **Metryka**: Provider-agnostic design
   - **Walidacja**: `pytest tests/test_llm_interface.py`
   - **Czas**: 2h

2. **[ ] Implementacja OpenAI adapter**
   - **Metryka**: GPT-4 integration working
   - **Walidacja**: API call success test
   - **Czas**: 3h

3. **[ ] Implementacja Anthropic adapter**
   - **Metryka**: Claude integration working
   - **Walidacja**: API call success test
   - **Czas**: 3h

### Blok 2: Prompt engineering framework

#### Zadania atomowe

1. **[ ] Prompt template system**
   - **Metryka**: Reusable prompt templates
   - **Walidacja**: Template rendering test
   - **Czas**: 2h

2. **[ ] Context injection pipeline**
   - **Metryka**: Dynamic context building
   - **Walidacja**: Context accuracy test
   - **Czas**: 3h

3. **[ ] Response parsing i validation**
   - **Metryka**: Structured output extraction
   - **Walidacja**: Parser reliability test
   - **Czas**: 2h

### Blok 3: Cost control i optimization

#### Zadania atomowe

1. **[ ] Token counting i budgeting**
   - **Metryka**: Accurate token prediction
   - **Walidacja**: Token count accuracy
   - **Czas**: 2h

2. **[ ] Response caching layer**
   - **Metryka**: 50%+ cache hit rate
   - **Walidacja**: Cache effectiveness test
   - **Czas**: 3h

3. **[ ] Daily/monthly spend limits**
   - **Metryka**: Hard cost limits enforced
   - **Walidacja**: Limit enforcement test
   - **Czas**: 2h

### Blok 4: Integration i monitoring

#### Zadania atomowe

1. **[ ] LLM metrics collection**
   - **Metryka**: Latency, tokens, cost tracked
   - **Walidacja**: Metrics dashboard
   - **Czas**: 2h

2. **[ ] Error handling i fallbacks**
   - **Metryka**: Graceful degradation
   - **Walidacja**: Failure scenario test
   - **Czas**: 2h

3. **[ ] A/B testing framework**
   - **Metryka**: Model comparison enabled
   - **Walidacja**: A/B test execution
   - **Czas**: 2h

## Całościowe metryki sukcesu zadania

1. **Latency**: p95 <2s for responses
2. **Cost efficiency**: <$0.10 per complex query
3. **Reliability**: 99.5% success rate
4. **Flexibility**: Easy provider switching

## Deliverables

1. `src/infrastructure/llm/` - LLM integration layer
2. `src/application/prompts/` - Prompt templates
3. `config/llm-providers.yml` - Provider config
4. `scripts/llm-benchmark/` - Performance tests
5. `docs/llm-integration-guide.md` - Usage guide

## Narzędzia

- **OpenAI SDK**: GPT-4 integration
- **Anthropic SDK**: Claude integration
- **tiktoken**: Token counting
- **Redis**: Response caching
- **LangSmith**: Prompt monitoring

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/llm-service.md`

### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/llm-service.md#deploy](docs/deployment/services/llm-service.md#deploy)

2. **[ ] Konfiguracja LLM providers**
   - **Metryka**: API keys secure in SOPS
   - **Walidacja**: Connection to OpenAI/Anthropic
   - **Procedura**: [docs/deployment/services/llm-service.md#providers](docs/deployment/services/llm-service.md#providers)

3. **[ ] Response caching setup**
   - **Metryka**: Redis cache for LLM responses
   - **Walidacja**: Cache hit rate >50%
   - **Procedura**: [docs/deployment/services/llm-service.md#caching](docs/deployment/services/llm-service.md#caching)

4. **[ ] Cost monitoring**
   - **Metryka**: Token usage tracking
   - **Walidacja**: Cost alerts configured
   - **Procedura**: [docs/deployment/services/llm-service.md#cost-monitoring](docs/deployment/services/llm-service.md#cost-monitoring)

5. **[ ] Performance validation**
   - **Metryka**: <2s response time p95
   - **Walidacja**: Load test via CI/CD
   - **Procedura**: [docs/deployment/services/llm-service.md#performance-testing](docs/deployment/services/llm-service.md#performance-testing)

### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

### **📋 Walidacja sukcesu:**
```bash
# Sprawdź deployment:
curl http://nebula:8005/health

# Test LLM connection:
curl -X POST http://nebula:8005/api/complete -d '{"prompt": "Hello, test", "max_tokens": 10}'

# Check cache stats:
curl http://nebula:8005/api/cache/stats
```

### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/llm-service.md](docs/deployment/services/llm-service.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

### **🔍 Metryki sukcesu bloku:**
- ✅ Multi-provider LLM support
- ✅ Secure API key management
- ✅ Response caching operational
- ✅ Cost monitoring and alerts
- ✅ <2s response time p95
- ✅ Zero-downtime deployment via CI/CD

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-intent-recognition.md](./02-intent-recognition.md)
