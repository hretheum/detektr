# Faza 1 / Zadanie 7: TDD setup i base service template

## Cel zadania
Konfiguracja kompletnego środowiska Test-Driven Development oraz implementacja szablonu bazowego serwisu z wbudowanym tracingiem, metrykami i testami jako wzorzec dla wszystkich przyszłych serwisów.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja Python testing tools**
   - **Metryka**: pytest, pytest-asyncio, pytest-cov zainstalowane
   - **Walidacja**: 
     ```bash
     pytest --version && \
     python -c "import pytest_asyncio, pytest_cov, pytest_mock"
     ```
   - **Czas**: 0.5h

2. **[ ] Weryfikacja CI pipeline działa**
   - **Metryka**: GitHub Actions wykonuje testy
   - **Walidacja**: 
     ```bash
     gh run list --limit 1 | grep -E "(completed|in_progress)"
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Testing framework setup

#### Zadania atomowe:
1. **[ ] Konfiguracja pytest z plugins**
   - **Metryka**: pytest.ini, conftest.py, coverage settings
   - **Walidacja**: 
     ```bash
     pytest --collect-only | grep "collected"
     # Should collect existing tests
     ```
   - **Czas**: 1h

2. **[ ] Test fixtures dla common components**
   - **Metryka**: Fixtures dla: database, telemetry, message queue
   - **Walidacja**: 
     ```python
     # W tests/conftest.py
     def test_fixtures_available(tracer, db_session, message_queue):
         assert tracer is not None
         assert db_session is not None
         assert message_queue is not None
     ```
   - **Czas**: 1.5h

3. **[ ] Test containers setup (testcontainers-python)**
   - **Metryka**: Automatic container lifecycle dla integration tests
   - **Walidacja**: 
     ```python
     # Integration test używa real PostgreSQL
     def test_with_real_db(postgres_container):
         assert postgres_container.get_connection_url().startswith("postgresql://")
     ```
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Tests run in <30s dla unit tests
- Integration tests z real dependencies
- Coverage report generowany automatycznie

### Blok 2: BaseService implementation

#### Zadania atomowe:
1. **[ ] Implementacja BaseService class**
   - **Metryka**: Base class z telemetry, health check, graceful shutdown
   - **Walidacja**: 
     ```python
     from src.shared.base_service import BaseService
     
     class TestService(BaseService):
         async def start(self): pass
         async def stop(self): pass
     
     service = TestService("test-svc")
     assert service.tracer is not None
     assert service.meter is not None
     ```
   - **Czas**: 2h

2. **[ ] Automatic health checks i readiness**
   - **Metryka**: /health i /ready endpoints w każdym serwisie
   - **Walidacja**: 
     ```bash
     # Start base service
     curl http://localhost:8000/health | jq '.status'
     # "healthy"
     curl http://localhost:8000/ready | jq '.ready'
     # true
     ```
   - **Czas**: 1h

3. **[ ] Graceful shutdown handling**
   - **Metryka**: SIGTERM properly stops service, drains requests
   - **Walidacja**: 
     ```python
     # Test graceful shutdown
     service.start()
     service.signal_handler(signal.SIGTERM, None)
     # Verify cleanup happened
     ```
   - **Czas**: 0.5h

#### Metryki sukcesu bloku:
- BaseService provides consistent interface
- Built-in observability from start
- Proper lifecycle management

### Blok 3: TDD example implementation

#### Zadania atomowe:
1. **[ ] Implement example FrameProcessor z TDD**
   - **Metryka**: 100% test coverage, tests written first
   - **Walidacja**: 
     ```bash
     # Coverage dla example service
     pytest tests/unit/test_frame_processor.py --cov=src.examples.frame_processor
     # Coverage: 100%
     ```
   - **Czas**: 2h

2. **[ ] Unit, integration i E2E tests przykłady**
   - **Metryka**: 3 levels of tests dla example service
   - **Walidacja**: 
     ```bash
     pytest tests/unit/test_frame_processor.py -v      # Fast, isolated
     pytest tests/integration/test_frame_pipeline.py -v # With dependencies
     pytest tests/e2e/test_frame_flow.py -v           # Full flow
     ```
   - **Czas**: 1.5h

3. **[ ] Performance tests z benchmarks**
   - **Metryka**: Baseline performance established
   - **Walidacja**: 
     ```bash
     pytest tests/performance/test_frame_processor_perf.py --benchmark-only
     # Shows operations/second, latency percentiles
     ```
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Clear TDD workflow demonstrated
- All test levels implemented
- Performance baselines set

### Blok 4: Testing best practices documentation

#### Zadania atomowe:
1. **[ ] TDD guide dla projektu**
   - **Metryka**: Step-by-step guide z przykładami
   - **Walidacja**: 
     ```bash
     # Markdown lint check
     markdownlint docs/testing/tdd-guide.md
     ```
   - **Czas**: 1h

2. **[ ] Test templates i snippets**
   - **Metryka**: VS Code snippets dla common test patterns
   - **Walidacja**: 
     ```bash
     # Snippets file exists
     ls -la .vscode/python.code-snippets | grep test
     ```
   - **Czas**: 0.5h

3. **[ ] CI integration z test reports**
   - **Metryka**: Test results visible w GitHub PR
   - **Walidacja**: 
     ```bash
     # Create test PR
     # Check for test summary comment
     ```
   - **Czas**: 0.5h

#### Metryki sukcesu bloku:
- Developers know how to write tests first
- Common patterns documented
- CI enforces test coverage

## Całościowe metryki sukcesu zadania

1. **Coverage**: Minimum 80% coverage enforced
2. **Speed**: Unit tests <30s, integration <2min
3. **Consistency**: All services use BaseService
4. **Documentation**: Clear TDD examples

## Deliverables

1. `/src/shared/base_service.py` - BaseService implementation
2. `/tests/conftest.py` - Common test fixtures
3. `/pytest.ini` - Test configuration
4. `/.coveragerc` - Coverage settings
5. `/src/examples/frame_processor/` - TDD example service
6. `/tests/unit|integration|e2e/` - Test examples
7. `/docs/testing/tdd-guide.md` - TDD documentation
8. `/.vscode/python.code-snippets` - Test snippets

## Narzędzia

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **pytest-benchmark**: Performance testing
- **testcontainers-python**: Integration test containers
- **pytest-mock**: Mocking support

## Zależności

- **Wymaga**: Frame tracking (zadanie 6), OpenTelemetry (zadanie 5)
- **Blokuje**: All future service implementations

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Slow test execution | Średnie | Średni | Parallel execution, test optimization | Tests >1min |
| Flaky integration tests | Wysokie | Średni | Retry logic, better isolation | Random failures |
| Low test coverage adoption | Średnie | Wysoki | Coverage gates w CI, education | Coverage dropping |

## Rollback Plan

1. **Detekcja problemu**: Tests blocking development, too slow
2. **Kroki rollback**:
   - [ ] Temporarily lower coverage requirements
   - [ ] Skip slow tests w CI (ale run nightly)
   - [ ] Focus on unit tests only
3. **Czas rollback**: <5 min (config change)

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [08-monitoring-dashboard.md](./08-monitoring-dashboard.md)