# Faza 6 / Zadanie 3: Multi-level Caching Implementation

## Cel zadania

Zaprojektować i wdrożyć wielopoziomową strategię cachowania minimalizującą powtarzalne obliczenia i dostępy do baz danych, zwiększając throughput systemu.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Cache infrastructure ready**
   - **Metryka**: Redis cluster operational
   - **Walidacja**:

     ```bash
     # Check Redis cluster health
     redis-cli --cluster check localhost:6379 | grep "All 16384 slots covered"
     # Memory available
     redis-cli INFO memory | grep used_memory_human | awk -F: '{print $2}'
     ```

   - **Czas**: 0.5h

2. **[ ] Performance metrics baseline**
   - **Metryka**: Current cache hit rates documented
   - **Walidacja**:

     ```python
     metrics = get_current_metrics()
     assert metrics.cache_hit_rate >= 0  # May be 0 if no caching yet
     assert metrics.db_query_rate > 100  # queries/sec showing need for cache
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Cache architecture design

#### Zadania atomowe

1. **[ ] Multi-tier cache strategy**
   - **Metryka**: 3-tier cache design documented
   - **Walidacja**:

     ```python
     design = load_cache_design("docs/cache-architecture.yaml")
     assert len(design.tiers) == 3  # L1: memory, L2: Redis, L3: disk
     assert all(t.ttl_seconds > 0 for t in design.tiers)
     assert design.tiers[0].size_mb < design.tiers[1].size_mb
     ```

   - **Czas**: 2h

2. **[ ] Cache key design patterns**
   - **Metryka**: Consistent key naming across services
   - **Walidacja**:

     ```python
     from cache_utils import validate_key_pattern
     test_keys = [
         "detection:frame:cam1:12345",
         "face:embedding:person123:v2",
         "config:camera:cam1:settings"
     ]
     assert all(validate_key_pattern(k) for k in test_keys)
     ```

   - **Czas**: 1.5h

3. **[ ] Invalidation strategy**
   - **Metryka**: Cache coherence guaranteed
   - **Walidacja**:

     ```python
     strategy = CacheInvalidationStrategy()
     assert strategy.supports_cascade_invalidation == True
     assert strategy.max_propagation_delay_ms < 100
     assert len(strategy.invalidation_patterns) > 5
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Architecture documented
- Patterns established
- Invalidation planned

### Blok 2: L1 Memory cache implementation

#### Zadania atomowe

1. **[ ] In-process LRU cache**
   - **Metryka**: Sub-millisecond access time
   - **Walidacja**:

     ```python
     from cache_benchmarks import test_memory_cache
     results = test_memory_cache(operations=10000)
     assert results.avg_get_time_us < 100  # <0.1ms
     assert results.hit_rate > 0.8
     assert results.memory_overhead_percent < 10
     ```

   - **Czas**: 2.5h

2. **[ ] Detection results caching**
   - **Metryka**: 90% reduction in re-detection
   - **Walidacja**:

     ```python
     cache_test = run_detection_cache_test()
     assert cache_test.cache_hits / cache_test.total_requests > 0.9
     assert cache_test.gpu_time_saved_percent > 85
     ```

   - **Czas**: 2h

