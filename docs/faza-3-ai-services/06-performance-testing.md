# Faza 3 / Zadanie 6: Testy wydajnościowe z analizą w Grafanie

## Cel zadania
Przeprowadzić kompleksowe testy wydajnościowe całego pipeline'u AI z automatyczną analizą wyników w Grafanie i baseline dla przyszłych optymalizacji.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja test data**
   - **Metryka**: 1000+ test images/videos ready
   - **Walidacja**: 
     ```bash
     find /test-data -name "*.jpg" -o -name "*.mp4" | wc -l
     # >1000 files
     ls -lh /test-data | grep -E "total.*G"
     # Several GB of test data
     ```
   - **Czas**: 0.5h

2. **[ ] Load testing tools ready**
   - **Metryka**: Locust/K6 installed and configured
   - **Walidacja**: 
     ```bash
     k6 version
     locust --version
     # Both tools available
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Performance test scenarios

#### Zadania atomowe:
1. **[ ] Baseline performance test**
   - **Metryka**: Single stream, measure all metrics
   - **Walidacja**: 
     ```bash
     k6 run baseline_test.js --duration 10m
     # Check results: FPS>10, latency<100ms
     ```
   - **Czas**: 2h

2. **[ ] Stress test implementation**
   - **Metryka**: Find breaking point (max concurrent streams)
   - **Walidacja**: 
     ```python
     results = run_stress_test(step_duration=60, step_increment=2)
     print(f"Max stable streams: {results.max_stable}")
     assert results.max_stable >= 5
     ```
   - **Czas**: 2.5h

3. **[ ] Endurance test (1 hour)**
   - **Metryka**: No degradation, no memory leaks
   - **Walidacja**: 
     ```bash
     # Run for 1 hour, monitor resources
     python endurance_test.py --duration 3600
     # Memory growth <5%, FPS stable
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- All test types executed
- Breaking points identified
- Stability confirmed

### Blok 2: Result analysis automation

#### Zadania atomowe:
1. **[ ] Test result collector**
   - **Metryka**: Auto-import to Prometheus/Grafana
   - **Walidacja**: 
     ```python
     # After test run
     metrics = get_test_metrics("test_run_123")
     assert "fps_avg" in metrics
     assert "latency_p95" in metrics
     assert metrics.saved_to_prometheus
     ```
   - **Czas**: 2h

2. **[ ] Performance regression detection**
   - **Metryka**: Compare with previous baselines
   - **Walidacja**: 
     ```bash
     python compare_performance.py --baseline v1.0 --current HEAD
     # Shows performance delta for each metric
     # Fails if regression >10%
     ```
   - **Czas**: 1.5h

3. **[ ] Automated report generation**
   - **Metryka**: HTML/PDF report with graphs
   - **Walidacja**: 
     ```bash
     python generate_perf_report.py --test-id latest
     # Creates performance_report_*.html
     # Contains all metrics, graphs, recommendations
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Results automatically analyzed
- Regressions detected
- Reports generated

### Blok 3: Performance dashboard

#### Zadania atomowe:
1. **[ ] Test execution dashboard**
   - **Metryka**: Live view during tests
   - **Walidacja**: 
     ```bash
     # During test run
     curl http://localhost:3000/dashboards/perf-test-live
     # Shows real-time metrics
     ```
   - **Czas**: 1.5h

2. **[ ] Historical comparison view**
   - **Metryka**: Trend analysis over releases
   - **Walidacja**: 
     ```promql
     # Query shows historical data
     avg_over_time(test_fps_result[30d])
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Live monitoring working
- Historical trends visible
- Insights actionable

## Całościowe metryki sukcesu zadania

1. **Coverage**: All components stress tested
2. **Automation**: Results auto-analyzed, reports generated
3. **Baseline**: Performance baseline established for future

## Deliverables

1. `/tests/performance/` - All test scenarios
2. `/scripts/perf_analysis/` - Analysis tools
3. `/reports/baseline_v1.html` - Initial baseline report
4. `/dashboards/performance-testing.json` - Test monitoring
5. `/.github/workflows/perf-test.yml` - CI integration

## Narzędzia

- **K6**: Load testing tool
- **Locust**: Alternative load testing
- **pytest-benchmark**: Micro benchmarks
- **matplotlib/plotly**: Report generation

## Zależności

- **Wymaga**: 
  - Full pipeline deployed
  - Test data prepared
- **Blokuje**: Production deployment

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Test environment differences | Średnie | Wysoki | Document env specs, use same hardware | >20% variance |
| Flaky test results | Średnie | Średni | Multiple runs, statistical analysis | High std deviation |

## Rollback Plan

1. **Detekcja problemu**: 
   - Tests crashing system
   - Invalid results
   - Resource exhaustion

2. **Kroki rollback**:
   - [ ] Stop all load generators
   - [ ] Reset test environment
   - [ ] Clear test data
   - [ ] Restart with lower load

3. **Czas rollback**: <15 min

## Następne kroki

Po ukończeniu tej fazy, przejdź do:
→ [Faza 4 - Integracja](../faza-4-integracja/01-mqtt-bridge.md)