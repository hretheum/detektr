# Test-Driven Development Guide

## Overview

This guide outlines the TDD practices for the Detektor project. We follow a strict test-first approach to ensure high quality, maintainable code.

## TDD Workflow

### 1. Red Phase - Write a Failing Test

```python
# test_new_feature.py
def test_frame_validator_rejects_invalid_frame():
    """Test that validator rejects frames with invalid data."""
    validator = FrameValidator()
    invalid_frame = Frame(camera_id="", timestamp=None)

    with pytest.raises(ValidationError):
        validator.validate(invalid_frame)
```

### 2. Green Phase - Make the Test Pass

```python
# frame_validator.py
class FrameValidator:
    def validate(self, frame: Frame) -> None:
        if not frame.camera_id:
            raise ValidationError("Camera ID is required")
        if not frame.timestamp:
            raise ValidationError("Timestamp is required")
```

### 3. Refactor Phase - Improve the Code

```python
# frame_validator.py (refactored)
class FrameValidator:
    """Validates frame data before processing."""

    REQUIRED_FIELDS = ['camera_id', 'timestamp']

    def validate(self, frame: Frame) -> None:
        """Validate frame has all required fields.

        Args:
            frame: Frame to validate

        Raises:
            ValidationError: If frame is invalid
        """
        for field in self.REQUIRED_FIELDS:
            if not getattr(frame, field, None):
                raise ValidationError(f"{field} is required")
```

## Test Organization

### Directory Structure

```
tests/
├── unit/                 # Fast, isolated tests
│   ├── test_domain/     # Domain logic tests
│   ├── test_services/   # Service tests with mocks
│   └── test_utils/      # Utility function tests
├── integration/         # Tests with real dependencies
│   ├── test_database/   # Database integration
│   ├── test_messaging/  # Message queue tests
│   └── test_api/        # API endpoint tests
├── e2e/                 # End-to-end scenarios
│   └── test_flows/      # Complete user flows
├── performance/         # Performance benchmarks
│   └── test_benchmarks/ # Load and stress tests
└── fixtures/            # Test data and helpers
```

### Test Naming Conventions

```python
# Pattern: test_<what>_<condition>_<expected_result>

def test_process_frame_with_valid_data_returns_success():
    pass

def test_process_frame_with_invalid_camera_raises_error():
    pass

def test_process_frame_when_detector_fails_returns_partial_result():
    pass
```

## Writing Effective Tests

### 1. Arrange-Act-Assert Pattern

```python
@pytest.mark.unit
async def test_frame_processor_handles_detection_error():
    # Arrange
    processor = FrameProcessor()
    frame = create_test_frame()
    processor.detector = Mock(side_effect=DetectionError("GPU OOM"))

    # Act
    result = await processor.process(frame)

    # Assert
    assert result.success is False
    assert "GPU OOM" in result.error_message
    assert processor.metrics.error_count == 1
```

### 2. Use Descriptive Test Names

```python
# ❌ Bad
def test_process():
    pass

def test_error():
    pass

# ✅ Good
def test_process_frame_increments_success_counter():
    pass

def test_process_frame_logs_error_on_detection_failure():
    pass
```

### 3. One Assertion Per Test (When Possible)

```python
# ❌ Bad - Multiple unrelated assertions
def test_frame_processing():
    result = processor.process(frame)
    assert result.success is True
    assert len(result.detections) > 0
    assert processor.metrics.processed == 1
    assert frame.state == "completed"

# ✅ Good - Focused tests
def test_successful_processing_returns_success_result():
    result = processor.process(frame)
    assert result.success is True

def test_processing_updates_frame_state():
    processor.process(frame)
    assert frame.state == "completed"

def test_processing_increments_metrics():
    processor.process(frame)
    assert processor.metrics.processed == 1
```

## Test Levels

### Unit Tests

**Purpose**: Test individual components in isolation

**Characteristics**:
- Fast (<100ms per test)
- No external dependencies
- Use mocks/stubs for collaborators
- Run on every commit

