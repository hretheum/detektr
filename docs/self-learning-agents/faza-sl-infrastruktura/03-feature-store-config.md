# Faza SL-1 / Zadanie 3: Feature Store Configuration

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Feature Store (Feast) jest w pełni skonfigurowany z PostgreSQL backend
2. Features są zaprojektowane dla każdego z 8 agentów specjalnie
3. Real-time i historical feature serving działa
4. Integration z MLflow jest seamless
5. Feature versioning i backwards compatibility
-->

## Cel zadania

Implementacja Feast Feature Store z PostgreSQL backend, zaprojektowanego specjalnie dla 8 agentów Detektor. Feature Store musi wspierać real-time serving, historical features dla treningu oraz seamless integration z MLflow dla reproducible experiments.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja PostgreSQL ML schema**
   - **Metryka**: ML schema exists z proper permissions para Feast
   - **Walidacja**: `docker exec detektor-postgres psql -U detektor -c "\dn" | grep -q "ml_learning"`
   - **Czas**: 0.5h

2. **[ ] Inventory wszystkich 8 agentów i ich decision patterns**
   - **Metryka**: Complete analysis dokumentów dla feature design
   - **Walidacja**: `ls -la .claude/agents/ | wc -l | grep -q "8"` && documentation review complete
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Feast Installation & Configuration

<!--
LLM PROMPT dla bloku:
Feast musi być zainstalowany jako Docker service z PostgreSQL backend.
Configuration musi być version controlled i deployable via CI/CD.
-->

#### Zadania atomowe:
1. **[ ] Feast Docker service implementation**
   - **Metryka**: Feast serving + registry running jako Docker containers
   - **Walidação**:
     ```bash
     curl -s http://nebula:6566/health | grep -q "OK"  # Feast serving
     curl -s http://nebula:6567/health | grep -q "OK"  # Feast registry
     docker ps | grep feast | wc -l | grep -q "2"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

2. **[ ] PostgreSQL backend configuration**
   - **Metryka**: Feast registry using PostgreSQL, connection pool configured
   - **Walidação**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "\dt feast.*" | wc -l | grep -E "[3-9]"
     feast registry-dump | grep -q "postgresql://detektor"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] Redis online store setup**
   - **Metryka**: Redis configured para online feature serving
   - **Walidão**:
     ```bash
     feast materialize-incremental $(date +%Y-%m-%d)
     redis-cli --scan --pattern "feast:*" | wc -l | grep -E "[1-9][0-9]+"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Feast fully operational z PostgreSQL + Redis
- Feature registry accessible via API
- Online serving functional <10ms latency
- Offline store ready para batch training
- Version control ready - all configs in Git

### Blok 2: Agent-Specific Feature Definitions

<!--
LLM PROMPT dla bloku:
Design features dla każdego z 8 agentów based on ich decision patterns.
Features muszą być relevant, measurable i useful para ML.
-->

#### Zadania atomowe:
1. **[ ] Code-reviewer agent features**
   - **Metryka**: 12 features capturing code review patterns i outcomes
   - **Walidação**:
     ```bash
     feast feature-views list | grep -q "code_review_features"
     feast get-online-features --feature-view code_review_features:avg_issues_per_review | jq .features | length | grep -q "12"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

2. **[ ] Deployment-specialist agent features**
   - **Metryka**: 8 features para deployment risk assessment
   - **Walidação**:
     ```bash
     feast feature-views list | grep -q "deployment_features"
     feast get-online-features --feature-view deployment_features:deployment_success_rate | jq .status | grep -q "SUCCESS"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] Detektor-coder agent features**
   - **Metryka**: 15 features para task complexity i code generation
   - **Walidão**:
     ```bash
     feast feature-views list | grep -q "coding_features"
     feast get-online-features --feature-view coding_features:avg_completion_time | jq .features | length | grep -q "15"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

4. **[ ] Documentation-keeper + outros 5 agentów features**
   - **Metryka**: Feature definitions para remaining agents (6-10 features each)
   - **Walidação**:
     ```bash
     feast feature-views list | wc -l | grep -q "8"  # Total 8 feature views
     feast get-online-features --feature-view documentation_features:sync_accuracy | jq .status | grep -q "SUCCESS"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

#### Metryki sukcesu bloku:
- All 8 agents tem dedicated feature views
- Total 70+ features defined i validated
- Features cover decision patterns comprehensively
- Real-time feature serving working para all
- Historical features accessible para training

### Blok 3: Feature Engineering Pipeline

<!--
LLM PROMPT dla bloku:
Automated pipeline para feature computation z existing data.
Must handle both real-time updates i batch computation.
-->

