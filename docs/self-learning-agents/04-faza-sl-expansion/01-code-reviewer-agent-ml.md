# Faza SL-4 / Zadanie 1: Code-Reviewer Agent ML Enhancement

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Code-reviewer ML enhancement zachowuje wszystkie istniejące capabilities
2. ML pattern recognition jest komplementarne, nie replacement
3. Learning from developer feedback loops (accept/reject suggestions)
4. Backward compatibility z existing /agent code-reviewer workflows
5. Real-time suggestions bez performance impact
6. Pattern learning from successful vs rejected reviews
-->

## Cel zadania

Wzbogacenie code-reviewer agenta o ML capabilities dla pattern recognition, automated suggestions, i adaptive learning from developer feedback. Agent musi zachować pełną backward compatibility i improve code review quality przez intelligent suggestions.

## Blok 0: Prerequisites check

<!--
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe:
1. **[ ] Weryfikacja działania A/B testing framework z Fazy SL-3**
   - **Metryka**: A/B framework operational, >100 experiments completed
   - **Walidacja**: `curl -s http://nebula:8093/api/experiments/stats | jq '.completed_experiments >= 100'`
   - **Czas**: 0.5h

2. **[ ] Backup istniejącej code-reviewer konfiguracji**
   - **Metryka**: Complete backup of current code-reviewer agent setup
   - **Walidacja**: `ls -la /opt/detektor/backups/$(date +%Y%m%d)/agents/code-reviewer/` pokazuje config files
   - **Czas**: 0.5h

3. **[ ] Test baseline performance code-reviewer agenta**
   - **Metryka**: Current performance metrics established (latency, accuracy)
   - **Walidacja**: `curl -s http://nebula:8080/api/agents/code-reviewer/metrics | jq '.avg_response_time_ms < 200'`
   - **Czas**: 1h

## Dekompozycja na bloki zadań

### Blok 1: ML Data Model & Feature Engineering

<!--
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. Code review features muszą być actionable i interpretable
2. Historical data analysis dla pattern identification
3. Developer feedback loop design (approve/reject tracking)
4. Integration z existing git workflows i code metrics
-->

#### Zadania atomowe:
1. **[ ] Code review ML data model design**
   <!--
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Analyzować historical code reviews z git history
   - Definiować features: complexity, style, bug patterns, test coverage
   - Strukturę dla developer feedback (approved/rejected suggestions)
   - Po ukończeniu ZAWSZE wymagać code review przez `/agent code-reviewer`
   -->
   - **Metryka**: Complete data model w TimescaleDB dla code review ML features
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "\dt code_review_ml.*" | grep -c "reviews\|patterns\|feedback\|features"
     ```
   - **Code Review**: `/agent code-reviewer` (OBOWIĄZKOWE po implementacji)
   - **Czas**: 3h

2. **[ ] Feature extraction pipeline implementation**
   - **Metryka**: Pipeline extracts 25+ features z code diffs i context
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8095/api/code-review/extract-features \
          -H "Content-Type: application/json" \
          -d '{"diff": "test-diff", "context": "test-context"}' | \
          jq '.features | length >= 25'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

3. **[ ] Historical code review data analysis**
   - **Metryka**: Analysis of 1000+ past code reviews dla pattern identification
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8095/api/analysis/historical-patterns | jq '.analyzed_reviews >= 1000 and .identified_patterns | length >= 10'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

4. **[ ] Developer feedback tracking system**
   - **Metryka**: System tracks approval/rejection of ML suggestions
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8095/api/feedback/suggestion \
          -d '{"suggestion_id": "test-123", "action": "approved", "developer": "test"}' | \
          jq '.status == "recorded"'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Complete ML data model for code review features
- Feature extraction pipeline operational (25+ features)
- Historical pattern analysis completed (1000+ reviews)
- Developer feedback loop implemented
- Real-time feature calculation <50ms

### Blok 2: ML Model Training & Inference

<!--
LLM PROMPT dla bloku:
ML models dla code review pattern recognition.
Musi być interpretable i reliable, nie black box.
-->

#### Zadania atomowe:
1. **[ ] Code pattern recognition model training**
   - **Metryka**: Model trained z >80% accuracy na pattern detection
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8095/api/models/pattern-recognition/metrics | jq '.accuracy >= 0.8 and .precision >= 0.75'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

2. **[ ] Bug prediction model implementation**
   - **Metryka**: Model predicts potential bugs z >75% recall
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8095/api/models/bug-prediction/predict \
          -d '{"code_diff": "sample-code"}' | \
          jq '.bug_probability >= 0.0 and .bug_probability <= 1.0'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

3. **[ ] Code style consistency model**
   - **Metryka**: Model learns project-specific style patterns z >85% consistency
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8095/api/models/style-consistency/stats | jq '.consistency_score >= 0.85'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

4. **[ ] Real-time inference optimization**
   - **Metryka**: Model inference <100ms dla real-time suggestions
   - **Walidacja**:
     ```bash
     time curl -X POST http://nebula:8095/api/inference/code-review \
          -d '{"code": "test-code"}' | \
          awk 'END {print ($1 < 0.1)}' # <100ms
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Pattern recognition model >80% accuracy
- Bug prediction model >75% recall
- Style consistency model >85% consistency
- Real-time inference <100ms
- Models deployed w MLflow registry