**Example**:
```python
@pytest.mark.unit
class TestFrameValidator:
    def test_validate_missing_camera_id_raises_error(self):
        frame = Frame(camera_id="", timestamp=datetime.now())
        validator = FrameValidator()

        with pytest.raises(ValidationError, match="camera_id"):
            validator.validate(frame)
```

### Integration Tests

**Purpose**: Test component interactions with real dependencies

**Characteristics**:
- Slower (100ms-2s per test)
- Use test containers for databases, queues
- Test repository implementations
- Run on pull requests

**Example**:
```python
@pytest.mark.integration
class TestFrameRepository:
    @pytest.mark.asyncio
    async def test_save_and_retrieve_frame(self, db_session):
        # Uses real database
        repo = FrameRepository(db_session)
        frame = create_test_frame()

        await repo.save(frame)
        retrieved = await repo.get_by_id(frame.id)

        assert retrieved.id == frame.id
        assert retrieved.camera_id == frame.camera_id
```

### E2E Tests

**Purpose**: Test complete user scenarios

**Characteristics**:
- Slowest (>2s per test)
- Test through public APIs
- Use docker-compose for full stack
- Run before deployment

**Example**:
```python
@pytest.mark.e2e
class TestFrameProcessingFlow:
    def test_submit_frame_via_api_updates_dashboard(self, services):
        # Submit frame
        response = requests.post(
            f"{API_URL}/frames",
            json={"camera_id": "cam01", "image": base64_image}
        )
        assert response.status_code == 202

        # Wait for processing
        frame_id = response.json()["frame_id"]
        wait_for_processing(frame_id)

        # Verify in dashboard
        metrics = requests.get(f"{DASHBOARD_URL}/api/frames/{frame_id}")
        assert metrics.json()["status"] == "completed"
```

## Mocking Strategies

### 1. Mock External Services

```python
@pytest.fixture
def mock_detection_service():
    """Mock external detection API."""
    with patch('src.services.detection_api') as mock:
        mock.detect.return_value = {
            "faces": [{"confidence": 0.95}],
            "objects": [{"class": "person", "confidence": 0.89}]
        }
        yield mock
```

### 2. Use Factories for Test Data

```python
# tests/factories.py
class FrameFactory:
    @staticmethod
    def create_frame(**kwargs):
        defaults = {
            "camera_id": "test_cam_01",
            "timestamp": datetime.now(),
            "image_data": b"fake_image_data"
        }
        defaults.update(kwargs)
        return Frame(**defaults)

# Usage
def test_process_night_vision_frame():
    frame = FrameFactory.create_frame(
        camera_id="night_cam",
        metadata={"mode": "night_vision"}
    )
```

### 3. Async Testing

```python
@pytest.mark.asyncio
async def test_concurrent_frame_processing():
    processor = FrameProcessor()
    frames = [FrameFactory.create_frame() for _ in range(10)]

    # Process concurrently
    results = await asyncio.gather(
        *[processor.process(f) for f in frames]
    )

    assert all(r.success for r in results)
```

## Testing Best Practices

### 1. Test Behavior, Not Implementation

```python
# ❌ Bad - Testing implementation details
def test_processor_calls_detector_detect_method():
    processor.detector.detect = Mock()
    processor.process(frame)
    processor.detector.detect.assert_called_once()

# ✅ Good - Testing behavior
def test_processor_returns_detection_results():
    processor.process(frame)
    assert len(result.detections) > 0
```

### 2. Use Proper Test Isolation

```python
@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset global metrics before each test."""
    yield
    MetricsRegistry.clear()

@pytest.fixture
def isolated_processor():
    """Create processor with isolated dependencies."""
    return FrameProcessor(
        detector=Mock(),
        repository=Mock(),
        metrics=Mock()
    )
```

### 3. Test Edge Cases

```python
class TestFrameProcessorEdgeCases:
    def test_process_empty_image_data(self):
        frame = Frame(camera_id="cam1", image_data=b"")
        # Should handle gracefully

    def test_process_corrupted_image_data(self):
        frame = Frame(camera_id="cam1", image_data=b"corrupted")
        # Should not crash

    def test_process_extremely_large_image(self):
        frame = Frame(camera_id="cam1", image_data=b"x" * 100_000_000)
        # Should handle or reject appropriately
```

