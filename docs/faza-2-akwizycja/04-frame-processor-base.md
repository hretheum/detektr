# Faza 2 / Zadanie 4: Frame Processor Base Service

## Cel zadania

Stworzyć bazowy serwis przetwarzania klatek jako template dla wszystkich serwisów AI, z wbudowanym tracingiem, metrykami i obsługą błędów.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites

#### Zadania atomowe

1. **[ ] Design pattern dla processor pipeline**
   - **Metryka**: Extensible architecture design
   - **Walidacja**: Architecture review checklist
   - **Czas**: 2h

2. **[ ] Analiza common requirements dla AI services**
   - **Metryka**: Lista shared functionality
   - **Walidacja**: Requirements coverage matrix
   - **Czas**: 1h

### Blok 1: Base processor abstraction

#### Zadania atomowe

1. **[ ] TDD: Abstract base processor class**
   - **Metryka**: 100% coverage base functionality
   - **Walidacja**: `pytest tests/test_base_processor.py`
   - **Czas**: 3h

2. **[ ] Implementacja processing pipeline**
   - **Metryka**: Pre/process/post hooks
   - **Walidacja**: Pipeline execution test
   - **Czas**: 3h

3. **[ ] Error handling i retry logic**
   - **Metryka**: Graceful degradation
   - **Walidacja**: Fault injection testing
   - **Czas**: 2h

### Blok 2: Observability integration

#### Zadania atomowe

1. **[ ] Automatic OpenTelemetry tracing**
   - **Metryka**: Every method traced
   - **Walidacja**: Jaeger shows full traces
   - **Czas**: 2h

2. **[ ] Prometheus metrics decorators**
   - **Metryka**: Auto-metrics dla latency, errors
   - **Walidacja**: Metrics endpoint test
   - **Czas**: 2h

3. **[ ] Structured logging z context**
   - **Metryka**: Correlation IDs preserved
   - **Walidacja**: Log aggregation test
   - **Czas**: 1h

### Blok 3: Frame lifecycle management

#### Zadania atomowe

1. **[ ] Frame state machine**
   - **Metryka**: State transitions tracked
   - **Walidacja**: State diagram validation
   - **Czas**: 2h

2. **[ ] Resource management (GPU/CPU)**
   - **Metryka**: No resource leaks
   - **Walidacja**: Memory profiler clean
   - **Czas**: 3h

3. **[ ] Batch processing support**
   - **Metryka**: Batch size optimization
   - **Walidacja**: Throughput test
   - **Czas**: 2h

### Blok 4: Testing framework

#### Zadania atomowe

1. **[ ] Test fixtures dla frame processing**
   - **Metryka**: Reusable test data
   - **Walidacja**:
     ```bash
     pytest tests/fixtures/test_frame_fixtures.py -v
     # All fixture tests pass
     ```
   - **Quality Gate**: Fixtures cover all edge cases
   - **Guardrails**: Test data versioned
   - **Czas**: 2h

2. **[ ] Performance benchmark suite**
   - **Metryka**: Automated benchmarks
   - **Walidacja**:
     ```bash
     pytest tests/benchmarks/ --benchmark-only
     # Baseline metrics established
     ```
   - **Quality Gate**: CI reports regression >10%
   - **Guardrails**: Benchmark data stored
   - **Czas**: 2h

3. **[ ] Example processor implementation**
   - **Metryka**: Working example with all features
   - **Walidacja**:
     ```bash
     cd examples/sample-processor
     python -m sample_processor.main
     # Processes test frames successfully
     ```
   - **Quality Gate**: Example uses all base features
   - **Guardrails**: Well documented
   - **Czas**: 2h

### Blok 5: CI/CD Pipeline i Package Distribution

#### Zadania atomowe

1. **[ ] Python package structure**
   - **Metryka**: Installable base-processor package
   - **Walidacja**:
     ```bash
     cd services/shared/base-processor
     python -m build
     pip install dist/base_processor-*.whl
     python -c "from base_processor import BaseProcessor"
     ```
   - **Quality Gate**: Package imports cleanly
   - **Guardrails**: Dependencies pinned
   - **Czas**: 1.5h

2. **[ ] GitHub Actions dla shared libraries**
   - **Metryka**: Auto-publish to package registry
   - **Walidacja**:
     ```bash
     cat .github/workflows/base-processor-publish.yml
     git tag v1.0.0 && git push --tags
     # Package published to GitHub Packages
     ```
   - **Quality Gate**: Tests pass before publish
   - **Guardrails**: Semantic versioning
   - **Czas**: 1.5h

3. **[ ] Dockerfile template dla processors**
   - **Metryka**: Reusable Dockerfile for AI services
   - **Walidacja**:
     ```dockerfile
     # Dockerfile.processor template includes:
     FROM python:3.11-slim
     # Base processor pre-installed
     RUN pip install base-processor==1.0.0
     ```
   - **Quality Gate**: Template builds <2min
   - **Guardrails**: Security scanning enabled
   - **Czas**: 1h

