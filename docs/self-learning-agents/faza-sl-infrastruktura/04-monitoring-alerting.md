# Faza SL-1 / Zadanie 4: Monitoring & Alerting

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Complete observability dla ML pipeline - zero blind spots
2. Proactive alerting para ML system health i performance
3. Integration z existing Prometheus/Grafana stack
4. ML-specific metrics (accuracy, drift, latency, etc.)
5. Runbooks para common ML issues
-->

## Cel zadania

Implementacja comprehensive monitoring i alerting dla ML infrastructure i learning processes. System musi zapewniać complete visibility w ML pipeline performance, data quality, model accuracy i system health z proactive alerting i automated remediation gdzie możliwe.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja existing observability stack**
   - **Metryka**: Prometheus, Grafana, Jaeger operational i collecting metrics
   - **Walidacja**: `curl -s http://nebula:9090/api/v1/query?query=up | jq '.data.result | length'` > 10
   - **Czas**: 0.5h

2. **[ ] Baseline metrics collection**
   - **Metryka**: Week of baseline data z existing services para comparison
   - **Walidacja**: `curl -s http://nebula:9090/api/v1/query_range?query=up&start=$(date -d '7 days ago' +%s)&end=$(date +%s)&step=3600 | jq '.data.result | length'` > 0
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: ML-Specific Metrics Implementation

<!--
LLM PROMPT dla bloku:
ML systems need unique metrics beyond standard infrastructure monitoring.
Focus on accuracy, drift, training metrics, feature quality.
-->

#### Zadania atomowe:
1. **[ ] Model performance metrics collection**
   - **Metryka**: 15+ ML metrics (accuracy, precision, recall, F1, AUC, etc.)
   - **Walidação**:
     ```bash
     curl -s http://nebula:9090/api/v1/query?query=ml_model_accuracy | jq '.data.result | length' | grep -E "[8-9]|[1-9][0-9]"  # 8 agents
     curl -s http://nebula:9090/api/v1/query?query=ml_prediction_latency_p95 | jq '.data.result[0].value[1]' | python -c "import sys; exit(0 if float(sys.stdin.read()) < 100 else 1)"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Data drift detection metrics**
   - **Metryka**: Real-time drift monitoring para features i target variables
   - **Walidação**:
     ```bash
     curl -s http://nebula:9090/api/v1/query?query=ml_feature_drift_score | jq '.data.result | length' | grep -E "[7-9][0-9]"  # 70+ features
     python scripts/test_drift_detection.py --generate-drift | grep "Drift detected: True"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Feature quality metrics**
   - **Metryka**: Feature freshness, completeness, distribution stats
   - **Walidação**:
     ```bash
     curl -s http://nebula:9090/api/v1/query?query=feast_feature_freshness_seconds | jq '.data.result | length' | grep -E "[7-9][0-9]"
     curl -s http://nebula:9090/api/v1/query?query=feast_feature_completeness_ratio | jq '.data.result[0].value[1]' | python -c "import sys; exit(0 if float(sys.stdin.read()) > 0.95 else 1)"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- 50+ ML-specific metrics being collected
- Real-time drift detection operational
- Feature quality monitoring comprehensive
- All metrics integrated w/ Prometheus
- Baseline performance established

### Blok 2: Advanced Grafana Dashboards

<!--
LLM PROMPT dla bloku:
Create comprehensive Grafana dashboards specifically para ML operations.
Multiple views: operational, business, debugging.
-->

#### Zadania atomowe:
1. **[ ] ML Operations Dashboard**
   - **Metryka**: Operational dashboard z 12+ panels para day-to-day monitoring
   - **Walidação**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/ml-operations | jq '.dashboard.panels | length' | grep -E "1[2-9]|[2-9][0-9]"
     curl -s http://nebula:3000/api/dashboards/db/ml-operations | jq '.dashboard.panels[] | select(.title | contains("Model Accuracy")) | .targets[0].expr' | grep -q "ml_model_accuracy"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Agent Performance Dashboard**
   - **Metryka**: Per-agent performance tracking z comparison views
   - **Walidação**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/agent-performance | jq '.dashboard.panels | length' | grep -E "[8-9]|[1-9][0-9]"
     curl -s http://nebula:3000/api/dashboards/db/agent-performance | jq '.dashboard.templating.list[] | select(.name=="agent") | .options | length' | grep -q "8"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] ML Business Metrics Dashboard**
   - **Metryka**: Business-focused metrics (ROI, accuracy improvements, user satisfaction)
   - **Walidação**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/ml-business-metrics | jq '.dashboard.panels[] | select(.title | contains("ROI")) | .targets[0].expr' | grep -q "ml_roi_percentage"
     curl -s http://nebula:3000/api/dashboards/db/ml-business-metrics | jq '.dashboard.panels[] | select(.title | contains("Accuracy Improvement")) | .targets[0].expr' | grep -q "ml_accuracy_improvement"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- 3 comprehensive Grafana dashboards operational
- Real-time updates working
- All 8 agents represented w/ individual views
- Business metrics clearly visualized
- Performance comparisons easily accessible

### Blok 3: Intelligent Alerting System

<!--
LLM PROMPT dla bloku:
Smart alerting that reduces noise but catches real issues.
Multi-channel notifications, escalation paths.
Context-aware alerts w/ suggested actions.
-->

#### Zadania atomowe:
1. **[ ] ML-specific alert rules**
   - **Metryka**: 15 alert rules covering model degradation, drift, performance
   - **Walidação**:
     ```bash
     curl -s http://nebula:9090/api/v1/rules | jq '.data.groups[] | .rules[] | select(.alert | contains("ML")) | .alert' | wc -l | grep -E "1[5-9]|[2-9][0-9]"
     curl -s http://nebula:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname=="MLModelAccuracyDrop")' | jq .state | grep -q "firing\|pending"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Multi-channel notification system**
   - **Metryka**: Alerting via Telegram, email, i Grafana w/ escalation
   - **Walidação**:
     ```bash
     # Test alert firing
     python scripts/test_alerts.py --trigger-ml-alert --check-channels
     grep -q "Alert sent successfully" /var/log/alertmanager/alertmanager.log
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Context-aware alert enrichment**
   - **Metryka**: Alerts include suggested actions, runbook links, context
   - **Walidação**:
     ```bash
     # Fire test alert and check enrichment
     python scripts/test_alerts.py --trigger-accuracy-drop
     curl -s http://nebula:9093/api/v1/alerts | jq '.data[] | select(.labels.alertname=="MLModelAccuracyDrop") | .annotations.runbook_url' | grep -q "runbooks"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- 15+ ML alerts configured i tested