## Performance Testing

### 1. Benchmark Critical Paths

```python
@pytest.mark.benchmark
def test_frame_processing_performance(benchmark):
    processor = FrameProcessor()
    frame = create_test_frame()

    result = benchmark(processor.process, frame)

    assert result.success
    assert benchmark.stats['mean'] < 0.1  # Less than 100ms average
```

### 2. Load Testing

```python
@pytest.mark.slow
async def test_sustained_load():
    processor = FrameProcessor()

    async def process_continuously():
        for _ in range(1000):
            frame = create_test_frame()
            await processor.process(frame)

    # Should complete without memory leaks or crashes
    await asyncio.wait_for(process_continuously(), timeout=60)
```

## Continuous Integration

### Running Tests Locally

```bash
# Run all tests
pytest

# Run only unit tests (fast)
pytest tests/unit -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_frame_processor.py

# Run tests matching pattern
pytest -k "test_process"

# Run benchmarks
pytest --benchmark-only

# Run tests in parallel
pytest -n auto
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: unit-tests
        name: Unit Tests
        entry: pytest tests/unit -v
        language: system
        pass_filenames: false
        always_run: true
```

### CI Pipeline Integration

```yaml
# .github/workflows/test.yml
test:
  runs-on: ubuntu-latest
  steps:
    - name: Run Unit Tests
      run: pytest tests/unit --cov=src --cov-report=xml

    - name: Run Integration Tests
      run: |
        docker-compose -f docker-compose.test.yml up -d
        pytest tests/integration -v

    - name: Upload Coverage
      uses: codecov/codecov-action@v3
```

## Common Patterns

### 1. Testing Async Services

```python
@pytest.fixture
async def service():
    service = MyAsyncService()
    await service.start()
    yield service
    await service.stop()

@pytest.mark.asyncio
async def test_async_operation(service):
    result = await service.do_something()
    assert result.success
```

### 2. Testing Error Scenarios

```python
@pytest.mark.parametrize("error,expected_message", [
    (ConnectionError("Network down"), "Connection failed"),
    (TimeoutError("Request timeout"), "Operation timed out"),
    (ValueError("Invalid input"), "Validation error"),
])
def test_error_handling(error, expected_message):
    processor = FrameProcessor()
    processor.detector = Mock(side_effect=error)

    result = processor.process(frame)

    assert not result.success
    assert expected_message in result.error
```

### 3. Testing State Machines

```python
class TestFrameStateMachine:
    def test_valid_state_transitions(self):
        frame = Frame()

        # Valid transition path
        assert frame.transition_to("processing")
        assert frame.state == "processing"
        assert frame.transition_to("completed")
        assert frame.state == "completed"

    def test_invalid_state_transition_rejected(self):
        frame = Frame()
        frame.state = "completed"

        # Cannot go back to processing from completed
        assert not frame.transition_to("processing")
        assert frame.state == "completed"
```

## Debugging Failed Tests

### 1. Use pytest's debugging features

```bash
# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l

# Increase verbosity
pytest -vv

# Show print statements
pytest -s
```

### 2. Add diagnostic output

```python
def test_complex_operation():
    result = complex_operation()

    # Add context on failure
    assert result.success, f"Operation failed: {result.error}, state: {result.state}"
```

### 3. Use pytest markers for test organization

```python
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.requires_gpu
def test_gpu_processing():
    pass

# Run only fast tests
pytest -m "not slow"

# Run only GPU tests
pytest -m requires_gpu
```

## Summary

1. **Always write tests first** - Let tests drive your design
2. **Keep tests simple and focused** - One concept per test
3. **Use appropriate test levels** - Unit for logic, integration for boundaries
4. **Mock external dependencies** - Keep tests fast and reliable
5. **Test edge cases** - Don't just test the happy path
6. **Maintain test quality** - Refactor tests like production code
7. **Run tests frequently** - Catch issues early
