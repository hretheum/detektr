# Faza SL-2 / Zadanie 1: Async Learning Architecture

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Learning NIGDY nie blokuje real-time processing
2. CQRS pattern properly implemented
3. Shadow mode ma ZERO wpływ na produkcję
4. Circuit breakers prevent cascading failures
5. Event sourcing dla full auditability
-->

## Cel zadania

Implementacja asynchronicznej architektury uczenia z CQRS pattern, która pozwala na ML learning w tle bez wpływu na real-time processing. Shadow mode musi działać równolegle z production agents z complete isolation i zero performance impact.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja ML infrastructure readiness**
   - **Metryka**: Wszystkie ML services (MLflow, Feast, monitoring) operational
   - **Walidação**: `./scripts/health-check-ml.sh | grep "All systems healthy"`
   - **Czas**: 0.5h

2. **[ ] Performance baseline measurement**
   - **Metryka**: Current agent response times documented para comparison
   - **Walidação**: `python scripts/benchmark_agents.py --baseline | grep "Baseline established"`
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: CQRS Pattern Implementation

<!--
LLM PROMPT dla bloku:
CQRS (Command Query Responsibility Segregation) musi separować:
- Commands (learning operations) - eventual consistency OK
- Queries (decision making) - immediate consistency required
-->

#### Zadania atomowe:
1. **[ ] Command side - Async learning writer**
   - **Metryka**: Learning commands processed asynchronously via Redis Streams
   - **Walidação**:
     ```bash
     python -c "
     from learning.cqrs import AsyncLearningWriter
     writer = AsyncLearningWriter()
     writer.record_decision({'agent': 'test', 'decision': 'test'})
     "
     redis-cli XLEN ml-learning-commands | grep -E "[1-9][0-9]*"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Query side - Cached decision reader**
   - **Metryka**: Decision queries served z cache <5ms latency
   - **Walidção**:
     ```bash
     python -c "
     from learning.cqrs import CachedDecisionReader
     reader = CachedDecisionReader()
     start = time.time()
     decision = reader.get_decision({'context': 'test'})
     latency = (time.time() - start) * 1000
     assert latency < 5, f'Latency {latency}ms too high'
     "
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Event sourcing dla auditability**
   - **Metryka**: All learning events stored w immutable event log
   - **Walidação**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "SELECT COUNT(*) FROM ml_learning.event_store WHERE event_type='decision_made';" | tail -1 | grep -E "[0-9]+"
     python scripts/test_event_replay.py | grep "Event replay successful"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- CQRS pattern fully operational
- Write operations non-blocking <1ms
- Read operations <5ms latency
- Event sourcing capturing all decisions
- Complete audit trail available

### Blok 2: Shadow Mode Framework

<!--
LLM PROMPT dla bloku:
Shadow mode framework that runs ML predictions w parallel
without affecting production decisions.
-->

#### Zadania atomowe:
1. **[ ] Shadow wrapper implementation**
   - **Metryka**: Shadow wrapper działa para any agent without modification
   - **Walidação**:
     ```bash
     python -c "
     from learning.shadow import ShadowLearner
     from agents.code_reviewer import CodeReviewer
     shadow = ShadowLearner('code-reviewer', CodeReviewer())
     result = shadow.execute_task({'type': 'review', 'code': 'test'})
     assert result is not None
     "
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Non-blocking prediction pipeline**
   - **Metryka**: ML predictions run w background, zero blocking
   - **Walidação**:
     ```bash
     python scripts/test_shadow_performance.py --measure-blocking
     # Should show 0ms blocking time
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Shadow result logging i comparison**
   - **Metryka**: Shadow vs production results logged para analysis
   - **Walidação**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "SELECT COUNT(*) FROM ml_learning.shadow_results WHERE created_at > NOW() - INTERVAL '1 hour';" | tail -1 | grep -E "[1-9][0-9]*"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Shadow framework works z any agent
- Zero production impact measured
- Shadow predictions logged para comparison
- Performance isolation verified
- Framework ready para all 8 agents

### Blok 3: Circuit Breaker Implementation

<!--
LLM PROMPT dla bloku:
Circuit breakers para prevent ML failures z affecting production.
Multiple circuit breaker patterns para different failure modes.
-->

