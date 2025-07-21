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

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/ha-bridge.md`

### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/ha-bridge.md#deploy](docs/deployment/services/ha-bridge.md#deploy)

2. **[ ] Konfiguracja HA API credentials**
   - **Metryka**: Secure HA token in SOPS
   - **Walidacja**: Bridge connects to HA instance
   - **Procedura**: [docs/deployment/services/ha-bridge.md#ha-configuration](docs/deployment/services/ha-bridge.md#ha-configuration)

3. **[ ] Action queue setup**
   - **Metryka**: Redis queue for HA actions
   - **Walidacja**: Actions queued and executed
   - **Procedura**: [docs/deployment/services/ha-bridge.md#action-queue](docs/deployment/services/ha-bridge.md#action-queue)

4. **[ ] Rate limiting configuration**
   - **Metryka**: Respect HA API limits
   - **Walidacja**: No 429 errors under load
   - **Procedura**: [docs/deployment/services/ha-bridge.md#rate-limiting](docs/deployment/services/ha-bridge.md#rate-limiting)

5. **[ ] Integration test with HA**
   - **Metryka**: End-to-end action execution
   - **Walidacja**: Test automation via bridge
   - **Procedura**: [docs/deployment/services/ha-bridge.md#integration-testing](docs/deployment/services/ha-bridge.md#integration-testing)

### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

### **📋 Walidacja sukcesu:**
```bash
# Sprawdź deployment:
curl http://nebula:8004/health

# Test HA connection:
curl http://nebula:8004/api/ha/status

# Execute test action:
curl -X POST http://nebula:8004/api/actions -d '{"service": "light.turn_on", "entity_id": "light.test"}'
```

### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/ha-bridge.md](docs/deployment/services/ha-bridge.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

### **🔍 Metryki sukcesu bloku:**
- ✅ HA Bridge service operational
- ✅ Secure API token management
- ✅ Action queue processing
- ✅ Rate limiting working
- ✅ Full tracing of all actions
- ✅ Zero-downtime deployment via CI/CD

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-dashboard-automation.md](./03-dashboard-automation.md)
