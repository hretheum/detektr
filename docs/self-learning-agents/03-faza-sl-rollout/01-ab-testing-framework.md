# Faza SL-3 / Zadanie 1: A/B Testing Framework

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. A/B testing framework jest w pełni zintegrowany z istniejącą infrastrukturą Detektor
2. Traffic splitting działa na poziomie request routing, nie agent level
3. Metryki są w czasie rzeczywistym i agregowane w Grafana
4. Framework jest generic - działa dla wszystkich agentów
5. Zero wpływu na performance existing services
-->

## Cel zadania

Implementacja kompletnego A/B testing framework dla gradual rollout ML decisions. Framework musi obsługiwać traffic splitting 5%-50%-100%, real-time metrics collection i automatic rollback w przypadku performance degradation.

## Blok 0: Prerequisites check

<!--
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe:
1. **[ ] Weryfikacja działania Shadow Mode z Fazy SL-2**
   - **Metryka**: >1000 shadow decisions collected, 0 production impact
   - **Walidacja**: `curl -s http://nebula:8090/api/shadow/stats | jq '.total_decisions'` pokazuje >1000
   - **Czas**: 0.5h

2. **[ ] Backup konfiguracji traffic routing**
   - **Metryka**: Kompletny backup nginx/traefik configuration z timestamp
   - **Walidacja**: `ls -la /opt/detektor/backups/$(date +%Y%m%d)/traffic/` pokazuje pliki
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Traffic Splitting Infrastructure

<!--
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. Traffic splitting musi być na poziomie HTTP request routing
2. Używamy feature flags dla gradual rollout
3. Integration z istniejącą observability
4. Real-time switching bez restart services
-->

#### Zadania atomowe:
1. **[ ] Feature flags service implementation**
   <!--
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Stworzyć /services/feature-flags/ service
   - Używać Redis backend dla flags state
   - Integrować z istniejącą autoryzacją
   - Po ukończeniu ZAWSZE wymagać code review przez `/agent code-reviewer`
   -->
   - **Metryka**: Feature flags API dostępne na http://nebula:8092, health check 200 OK
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8092/health | grep -q "OK"
     curl -s http://nebula:8092/api/flags/ml-agent-rollout | jq '.percentage'
     ```
   - **Code Review**: `/agent code-reviewer` (OBOWIĄZKOWE po implementacji)
   - **Czas**: 3h

2. **[ ] Request routing middleware z percentage splitting**
   - **Metryka**: Middleware poprawnie routuje traffic podle percentage flags
   - **Walidacja**:
     ```bash
     # Test 10% routing
     curl -X POST http://nebula:8092/api/flags/ml-agent-rollout -d '{"percentage": 10}'
     for i in {1..100}; do curl -s http://nebula:8080/api/agent/decision | jq '.source'; done | grep -c "ml" # Should be ~10
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Agent decision routing implementation**
   - **Metryka**: Routing działa dla documentation-keeper agent z fallback
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8080/api/agent/documentation-keeper/decide -H "X-Test-Mode: validation" | jq '.routing_decision'
     # Should return: {"source": "ml", "confidence": 0.85, "fallback_available": true}
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Feature flags service operational z Redis persistence
- Traffic routing działa z configurable percentages
- Agent decisions correctly routed ML vs deterministic
- Zero latency impact (<1ms overhead)
- Real-time flag updates bez service restart

### Blok 2: Metrics Collection & Analysis

<!--
LLM PROMPT dla bloku:
Real-time metrics collection dla A/B testing analysis.
Musi integrować z Prometheus/Grafana i dawać immediate feedback.
-->

#### Zadania atomowe:
1. **[ ] A/B testing metrics schema w TimescaleDB**
   - **Metryka**: Schema z comprehensive A/B testing data model
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "\dt ab_testing.*" | grep -c "experiments\|cohorts\|decisions\|outcomes"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

2. **[ ] Real-time metrics collector service**
   - **Metryka**: Service zbiera metrics z <100ms latency
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8093/metrics | grep -q "ab_testing_decision_latency"
     curl -s http://nebula:9090/api/v1/query?query=ab_testing_decision_latency | jq '.data.result[0].value[1]' | bc -l | awk '{print ($1 < 0.1)}'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

3. **[ ] Statistical significance calculation engine**
   - **Metryka**: Engine calculates statistical significance w real-time
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8093/api/experiments/current/significance | jq '.p_value < 0.05 and .power > 0.8'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Complete A/B testing data model w TimescaleDB
- Real-time metrics collection <100ms latency
- Statistical significance calculations accurate
- Integration z Prometheus dla alerting
- Historical data retention 90 days

### Blok 3: Automatic Rollback System

<!--
LLM PROMPT dla bloku:
Circuit breaker pattern dla automatic rollback jeśli ML decisions degradują performance.
Musi być immediate i reliable.
-->