### Blok 6: DEPLOYMENT NA NEBULA I WALIDACJA ⚠️

#### Zadania atomowe

1. **[ ] Deploy example processor na Nebuli**
   - **Metryka**: Example processor running
   - **Walidacja NA SERWERZE**:
     ```bash
     # Deploy example
     ssh nebula "cd /opt/detektor && docker-compose -f docker-compose.yml -f docker-compose.example.yml up -d example-processor"

     # Check health
     curl -s http://nebula:8099/health | jq .
     # {"status": "healthy", "processor": "example"}
     ```
   - **Quality Gate**: Service healthy
   - **Guardrails**: Resource limits set
   - **Czas**: 1h

2. **[ ] Trace validation na produkcji**
   - **Metryka**: Complete traces visible
   - **Walidacja NA SERWERZE**:
     ```bash
     # Generate test load
     ssh nebula "docker exec example-processor python -m base_processor.generate_load --duration 60"

     # Check traces
     curl -s "http://nebula:16686/api/traces?service=example-processor" | jq '.[0].spans | length'
     # Multiple spans per trace
     ```
   - **Quality Gate**: All methods traced
   - **Guardrails**: <1% trace drops
   - **Czas**: 1h

3. **[ ] Metrics validation**
   - **Metryka**: All base metrics exported
   - **Walidacja NA SERWERZE**:
     ```bash
     # Check metrics
     curl -s http://nebula:8099/metrics | grep -E "processor_frames_processed|processor_errors_total|processor_processing_time"
     # All base metrics present

     # Verify in Prometheus
     curl -s "http://nebula:9090/api/v1/query?query=processor_frames_processed_total" | jq .data.result
     ```
   - **Quality Gate**: Metrics updating
   - **Guardrails**: No metric gaps
   - **Czas**: 1h

4. **[ ] Performance baseline na Nebuli**
   - **Metryka**: Processing overhead measured
   - **Walidacja NA SERWERZE**:
     ```bash
     # Run benchmark
     ssh nebula "docker exec example-processor python -m base_processor.benchmark --frames 10000"
     # Overhead: <1ms per frame
     # Throughput: >1000 fps
     ```
   - **Quality Gate**: Meets performance targets
   - **Guardrails**: No memory leaks
   - **Czas**: 2h

## Całościowe metryki sukcesu zadania

1. **Reusability**: 90% code reuse in AI services
2. **Observability**: 100% operations traced
3. **Performance**: <1ms overhead per frame
4. **Reliability**: Automatic error recovery

## Deliverables

1. `src/shared/processing/` - Base processor framework
2. `src/shared/observability/` - Tracing/metrics helpers
3. `tests/fixtures/frames/` - Test frame data
4. `docs/processor-development.md` - Developer guide
5. `examples/sample-processor/` - Reference implementation

## Narzędzia

- **Python ABC**: Abstract base classes
- **OpenTelemetry**: Distributed tracing
- **prometheus-client**: Metrics
- **structlog**: Structured logging
- **pytest-benchmark**: Performance testing

## CI/CD i Deployment Guidelines

### Package Registry Structure
```
GitHub Packages:
├── base-processor v1.0.0     # Core framework
├── base-processor v1.1.0     # With batch support
└── processor-utils v1.0.0    # Helper utilities

Docker Registry (ghcr.io):
├── example-processor:latest  # Reference implementation
└── processor-template:latest # Base image for new processors
```

### Development Workflow
1. **Extend BaseProcessor**:
   ```python
   from base_processor import BaseProcessor

   class MyProcessor(BaseProcessor):
       async def process_frame(self, frame):
           # Your AI logic here
           pass
   ```

2. **Use provided Dockerfile template**:
   ```dockerfile
   FROM ghcr.io/hretheum/bezrobocie-detektor/processor-template:latest
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   ```

3. **Automatic observability**:
   - Tracing: Inherited from base class
   - Metrics: Auto-exported via decorators
   - Logging: Structured with correlation IDs

### Deployment Checklist
- [ ] Processor extends BaseProcessor
- [ ] Unit tests >80% coverage
- [ ] Integration tests with base fixtures
- [ ] Dockerfile uses template
- [ ] Health endpoint implemented
- [ ] Metrics endpoint at /metrics
- [ ] Resource limits defined
- [ ] Benchmark results documented

### Monitoring Endpoints
- Health: `http://nebula:80XX/health`
- Metrics: `http://nebula:80XX/metrics`
- Ready: `http://nebula:80XX/ready`

### Key Metrics Provided
```promql
# Processing performance
processor_frames_processed_total
processor_processing_time_seconds
processor_errors_total{error_type="..."}

# Resource usage
processor_memory_usage_bytes
processor_active_frames

# Queue metrics
processor_queue_size
processor_queue_lag_seconds
```

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-health-checks.md](./05-health-checks.md)
