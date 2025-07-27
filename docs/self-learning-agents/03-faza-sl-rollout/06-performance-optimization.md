# Faza SL-3 / Zadanie 6: Performance Optimization

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. End-to-end latency optimization dla entire ML pipeline
2. Memory i CPU usage optimization pod production load
3. Database query optimization dla ML data access
4. Caching strategies dla frequently accessed predictions
5. Load testing i performance validation pod różnymi scenarios
-->

## Cel zadania

Comprehensive performance optimization całej ML infrastructure. Target: P95 latency <50ms dla ML decisions, memory usage <2GB per service, CPU utilization <60% pod peak load. Validation przez extensive load testing i production scenarios.

## Blok 0: Prerequisites check

<!--
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe:
1. **[ ] Weryfikacja production hardening stability z Zadania 5**
   - **Metryka**: All security i redundancy features operational bez performance issues
   - **Walidacja**: `curl -s http://nebula:8093/api/sla/ml-services/current | jq '.uptime_percentage > 99.9 and .response_time_p95 < 100'`
   - **Czas**: 0.5h

2. **[ ] Current performance baseline measurement**
   - **Metryka**: Baseline P95 latency, memory, CPU usage documented
   - **Walidacja**: `/scripts/performance-baseline.sh ml-services | grep -E "p95_latency|memory_usage|cpu_usage"` shows current metrics
   - **Czas**: 1h

## Dekompozycja na bloki zadań

### Blok 1: ML Pipeline Latency Optimization

<!--
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. Feature pipeline optimization - reduce feature preparation time
2. Model inference optimization - faster prediction generation
3. Response serialization optimization - faster API responses
4. End-to-end request flow optimization
-->

#### Zadania atomowe:
1. **[ ] Feature pipeline performance optimization**
   <!--
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Profile feature preparation bottlenecks
   - Implement caching dla expensive feature calculations
   - Optimize database queries dla feature retrieval
   - Po ukończeniu ZAWSZE wymagać code review przez `/agent code-reviewer`
   -->
   - **Metryka**: Feature preparation time reduced from >10ms to <5ms
   - **Walidacja**:
     ```bash
     # Test feature preparation speed
     time curl -s http://nebula:8095/api/documentation-keeper/features -d '{"context": "large context with 1000 words"}' | jq '.preparation_time_ms < 5'
     ```
   - **Code Review**: `/agent code-reviewer` (OBOWIĄZKOWE po implementacji)
   - **Czas**: 4h

2. **[ ] Model inference optimization**
   - **Metryka**: Model prediction time reduced to <20ms dla single prediction
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8095/api/documentation-keeper/decide -d '{"task": "update README"}' | jq '.inference_time_ms < 20'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

3. **[ ] API response optimization**
   - **Metryka**: Total API response time <50ms P95
   - **Walidacja**:
     ```bash
     # Load test API responses
     wrk -t 4 -c 40 -d 60s --script=/scripts/api-test.lua http://nebula:8095/api/documentation-keeper/decide
     # Check P95 latency in output is <50ms
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

#### Metryki sukcesu bloku:
- Feature preparation <5ms consistently
- Model inference <20ms P95
- End-to-end API response <50ms P95
- Throughput increased by >50%
- Zero accuracy degradation from optimizations

### Blok 2: Memory i Resource Optimization

<!--
LLM PROMPT dla bloku:
Optimization memory usage i CPU consumption.
Musi maintain functionality while reducing resource footprint.
-->

#### Zadania atomowe:
1. **[ ] Memory usage optimization**
   - **Metryka**: ML services memory usage <2GB per instance
   - **Walidacja**:
     ```bash
     docker stats --no-stream | grep ml-serving | awk '{print $4}' | grep -E "^[0-9]+[.]?[0-9]*[MG]iB$" | sed 's/GiB/ * 1024/g; s/MiB//g' | bc | awk '{print ($1 < 2048)}'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

2. **[ ] CPU utilization optimization**
   - **Metryka**: CPU usage <60% pod peak load
   - **Walidacja**:
     ```bash
     # Load test i monitor CPU
     wrk -t 8 -c 80 -d 300s http://nebula:8095/api/documentation-keeper/decide &
     sleep 60
     docker stats --no-stream | grep ml-serving | awk '{print $3}' | sed 's/%//g' | awk '{print ($1 < 60)}'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

3. **[ ] Garbage collection i memory leak prevention**
   - **Metryka**: No memory leaks detected w 24h stress test
   - **Walidacja**:
     ```bash
     # Start stress test i monitor memory over 24h
     /scripts/memory-stress-test.sh 24h
     # Memory should remain stable, no continuous growth
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h + 24h monitoring

#### Metryki sukcesu bloku:
- Memory usage consistently <2GB per service
- CPU utilization <60% pod peak load
- No memory leaks detected
- Resource usage stable over time
- Efficient garbage collection tuned

### Blok 3: Database i Caching Optimization

<!--
LLM PROMPT dla bloku:
Database query optimization i intelligent caching strategies.
Musi significantly reduce database load.
-->

#### Zadania atomowe:
1. **[ ] Database query optimization**
   - **Metryka**: ML-related database queries <10ms P95
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "SELECT query, mean_exec_time FROM pg_stat_statements WHERE query LIKE '%ml_learning%' ORDER BY mean_exec_time DESC LIMIT 5;" | awk 'NR>2 {print $2}' | awk '{print ($1 < 10)}'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

