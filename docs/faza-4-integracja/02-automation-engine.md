# Faza 4 / Zadanie 2: Rule engine for if-then-else automation

## Cel zadania
Zaimplementować elastyczny silnik reguł umożliwiający tworzenie złożonych automatyzacji z warunkami, akcjami i integracją z Home Assistant.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja event bus**
   - **Metryka**: Event bus przyjmuje i dystrybuuje eventy
   - **Walidacja**: 
     ```bash
     # Send test event
     curl -X POST http://localhost:8003/events \
          -H "Content-Type: application/json" \
          -d '{"type": "test.event", "data": {"timestamp": "'$(date +%s)'"}}'
     # Check propagation
     docker logs detektor-event-bus --tail 50 | grep "test.event"
     ```
   - **Czas**: 0.5h

2. **[ ] Test action executors**
   - **Metryka**: Podstawowe akcje (MQTT, HTTP, log) działają
   - **Walidacja**: 
     ```python
     from src.automation.actions import ActionRegistry
     registry = ActionRegistry()
     assert "mqtt_publish" in registry.available_actions()
     assert "http_request" in registry.available_actions()
     assert "log_message" in registry.available_actions()
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Rule definition and storage

#### Zadania atomowe:
1. **[ ] Rule schema design**
   - **Metryka**: Elastyczny format YAML/JSON dla złożonych reguł
   - **Walidacja**: 
     ```python
     from src.automation.rules import RuleSchema
     
     # Test complex rule parsing
     rule_yaml = """
     name: "Motion Light Control"
     triggers:
       - type: event
         event_type: motion_detected
         filters:
           camera_id: front_door
           time_range: "sunset-sunrise"
     conditions:
       - type: state
         entity: binary_sensor.front_door
         state: "closed"
       - type: numeric
         entity: sensor.luminance
         below: 30
     actions:
       - type: mqtt_publish
         topic: homeassistant/light/entrance/set
         payload: 
           state: "on"
           brightness: 80
       - type: delay
         seconds: 300
       - type: mqtt_publish
         topic: homeassistant/light/entrance/set
         payload:
           state: "off"
     """
     
     rule = RuleSchema.parse(rule_yaml)
     assert rule.name == "Motion Light Control"
     assert len(rule.triggers) == 1
     assert len(rule.conditions) == 2
     assert len(rule.actions) == 3
     ```
   - **Czas**: 2.5h

2. **[ ] Rule repository with PostgreSQL**
   - **Metryka**: CRUD operations, versioning, validation
   - **Walidacja**: 
     ```python
     from src.automation.repositories import RuleRepository
     
     repo = RuleRepository()
     
     # Test CRUD
     rule_id = repo.create(rule_data)
     assert rule_id is not None
     
     rule = repo.get(rule_id)
     assert rule.version == 1
     
     repo.update(rule_id, updated_data)
     rule = repo.get(rule_id)
     assert rule.version == 2
     
     # Test validation
     try:
         repo.create(invalid_rule_data)
         assert False, "Should reject invalid rule"
     except ValidationError:
         pass
     ```
   - **Czas**: 2h

3. **[ ] Rule import/export API**
   - **Metryka**: RESTful API dla zarządzania regułami
   - **Walidacja**: 
     ```bash
     # Create rule via API
     curl -X POST http://localhost:8003/api/rules \
          -H "Content-Type: application/yaml" \
          --data-binary @test_rule.yaml
     
     # List rules
     curl http://localhost:8003/api/rules | jq '.rules | length'
     # Should return count > 0
     
     # Export rules
     curl http://localhost:8003/api/rules/export > rules_backup.yaml
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Kompletny model reguł
- Persistent storage z wersjonowaniem
- RESTful API dla zarządzania

### Blok 2: Rule execution engine

#### Zadania atomowe:
1. **[ ] Event matching and filtering**
   - **Metryka**: Wydajne dopasowanie eventów do triggerów
   - **Walidacja**: 
     ```python
     from src.automation.engine import RuleEngine
     
     engine = RuleEngine()
     engine.load_rules()
     
     # Test event matching
     matched_rules = engine.match_event({
         "type": "motion_detected",
         "camera_id": "front_door",
         "timestamp": "2024-01-15T22:00:00Z"
     })
     
     assert len(matched_rules) > 0
     assert all(r.has_matching_trigger() for r in matched_rules)
     
     # Performance test
     import time
     start = time.time()
     for _ in range(10000):
         engine.match_event(test_event)
     elapsed = time.time() - start
     assert elapsed < 1.0  # 10k matches in <1s
     ```
   - **Czas**: 2.5h

2. **[ ] Condition evaluation engine**
   - **Metryka**: Obsługa złożonych warunków z AND/OR/NOT
   - **Walidacja**: 
     ```python
     from src.automation.conditions import ConditionEvaluator
     
     evaluator = ConditionEvaluator()
     
     # Complex condition test
     conditions = {
         "and": [
             {"state": {"entity": "sensor.temperature", "above": 25}},
             {"or": [
                 {"state": {"entity": "binary_sensor.window", "is": "open"}},
                 {"state": {"entity": "fan.bedroom", "is": "off"}}
             ]},
             {"not": {"state": {"entity": "input_boolean.vacation", "is": "on"}}}
         ]
     }
     
     context = {
         "sensor.temperature": 26,
         "binary_sensor.window": "closed",
         "fan.bedroom": "off",
         "input_boolean.vacation": "off"
     }
     
     result = evaluator.evaluate(conditions, context)
     assert result == True
     ```
   - **Czas**: 2.5h

