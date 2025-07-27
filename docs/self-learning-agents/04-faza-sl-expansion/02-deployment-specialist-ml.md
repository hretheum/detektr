# Faza SL-4 / Zadanie 2: Deployment-Specialist Agent ML Enhancement

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Deployment-specialist ML enhancement focus na risk assessment i strategy optimization
2. ML learns from deployment success/failure patterns
3. Predictive capabilities dla rollback scenarios
4. Integration z existing CI/CD i deployment infrastructure
5. Real-time deployment decision support
6. Pattern learning from historical deployment data i incidents
-->

## Cel zadania

Wzbogacenie deployment-specialist agenta o ML capabilities dla intelligent risk assessment, deployment strategy optimization, i predictive rollback recommendations. Agent musi improve deployment success rates przez data-driven decision making.

## Blok 0: Prerequisites check

<!--
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe:
1. **[ ] Weryfikacja działania code-reviewer ML z Task 1**
   - **Metryka**: Code-reviewer ML operational z >60% acceptance rate
   - **Walidacja**: `curl -s http://nebula:8095/api/monitoring/suggestion-quality | jq '.acceptance_rate >= 0.6'`
   - **Czas**: 0.5h

2. **[ ] Backup istniejącej deployment-specialist konfiguracji**
   - **Metryka**: Complete backup of current deployment-specialist setup
   - **Walidacja**: `ls -la /opt/detektor/backups/$(date +%Y%m%d)/agents/deployment-specialist/` pokazuje config files
   - **Czas**: 0.5h

3. **[ ] Historical deployment data verification**
   - **Metryka**: Access to >500 historical deployments z success/failure data
   - **Walidacja**: `curl -s http://nebula:8080/api/deployment/history/count | jq '. >= 500'`
   - **Czas**: 1h

## Dekompozycja na bloki zadań

### Blok 1: Deployment Intelligence Data Model

<!--
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. Deployment features muszą capture risk factors i environmental conditions
2. Historical deployment analysis dla success/failure pattern identification
3. Real-time system state features (health, load, dependencies)
4. Integration z existing deployment logs i CI/CD metadata
-->

