# Faza 6 / Zadanie 1: System-wide Performance Profiling

## Cel zadania
Przeprowadzić kompleksowe profilowanie wydajności całego systemu, identyfikując obszary zużycia zasobów i tworząc bazową mapę wydajności dla optymalizacji.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja narzędzi profilowania**
   - **Metryka**: Wszystkie profilery zainstalowane i działające
   - **Walidacja**: 
     ```bash
     # Check profiling tools
     python -m cProfile --version && echo "cProfile: OK"
     py-spy --version && echo "py-spy: OK"
     nvidia-smi && echo "NVIDIA tools: OK"
     ```
   - **Czas**: 0.5h

2. **[ ] System pod obciążeniem testowym**
   - **Metryka**: Symulacja 10 kamer @ 30 FPS
   - **Walidacja**: 
     ```bash
     # Verify load generator running
     docker logs load-generator 2>&1 | grep "FPS: 30" | wc -l
     # Should return >= 10
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: CPU & Memory profiling

#### Zadania atomowe:
1. **[ ] Profile głównych procesów Python**
   - **Metryka**: Profile dla każdego serwisu zebrane
   - **Walidacja**: 
     ```python
     import os
     profiles = os.listdir("profiles/cpu/")
     services = ["capture", "detection", "aggregation", "api"]
     assert all(f"{s}_profile.prof" in profiles for s in services)
     ```
   - **Czas**: 2.5h

2. **[ ] Analiza memory leaks**
   - **Metryka**: Żadnych wycieków >10MB/h
   - **Walidacja**: 
     ```python
     from memory_profiler import analyze_growth
     growth = analyze_growth("profiles/memory/24h_run.log")
     assert growth.rate_mb_per_hour < 10
     assert growth.gc_effectiveness > 0.95
     ```
   - **Czas**: 2h

3. **[ ] Flame graphs generation**
   - **Metryka**: Interactive flame graphs dla hot paths
   - **Walidacja**: 
     ```bash
     # Check flame graphs exist and are valid HTML
     for service in capture detection aggregation; do
       file="profiles/flamegraphs/${service}_flame.html"
       test -f "$file" && grep -q "svg" "$file" && echo "$service: OK"
     done
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- CPU hotspots zidentyfikowane
- Memory usage patterns clear
- Visual profiles generated

### Blok 2: GPU & AI profiling

#### Zadania atomowe:
1. **[ ] NVIDIA Nsight profiling**
   - **Metryka**: GPU utilization timeline captured
   - **Walidacja**: 
     ```python
     import json
     with open("profiles/gpu/nsight_report.json") as f:
         report = json.load(f)
     assert report["gpu_utilization_avg"] > 0.4
     assert report["memory_bandwidth_efficiency"] > 0.7
     ```
   - **Czas**: 2h

2. **[ ] Model inference profiling**
   - **Metryka**: Per-layer latency breakdown
   - **Walidacja**: 
     ```python
     from torch.profiler import profile_analyzer
     analysis = profile_analyzer.load("profiles/models/yolo_profile.json")
     assert analysis.total_inference_time_ms < 50
     assert len(analysis.layer_timings) > 20
     ```
   - **Czas**: 2h

3. **[ ] Batch processing analysis**
   - **Metryka**: Optimal batch sizes identified
   - **Walidacja**: 
     ```python
     batch_analysis = analyze_batch_performance()
     assert batch_analysis.optimal_batch_size in range(4, 33)
     assert batch_analysis.throughput_gain > 2.0  # vs batch_size=1
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- GPU bottlenecks identified
- Model optimization opportunities found
- Batch processing optimized

### Blok 3: I/O & Network profiling

#### Zadania atomowe:
1. **[ ] Database query profiling**
   - **Metryka**: Slow queries identified and indexed
   - **Walidacja**: 
     ```sql
     -- No queries >100ms
     SELECT count(*) FROM pg_stat_statements 
     WHERE mean_exec_time > 100;
     -- Should return 0
     ```
   - **Czas**: 2h

2. **[ ] Redis operations analysis**
   - **Metryka**: Pipeline efficiency >80%
   - **Walidacja**: 
     ```bash
     redis-cli INFO commandstats | python -c "
     import sys
     stats = sys.stdin.read()
     pipeline = int(stats.split('calls_pipeline=')[1].split(',')[0])
     total = int(stats.split('calls_total=')[1].split(',')[0])
     assert pipeline/total > 0.8
     "
     ```
   - **Czas**: 1.5h

3. **[ ] Network latency mapping**
   - **Metryka**: Service mesh latency <5ms p99
   - **Walidacja**: 
     ```bash
     curl -s http://prometheus:9090/api/v1/query \
       -d 'query=histogram_quantile(0.99, http_request_duration_seconds_bucket)' \
       | jq '.data.result[0].value[1]' \
       | awk '{if ($1 < 0.005) print "OK"; else print "FAIL"}'
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Database optimized
- Caching effective
- Network overhead minimized

### Blok 4: Profiling automation

#### Zadania atomowe:
1. **[ ] Continuous profiling setup**
   - **Metryka**: Auto-profiling every 6h
   - **Walidacja**: 
     ```bash
     # Check cron job configured
     crontab -l | grep "profile_system.py"
     # Check last run
     find profiles/automated -name "*.prof" -mmin -360 | wc -l
     # Should return > 0
     ```
   - **Czas**: 2h

2. **[ ] Performance regression detection**
   - **Metryka**: Automated alerts for >10% regression
   - **Walidacja**: 
     ```python
     from performance_monitor import check_regression
     result = check_regression(baseline="v1.0", current="HEAD")
     assert result.regression_detected == False
     assert result.alert_threshold == 0.1
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Profiling automated
- Regressions detected early
- Historical data collected

## Całościowe metryki sukcesu zadania

1. **Coverage**: 100% serwisów sprofilowanych
2. **Baseline**: Performance baseline established dla wszystkich komponentów
3. **Automation**: Continuous profiling aktywne

## Deliverables

1. `/profiles/cpu/` - CPU profiles dla każdego serwisu
2. `/profiles/memory/` - Memory usage analysis
3. `/profiles/gpu/` - GPU utilization reports
4. `/profiles/flamegraphs/` - Interactive flame graphs
5. `/scripts/profile_system.py` - Automated profiling script
6. `/docs/performance-baseline.md` - Baseline documentation

## Narzędzia

- **cProfile**: Python CPU profiling
- **py-spy**: Sampling profiler dla produkcji
- **memory_profiler**: Memory leak detection
- **NVIDIA Nsight**: GPU profiling
- **FlameGraph**: Visualization

## Zależności

- **Wymaga**: System running z pełnym obciążeniem
- **Blokuje**: Optymalizacje wydajności

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Profiling overhead | Średnie | Średni | Use sampling profilers | CPU >80% |
| Incomplete coverage | Niskie | Wysoki | Automated checks | Missing profiles |
| Misleading data | Średnie | Wysoki | Multiple profiling runs | High variance |

## Rollback Plan

1. **Detekcja problemu**: 
   - Profiling crashes system
   - Invalid data collected
   - Performance degradation

2. **Kroki rollback**:
   - [ ] Stop profiling processes
   - [ ] Remove profiling hooks
   - [ ] Restore normal operation
   - [ ] Use lighter profiling

3. **Czas rollback**: <15 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-bottleneck-analysis.md](./02-bottleneck-analysis.md)