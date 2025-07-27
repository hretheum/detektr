# Faza SL-3 / Zadanie 2: First Agent Production (5%)

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Documentation-keeper agent jest pierwszym w production z 5% traffic
2. Comprehensive monitoring każdego ML decision w real-time
3. Immediate fallback to deterministic jeśli cokolwiek pójdzie źle
4. Business metrics są tracked (accuracy, user satisfaction, time savings)
5. Zero risk dla existing production workflows
-->

## Cel zadania

Wprowadzenie pierwszego agenta (documentation-keeper) do production z 5% ML traffic. Comprehensive monitoring, immediate rollback capability i business impact measurement. Proof of concept dla full production rollout.

## Blok 0: Prerequisites check

<!--
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe:
1. **[ ] Weryfikacja działania A/B testing framework z Zadania 1**
   - **Metryka**: A/B framework operational, traffic splitting działa
   - **Walidacja**: `curl -s http://nebula:8092/api/flags/ml-agent-rollout | jq '.percentage == 0'`
   - **Czas**: 0.5h

2. **[ ] Documentation-keeper shadow mode validation**
   - **Metryka**: >500 shadow decisions z accuracy >75%
   - **Walidacja**: `curl -s http://nebula:8090/api/shadow/documentation-keeper/stats | jq '.accuracy > 0.75 and .total_decisions > 500'`
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Production ML Pipeline dla Documentation-Keeper

<!--
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. Documentation-keeper musi mieć complete ML pipeline ready
2. Model serving infrastructure w production quality
3. Fallback to deterministic zawsze available
4. Performance benchmarking przed włączeniem
-->

#### Zadania atomowe:
1. **[ ] Model serving service dla documentation-keeper**
   <!--
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Stworzyć /services/ml-serving/documentation-keeper/
   - Używać trained model z shadow mode
   - Integrować z feature flags dla gradual rollout
   - Po ukończeniu ZAWSZE wymagać code review przez `/agent code-reviewer`
   -->
   - **Metryka**: ML serving API dostępne na http://nebula:8095, <50ms latency
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8095/health | grep -q "OK"
     time curl -s http://nebula:8095/api/documentation-keeper/decide -d '{"task": "update README"}' | jq '.prediction'
     # Should complete in <50ms
     ```
   - **Code Review**: `/agent code-reviewer` (OBOWIĄZKOWE po implementacji)
   - **Czas**: 3.5h

2. **[ ] Feature vector preparation pipeline**
   - **Metryka**: Real-time feature engineering z <10ms overhead
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8095/api/documentation-keeper/features -d '{"context": "code change in services/"}' | jq '.features | length > 10'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Deterministic fallback integration**
   - **Metryka**: Seamless fallback jeśli ML prediction fails
   - **Walidacja**:
     ```bash
     # Simulate ML service failure
     docker stop ml-serving-documentation-keeper
     curl -s http://nebula:8080/api/agent/documentation-keeper/decide | jq '.source == "deterministic" and .success == true'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- ML serving infrastructure production-ready
- Feature preparation <10ms latency
- Deterministic fallback seamlessly working
- Model predictions consistent z shadow mode
- Health checks comprehensive

### Blok 2: Business Metrics Implementation

<!--
LLM PROMPT dla bloku:
Business impact measurement dla documentation-keeper decisions.
Musi pokazywać ROI i value proposition ML enhancement.
-->

#### Zadania atomowe:
1. **[ ] Task completion accuracy tracking**
   - **Metryka**: System tracks accuracy documentation-keeper decisions
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8093/api/metrics/documentation-keeper/accuracy | jq '.current_accuracy > 0.75 and .sample_size > 50'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

2. **[ ] Time-to-completion measurement**
   - **Metryka**: Automated measurement task completion times
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8093/api/metrics/documentation-keeper/timing | jq '.avg_completion_time_ml < .avg_completion_time_deterministic'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] User satisfaction scoring system**
   - **Metryka**: Implicit feedback collection z user interactions
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8093/api/metrics/documentation-keeper/satisfaction | jq '.satisfaction_score > 3.5 and .feedback_count > 20'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

#### Metryki sukcesu bloku:
- Accuracy tracking automated i reliable
- Time measurements showing ML benefits
- User satisfaction metrics positive
- Business impact clearly quantified
- Comparison ML vs deterministic available

### Blok 3: Production Monitoring & Alerting

<!--
LLM PROMPT dla bloku:
Comprehensive monitoring specifically dla first production agent.
Musi catch any issues immediately.
-->