3. **[ ] Configuration cache layer**
   - **Metryka**: Zero config DB queries in hot path
   - **Walidacja**:

     ```bash
     # Monitor DB queries during load test
     pg_stat_statements_reset();
     # Run 1 minute load test
     sleep 60
     # Check config queries
     psql -c "SELECT count(*) FROM pg_stat_statements WHERE query LIKE '%config%'" \
       | grep -E "^\s*0"
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Memory cache operational
- Hit rate >80%
- Latency reduced

### Blok 3: L2 Redis cache layer

#### Zadania atomowe

1. **[ ] Redis connection pooling**
   - **Metryka**: <5ms connection overhead
   - **Walidacja**:

     ```python
     pool_stats = redis_connection_pool.get_stats()
     assert pool_stats.avg_connection_time_ms < 5
     assert pool_stats.pool_efficiency > 0.9
     assert pool_stats.connections_created < 100  # Good reuse
     ```

   - **Czas**: 2h

2. **[ ] Frame metadata caching**
   - **Metryka**: 95% cache hit for recent frames
   - **Walidacja**:

     ```python
     frame_cache_test = test_frame_metadata_cache()
     assert frame_cache_test.hit_rate_1min_window > 0.95
     assert frame_cache_test.memory_used_mb < 1000
     assert frame_cache_test.eviction_rate < 0.05
     ```

   - **Czas**: 2.5h

3. **[ ] Aggregated events cache**
   - **Metryka**: 10x reduction in aggregation compute
   - **Walidacja**:

     ```python
     before = measure_aggregation_cpu(cache_enabled=False)
     after = measure_aggregation_cpu(cache_enabled=True)
     assert before.cpu_seconds / after.cpu_seconds > 10
     assert after.result_accuracy == 1.0  # No data loss
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Redis cache integrated
- Significant CPU savings
- Data consistency maintained

### Blok 4: Cache monitoring and optimization

#### Zadania atomowe

1. **[ ] Cache metrics dashboard**
   - **Metryka**: Real-time cache performance visible
   - **Walidacja**:

     ```bash
     # Check Grafana dashboard exists
     curl -s http://localhost:3000/api/dashboards/uid/cache-performance \
       | jq '.dashboard.panels | length' | grep -E "^[1-9]"
     # Verify metrics flowing
     curl -s http://localhost:9090/api/v1/query?query=cache_hit_rate \
       | jq '.data.result | length' | grep -E "^[1-9]"
     ```

   - **Czas**: 2h

2. **[ ] Auto-tuning cache sizes**
   - **Metryka**: Optimal memory allocation
   - **Walidacja**:

     ```python
     tuner = CacheSizeAutoTuner()
     recommendations = tuner.analyze_last_24h()
     assert recommendations.memory_saved_mb > 100
     assert recommendations.hit_rate_improvement > 0.05
     tuner.apply_recommendations()
     ```

   - **Czas**: 2h

3. **[ ] Cache warmup strategies**
   - **Metryka**: <30s cold start time
   - **Walidacja**:

     ```bash
     # Restart system and measure warmup
     docker-compose restart
     time_to_90_percent_hitrate=$(measure_cache_warmup_time.py)
     test $time_to_90_percent_hitrate -lt 30 && echo "OK"
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Cache observable
- Self-optimizing
- Fast warmup

## Całościowe metryki sukcesu zadania

1. **Hit Rate**: >85% overall cache hit rate
2. **Latency**: 50% reduction in average response time
3. **Efficiency**: 70% reduction in database load

## Deliverables

1. `/src/cache/` - Cache implementation modules
2. `/configs/cache-tiers.yaml` - Cache configuration
3. `/dashboards/cache-performance.json` - Monitoring dashboard
4. `/docs/cache-architecture.md` - Design documentation
5. `/scripts/cache-warmup.py` - Warmup automation

## Narzędzia

- **Redis**: Distributed cache
- **lru-cache**: Python in-memory cache
- **redis-py**: Redis client
- **prometheus**: Metrics collection

## Zależności

- **Wymaga**: Bottleneck analysis complete
- **Blokuje**: Horizontal scaling

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Cache stampede | Średnie | Wysoki | Probabilistic early expiration | Spike in DB load |
| Memory pressure | Średnie | Średni | Adaptive sizing | OOM warnings |
| Stale data | Niskie | Wysoki | TTL + invalidation | User complaints |

## Rollback Plan

1. **Detekcja problemu**:
   - Cache corruption
   - Performance degradation
   - Memory exhaustion

2. **Kroki rollback**:
   - [ ] Disable cache layers
   - [ ] Flush Redis
   - [ ] Restart services
   - [ ] Monitor direct DB load

3. **Czas rollback**: <15 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-horizontal-scaling.md](./04-horizontal-scaling.md)