#### Zadania atomowe:
1. **[ ] ML service circuit breaker**
   - **Metryka**: Circuit breaker opens on ML service failures, fallback to deterministic
   - **Walidação**:
     ```bash
     # Simulate MLflow failure
     docker stop mlflow
     python scripts/test_circuit_breaker.py --service=mlflow
     # Should fallback to deterministic after 5 failures
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

2. **[ ] Prediction latency circuit breaker**
   - **Metryka**: Circuit breaker on prediction timeout (>100ms)
   - **Walidação**:
     ```bash
     python scripts/test_latency_breaker.py --simulate-slow-prediction
     # Should open circuit after 3 slow predictions
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] Model accuracy circuit breaker**
   - **Metryka**: Circuit breaker on accuracy drop >20%
   - **Walidação**:
     ```bash
     python scripts/test_accuracy_breaker.py --simulate-bad-model
     # Should trigger rollback to deterministic
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- 3 circuit breaker types operational
- Automatic fallback to deterministic working
- Circuit recovery after issues resolved
- <30 second detection time para issues
- Zero cascading failures observed

### Blok 4: Performance Isolation

<!--
LLM PROMPT dla bloku:
Guarantee that ML learning never impacts production performance.
Resource isolation, monitoring, automatic throttling.
-->

#### Zadania atomowe:
1. **[ ] Resource quota enforcement**
   - **Metryka**: ML processes limited to 20% CPU, 4GB RAM max
   - **Walidação**:
     ```bash
     docker stats ml-learning --no-stream | grep -E "([0-9]|1[0-9])\..*%" # <20% CPU
     docker stats ml-learning --no-stream | grep -E "[0-3]\.[0-9]+GiB"   # <4GB RAM
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

2. **[ ] Automatic throttling on high load**
   - **Metryka**: ML learning automatically slows down when system under load
   - **Walidação**:
     ```bash
     # Simulate high system load
     stress --cpu 6 --timeout 60s &
     python scripts/test_throttling.py | grep "Learning throttled"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Performance monitoring i alerting**
   - **Metryka**: Real-time monitoring para ML impact on production
   - **Walidação**:
     ```bash
     curl -s http://nebula:9090/api/v1/query?query=ml_performance_impact_ratio | jq '.data.result[0].value[1]' | python -c "import sys; exit(0 if float(sys.stdin.read()) < 0.05 else 1)"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Resource isolation enforced
- Automatic throttling working
- Production performance unaffected
- Real-time impact monitoring
- <5% impact threshold maintained

## Całościowe metryki sukcesu zadania

1. **Zero Production Impact**: Production agent latency unchanged (<1ms variance)
2. **Shadow Mode Operational**: ML predictions running w parallel para all agents
3. **Circuit Breaker Protection**: Automatic fallback to deterministic on any ML issue
4. **Performance Isolation**: ML learning using <20% resources, automatic throttling
5. **Audit Trail Complete**: All decisions i predictions logged para analysis

## Deliverables

1. `/services/ml-learning/cqrs/` - CQRS implementation
2. `/services/ml-learning/shadow/` - Shadow mode framework
3. `/services/ml-learning/circuit-breaker/` - Circuit breaker implementation
4. `/scripts/performance/` - Performance monitoring i testing
5. `/docs/self-learning-agents/architecture-guide.md` - Architecture documentation
6. `/tests/integration/shadow-mode/` - Shadow mode integration tests

## Narzędzia

- **Python asyncio**: Asynchronous processing
- **Redis Streams**: Event processing i queuing
- **PostgreSQL**: Event sourcing storage
- **Docker**: Resource isolation
- **Prometheus**: Performance monitoring
- **py-breaker**: Circuit breaker implementation

## Zależności

- **Wymaga**: Faza SL-1 completed (ML infrastructure ready)
- **Blokuje**: 02-shadow-mode-wrapper.md (wymaga async architecture)

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Memory leaks w async processing | Średnie | Średni | Memory monitoring, automatic restarts | Memory usage >4GB |
| Circuit breaker false positives | Średnie | Niski | Careful threshold tuning | >5 false triggers/day |
| Event sourcing storage growth | Wysokie | Średni | Automated archival, compression | Storage growth >1GB/day |
| Resource contention despite isolation | Niskie | Średni | Additional resource limits | CPU steal time >5% |

## Rollback Plan

1. **Detekcja problemu**: Production performance degradation or ML system instability
2. **Kroki rollback**:
   - [ ] Disable shadow learning: `docker stop ml-learning-service`
   - [ ] Open all circuit breakers: `curl -X POST http://nebula:8090/circuit-breakers/open-all`
   - [ ] Revert to deterministic: `export ML_ENABLED=false && make deploy`
   - [ ] Clear event queues: `redis-cli DEL ml-learning-commands`
3. **Czas rollback**: <30 seconds

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-shadow-mode-wrapper.md](./02-shadow-mode-wrapper.md)