### Blok 3: Agent Integration & Shadow Mode

<!--
LLM PROMPT dla bloku:
Integration ML capabilities z existing code-reviewer agent.
Shadow mode first - zero impact na current functionality.
-->

#### Zadania atomowe:
1. **[ ] ML-enhanced code-reviewer service implementation**
   - **Metryka**: Enhanced service provides both deterministic i ML suggestions
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8080/api/agents/code-reviewer/review \
          -d '{"mode": "enhanced", "code": "test"}' | \
          jq '.suggestions | length >= 1 and .ml_enhanced == true'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

2. **[ ] Shadow mode ML suggestions implementation**
   - **Metryka**: Shadow mode logs ML suggestions bez affecting deterministic output
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8080/api/agents/code-reviewer/review \
          -d '{"code": "test", "shadow_mode": true}' | \
          jq '.deterministic_result != null and .shadow_ml_logged == true'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

3. **[ ] Backward compatibility validation**
   - **Metryka**: All existing code-reviewer APIs work bez changes
   - **Walidacja**:
     ```bash
     # Test existing workflows
     /agent code-reviewer --file=test.py
     curl -s http://nebula:8080/api/agents/code-reviewer/health | jq '.backward_compatible == true'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

4. **[ ] Performance impact assessment**
   - **Metryka**: ML enhancement adds <10ms overhead
   - **Walidacja**:
     ```bash
     # Compare response times
     curl -w "%{time_total}" -s http://nebula:8080/api/agents/code-reviewer/review \
          -d '{"mode": "deterministic"}' > deterministic_time
     curl -w "%{time_total}" -s http://nebula:8080/api/agents/code-reviewer/review \
          -d '{"mode": "enhanced"}' > enhanced_time
     # Difference should be <0.01 seconds
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- ML-enhanced code-reviewer service operational
- Shadow mode working bez production impact
- 100% backward compatibility maintained
- Performance overhead <10ms
- Deterministic fallback working

### Blok 4: Gradual Rollout & Monitoring

<!--
LLM PROMPT dla bloku:
Controlled rollout of ML suggestions od 5% do 100%.
Comprehensive monitoring i feedback collection.
-->

#### Zadania atomowe:
1. **[ ] Gradual rollout implementation (5% → 25% → 50% → 100%)**
   - **Metryka**: Traffic splitting works dla ML suggestions
   - **Walidacja**:
     ```bash
     # Test 25% rollout
     curl -X POST http://nebula:8092/api/flags/code-reviewer-ml -d '{"percentage": 25}'
     for i in {1..100}; do curl -s http://nebula:8080/api/agents/code-reviewer/review -d '{"code":"test"}' | jq '.ml_used'; done | grep -c "true" # Should be ~25
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] ML suggestion quality monitoring**
   - **Metryka**: Real-time monitoring of suggestion acceptance rates
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8095/api/monitoring/suggestion-quality | jq '.acceptance_rate >= 0.6 and .false_positive_rate <= 0.1'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Developer feedback dashboard**
   - **Metryka**: Dashboard shows ML vs deterministic performance comparison
   - **Walidacja**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/code-reviewer-ml | jq '.dashboard.panels[] | select(.title | contains("ML vs Deterministic"))'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

4. **[ ] Automatic quality gates i rollback triggers**
   - **Metryka**: Automatic rollback jeśli acceptance rate <50%
   - **Walidacja**:
     ```bash
     # Simulate low acceptance rate
     curl -X POST http://nebula:8095/api/feedback/batch \
          -d '{"suggestions": [{"id": "1", "accepted": false}] * 20}'
     sleep 30
     curl -s http://nebula:8092/api/flags/code-reviewer-ml | jq '.percentage == 0' # Should auto-rollback
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Gradual rollout mechanism working (5%-100%)
- Real-time quality monitoring operational
- Developer feedback dashboard deployed
- Automatic rollback triggers tested
- ML suggestions acceptance rate >60%

