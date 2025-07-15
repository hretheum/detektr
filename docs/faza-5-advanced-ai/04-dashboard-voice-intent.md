# Faza 5 / Zadanie 4: Dashboard Voice & Intent Processing

## Cel zadania
Stworzyć dashboard monitorujący przetwarzanie komend głosowych i rozpoznawanie intencji z metrykami jakości i kosztów API.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja voice/LLM metrics**
   - **Metryka**: Both services export metrics
   - **Walidacja**: 
     ```bash
     curl localhost:8006/metrics | grep -E "stt_|whisper_"
     curl localhost:8005/metrics | grep -E "llm_|intent_"
     # Both return relevant metrics
     ```
   - **Czas**: 0.5h

2. **[ ] Cost tracking enabled**
   - **Metryka**: API costs calculated
   - **Walidacja**: 
     ```python
     from llm_client import get_usage_stats
     stats = get_usage_stats()
     assert "total_cost" in stats
     assert "tokens_used" in stats
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Voice processing panels

#### Zadania atomowe:
1. **[ ] Voice commands timeline**
   - **Metryka**: Show commands over time
   - **Walidacja**: 
     ```promql
     rate(voice_commands_total[5m])
     # Time series of voice activity
     ```
   - **Czas**: 1.5h

2. **[ ] WER tracking gauge**
   - **Metryka**: Real-time accuracy metric
   - **Walidacja**: 
     ```javascript
     panel.targets[0].expr === "avg(stt_wer_score)"
     panel.fieldConfig.defaults.thresholds.steps[0].value === 0.1
     ```
   - **Czas**: 1h

3. **[ ] Language distribution**
   - **Metryka**: Commands by language
   - **Walidacja**: 
     ```promql
     sum by (language) (voice_commands_total)
     # Shows pl, en, etc.
     ```
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Voice metrics visible
- Quality tracked
- Patterns clear

### Blok 2: Intent processing panels

#### Zadania atomowe:
1. **[ ] Intent recognition rate**
   - **Metryka**: Success/failure breakdown
   - **Walidacja**: 
     ```promql
     rate(intent_recognition_success[5m]) / 
     rate(intent_recognition_total[5m])
     # Should be >0.95
     ```
   - **Czas**: 1.5h

2. **[ ] API latency heatmap**
   - **Metryka**: LLM response times
   - **Walidacja**: 
     ```bash
     # Heatmap shows time-of-day patterns
     curl http://localhost:3000/api/panels/llm-latency-heatmap
     ```
   - **Czas**: 1.5h

3. **[ ] Intent type distribution**
   - **Metryka**: Most common intents
   - **Walidacja**: 
     ```promql
     topk(10, sum by (intent_type) (
       intent_recognized_total
     ))
     ```
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Intent metrics complete
- Performance visible
- Usage patterns clear

### Blok 3: Cost tracking

#### Zadania atomowe:
1. **[ ] API cost gauge**
   - **Metryka**: Real-time cost tracking
   - **Walidacja**: 
     ```promql
     llm_api_cost_dollars_total
     # Shows cumulative cost
     increase(llm_api_cost_dollars_total[24h])
     # Daily cost
     ```
   - **Czas**: 1.5h

2. **[ ] Cost breakdown table**
   - **Metryka**: Cost by model/service
   - **Walidacja**: 
     ```javascript
     // Table shows cost breakdown
     panel.targets[0].format === "table"
     panel.transformations[0].id === "groupBy"
     ```
   - **Czas**: 1.5h

3. **[ ] Budget alerts**
   - **Metryka**: Alert before limit
   - **Walidacja**: 
     ```yaml
     - alert: APIBudgetWarning
       expr: llm_api_cost_dollars_total > 40
       annotations:
         summary: "API costs at ${{ $value }}, budget $50"
     ```
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Costs tracked
- Budgets monitored
- Alerts configured

## Całościowe metryki sukcesu zadania

1. **Completeness**: All voice/intent metrics visible
2. **Cost Control**: API spend tracked and alerted
3. **Insights**: Usage patterns and optimization opportunities

## Deliverables

1. `/dashboards/voice-intent-processing.json` - Main dashboard
2. `/dashboards/api-cost-tracking.json` - Cost dashboard
3. `/alerts/voice-intent-rules.yml` - Alert rules
4. `/scripts/cost_analyzer.py` - Cost analysis tool
5. `/docs/dashboard-guide.md` - User documentation

## Narzędzia

- **Grafana**: Visualization
- **Prometheus**: Metrics storage
- **Python**: Cost calculation
- **PostgreSQL**: Historical costs

## Zależności

- **Wymaga**: 
  - Voice/LLM services running
  - Metrics exported
- **Blokuje**: Cost optimization

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Cost data gaps | Niskie | Wysoki | Backup cost tracking, reconciliation | Missing cost metrics |
| Metric explosion | Średnie | Średni | Aggregation, cardinality limits | Prometheus memory growth |

## Rollback Plan

1. **Detekcja problemu**: 
   - Dashboard errors
   - Cost data wrong
   - Queries too slow

2. **Kroki rollback**:
   - [ ] Restore previous dashboard
   - [ ] Fix cost calculations
   - [ ] Simplify queries
   - [ ] Manual cost check

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-voice-to-action-trace.md](./05-voice-to-action-trace.md)