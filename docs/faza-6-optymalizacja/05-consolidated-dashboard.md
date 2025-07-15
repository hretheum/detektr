# Faza 6 / Zadanie 5: Consolidated monitoring dashboard

## Cel zadania
Utworzyć pojedynczy, kompleksowy dashboard agregujący wszystkie kluczowe metryki systemu z możliwością drill-down do szczegółów.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] All metrics sources available**
   - **Metryka**: All services export metrics
   - **Walidacja**: 
     ```bash
     # Check all metric endpoints
     for port in 8001 8002 8003 8004 8005 8006; do
       curl -s localhost:$port/metrics | grep -c "^#" || echo "Port $port missing"
     done
     # All should return metrics
     ```
   - **Czas**: 0.5h

2. **[ ] Dashboard requirements gathered**
   - **Metryka**: Key metrics identified
   - **Walidacja**: 
     ```yaml
     # requirements.yaml exists with:
     - system_health_score
     - service_statuses  
     - resource_usage
     - automation_stats
     - cost_tracking
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Health score calculation

#### Zadania atomowe:
1. **[ ] System health score algorithm**
   - **Metryka**: 0-100 score calculated
   - **Walidacja**: 
     ```promql
     # Health score formula
     (
       (avg(up) * 0.3) +
       (1 - avg(rate(errors_total[5m])) * 0.3) +
       (avg(1 - cpu_usage) * 0.2) +
       (avg(1 - memory_usage) * 0.2)
     ) * 100
     ```
   - **Czas**: 2h

2. **[ ] Service dependency mapping**
   - **Metryka**: Show service relationships
   - **Walidacja**: 
     ```javascript
     // Dependency graph data
     const dependencies = {
       'rtsp-capture': [],
       'face-recognition': ['rtsp-capture'],
       'ha-bridge': ['face-recognition', 'object-detection']
     };
     // Visualized as flow diagram
     ```
   - **Czas**: 2h

3. **[ ] Alert impact scoring**
   - **Metryka**: Prioritize critical alerts
   - **Walidacja**: 
     ```python
     alerts = get_active_alerts()
     for alert in alerts:
         assert alert.severity in ['critical', 'warning', 'info']
         assert alert.impact_score >= 0
     # Critical alerts reduce health score more
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Health score accurate
- Dependencies clear
- Alerts prioritized

### Blok 2: Unified dashboard creation

#### Zadania atomowe:
1. **[ ] Top-level KPI panel**
   - **Metryka**: Key metrics at a glance
   - **Walidacja**: 
     ```javascript
     // KPI panels configured
     panels = [
       'System Health Score',
       'Active Detections/min',
       'Automation Success Rate', 
       'API Costs Today'
     ];
     assert(panels.every(p => dashboard.hasPanel(p)));
     ```
   - **Czas**: 2h

2. **[ ] Service status grid**
   - **Metryka**: All services with drill-down
   - **Walidacja**: 
     ```javascript
     // Each service shows:
     servicePanel = {
       status: 'green|yellow|red',
       uptime: '99.9%',
       metrics: {cpu, memory, custom},
       link: '/service-details/{name}'
     };
     ```
   - **Czas**: 2h

3. **[ ] Resource usage trends**
   - **Metryka**: Historical resource data
   - **Walidacja**: 
     ```promql
     # 7-day trends for:
     avg_over_time(cpu_usage[7d])
     avg_over_time(memory_usage[7d])
     avg_over_time(gpu_usage[7d])
     avg_over_time(disk_usage[7d])
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Dashboard comprehensive
- Navigation intuitive
- Data aggregated

### Blok 3: Advanced features

#### Zadania atomowe:
1. **[ ] One-click drill-down**
   - **Metryka**: Navigate to problem source
   - **Walidacja**: 
     ```javascript
     // Click on alert → see trace
     // Click on service → see details
     // Click on metric → see history
     dashboard.panels.forEach(panel => {
       assert(panel.links.length > 0);
     });
     ```
   - **Czas**: 2h

2. **[ ] Cost tracking integration**
   - **Metryka**: Show API and infra costs
   - **Walidacja**: 
     ```promql
     # Cost panels show:
     sum(api_cost_dollars_total)
     sum(rate(api_cost_dollars_total[24h])) * 86400  # Daily rate
     # Budget vs actual
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Drill-down working
- Costs visible
- Insights actionable

## Całościowe metryki sukcesu zadania

1. **Completeness**: Single pane of glass achieved
2. **Performance**: Dashboard loads <2s
3. **Actionability**: Problems identified in <30s

## Deliverables

1. `/dashboards/system-overview.json` - Main dashboard
2. `/dashboards/drill-down/` - Detail dashboards
3. `/scripts/health_score.py` - Score calculation
4. `/alerts/dashboard-alerts.yml` - Dashboard-driven alerts
5. `/docs/dashboard-guide.md` - User documentation

## Narzędzia

- **Grafana**: Dashboard platform
- **Prometheus**: Metrics aggregation
- **Python**: Custom calculations
- **D3.js**: Custom visualizations

## Zależności

- **Wymaga**: 
  - All metrics available
  - Grafana 10+
- **Blokuje**: Operations visibility

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Information overload | Wysokie | Średni | Progressive disclosure, filters | User feedback |
| Performance with many panels | Średnie | Niski | Caching, optimized queries | Load time >5s |

## Rollback Plan

1. **Detekcja problemu**: 
   - Dashboard too slow
   - Data incorrect
   - Users confused

2. **Kroki rollback**:
   - [ ] Simplify to essential panels
   - [ ] Fix data sources
   - [ ] Add help tooltips
   - [ ] Provide training

3. **Czas rollback**: <15 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [06-documentation-traces.md](./06-documentation-traces.md)