3. **[ ] Action execution with retry**
   - **Metryka**: Reliable action execution, automatic retry on failure
   - **Walidacja**: 
     ```python
     from src.automation.actions import ActionExecutor
     
     executor = ActionExecutor()
     
     # Test retry logic
     action = {
         "type": "http_request",
         "url": "http://flaky-service:8080/trigger",
         "retry": {
             "attempts": 3,
             "delay": 1,
             "backoff": 2
         }
     }
     
     result = executor.execute(action)
     assert result.success == True
     assert result.attempts <= 3
     
     # Test action chaining
     actions = [
         {"type": "log", "message": "Starting sequence"},
         {"type": "delay", "seconds": 1},
         {"type": "mqtt_publish", "topic": "test/action", "payload": "done"}
     ]
     
     results = executor.execute_sequence(actions)
     assert all(r.success for r in results)
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Szybkie dopasowanie eventów (<0.1ms per event)
- Złożone warunki z pełną logiką boolowską
- Niezawodne wykonanie akcji z retry

### Blok 3: Monitoring and debugging

#### Zadania atomowe:
1. **[ ] Rule execution tracing**
   - **Metryka**: Pełny trace każdego wykonania reguły
   - **Walidacja**: 
     ```python
     # Enable tracing
     engine = RuleEngine(tracing=True)
     
     # Execute rule
     trace_id = engine.process_event(test_event)
     
     # Get execution trace
     trace = engine.get_trace(trace_id)
     assert trace.trigger_match_time < 0.001  # <1ms
     assert trace.condition_eval_time < 0.01   # <10ms
     assert trace.total_execution_time < 0.1   # <100ms
     assert len(trace.action_results) > 0
     ```
   - **Czas**: 2h

2. **[ ] Rule performance metrics**
   - **Metryka**: Prometheus metrics dla każdej reguły
   - **Walidacja**: 
     ```bash
     # Check Prometheus metrics
     curl http://localhost:8003/metrics | grep -E "automation_rule_"
     # Should show:
     # automation_rule_executions_total{rule="Motion Light Control"}
     # automation_rule_execution_duration_seconds{rule="..."}
     # automation_rule_failures_total{rule="..."}
     # automation_rule_condition_evaluations_total{rule="...",result="true"}
     ```
   - **Czas**: 1.5h

3. **[ ] Debug UI for rule testing**
   - **Metryka**: Web UI do testowania reguł bez skutków
   - **Walidacja**: 
     ```bash
     # Access debug UI
     curl http://localhost:8003/debug/rules
     
     # Test rule execution
     curl -X POST http://localhost:8003/debug/rules/test \
          -H "Content-Type: application/json" \
          -d '{
               "rule_id": "motion-light-control",
               "event": {"type": "motion_detected", "camera_id": "front_door"},
               "dry_run": true
              }'
     # Returns execution plan without running actions
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Pełna observability wykonania reguł
- Metryki wydajności dla każdej reguły
- Możliwość debugowania bez side effects

## Całościowe metryki sukcesu zadania

1. **Funkcjonalność**: Obsługa 100+ złożonych reguł automatyzacji
2. **Wydajność**: <1ms rule matching, <10ms condition evaluation
3. **Niezawodność**: 99.9% successful action execution (with retries)
4. **Skalowalność**: 10,000+ events/second processing

## Deliverables

1. `/src/contexts/automation/domain/rules/rule_schema.py` - Rule definition model
2. `/src/contexts/automation/infrastructure/rule_repository.py` - PostgreSQL storage
3. `/src/contexts/automation/domain/engine/rule_engine.py` - Execution engine
4. `/src/contexts/automation/domain/conditions/evaluator.py` - Condition evaluator
5. `/src/contexts/automation/domain/actions/executor.py` - Action executor
6. `/config/automation/default_rules.yaml` - Example rules
7. `/dashboards/automation-metrics.json` - Grafana dashboard
8. `/docs/automation/rule-syntax.md` - Rule documentation

## Narzędzia

- **Python 3.11+**: Core implementation
- **PostgreSQL**: Rule storage with JSONB
- **Redis**: Rule cache and state storage
- **Celery**: Async action execution
- **FastAPI**: REST API for rule management

## Zależności

- **Wymaga**: 
  - Event bus operational
  - PostgreSQL database
  - Redis cache
  - MQTT broker for actions
- **Blokuje**: 
  - Advanced automations
  - Scene management
  - Scheduled tasks

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Rule loops/cascades | Wysokie | Wysoki | Loop detection, execution limits | Spike in rule executions |
| Performance degradation | Średnie | Wysoki | Rule indexing, caching | Execution time >10ms |
| Action failures | Średnie | Średni | Retry logic, dead letter queue | Failed action metrics |
| Complex rule debugging | Wysokie | Średni | Comprehensive tracing, dry-run mode | User complaints |

## Rollback Plan

1. **Detekcja problemu**: 
   - Rule execution errors >1%
   - Performance degradation
   - Action failures cascade

2. **Kroki rollback**:
   - [ ] Disable rule engine: `docker exec detektor-automation touch /tmp/disable_rules`
   - [ ] Clear rule cache: `redis-cli FLUSHDB`
   - [ ] Restore previous rules: `psql -d detektor -f /backup/rules_backup.sql`
   - [ ] Restart with safe mode: `AUTOMATION_SAFE_MODE=true docker-compose up -d automation`

3. **Czas rollback**: <5 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-event-bus-kafka.md](./03-event-bus-kafka.md)