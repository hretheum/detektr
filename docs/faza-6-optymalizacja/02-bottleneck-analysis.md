# Faza 6 / Zadanie 2: Identifying and Fixing Bottlenecks

## Cel zadania

Przeprowadzić data-driven analizę bottlenecków zidentyfikowanych podczas profilowania i wdrożyć targeted optymalizacje z mierzalnym wpływem na wydajność.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Profiling data kompletne**
   - **Metryka**: Profile data z ostatnich 7 dni
   - **Walidacja**:

     ```bash
     # Check profile data exists
     find profiles/ -name "*.prof" -mtime -7 | wc -l
     # Should return > 50
     ```

   - **Czas**: 0.5h

2. **[ ] Performance baseline documented**
   - **Metryka**: Current metrics recorded
   - **Walidacja**:

     ```python
     import json
     with open("docs/performance-baseline.json") as f:
         baseline = json.load(f)
     assert all(k in baseline for k in ["fps", "latency_p99", "cpu_avg", "memory_mb"])
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Bottleneck prioritization

#### Zadania atomowe

1. **[ ] Automated bottleneck ranking**
   - **Metryka**: Top 10 bottlenecks by impact
   - **Walidacja**:

     ```python
     from bottleneck_analyzer import rank_bottlenecks
     bottlenecks = rank_bottlenecks()
     assert len(bottlenecks) >= 10
     assert bottlenecks[0].impact_score > bottlenecks[-1].impact_score
     assert sum(b.estimated_improvement for b in bottlenecks[:5]) > 0.3
     ```

   - **Czas**: 2h

2. **[ ] Cost-benefit analysis**
   - **Metryka**: ROI calculated for each optimization
   - **Walidacja**:

     ```python
     analysis = cost_benefit_analysis(bottlenecks)
     assert all(opt.roi > 2.0 for opt in analysis.recommended)
     assert all(opt.implementation_hours < 8 for opt in analysis.quick_wins)
     ```

   - **Czas**: 1.5h

3. **[ ] Optimization roadmap**
   - **Metryka**: Prioritized fix sequence
   - **Walidacja**:

     ```bash
     # Roadmap includes dependencies and timeline
     jq '.optimizations[] | select(.priority=="P0") | .estimated_gain' \
       optimization_roadmap.json | awk '{s+=$1} END {print s > 0.2}'
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Bottlenecks ranked by impact
- Quick wins identified
- Clear optimization path

### Blok 2: Quick win optimizations

#### Zadania atomowe

1. **[ ] Inefficient loops optimization**
   - **Metryka**: 30% reduction in CPU time
   - **Walidacja**:

     ```python
     from performance_tests import measure_optimization
     before = measure_optimization("detection_loop", version="before")
     after = measure_optimization("detection_loop", version="after")
     assert (before.cpu_time - after.cpu_time) / before.cpu_time > 0.3
     ```

   - **Czas**: 2.5h

2. **[ ] Database query optimization**
   - **Metryka**: All queries <50ms
   - **Walidacja**:

     ```sql
     -- Check optimized queries
     SELECT max(mean_exec_time) as max_time
     FROM pg_stat_statements
     WHERE query LIKE '%detection%';
     -- Should return < 50
     ```

   - **Czas**: 2h

3. **[ ] Memory allocation patterns**
   - **Metryka**: 40% reduction in allocations
   - **Walidacja**:

     ```python
     import tracemalloc
     stats = analyze_memory_allocations("after_optimization")
     assert stats.allocations_per_second < 1000
     assert stats.peak_memory_mb < baseline.peak_memory_mb * 0.6
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Quick wins implemented
- Measurable improvements
- No regressions

### Blok 3: Algorithmic optimizations

#### Zadania atomowe

1. **[ ] Frame processing pipeline**
   - **Metryka**: 2x throughput increase
   - **Walidacja**:

     ```python
     pipeline_test = run_pipeline_benchmark()
     assert pipeline_test.frames_per_second > baseline.fps * 2
     assert pipeline_test.latency_p99_ms < baseline.latency_p99 * 0.7
     ```

   - **Czas**: 3h

2. **[ ] Detection batching strategy**
   - **Metryka**: GPU utilization >80%
   - **Walidacja**:

     ```bash
     # Monitor GPU during load test
     nvidia-smi --query-gpu=utilization.gpu \
       --format=csv,noheader,nounits -l 1 | \
       awk '{s+=$1; n++} END {print s/n > 80}'
     ```

   - **Czas**: 2.5h

3. **[ ] Event aggregation optimization**
   - **Metryka**: 50% reduction in redundant events
   - **Walidacja**:

     ```python
     from event_analyzer import measure_redundancy
     redundancy = measure_redundancy(window="1h")
     assert redundancy.duplicate_rate < 0.05
     assert redundancy.aggregation_ratio > 10
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Core algorithms optimized
- Resource utilization improved
- System more efficient

### Blok 4: Optimization validation

#### Zadania atomowe

1. **[ ] End-to-end performance tests**
   - **Metryka**: All SLAs met under load
   - **Walidacja**:

     ```bash
     # Run full performance suite
     pytest tests/performance/ -v --benchmark-only
     # All tests should pass with margins
     ```

   - **Czas**: 2h

2. **[ ] Before/after comparison report**
   - **Metryka**: Detailed improvements documented
   - **Walidacja**:

     ```python
     report = generate_optimization_report()
     assert report.overall_improvement > 0.4
     assert all(m.improved for m in report.metrics)
     assert report.includes_graphs == True
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Improvements validated
- Results documented
- Ready for production

## Całościowe metryki sukcesu zadania

1. **Performance**: >40% overall improvement vs baseline
2. **Efficiency**: Resource usage reduced by >30%
3. **Stability**: No performance regressions

## Deliverables

1. `/src/optimized/` - Optimized code modules
2. `/benchmarks/before_after/` - Performance comparisons
3. `/docs/optimization-report.html` - Detailed results
4. `/configs/optimized-settings.yaml` - Tuned configurations
5. `/tests/performance/regression/` - Regression test suite

## Narzędzia

- **perf**: Linux performance analysis
- **pytest-benchmark**: Micro benchmarks
- **locust**: Load testing
- **grafana**: Visualization

## Zależności

- **Wymaga**: Performance profiling complete
- **Blokuje**: Production deployment

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Optimization breaks functionality | Średnie | Wysoki | Comprehensive testing | Test failures |
| Minimal improvement | Niskie | Średni | Multiple approaches | <10% gain |
| New bottlenecks appear | Średnie | Średni | Continuous profiling | Metrics shift |

## Rollback Plan

1. **Detekcja problemu**:
   - Performance regression
   - Functionality broken
   - Instability increased

2. **Kroki rollback**:
   - [ ] Revert optimized code
   - [ ] Restore original configs
   - [ ] Clear caches
   - [ ] Verify baseline restored

3. **Czas rollback**: <30 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-caching-strategy.md](./03-caching-strategy.md)
