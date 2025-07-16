# Faza 4 / Zadanie 2: HA Bridge service z tracingiem akcji

## Cel zadania

Zbudować serwis integracyjny z Home Assistant API umożliwiający wykonywanie akcji z pełnym śledzeniem i obsługą błędów.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja HA API access**
   - **Metryka**: API token valid, endpoints accessible
   - **Walidacja**:

     ```bash
     curl -H "Authorization: Bearer $HA_TOKEN" \
       http://localhost:8123/api/states | jq length
     # Returns >0 entities
     ```

   - **Czas**: 0.5h

2. **[ ] Test HA service calls**
   - **Metryka**: Can control test entity
   - **Walidacja**:

     ```bash
     curl -X POST -H "Authorization: Bearer $HA_TOKEN" \
       http://localhost:8123/api/services/light/turn_on \
       -d '{"entity_id":"light.test"}'
     # Returns 200 OK
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: HA API client library

#### Zadania atomowe

1. **[ ] Async HA client z retry**
   - **Metryka**: Handles rate limits, retries failures
   - **Walidacja**:

     ```python
     client = HAClient(retry_policy=ExponentialBackoff())
     # Force 429 rate limit
     response = await client.call_service("light.turn_on", entity_id="test")
     assert response.success
     assert client.retry_count > 0
     ```

   - **Czas**: 2h

2. **[ ] Entity state cache**
   - **Metryka**: Cache hit rate >80%, fresh data
   - **Walidacja**:

     ```python
     # First call - cache miss
     state1 = await client.get_state("sensor.temperature")
     # Second call - cache hit
     state2 = await client.get_state("sensor.temperature")
     assert client.cache_hits == 1
     assert state1 == state2
     ```

   - **Czas**: 2h

3. **[ ] Service call validation**
   - **Metryka**: Validate params before sending
   - **Walidacja**:

     ```python
     # Invalid service call
     with pytest.raises(ValidationError):
         await client.call_service("invalid.service", bad_param=True)
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Robust HA communication
- Efficient with caching
- Fail-safe operations

### Blok 2: Action execution engine

#### Zadania atomowe

1. **[ ] Action queue processor**
   - **Metryka**: Sequential execution, priority support
   - **Walidacja**:

     ```python
     queue.add(TurnOnLight(priority=HIGH))
     queue.add(SendNotification(priority=LOW))
     executed = await queue.process_all()
     assert executed[0].action_type == "TurnOnLight"
     ```

   - **Czas**: 2h

2. **[ ] Conditional action logic**
   - **Metryka**: If-then-else, time conditions
   - **Walidacja**:

     ```python
     action = ConditionalAction(
         condition="sensor.motion == 'on'",
         then_action=TurnOnLight(),
         else_action=None
     )
     result = await executor.execute(action)
     assert result.executed == (motion_state == "on")
     ```

   - **Czas**: 2.5h

#### Metryki sukcesu bloku

- Complex automations supported
- Reliable execution
- Flexible conditions

### Blok 3: Observability

#### Zadania atomowe

1. **[ ] Action trace spans**
   - **Metryka**: Every action traced end-to-end
   - **Walidacja**:

     ```python
     with tracer.start_span("execute_automation"):
         result = await bridge.execute_action(action)

     # Check trace has all steps
     trace = get_latest_trace()
     assert "validate_action" in trace.span_names
     assert "call_ha_service" in trace.span_names
     assert "verify_result" in trace.span_names
     ```

   - **Czas**: 1.5h

2. **[ ] Action metrics dashboard**
   - **Metryka**: Success rate, latency, frequency
   - **Walidacja**:

     ```promql
     rate(ha_actions_total[5m])
     histogram_quantile(0.95, ha_action_duration_bucket)
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Full visibility
- Performance tracked
- Debugging enabled

## Całościowe metryki sukcesu zadania

1. **Reliability**: 99% action success rate
2. **Performance**: <500ms action execution
3. **Flexibility**: Support complex automations

## Deliverables

1. `/services/ha-bridge/` - HA bridge service
2. `/src/home_assistant/` - HA client library
3. `/config/automations/` - Automation definitions
4. `/dashboards/ha-actions.json` - Action metrics
5. `/docs/automation-dsl.md` - Automation language docs

## Narzędzia

- **aiohttp**: Async HTTP client
- **Home Assistant API**: REST API
- **PyYAML**: Automation definitions
- **Pydantic**: Validation

## Zależności

- **Wymaga**:
  - Home Assistant running
  - API token configured
- **Blokuje**: Automation execution

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| HA API changes | Niskie | Wysoki | Version detection, compatibility layer | API errors increase |
| Action loops | Średnie | Średni | Loop detection, rate limiting | Rapid repeated actions |

## Rollback Plan

1. **Detekcja problemu**:
   - Actions failing >10%
   - HA overloaded
   - Infinite loops detected

2. **Kroki rollback**:
   - [ ] Disable action processing
   - [ ] Clear action queue
   - [ ] Review failed actions
   - [ ] Re-enable with fixes

3. **Czas rollback**: <5 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-dashboard-automation.md](./03-dashboard-automation.md)