#### Zadania atomowe:
1. **[ ] Real-time feature computation**
   - **Metryka**: Streaming pipeline updating features em real-time
   - **Walidação**:
     ```bash
     # Trigger agent action and check feature update
     python scripts/test_feature_pipeline.py --agent=code-reviewer --action=review
     sleep 5
     feast get-online-features --feature-view code_review_features:recent_reviews_count | jq .features.recent_reviews_count | grep -E "[1-9]+"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Historical feature backfill**
   - **Metryka**: Backfill features z existing agent data (6 months history)
   - **Walidação**:
     ```bash
     feast materialize 2024-12-01T00:00:00 2025-07-27T23:59:59
     docker exec detektor-postgres psql -U detektor -c "SELECT COUNT(*) FROM feast.agent_features_historical;" | tail -1 | grep -E "[0-9]{4,}"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Feature validation i monitoring**
   - **Metryka**: Data quality checks i feature drift detection
   - **Walidação**:
     ```bash
     python scripts/feature_validation.py --check-all | grep "All validations passed"
     curl -s http://nebula:9090/api/v1/query?query=feast_feature_drift_score | jq '.data.result[0].value[1]' | python -c "import sys; exit(0 if float(sys.stdin.read()) < 0.1 else 1)"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Real-time feature updates <1 second latency
- Historical backfill complete para all agents
- Feature quality monitoring operational
- Data drift detection working
- Feature serving SLA >99.9% uptime

### Blok 4: MLflow Integration

<!--
LLM PROMPT dla bloku:
Seamless integration between Feast i MLflow para reproducible experiments.
Feature versioning i experiment tracking.
-->

#### Zadania atomowe:
1. **[ ] Feature versioning i MLflow integration**
   - **Metryka**: MLflow experiments automatically log feature versions used
   - **Walidação**:
     ```bash
     python scripts/test_ml_experiment.py --agent=code-reviewer --features=v1.2.0
     mlflow experiments search | grep -q "feature_version"
     mlflow runs search --experiment-id 1 | grep -q "feast_feature_hash"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

2. **[ ] Automated feature serving para model inference**
   - **Metryka**: Models podem retrieve features directly via Feast API
   - **Walidação**:
     ```bash
     python -c "
     import mlflow
     model = mlflow.sklearn.load_model('models:/code-reviewer/production')
     features = model.get_features_for_prediction({'agent_id': 'code-reviewer'})
     assert len(features) > 0
     print('Feature serving integration working')
     "
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] Feature store monitoring via Grafana**
   - **Metryka**: Complete Grafana dashboard para Feast operations
   - **Walidação**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/feast-feature-store | jq '.dashboard.panels | length' | grep -E "[8-9]|[1-9][0-9]"
     curl -s http://nebula:9090/api/v1/query?query=feast_online_serving_latency | jq '.data.result | length' | grep -q "1"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- MLflow-Feast integration seamless
- Feature versioning automated
- Model serving uses features correctly
- Complete observability dla feature store
- Reproducible experiments guaranteed

## Całościowe metryki sukcesu zadania

1. **Feature Store Completeness**: Feast operational z 8 agent feature views, 70+ total features
2. **Performance**: Real-time serving <10ms, historical queries <1s
3. **Integration Quality**: MLflow seamlessly uses versioned features
4. **Data Quality**: Feature validation passing, drift detection operational
5. **Operational Readiness**: Monitoring, alerting, i backup procedures working

## Deliverables

1. `/docker/features/feast.yml` - Feast Docker Compose configuration
2. `/ml-features/` - Complete feature definitions para all 8 agents
3. `/ml-features/feature_repo/` - Feast repository configuration
4. `/scripts/feature-engineering/` - Feature computation pipelines
5. `/monitoring/grafana/dashboards/feast-overview.json` - Feature store monitoring
6. `/docs/self-learning-agents/feature-guide.md` - Feature engineering guide
7. `/tests/feature-integration/` - Feature store integration tests

## Narzędzia

- **Feast 0.32+**: Feature store framework
- **PostgreSQL**: Offline feature store backend
- **Redis**: Online feature serving
- **Pandas**: Feature data manipulation
- **Apache Arrow**: Efficient data serialization
- **MLflow**: Experiment tracking integration
- **Prometheus**: Feature store metrics
- **Grafana**: Feature store observability

## Zależności

- **Wymaga**: 02-security-privacy-layer.md completed (secure infrastructure)
- **Blokuje**: Faza SL-2 (Shadow Learning) - wymaga features para training

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Feature serving latency too high | Średnie | Wysoki | Redis optimization, feature caching | Serving latency >50ms |
| Feature drift breaking models | Średnie | Wysoki | Automated drift detection, feature validation | Drift score >0.2 |
| Historical backfill performance issues | Średnie | Średni | Incremental processing, batch optimization | Backfill taking >4 hours |
| Feature complexity hurting interpretability | Niskie | Średni | Feature documentation, SHAP integration | Model explanations unclear |

## Rollback Plan

1. **Detekcja problemu**: Feature serving failures, performance degradation, or data quality issues
2. **Kroki rollback**:
   - [ ] Disable Feast serving: `docker stop feast-serving feast-registry`
   - [ ] Fallback to static features: `cp /backups/static-features.json /config/`
   - [ ] Remove feature dependencies: `git revert <feature-integration-commits>`
   - [ ] Restart with deterministic mode: `make deploy-deterministic`
3. **Czas rollback**: <8 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-monitoring-alerting.md](./04-monitoring-alerting.md)
