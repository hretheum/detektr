# Faza 4 / Zadanie 5: End-to-end integration testing

## Cel zadania

Stworzyć kompleksowy framework testów E2E weryfikujący pełne flow integracji od detekcji przez event bus do automatyzacji w Home Assistant.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja całego stacku**
   - **Metryka**: Wszystkie komponenty działają i komunikują się
   - **Walidacja**:

     ```bash
     # Run system health check
     ./scripts/health-check-all.sh
     # All services: HEALTHY
     # Database connections: OK
     # Message queues: OPERATIONAL
     # API gateway: RESPONDING

     # Check integration points
     curl http://localhost:8000/api/v1/system/integration-status
     # All integrations: CONNECTED
     ```

   - **Czas**: 0.5h

2. **[ ] Test environment setup**
   - **Metryka**: Isolated test environment z test data
   - **Walidacja**:

     ```bash
     # Setup test environment
     docker-compose -f docker-compose.test.yml up -d

     # Load test fixtures
     ./scripts/load-test-data.sh
     # Loaded: cameras, rules, test videos

     # Verify isolation
     docker network ls | grep detektor-test
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: E2E test framework

#### Zadania atomowe

1. **[ ] Test orchestration framework**
   - **Metryka**: Framework do zarządzania kompleksowymi scenariuszami
   - **Walidacja**:

     ```python
     from tests.e2e.framework import E2ETestRunner

     runner = E2ETestRunner()

     # Define test scenario
     scenario = runner.create_scenario("person_detection_to_lights")
     scenario.given("camera", "front_door", state="active")
     scenario.given("automation_rule", "motion_lights", enabled=True)
     scenario.when("person_appears", camera="front_door")
     scenario.then("light", "entrance", state="on", within_seconds=5)

     # Run scenario
     result = runner.execute(scenario)
     assert result.passed
     assert result.execution_time < 5.0
     ```

   - **Czas**: 3h

2. **[ ] Video injection for testing**
   - **Metryka**: Ability to inject test videos into RTSP streams
   - **Walidacja**:

     ```python
     from tests.e2e.video import VideoInjector

     injector = VideoInjector()

     # Inject test video
     injector.inject_video(
         camera="front_door",
         video_file="tests/fixtures/person_walking.mp4",
         loop=True
     )

     # Verify detection triggered
     events = wait_for_events(
         event_type="PersonDetected",
         camera="front_door",
         timeout=10
     )
     assert len(events) > 0
     assert events[0].confidence > 0.8
     ```

   - **Czas**: 2.5h

3. **[ ] Event flow verification**
   - **Metryka**: Trace complete event flow through system
   - **Walidacja**:

     ```python
     from tests.e2e.tracing import FlowTracer

     tracer = FlowTracer()

     # Start tracing
     trace_id = tracer.start_trace("test_motion_flow")

     # Trigger event
     trigger_motion_event(camera="garage")

     # Get trace
     trace = tracer.get_trace(trace_id)

     # Verify flow
     assert trace.span_count >= 5
     assert "rtsp_capture" in trace.spans
     assert "object_detection" in trace.spans
     assert "event_published" in trace.spans
     assert "rule_evaluated" in trace.spans
     assert "action_executed" in trace.spans

     # Check timing
     assert trace.total_duration < 1000  # <1s
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Flexible test scenario framework
- Realistic test data injection
- Complete flow visibility

### Blok 2: Integration test scenarios

#### Zadania atomowe

1. **[ ] Detection to automation tests**
   - **Metryka**: Test każdego typu detekcji triggering automation
   - **Walidacja**:

     ```python
     @pytest.mark.e2e
     class TestDetectionAutomation:

         def test_person_detection_triggers_notification(self):
             # Setup
             create_rule("notify_on_person",
                        trigger="PersonDetected",
                        action="send_notification")

             # Act
             inject_person_video("front_door")

             # Assert
             notification = wait_for_notification(timeout=10)
             assert notification.title == "Person Detected"
             assert "front_door" in notification.body

         def test_multiple_detections_deduplication(self):
             # Send multiple identical detections
             for _ in range(5):
                 trigger_detection("motion", "backyard")

             # Should only trigger one action
             actions = get_executed_actions(last_seconds=10)
             assert len(actions) == 1

         def test_zone_based_automation(self):
             # Define zone
             create_zone("restricted", coordinates=[(0,0), (100,100)])

             # Trigger in zone
             trigger_detection("person", "camera1", position=(50,50))

             # Verify zone-specific action
             assert wait_for_action("alert_security", timeout=5)
     ```

   - **Czas**: 2.5h

2. **[ ] Home Assistant integration tests**
   - **Metryka**: Complete HA integration scenarios
   - **Walidacja**:

     ```python
     @pytest.mark.e2e_ha
     class TestHomeAssistantIntegration:

         def test_device_discovery(self):
             # Restart HA
             restart_home_assistant()

             # Wait for discovery
             wait_for_ha_startup()

             # Check devices
             devices = get_ha_devices()
             detektor_devices = [d for d in devices
                               if d.manufacturer == "Detektor"]
             assert len(detektor_devices) >= 5

         def test_state_synchronization(self):
             # Change detection state
             set_camera_detection("front", enabled=False)

             # Verify in HA
             ha_state = get_ha_entity_state(
                 "binary_sensor.detektor_front_detection"
             )
             assert ha_state == "off"

         def test_ha_automation_trigger(self):
             # Create HA automation
             create_ha_automation(
                 trigger="state.sensor.detektor_motion",
                 condition="state.sun = below_horizon",
                 action="light.turn_on"
             )

             # Trigger at night
             set_ha_time("22:00")
             trigger_motion("entrance")

             # Verify
             assert get_ha_entity_state("light.entrance") == "on"
     ```

   - **Czas**: 2h