#### Zadania atomowe:
1. **[ ] Deployment risk assessment data model**
   <!--
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Analyzować deployment patterns z GitHub Actions, Docker logs
   - Definiować features: code changes, system state, timing, dependencies
   - Include success/failure outcomes z rollback scenarios
   - Po ukończeniu ZAWSZE wymagać code review przez `/agent code-reviewer`
   -->
   - **Metryka**: Complete data model w TimescaleDB dla deployment risk features
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "\dt deployment_ml.*" | grep -c "deployments\|risks\|outcomes\|features"
     ```
   - **Code Review**: `/agent code-reviewer` (OBOWIĄZKOWE po implementacji)
   - **Czas**: 3.5h

2. **[ ] Deployment feature extraction pipeline**
   - **Metryka**: Pipeline extracts 30+ deployment risk features
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8096/api/deployment/extract-features \
          -H "Content-Type: application/json" \
          -d '{"deployment_context": "test-deployment"}' | \
          jq '.features | length >= 30'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

3. **[ ] Historical deployment pattern analysis**
   - **Metryka**: Analysis of 500+ past deployments dla risk pattern identification
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8096/api/analysis/deployment-patterns | jq '.analyzed_deployments >= 500 and .identified_risk_patterns | length >= 15'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

4. **[ ] Real-time system state integration**
   - **Metryka**: System integrates current infrastructure health jako deployment features
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8096/api/system-state/current | jq '.health_indicators | length >= 10 and .infrastructure_load != null'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Complete deployment risk data model implemented
- Feature extraction pipeline operational (30+ features)
- Historical pattern analysis completed (500+ deployments)
- Real-time system state integration working
- Feature calculation <100ms per deployment

### Blok 2: Risk Prediction & Strategy Models

<!--
LLM PROMPT dla bloku:
ML models dla deployment risk assessment i strategy recommendation.
Musi być actionable i provide clear reasoning for decisions.
-->

#### Zadania atomowe:
1. **[ ] Deployment risk prediction model training**
   - **Metryka**: Model trained z >85% accuracy na deployment success prediction
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8096/api/models/risk-prediction/metrics | jq '.accuracy >= 0.85 and .precision >= 0.8'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4.5h

2. **[ ] Rollback probability model implementation**
   - **Metryka**: Model predicts rollback necessity z >80% recall
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8096/api/models/rollback-prediction/predict \
          -d '{"deployment_features": "sample-features"}' | \
          jq '.rollback_probability >= 0.0 and .rollback_probability <= 1.0 and .confidence >= 0.7'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

3. **[ ] Deployment strategy optimization model**
   - **Metryka**: Model recommends optimal deployment strategies (blue-green, canary, rolling)
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8096/api/models/strategy-optimization/recommend | jq '.recommended_strategy != null and .confidence >= 0.75'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

4. **[ ] Deployment timing optimization**
   - **Metryka**: Model recommends optimal deployment windows based on historical data
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8096/api/models/timing-optimization/optimal-window \
          -d '{"date": "2025-08-01"}' | \
          jq '.optimal_hours | length >= 3 and .risk_score <= 0.3'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

#### Metryki sukcesu bloku:
- Risk prediction model >85% accuracy
- Rollback prediction model >80% recall
- Strategy optimization model operational
- Timing optimization recommendations available
- All models deployed w MLflow registry

### Blok 3: Intelligent Deployment Agent Integration

<!--
LLM PROMPT dla bloku:
Integration ML capabilities z existing deployment-specialist agent.
Shadow mode first, then gradual rollout z decision support.
-->

#### Zadania atomowe:
1. **[ ] ML-enhanced deployment-specialist service**
   - **Metryka**: Enhanced service provides risk assessment i strategy recommendations
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8080/api/agents/deployment-specialist/assess \
          -d '{"deployment_plan": "test-plan", "mode": "enhanced"}' | \
          jq '.risk_assessment != null and .strategy_recommendation != null and .ml_enhanced == true'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4.5h

2. **[ ] Shadow mode risk assessment implementation**
   - **Metryka**: Shadow mode provides ML risk scores bez affecting deployment decisions
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8080/api/agents/deployment-specialist/assess \
          -d '{"deployment_plan": "test", "shadow_mode": true}' | \
          jq '.deterministic_result != null and .shadow_ml_risk_score != null'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

3. **[ ] CI/CD pipeline integration**
   - **Metryka**: ML agent integrates z GitHub Actions dla real-time deployment advice
   - **Walidacja**:
     ```bash
     # Test GitHub Actions integration
     curl -X POST http://nebula:8080/api/agents/deployment-specialist/ci-advice \
          -H "X-GitHub-Event: deployment" \
          -d '{"repository": "test-repo", "commit": "abc123"}' | \
          jq '.deployment_advice != null'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

4. **[ ] Real-time deployment monitoring integration**
   - **Metryka**: Agent monitors ongoing deployments i provides alerts
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8080/api/agents/deployment-specialist/monitor/active | jq '.active_deployments | length >= 0 and .monitoring_active == true'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- ML-enhanced deployment-specialist service operational
- Shadow mode working bez deployment impact
- CI/CD pipeline integration functioning
- Real-time monitoring active
- Backward compatibility maintained 100%

### Blok 4: Production Rollout & Decision Support

<!--
LLM PROMPT dla bloku:
Controlled rollout of ML deployment recommendations.
Focus na actionable insights i explainable decisions.
-->

#### Zadania atomowe:
1. **[ ] Gradual ML recommendation rollout (10% → 50% → 100%)**
   - **Metryka**: Traffic splitting works dla deployment ML recommendations
   - **Walidacja**:
     ```bash
     # Test 50% rollout
     curl -X POST http://nebula:8092/api/flags/deployment-specialist-ml -d '{"percentage": 50}'
     for i in {1..100}; do curl -s http://nebula:8080/api/agents/deployment-specialist/assess -d '{"plan":"test"}' | jq '.ml_recommendation_used'; done | grep -c "true" # Should be ~50
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Explainable AI deployment dashboard**
   - **Metryka**: Dashboard shows reasoning behind ML deployment recommendations
   - **Walidacja**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/deployment-specialist-ml | jq '.dashboard.panels[] | select(.title | contains("Recommendation Reasoning"))'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

3. **[ ] Deployment success rate monitoring**
   - **Metryka**: Real-time tracking of ML vs deterministic recommendation outcomes
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8096/api/monitoring/deployment-success | jq '.ml_recommendations.success_rate >= 0.8 and .comparison_available == true'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

4. **[ ] Automatic feedback integration z deployment outcomes**
   - **Metryka**: System automatically learns from actual deployment results
   - **Walidacja**:
     ```bash
     # Simulate deployment completion
     curl -X POST http://nebula:8096/api/feedback/deployment-outcome \
          -d '{"deployment_id": "test-123", "outcome": "success", "ml_recommendation_followed": true}' | \
          jq '.feedback_recorded == true'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Gradual rollout mechanism working (10%-100%)