#### Zadania atomowe:
1. **[ ] Circuit breaker implementation dla ML decisions**
   - **Metryka**: Circuit breaker triggers w <30 sekund przy degradation
   - **Walidacja**:
     ```bash
     # Simulate ML service failure
     docker stop ml-decision-service
     sleep 35
     curl -s http://nebula:8080/api/agent/decision | jq '.source' | grep -q "deterministic"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Health check aggregation service**
   - **Metryka**: Service agreguje health z wszystkich ML components
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8094/health/aggregate | jq '.overall_health == "healthy" and .ml_components | length > 3'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] Rollback automation scripts i procedures**
   - **Metryka**: Automated rollback działa w <30 sekund
   - **Walidacja**:
     ```bash
     # Test emergency rollback
     time /scripts/emergency-rollback.sh ml-agents
     # Should complete in <30 seconds and all agents return to deterministic
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Circuit breaker responds w <30 sekund
- Health aggregation covers all ML components
- Emergency rollback procedures tested
- Automatic fallback to deterministic working
- Recovery procedures documented i tested

### Blok 4: A/B Testing Dashboard

<!--
LLM PROMPT dla bloku:
Comprehensive dashboard dla monitoring A/B testing experiments.
Musi być business-friendly i technical detailed.
-->

#### Zadania atomowe:
1. **[ ] Grafana A/B testing dashboard implementation**
   - **Metryka**: Dashboard z 12 panels covering all A/B metrics
   - **Walidacja**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/ab-testing-overview | jq '.dashboard.panels | length' | grep -q "12"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Business metrics visualization**
   - **Metryka**: Panels pokazują business impact (accuracy, latency, satisfaction)
   - **Walidacja**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/ab-testing-overview | jq '.dashboard.panels[] | select(.title | contains("Business Impact"))'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] Experiment control panel implementation**
   - **Metryka**: UI dla managing experiments i traffic percentages
   - **Walidacja**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/ab-testing-control | jq '.dashboard.panels[] | select(.type == "stat" and .title | contains("Traffic Split"))'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Complete A/B testing visibility w Grafana
- Business metrics clearly displayed
- Experiment control capabilities functional
- Real-time updates <10 second refresh
- Historical trend analysis available

## Całościowe metryki sukcesu zadania

<!--
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **Framework Completeness**: A/B testing infrastructure fully operational z traffic splitting 5%-100%
2. **Performance Impact**: Zero latency impact (<1ms overhead), wszystkie metrics w real-time
3. **Reliability**: Automatic rollback działa w <30 sekund, circuit breakers tested
4. **Observability**: Complete visibility w Grafana dashboard z business i technical metrics
5. **Statistical Validity**: Statistical significance calculations accurate, >95% confidence level

## Deliverables

<!--
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi mieć konkretną ścieżkę i być wymieniony w zadaniu atomowym.
-->

1. `/services/feature-flags/` - Feature flags microservice
2. `/services/ab-testing-metrics/` - Metrics collection service
3. `/scripts/sql/ab-testing-schema.sql` - A/B testing database schema
4. `/monitoring/grafana/dashboards/ab-testing-overview.json` - A/B testing dashboard
5. `/monitoring/grafana/dashboards/ab-testing-control.json` - Experiment control dashboard
6. `/scripts/emergency-rollback.sh` - Automated rollback procedures
7. `/middleware/traffic-routing/` - Request routing middleware
8. `/docs/self-learning-agents/ab-testing-guide.md` - Operations guide

## Narzędzia

<!--
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
-->

- **Redis 7**: Feature flags persistence i real-time updates
- **TimescaleDB**: A/B testing metrics i statistical data
- **Prometheus**: Metrics collection i alerting
- **Grafana**: A/B testing dashboards i visualization
- **Python 3.11**: Statistical significance calculations
- **FastAPI**: Feature flags i metrics APIs
- **Circuit Breaker Pattern**: Automatic rollback implementation

## Zależności

- **Wymaga**: Faza SL-2 ukończona (Shadow Mode działa, >1000 decisions collected)
- **Blokuje**: 02-first-agent-production.md (pierwszy agent w production)

## Ryzyka i mitigacje

<!--
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Traffic routing adds latency | Średnie | Wysoki | Benchmark każdy step, optimize middleware | P95 latency >100ms |
| Feature flags Redis failure | Niskie | Wysoki | Fallback to default percentages | Feature flags API fails |
| Statistical calculations incorrect | Średnie | Średni | Peer review calculations, test with known data | A/B results don't match manual calc |
| Circuit breaker false positives | Średnie | Średni | Tune thresholds carefully, test scenarios | Too many unnecessary rollbacks |

## Rollback Plan

<!--
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
-->

1. **Detekcja problemu**: A/B testing adds latency lub incorrect routing
2. **Kroki rollback**:
   - [ ] Set all ML traffic to 0%: `curl -X POST http://nebula:8092/api/flags/ml-agent-rollout -d '{"percentage": 0}'`
   - [ ] Bypass routing middleware: `docker compose restart agent-gateway`
   - [ ] Remove A/B services: `docker compose -f docker/features/ab-testing.yml down`
   - [ ] Restore backup routing: `cp -r /backups/$(date +%Y%m%d)/traffic/ .`
3. **Czas rollback**: <5 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-first-agent-production.md](./02-first-agent-production.md)