#### Zadania atomowe:
1. **[ ] Documentation-keeper specific metrics dashboard**
   - **Metryka**: Grafana dashboard z 8 panels dla documentation-keeper
   - **Walidacja**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/documentation-keeper-ml | jq '.dashboard.panels | length' | grep -q "8"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Alert rules dla ML decision quality**
   - **Metryka**: 5 alert rules dla quality degradation
   - **Walidacja**:
     ```bash
     curl -s http://nebula:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.alert | contains("DocumentationKeeper")) | .alert' | wc -l | grep -q "5"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] Real-time decision logging i audit trail**
   - **Metryka**: Every ML decision logged z complete context
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "SELECT COUNT(*) FROM ml_learning.agent_decisions WHERE agent_name='documentation-keeper' AND created_at > NOW() - INTERVAL '1 hour';" | grep -q "[1-9]"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Complete observability dla documentation-keeper
- Proactive alerting na quality issues
- Audit trail dla wszystkich decisions
- Real-time monitoring <10 second lag
- Historical trending available

### Blok 4: 5% Traffic Rollout

<!--
LLM PROMPT dla bloku:
Actual production rollout z 5% traffic.
Musi być extremely careful i reversible w każdej chwili.
-->

#### Zadania atomowe:
1. **[ ] Pre-rollout testing i validation**
   - **Metryka**: 100 test requests z 100% success rate
   - **Walidacja**:
     ```bash
     # Set to 100% for testing
     curl -X POST http://nebula:8092/api/flags/ml-agent-rollout -d '{"percentage": 100}'
     for i in {1..100}; do curl -s http://nebula:8080/api/agent/documentation-keeper/decide | jq '.success'; done | grep -c "true" | grep -q "100"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

2. **[ ] Gradual 5% rollout implementation**
   - **Metryka**: Exactly 5% traffic routed to ML, remainder deterministic
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8092/api/flags/ml-agent-rollout -d '{"percentage": 5}'
     sleep 300
     for i in {1..1000}; do curl -s http://nebula:8080/api/agent/documentation-keeper/decide | jq '.source'; done | grep -c "ml" | awk '{print ($1 >= 40 && $1 <= 60)}' # 5% of 1000 = 50, allow ±10
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1.5h

3. **[ ] 24-hour monitoring i stability verification**
   - **Metryka**: 24 hours z zero incidents, positive business metrics
   - **Walidacja**:
     ```bash
     # Check after 24 hours
     curl -s http://nebula:8093/api/metrics/documentation-keeper/stability | jq '.incidents_count == 0 and .uptime_percentage > 99.9'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1h (plus 24h monitoring)

#### Metryki sukcesu bloku:
- 5% traffic successfully routed to ML
- Zero production incidents podczas rollout
- Business metrics showing improvement
- All monitoring i alerting working
- Ready dla next percentage increase

## Całościowe metryki sukcesu zadania

<!--
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **Production Readiness**: Documentation-keeper agent successfully serving 5% production traffic
2. **Performance Excellence**: ML decisions <50ms latency, deterministic fallback <10ms
3. **Business Impact**: >10% improvement w documentation accuracy, user satisfaction >4.0/5
4. **System Reliability**: 99.9% uptime, zero ML-related incidents w 24h
5. **Monitoring Completeness**: Full observability, proactive alerting operational

## Deliverables

<!--
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi mieć konkretną ścieżkę i być wymieniony w zadaniu atomowym.
-->

1. `/services/ml-serving/documentation-keeper/` - ML serving microservice
2. `/services/business-metrics/` - Business impact measurement service
3. `/monitoring/grafana/dashboards/documentation-keeper-ml.json` - Agent-specific dashboard
4. `/monitoring/prometheus/rules/documentation-keeper-alerts.yml` - ML quality alerts
5. `/scripts/production-rollout/5-percent-validation.sh` - Rollout validation script
6. `/docs/self-learning-agents/first-agent-production-guide.md` - Production operations guide
7. `/scripts/sql/agent-decisions-audit.sql` - Audit trail schema

## Narzędzia

<!--
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
-->

- **FastAPI**: ML serving API endpoints
- **scikit-learn 1.3**: ML model inference
- **TimescaleDB**: Business metrics i audit trail
- **Prometheus**: Real-time metrics collection
- **Grafana**: Agent-specific monitoring dashboard
- **Redis**: Feature caching i real-time flags
- **PostgreSQL**: Audit trail i decision logging

## Zależności

- **Wymaga**: 01-ab-testing-framework.md ukończone (A/B framework operational)
- **Blokuje**: 03-gradual-traffic-increase.md (zwiększenie do 25%-50%)

## Ryzyka i mitigacje

<!--
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| ML predictions worse than deterministic | Średnie | Wysoki | Continuous comparison, immediate rollback | Accuracy drops below 75% |
| Model serving latency spikes | Średnie | Średni | Load testing, auto-scaling, fallback | P95 latency >100ms |
| Feature pipeline failures | Niskie | Wysoki | Extensive testing, input validation | Feature extraction errors |
| User workflow disruption | Niskie | Krytyczny | Shadow mode validation, gradual rollout | User satisfaction <3.0 |

## Rollback Plan

<!--
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
-->

1. **Detekcja problemu**: ML decisions degradują performance lub accuracy
2. **Kroki rollback**:
   - [ ] Immediate: Set ML traffic to 0%: `curl -X POST http://nebula:8092/api/flags/ml-agent-rollout -d '{"percentage": 0}'`
   - [ ] Monitor: Verify all traffic returns to deterministic
   - [ ] Analyze: Check logs dla root cause
   - [ ] Document: Record incident dla learning
3. **Czas rollback**: <30 sekund

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-gradual-traffic-increase.md](./03-gradual-traffic-increase.md)
