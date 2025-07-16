# Faza 2 / Zadanie 5: Dashboard Frame Pipeline Overview

## Cel zadania

Stworzyć kompleksowy dashboard w Grafanie wizualizujący cały pipeline przetwarzania klatek w czasie rzeczywistym z alertami.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja datasources w Grafana**
   - **Metryka**: Prometheus, Jaeger, Loki connected
   - **Walidacja**:

     ```bash
     curl -s http://admin:admin@localhost:3000/api/datasources | \
       jq '.[].name' | grep -E "(Prometheus|Jaeger|Loki)"
     # All 3 datasources present
     ```

   - **Czas**: 0.5h

2. **[ ] Test query metrics**
   - **Metryka**: Frame metrics available in Prometheus
   - **Walidacja**:

     ```bash
     curl -G http://localhost:9090/api/v1/label/__name__/values | \
       jq '.data[]' | grep frame_
     # Multiple frame_ metrics exist
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Core pipeline panels

#### Zadania atomowe

1. **[ ] FPS gauge i trend panel**
   - **Metryka**: Real-time FPS z historią 24h
   - **Walidacja**:

     ```bash
     # Import panel, verify data
     curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
       -H "Content-Type: application/json" \
       -d @panels/fps-gauge.json
     # Panel shows current FPS value
     ```

   - **Czas**: 1.5h

2. **[ ] Processing latency heatmap**
   - **Metryka**: Latency distribution over time
   - **Walidacja**:

     ```promql
     # Query returns histogram data
     histogram_quantile(0.95,
       rate(frame_processing_duration_bucket[5m]))
     ```

   - **Czas**: 2h

3. **[ ] Queue depth time series**
   - **Metryka**: Redis/RabbitMQ queue sizes
   - **Walidacja**:

     ```bash
     # Panel updates every 10s
     watch -n 10 'curl -s http://localhost:3000/render/d/pipeline/queue-depth'
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Core metrics visualized
- Auto-refresh working
- Historical data retained

### Blok 2: Advanced visualizations

#### Zadania atomowe

1. **[ ] Frame journey Sankey diagram**
   - **Metryka**: Flow visualization capture→AI→action
   - **Walidacja**:

     ```javascript
     // Panel query returns flow data
     panel.targets[0].query.includes("sum by (source, destination)")
     ```

   - **Czas**: 2.5h

2. **[ ] Error rate by component**
   - **Metryka**: Stacked graph of errors per service
   - **Walidacja**:

     ```promql
     sum by (service) (rate(errors_total[5m])) > 0
     # Shows error distribution
     ```

   - **Czas**: 1.5h

3. **[ ] Resource usage grid**
   - **Metryka**: CPU, Memory, GPU per service
   - **Walidacja**:

     ```bash
     # All services have resource panels
     services=("rtsp-capture" "redis" "postgres")
     for svc in "${services[@]}"; do
       curl -s ".../api/panels?service=$svc" | jq length
     done
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Complex visualizations working
- Data correlation visible
- Performance acceptable

### Blok 3: Alerts i annotations

#### Zadania atomowe

1. **[ ] Alert rules configuration**
   - **Metryka**: 5+ critical alerts defined
   - **Walidacja**:

     ```bash
     curl -s http://localhost:3000/api/ruler/grafana/api/v1/rules | \
       jq '.[] | select(.name | contains("frame_pipeline"))'
     # Shows configured alerts
     ```

   - **Czas**: 1.5h

2. **[ ] Dashboard annotations**
   - **Metryka**: Deployments, incidents marked
   - **Walidacja**:

     ```bash
     # Create test annotation
     curl -X POST http://localhost:3000/api/annotations \
       -d '{"dashboardId":1,"text":"Test deployment"}'
     # Annotation visible on dashboard
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Alerts properly configured
- Annotations working
- Integration complete

## Całościowe metryki sukcesu zadania

1. **Completeness**: All pipeline stages visualized
2. **Performance**: Dashboard loads <2s, refresh <500ms
3. **Usability**: Zero-click problem identification

## Deliverables

1. `/dashboards/frame-pipeline-overview.json` - Main dashboard
2. `/dashboards/panels/` - Reusable panel definitions
3. `/alerts/frame-pipeline-rules.yml` - Alert configuration
4. `/docs/dashboard-guide.md` - User documentation
5. `/scripts/dashboard-backup.sh` - Backup automation

## Narzędzia

- **Grafana 10+**: Visualization platform
- **Prometheus**: Metrics source
- **Jaeger**: Trace data source
- **Loki**: Log aggregation

## Zależności

- **Wymaga**:
  - All metrics being collected
  - Grafana deployed (Faza 1)
- **Blokuje**: Effective monitoring

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Query performance issues | Średnie | Średni | Query optimization, caching | Panel load >2s |
| Data cardinality explosion | Średnie | Wysoki | Label limits, aggregation | Prometheus memory >8GB |

## Rollback Plan

1. **Detekcja problemu**:
   - Dashboard not loading
   - Queries timing out
   - Grafana crashes

2. **Kroki rollback**:
   - [ ] Export current dashboard: `/api/dashboards/uid/pipeline`
   - [ ] Restore previous version from backup
   - [ ] Reduce query complexity
   - [ ] Clear Grafana cache

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [06-alerts-configuration.md](./06-alerts-configuration.md)