- Multi-channel notifications working
- Alert noise <5 false positives per day
- Mean time to resolution <30 minutes
- Context enrichment providing actionable info

### Blok 4: Automated Remediation

<!--
LLM PROMPT dla bloku:
Where possible, implement automated responses to common issues.
Self-healing systems para model degradation, infrastructure issues.
-->

#### Zadania atomowe:
1. **[ ] Automated model rollback**
   - **Metryka**: System automatically rolls back to previous model version on accuracy drop
   - **Walidação**:
     ```bash
     # Simulate accuracy drop and test rollback
     python scripts/test_auto_remediation.py --simulate-accuracy-drop --agent=code-reviewer
     sleep 60
     mlflow models get-latest-versions --name="code-reviewer" --stage="Production" | jq '.model_version.version' | grep -v "$(cat /tmp/test_bad_version.txt)"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Feature store auto-recovery**
   - **Metryka**: Feast automatically recovers z Redis failures, re-materializes features
   - **Walidação**:
     ```bash
     # Simulate Redis failure
     docker stop redis
     sleep 30
     docker start redis
     sleep 60
     feast get-online-features --feature-view code_review_features:avg_issues_per_review | jq .status | grep -q "SUCCESS"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Circuit breaker automation**
   - **Metryka**: ML services automatically fall back to deterministic when unhealthy
   - **Walidação**:
     ```bash
     # Simulate ML service failure
     docker stop mlflow
     python scripts/test_agent_decision.py --agent=code-reviewer --expect-deterministic
     grep -q "Circuit breaker opened" /var/log/agent-decisions.log
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Automated rollback working para model degradation
- Feature store auto-recovery tested
- Circuit breakers preventing cascading failures
- Mean time to recovery <5 minutes
- Zero manual intervention needed para common issues

## Całościowe metryki sukcesu zadania

1. **Observability Completeness**: 50+ ML metrics collected, 0 blind spots w/ pipeline
2. **Dashboard Quality**: 3 comprehensive dashboards covering ops, business, debugging
3. **Alert Effectiveness**: <5 false positives/day, >95% issue detection rate
4. **Automated Recovery**: 80% common issues auto-resolved
5. **Performance Impact**: <2% overhead z monitoring on existing systems

## Deliverables

1. `/monitoring/prometheus/rules/ml-alerts.yml` - ML-specific alert rules
2. `/monitoring/grafana/dashboards/ml-operations.json` - Operational dashboard
3. `/monitoring/grafana/dashboards/agent-performance.json` - Agent-focused dashboard
4. `/monitoring/grafana/dashboards/ml-business-metrics.json` - Business metrics
5. `/scripts/monitoring/ml-metrics-collector.py` - Custom metrics collection
6. `/scripts/auto-remediation/` - Automated recovery scripts
7. `/docs/self-learning-agents/monitoring-guide.md` - Monitoring operations guide
8. `/docs/runbooks/ml-troubleshooting.md` - ML troubleshooting runbook

## Narzędzia

- **Prometheus**: Metrics collection i alerting
- **Grafana**: Visualization i dashboarding
- **Alertmanager**: Alert routing i notifications
- **Telegram Bot API**: Instant notifications
- **MLflow**: Model performance tracking
- **Feast**: Feature store metrics
- **Python**: Custom metrics collection
- **Bash**: Automated remediation scripts

## Zależności

- **Wymaga**: 03-feature-store-config.md completed (features para monitoring)
- **Blokuje**: Faza SL-2 (Shadow Learning) - wymaga monitoring para safe rollout

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Alert fatigue z too many notifications | Średnie | Średni | Careful threshold tuning, alert grouping | >10 alerts per day |
| Monitoring overhead affecting performance | Niskie | Średni | Lightweight metrics, sampling | >2% CPU increase |
| False positive alerts during model updates | Średnie | Niski | Alert suppression during deployments | Alerts during known maintenance |
| Automated remediation causing instability | Niskie | Wysoki | Conservative thresholds, manual override | Circuit breaker loops |

## Rollback Plan

1. **Detekcja problemu**: Monitoring system instability, performance degradation, or excessive alerting
2. **Kroki rollback**:
   - [ ] Disable automated remediation: `systemctl stop ml-auto-remediation`
   - [ ] Reduce alert sensitivity: `cp /backups/conservative-alerts.yml /etc/prometheus/`
   - [ ] Remove ML dashboards: `curl -X DELETE http://nebula:3000/api/dashboards/db/ml-operations`
   - [ ] Fallback to basic monitoring: `make deploy-basic-monitoring`
3. **Czas rollback**: <5 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [Faza SL-2: Shadow Learning Implementation](../faza-sl-shadow/01-async-learning-architecture.md)