2. **[ ] Redis caching strategy implementation**
   - **Metryka**: 80%+ cache hit rate dla ML features i predictions
   - **Walidação**:
     ```bash
     redis-cli info stats | grep keyspace_hits | awk -F: '{hits=$2}' && redis-cli info stats | grep keyspace_misses | awk -F: '{misses=$2}' && echo "scale=2; $hits / ($hits + $misses) * 100" | bc | awk '{print ($1 > 80)}'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

3. **[ ] Prediction result caching i invalidation**
   - **Metryka**: Frequently requested predictions served from cache <1ms
   - **Walidação**:
     ```bash
     # Test cache performance
     curl -s http://nebula:8095/api/documentation-keeper/decide -d '{"task": "update README"}' | jq '.cache_hit == false'
     curl -s http://nebula:8095/api/documentation-keeper/decide -d '{"task": "update README"}' | jq '.cache_hit == true and .response_time_ms < 1'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Database queries optimized <10ms P95
- Cache hit rate >80% dla ML operations
- Prediction caching working effectively
- Cache invalidation strategies proper
- Database load reduced by >60%

### Blok 4: Load Testing i Performance Validation

<!--
LLM PROMPT dla bloku:
Comprehensive load testing pod various scenarios.
Musi validate performance pod real production conditions.
-->

#### Zadania atomowe:
1. **[ ] Comprehensive load testing suite**
   - **Metryka**: Load tests pass dla 1000 RPS sustained
   - **Walidação**:
     ```bash
     # Test sustained high load
     wrk -t 10 -c 100 -d 600s --rate 1000 http://nebula:8095/api/documentation-keeper/decide
     # Should maintain P95 <50ms throughout test
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

2. **[ ] Stress testing i breaking point identification**
   - **Metryka**: System gracefully degrades, no crashes pod extreme load
   - **Walidação**:
     ```bash
     # Gradually increase load until breaking point
     /scripts/stress-test-gradual.sh
     # System should degrade gracefully, not crash
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

3. **[ ] Production scenario simulation**
   - **Metryka**: Real production patterns simulated successfully
   - **Walidação**:
     ```bash
     # Simulate production traffic patterns
     /scripts/production-simulation.sh --duration 3600s
     # Should handle realistic traffic patterns without issues
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Sustained 1000 RPS performance achieved
- Graceful degradation pod extreme load
- Production scenarios handled successfully
- No performance regression detected
- SLA targets met pod all test conditions

## Całościowe metryki sukcesu zadania

<!--
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **Latency Excellence**: P95 latency consistently <50ms dla all ML decisions
2. **Resource Efficiency**: Memory <2GB per service, CPU <60% pod peak load
3. **Throughput Achievement**: System handles 1000+ RPS sustained load
4. **Database Performance**: ML queries <10ms P95, cache hit rate >80%
5. **Production Readiness**: All performance targets met pod realistic load scenarios

## Deliverables

<!--
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi mieć konkretną ścieżkę i być wymieniony w zadaniu atomowym.
-->

1. `/services/ml-serving/optimized/` - Performance-optimized ML serving
2. `/scripts/performance/load-testing-suite/` - Comprehensive load testing tools
3. `/scripts/performance/performance-baseline.sh` - Performance measurement tools
4. `/monitoring/grafana/dashboards/ml-performance-monitoring.json` - Performance dashboard
5. `/docs/self-learning-agents/performance-tuning-guide.md` - Performance optimization guide
6. `/scripts/caching/redis-ml-cache-config.sh` - Optimized caching configuration
7. `/scripts/database/ml-query-optimization.sql` - Database optimization queries
8. `/scripts/performance/production-simulation.sh` - Production load simulation

## Narzędzia

<!--
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
-->

- **wrk**: HTTP load testing i benchmarking
- **py-spy**: Python profiling dla performance analysis
- **Redis**: High-performance caching layer
- **PostgreSQL pg_stat_statements**: Query performance monitoring
- **Prometheus**: Performance metrics collection
- **Grafana**: Performance visualization
- **Docker Stats**: Container resource monitoring

## Zależności

- **Wymaga**: 05-production-hardening.md ukończone (security i reliability operational)
- **Blokuje**: Faza SL-4 (Multi-Agent Expansion)

## Ryzyka i mitigacje

<!--
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Optimization breaks functionality | Średnie | Wysoki | Extensive testing, gradual rollout | Accuracy drops lub service errors |
| Performance gains not sustainable | Średnie | Średni | Long-term testing, monitoring | Performance regression detected |
| Caching introduces stale data | Niskie | Średni | Proper cache invalidation, TTL policies | Incorrect predictions |
| Load testing impacts production | Niskie | Średni | Separate test environment, rate limiting | Production performance degrades |

## Rollback Plan

<!--
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
-->

1. **Detekcja problemu**: Performance optimizations cause functionality issues
2. **Kroki rollback**:
   - [ ] Revert optimization: Roll back to previous working version
   - [ ] Disable caching: Fall back to direct database queries
   - [ ] Restore baseline: Use pre-optimization configuration
   - [ ] Validate function: Ensure all features working correctly
3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, Faza SL-3 jest complete. Przejdź do:
→ Faza SL-4: Multi-Agent Expansion `/nakurwiaj faza-sl-4`

---

## 🎉 Faza SL-3 Complete!

Gratulations! Documentation-keeper agent jest teraz fully operational w production z:
- ✅ A/B testing framework
- ✅ 100% ML traffic rollout
- ✅ Explainable AI dashboard
- ✅ Production hardening
- ✅ Performance optimization

**Ready for multi-agent expansion!** 🚀