- Explainable AI dashboard operational
- Success rate monitoring active
- Automatic feedback loop implemented
- ML recommendations success rate >80%

## Całościowe metryki sukcesu zadania

<!--
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **Risk Assessment Accuracy**: ML deployment risk predictions >85% accuracy
2. **Deployment Success Improvement**: >15% improvement w deployment success rate
3. **Rollback Prediction**: >80% accuracy w predicting necessary rollbacks
4. **Response Time**: Deployment analysis <200ms dla real-time decision support
5. **Integration Success**: 100% compatibility z existing CI/CD workflows

## Deliverables

<!--
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi mieć konkretną ścieżkę i być wymieniony w zadaniu atomowym.
-->

1. `/services/agents/deployment-specialist-ml/` - ML-enhanced deployment-specialist service
2. `/ml/models/deployment/` - Trained ML models (risk prediction, rollback, strategy, timing)
3. `/ml/feature-engineering/deployment/` - Deployment feature extraction pipeline
4. `/scripts/sql/deployment-ml-schema.sql` - ML data model for deployments
5. `/monitoring/grafana/dashboards/deployment-specialist-ml.json` - ML monitoring dashboard
6. `/integration/github-actions/deployment-ml-advisor/` - CI/CD integration components
7. `/docs/agents/deployment-specialist-ml-guide.md` - Operations and usage guide
8. `/tests/agents/deployment-specialist-ml/` - Comprehensive test suite

## Narzędzia

<!--
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
-->

- **Python 3.11**: ML model development (scikit-learn, xgboost)
- **TimescaleDB**: Deployment metrics i feature storage
- **MLflow**: Model registry i experiment tracking
- **GitHub Actions**: CI/CD integration i webhook handling
- **FastAPI**: ML-enhanced agent service API
- **Prometheus**: Deployment success metrics
- **Grafana**: Deployment intelligence dashboard
- **Docker**: Deployment environment analysis

## Zależności

- **Wymaga**: Task 1 completed (Code-reviewer ML operational)
- **Blokuje**: Task 5 (Cross-Agent Learning) - needs deployment patterns for sharing

## Ryzyka i mitigacje

<!--
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| ML recommendations delay deployments | Średnie | Wysoki | Async processing, timeout fallback | Response time >200ms |
| False positive risk assessments | Wysokie | Średni | Conservative thresholds, human override | High false alarm rate |
| Integration breaks CI/CD | Niskie | Krytyczny | Comprehensive testing, rollback capability | CI/CD pipeline failures |
| Model overfitting to current environment | Średnie | Średni | Regular retraining, diverse data | Poor performance on new deployments |
| Dependency on external APIs | Średnie | Średni | Caching, graceful degradation | API timeout/failures |

## Rollback Plan

<!--
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
-->

1. **Detekcja problemu**: ML recommendations causing deployment delays lub false positives
2. **Kroki rollback**:
   - [ ] Immediate: Disable ML recommendations: `curl -X POST http://nebula:8092/api/flags/deployment-specialist-ml -d '{"percentage": 0}'`
   - [ ] CI/CD integration: Remove ML hooks from GitHub Actions
   - [ ] Service rollback: `docker compose restart deployment-specialist-agent`
   - [ ] Full rollback: `git checkout pre-deployment-ml && make deploy-agents`
3. **Czas rollback**: <3 min immediate, <15 min full

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-detektor-coder-agent-ml.md](./03-detektor-coder-agent-ml.md)

## Learning Outcomes

Po ukończeniu deweloper będzie umiał:
1. **Build deployment intelligence** z historical data analysis
2. **Implement risk prediction models** dla deployment scenarios
3. **Integrate ML z CI/CD pipelines** bez breaking existing workflows
4. **Design explainable AI** dla deployment decision support
5. **Monitor deployment success** z ML recommendation feedback loops
