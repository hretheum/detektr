# Faza 4 / Zadanie 5: Testowanie scenariuszy z pełną widocznością

## Cel zadania

Utworzyć kompleksowy framework testowania scenariuszy end-to-end z automatyczną weryfikacją i pełną observability każdego testu.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja test fixtures**
   - **Metryka**: Test videos, HA mock ready
   - **Walidacja**:

     ```bash
     ls -la /test-fixtures/scenarios/
     # person_at_door.mp4, gesture_stop.mp4, pet_in_kitchen.mp4
     docker ps | grep ha-mock
     # Home Assistant mock running
     ```

   - **Czas**: 0.5h

2. **[ ] Scenario definitions ready**
   - **Metryka**: YAML scenarios defined
   - **Walidacja**:

     ```bash
     find /scenarios -name "*.yaml" | wc -l
     # >10 scenario files
     yamllint /scenarios/*.yaml
     # All valid YAML
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Test framework core

#### Zadania atomowe

1. **[ ] Scenario runner implementation**
   - **Metryka**: Execute scenarios from YAML
   - **Walidacja**:

     ```python
     runner = ScenarioRunner()
     result = runner.run("person_at_door.yaml")
     assert result.status == "passed"
     assert len(result.steps) > 0
     assert result.trace_id is not None
     ```

   - **Czas**: 2.5h

2. **[ ] Assertion framework**
   - **Metryka**: Verify expected outcomes
   - **Walidacja**:

     ```yaml
     # Scenario file
     assertions:
       - type: mqtt_message
         topic: "homeassistant/notification"
         timeout: 5s
       - type: ha_state
         entity: "light.entrance"
         state: "on"
     ```

   - **Czas**: 2h

3. **[ ] Test isolation mechanism**
   - **Metryka**: Each test runs clean
   - **Walidacja**:

     ```python
     # Run same test twice
     result1 = runner.run("test.yaml")
     result2 = runner.run("test.yaml")
     assert result1.initial_state == result2.initial_state
     assert no_side_effects_detected()
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Framework functional
- Tests repeatable
- Assertions comprehensive

### Blok 2: Scenario implementation

#### Zadania atomowe

1. **[ ] Core scenarios implementation**
   - **Metryka**: 10+ scenarios automated
   - **Walidacja**:

     ```bash
     python run_all_scenarios.py
     # Summary: 10/10 passed
     # Each scenario <30s execution
     ```

   - **Czas**: 3h

2. **[ ] Edge case scenarios**
   - **Metryka**: Handle failures, timeouts
   - **Walidacja**:

     ```python
     # Scenarios that should fail
     edge_cases = ["no_person_detected", "ha_timeout", "low_confidence"]
     for scenario in edge_cases:
         result = runner.run(f"{scenario}.yaml")
         assert result.handled_gracefully
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- All scenarios covered
- Edge cases handled
- Reliable execution

### Blok 3: Observability integration

#### Zadania atomowe

1. **[ ] Test execution dashboard**
   - **Metryka**: Real-time test progress
   - **Walidacja**:

     ```bash
     # During test run
     curl http://localhost:3000/api/dashboards/test-execution
     # Shows current scenario, step, status
     ```

   - **Czas**: 1.5h

2. **[ ] Test report generation**
   - **Metryka**: HTML reports with traces
   - **Walidacja**:

     ```bash
     python generate_test_report.py --run-id latest
     # Creates report.html with:
     # - Pass/fail summary
     # - Trace links
     # - Performance metrics
     ```

   - **Czas**: 1.5h

3. **[ ] CI/CD integration**
   - **Metryka**: Tests run on every commit
   - **Walidacja**:

     ```yaml
     # .github/workflows/scenarios.yml
     - name: Run E2E Scenarios
       run: python run_scenarios.py --ci
     - name: Upload results
       uses: actions/upload-artifact@v3
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Full visibility
- Automated reporting
- CI/CD ready

## Całościowe metryki sukcesu zadania

1. **Coverage**: All critical paths tested
2. **Reliability**: <1% flaky tests
3. **Speed**: Full suite <10 minutes

## Deliverables

1. `/tests/scenarios/` - Scenario definitions
2. `/tests/framework/` - Test framework code
3. `/reports/` - Test execution reports
4. `/dashboards/test-execution.json` - Test dashboard
5. `/.github/workflows/e2e-tests.yml` - CI configuration

## Narzędzia

- **pytest**: Test framework base
- **PyYAML**: Scenario definitions
- **Selenium**: UI testing if needed
- **Allure**: Test reporting

## Zależności

- **Wymaga**:
  - Full system deployed
  - Test fixtures prepared
- **Blokuje**: Production confidence

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Flaky tests | Wysokie | Średni | Retry logic, better assertions | >5% failure rate |
| Test duration | Średnie | Niski | Parallel execution, optimization | >15 min total |

## Rollback Plan

1. **Detekcja problemu**:
   - Tests blocking deployment
   - False positives >10%
   - Infrastructure issues

2. **Kroki rollback**:
   - [ ] Mark flaky tests as skip
   - [ ] Reduce test scope temporarily
   - [ ] Fix infrastructure issues
   - [ ] Re-enable incrementally

3. **Czas rollback**: <15 min

## Następne kroki

Po ukończeniu tej fazy, przejdź do:
→ [Faza 5 - Advanced AI](../faza-5-advanced-ai/01-gesture-detection.md)
