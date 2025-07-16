# Faza 3 / Zadanie 4: Dashboard AI Processing Performance

## Cel zadania

Stworzyć kompleksowy dashboard monitorujący wydajność wszystkich serwisów AI z metrykami GPU, latencji i jakości detekcji.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja metryk AI services**
   - **Metryka**: Face, object detection eksportują metryki
   - **Walidacja**:

     ```bash
     for port in 8002 8003; do
       curl -s localhost:$port/metrics | grep -E "(inference_duration|detections_total)"
     done
     # Both services return metrics
     ```

   - **Czas**: 0.5h

2. **[ ] GPU metrics availability**
   - **Metryka**: nvidia-smi exporter działa
   - **Walidacja**:

     ```bash
     curl localhost:9835/metrics | grep nvidia_gpu_utilization
     # Returns current GPU usage
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: GPU performance panels

#### Zadania atomowe

1. **[ ] GPU utilization heatmap**
   - **Metryka**: GPU usage over time per service
   - **Walidacja**:

     ```promql
     nvidia_gpu_utilization{service=~"face-.*|object-.*"}
     # Returns time series for each AI service
     ```

   - **Czas**: 1.5h

2. **[ ] VRAM usage stacked graph**
   - **Metryka**: Memory per model/service
   - **Walidacja**:

     ```bash
     # Panel shows memory breakdown
     curl http://localhost:3000/api/panels/gpu-memory | \
       jq '.targets[].expr' | grep container_name
     ```

   - **Czas**: 1.5h

3. **[ ] GPU temperature monitoring**
   - **Metryka**: Temperature with alert thresholds
   - **Walidacja**:

     ```promql
     nvidia_gpu_temperature_celsius > 80
     # Alert rule configured
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Complete GPU visibility
- Historical trending
- Thermal monitoring

### Blok 2: AI inference metrics

#### Zadania atomowe

1. **[ ] Inference latency by model**
   - **Metryka**: p50/p95/p99 per model type
   - **Walidacja**:

     ```promql
     histogram_quantile(0.95,
       rate(inference_duration_bucket{model="yolov8m"}[5m]))
     ```

   - **Czas**: 2h

2. **[ ] Detection confidence distribution**
   - **Metryka**: Histogram of confidence scores
   - **Walidacja**:

     ```bash
     # Should show bell curve around 0.7-0.9
     curl http://localhost:9090/api/v1/query?query=detection_confidence_bucket
     ```

   - **Czas**: 1.5h

3. **[ ] Objects per frame statistics**
   - **Metryka**: Avg/max objects detected
   - **Walidacja**:

     ```promql
     avg_over_time(objects_per_frame[5m])
     # Reasonable values 0-20
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Quality metrics tracked
- Performance visible
- Anomalies detectable

### Blok 3: Comparative analysis

#### Zadania atomowe

1. **[ ] Model comparison table**
   - **Metryka**: Side-by-side model performance
   - **Walidacja**:

     ```javascript
     // Table panel config
     panel.targets.forEach(t =>
       assert(t.format === "table" && t.instant === true)
     )
     ```

   - **Czas**: 1.5h

2. **[ ] Cost efficiency metrics**
   - **Metryka**: Inferences per watt, $/1K inferences
   - **Walidacja**:

     ```promql
     rate(inferences_total[5m]) / nvidia_gpu_power_draw
     # Shows efficiency metric
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Models comparable
- Efficiency tracked
- ROI visible

## Całościowe metryki sukcesu zadania

1. **Completeness**: All AI services monitored
2. **Insights**: Clear performance bottlenecks visible
3. **Actionability**: Easy model/config optimization

## Deliverables

1. `/dashboards/ai-performance.json` - Main AI dashboard
2. `/dashboards/gpu-monitoring.json` - GPU-specific dashboard
3. `/alerts/ai-performance-rules.yml` - Performance alerts
4. `/scripts/gpu_benchmark.py` - Benchmark different models
5. `/docs/ai-tuning-guide.md` - Performance tuning docs

## Narzędzia

- **Grafana**: Visualization
- **Prometheus**: Metrics storage
- **nvidia-smi**: GPU metrics source
- **Python**: Custom metric exporters

## Zależności

- **Wymaga**:
  - AI services deployed
  - GPU metrics available
- **Blokuje**: Performance optimization

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Metric cardinality explosion | Średnie | Średni | Label limiting, aggregation | Prometheus memory >10GB |
| GPU metrics gaps | Niskie | Niski | Multiple exporters, fallbacks | Missing data points |

## Rollback Plan

1. **Detekcja problemu**:
   - Dashboard not loading
   - Queries too slow
   - Missing metrics

2. **Kroki rollback**:
   - [ ] Reduce query complexity
   - [ ] Increase aggregation intervals
   - [ ] Disable expensive panels
   - [ ] Use cached datasource

3. **Czas rollback**: <5 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-end-to-end-tracing.md](./05-end-to-end-tracing.md)