## Całościowe metryki sukcesu zadania

<!--
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **ML Enhancement Operational**: Code-reviewer agent provides ML suggestions z >80% accuracy
2. **Developer Adoption**: >60% acceptance rate of ML suggestions w production
3. **Performance Maintained**: <10ms latency overhead, 100% backward compatibility
4. **Quality Improvement**: >20% improvement w bug detection over deterministic baseline
5. **Reliability**: Zero regressions, automatic rollback working <30 seconds

## Deliverables

<!--
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi mieć konkretną ścieżkę i być wymieniony w zadaniu atomowym.
-->

1. `/services/agents/code-reviewer-ml/` - ML-enhanced code-reviewer service
2. `/ml/models/code-review/` - Trained ML models (pattern recognition, bug prediction, style)
3. `/ml/feature-engineering/code-review/` - Feature extraction pipeline
4. `/scripts/sql/code-review-ml-schema.sql` - ML data model for code reviews
5. `/monitoring/grafana/dashboards/code-reviewer-ml.json` - ML monitoring dashboard
6. `/services/agents/code-reviewer-ml/feedback/` - Developer feedback tracking system
7. `/docs/agents/code-reviewer-ml-guide.md` - Operations and usage guide
8. `/tests/agents/code-reviewer-ml/` - Comprehensive test suite

## Narzędzia

<!--
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
-->

- **Python 3.11**: ML model development (scikit-learn, pandas)
- **TimescaleDB**: ML training data i feature storage
- **MLflow**: Model registry i experiment tracking
- **Redis**: Real-time suggestion caching
- **FastAPI**: ML-enhanced agent service API
- **Prometheus**: ML metrics collection
- **Grafana**: ML suggestion quality monitoring
- **Git**: Code history analysis dla pattern extraction

## Zależności

- **Wymaga**: Faza SL-3 ukończona (A/B testing framework operational, >100 experiments)
- **Blokuje**: Task 5 (Cross-Agent Learning) - needs patterns from enhanced agents

## Ryzyka i mitigacje

<!--
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| ML suggestions low quality | Średnie | Wysoki | Comprehensive feature engineering, developer feedback | Acceptance rate <50% |
| Performance degradation | Niskie | Wysoki | Async processing, caching, circuit breakers | Response time >200ms |
| Developer resistance | Średnie | Średni | Gradual rollout, explainable suggestions | Low adoption rates |
| Model overfitting | Średnie | Średni | Cross-validation, diverse training data | Poor performance on new code |
| False positive suggestions | Wysoki | Średni | Conservative thresholds, feedback learning | High rejection rates |

## Rollback Plan

<!--
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
-->

1. **Detekcja problemu**: ML suggestions quality degradation lub performance issues
2. **Kroki rollback**:
   - [ ] Immediate: Set ML traffic to 0%: `curl -X POST http://nebula:8092/api/flags/code-reviewer-ml -d '{"percentage": 0}'`
   - [ ] Service rollback: `docker compose restart code-reviewer-agent`
   - [ ] Full rollback: `git checkout pre-ml-enhancement && make deploy-agents`
   - [ ] Verify deterministic mode: `/agent code-reviewer --deterministic`
3. **Czas rollback**: <2 min immediate, <10 min full

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-deployment-specialist-ml.md](./02-deployment-specialist-ml.md)

## Learning Outcomes

Po ukończeniu deweloper będzie umiał:
1. **Integrate ML** w existing agent bez breaking changes
2. **Implement feedback loops** dla continuous improvement
3. **Design interpretable ML** features dla code review
4. **Deploy gradual rollouts** z automatic quality gates
5. **Monitor ML performance** w production environment