3. **[ ] Performance and stress tests**
   - **Metryka**: System behavior under load
   - **Walidacja**:

     ```python
     @pytest.mark.stress
     class TestSystemStress:

         def test_concurrent_detections(self):
             # Simulate 10 cameras with activity
             results = []

             async def camera_activity(camera_id):
                 for _ in range(100):
                     await trigger_detection_async(
                         "motion", f"camera_{camera_id}"
                     )
                     await asyncio.sleep(0.1)

             # Run concurrently
             tasks = [camera_activity(i) for i in range(10)]
             await asyncio.gather(*tasks)

             # Verify no message loss
             total_triggered = 1000
             total_processed = get_processed_events_count()
             assert total_processed >= total_triggered * 0.99

         def test_cascade_prevention(self):
             # Create potential loop
             create_rule("rule1",
                        trigger="event.A",
                        action="publish.event.B")
             create_rule("rule2",
                        trigger="event.B",
                        action="publish.event.A")

             # Trigger cascade
             publish_event("event.A")

             # Wait and verify loop prevention
             time.sleep(5)
             events = get_events_last_seconds(5)
             assert len(events) < 10  # Loop prevented
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Comprehensive scenario coverage
- HA integration verified
- System limits understood

### Blok 3: Continuous integration setup

#### Zadania atomowe

1. **[ ] CI/CD pipeline for E2E tests**
   - **Metryka**: Automated E2E tests on every commit
   - **Walidacja**:

     ```yaml
     # .github/workflows/e2e-tests.yml
     name: E2E Integration Tests

     on:
       push:
         branches: [main, develop]
       pull_request:

     jobs:
       e2e-tests:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v3

           - name: Start test environment
             run: |
               docker-compose -f docker-compose.test.yml up -d
               ./scripts/wait-for-healthy.sh

           - name: Run E2E tests
             run: |
               pytest tests/e2e/ -v --tb=short \
                      --junit-xml=test-results/e2e.xml

           - name: Upload test results
             uses: actions/upload-artifact@v3
             with:
               name: e2e-test-results
               path: test-results/
     ```

   - **Czas**: 2h

2. **[ ] Test report generation**
   - **Metryka**: Detailed reports with traces and screenshots
   - **Walidacja**:

     ```python
     # Test with reporting
     @pytest.mark.e2e
     def test_with_report(e2e_reporter):
         with e2e_reporter.scenario("person_detection"):
             # Capture initial state
             e2e_reporter.capture_state("initial")

             # Perform test
             inject_person("front_door")

             # Capture traces
             trace = get_current_trace()
             e2e_reporter.attach_trace(trace)

             # Verify and capture
             result = wait_for_automation("lights_on")
             e2e_reporter.capture_state("final")

             assert result.success

     # Check generated report
     # report.html includes:
     # - Test execution timeline
     # - System state snapshots
     # - Distributed traces
     # - Performance metrics
     ```

   - **Czas**: 1.5h

3. **[ ] Monitoring test environment**
   - **Metryka**: Grafana dashboard for E2E test metrics
   - **Walidacja**:

     ```bash
     # Import E2E dashboard
     curl -X POST http://localhost:3000/api/dashboards/import \
          -H "Content-Type: application/json" \
          -d @dashboards/e2e-test-metrics.json

     # Run tests and check dashboard
     pytest tests/e2e/ --metrics-export

     # Dashboard shows:
     # - Test execution times
     # - Success/failure rates
     # - System performance during tests
     # - Resource utilization
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Automated E2E testing in CI
- Comprehensive test reporting
- Test environment monitoring

## Całościowe metryki sukcesu zadania

1. **Coverage**: 95%+ integration points tested
2. **Reliability**: E2E tests success rate >98%
3. **Performance**: Full E2E suite runs <15 minutes
4. **Traceability**: Every test failure traceable to root cause

## Deliverables

1. `/tests/e2e/framework/` - E2E test framework
2. `/tests/e2e/scenarios/` - Test scenarios
3. `/tests/e2e/fixtures/` - Test videos and data
4. `/.github/workflows/e2e-tests.yml` - CI pipeline
5. `/dashboards/e2e-test-metrics.json` - Test monitoring
6. `/docs/testing/e2e-guide.md` - E2E testing guide
7. `/scripts/e2e-test-runner.sh` - Local test runner

## Narzędzia

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **testcontainers**: Container management
- **OpenTelemetry**: Distributed tracing
- **Allure**: Test reporting
- **Locust**: Load testing

## Zależności

- **Wymaga**:
  - Complete system deployed
  - Test environment infrastructure
  - All integrations working
- **Blokuje**:
  - Production deployment
  - Performance optimization
  - Advanced features

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Flaky tests | Wysokie | Średni | Retry logic, stabilization waits | Intermittent failures |
| Test environment drift | Średnie | Wysoki | Infrastructure as code, regular sync | Test failures in CI |
| Long test execution | Wysokie | Średni | Parallel execution, test selection | Suite >30 min |
| Resource exhaustion | Średnie | Średni | Resource limits, cleanup | OOM errors |

## Rollback Plan

1. **Detekcja problemu**:
   - Test suite failures >10%
   - CI pipeline blocked
   - Environment corruption

2. **Kroki rollback**:
   - [ ] Skip failing tests: `pytest -m "not flaky"`
   - [ ] Reset test environment: `docker-compose -f docker-compose.test.yml down -v`
   - [ ] Clear test data: `./scripts/reset-test-data.sh`
   - [ ] Use previous test suite: `git checkout HEAD~1 -- tests/e2e/`
   - [ ] Run smoke tests only: `pytest -m smoke`

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ Faza 5: [Advanced AI - Gesture Detection](../faza-5-advanced-ai/01-gesture-detection.md)
