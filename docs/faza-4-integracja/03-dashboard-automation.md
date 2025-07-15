# Faza 4 / Zadanie 3: Dashboard Automation Execution

## Cel zadania
Stworzyć dashboard wizualizujący wykonywanie automatyzacji w czasie rzeczywistym z historią i statystykami.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja automation metrics**
   - **Metryka**: HA bridge eksportuje metryki automatyzacji
   - **Walidacja**: 
     ```bash
     curl localhost:8004/metrics | grep -E "automation_executed|action_success"
     # Metrics present with values
     ```
   - **Czas**: 0.5h

2. **[ ] Test data generation**
   - **Metryka**: Generate sample automations
   - **Walidacja**: 
     ```bash
     python generate_test_automations.py --count 100
     # 100 test automations executed
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Core automation panels

#### Zadania atomowe:
1. **[ ] Automation trigger frequency**
   - **Metryka**: Bar chart of triggers by type
   - **Walidacja**: 
     ```promql
     sum by (trigger_type) (
       rate(automation_triggered_total[1h])
     )
     # Shows motion, time, state triggers
     ```
   - **Czas**: 1.5h

2. **[ ] Success/failure pie chart**
   - **Metryka**: Visual success rate
   - **Walidacja**: 
     ```javascript
     panel.targets[0].expr.includes("automation_success_total")
     panel.targets[1].expr.includes("automation_failed_total")
     ```
   - **Czas**: 1h

3. **[ ] Execution timeline**
   - **Metryka**: Gantt-style automation history
   - **Walidacja**: 
     ```sql
     -- Query returns automation timeline
     SELECT name, start_time, end_time, status 
     FROM automation_executions 
     ORDER BY start_time DESC
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Key metrics visible
- Real-time updates
- Historical view

### Blok 2: Detailed analytics

#### Zadania atomowe:
1. **[ ] Top triggered automations**
   - **Metryka**: Table of most active automations
   - **Walidacja**: 
     ```promql
     topk(10, sum by (automation_name) (
       automation_triggered_total
     ))
     ```
   - **Czas**: 1.5h

2. **[ ] Latency distribution heatmap**
   - **Metryka**: Show execution time patterns
   - **Walidacja**: 
     ```bash
     # Heatmap shows time-of-day patterns
     curl http://localhost:3000/api/panels/automation-latency-heatmap
     ```
   - **Czas**: 1.5h

3. **[ ] Entity interaction graph**
   - **Metryka**: Which entities trigger which actions
   - **Walidacja**: 
     ```javascript
     // Node graph panel configured
     panel.options.nodeGraph.enabled === true
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Deep insights available
- Patterns visible
- Optimization opportunities clear

### Blok 3: Alerting and drill-down

#### Zadania atomowe:
1. **[ ] Failed automation alerts**
   - **Metryka**: Alert on repeated failures
   - **Walidacja**: 
     ```yaml
     - alert: AutomationFailureRate
       expr: rate(automation_failed_total[5m]) > 0.1
       annotations:
         description: "{{ $labels.automation_name }} failing"
     ```
   - **Czas**: 1h

2. **[ ] Trace link integration**
   - **Metryka**: Click to see automation trace
   - **Walidacja**: 
     ```javascript
     panel.fieldConfig.defaults.links[0].title === "View Trace"
     panel.fieldConfig.defaults.links[0].url.includes("jaeger")
     ```
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Proactive alerting
- Easy debugging
- Full context available

## Całościowe metryki sukcesu zadania

1. **Visibility**: 100% automations tracked
2. **Insights**: Clear performance patterns
3. **Actionability**: One-click to root cause

## Deliverables

1. `/dashboards/automation-execution.json` - Main dashboard
2. `/dashboards/automation-analytics.json` - Analytics dashboard
3. `/alerts/automation-rules.yml` - Alert rules
4. `/scripts/automation_analyzer.py` - Analysis tool
5. `/docs/dashboard-guide.md` - User guide

## Narzędzia

- **Grafana**: Dashboard platform
- **Prometheus**: Metrics source
- **PostgreSQL**: Historical data
- **D3.js**: Custom visualizations

## Zależności

- **Wymaga**: 
  - Automation metrics collected
  - Historical data available
- **Blokuje**: Automation optimization

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Data volume growth | Wysokie | Średni | Aggregation, retention policies | >1M data points |
| Complex queries slow | Średnie | Niski | Query optimization, caching | Panel load >5s |

## Rollback Plan

1. **Detekcja problemu**: 
   - Dashboard not loading
   - Queries timing out
   - Wrong data shown

2. **Kroki rollback**:
   - [ ] Restore previous dashboard version
   - [ ] Clear dashboard cache
   - [ ] Reduce query complexity
   - [ ] Switch to simple view

3. **Czas rollback**: <5 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-automation-tracing.md](./04-automation-tracing.md)