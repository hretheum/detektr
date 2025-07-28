# Frame Buffer Implementation Plan - TDD Approach

## Overview

This document provides a detailed implementation plan for the frame-buffer redesign, following Test-Driven Development (TDD) methodology. Each task is atomic (0.5-2h), with clear success metrics, validation methods, and quality gates.

## Block 0: Prerequisites & Setup

### Zadania atomowe

1. **[ ] Przygotowanie środowiska testowego**
   - **Metryka**: Pełne środowisko testowe z Redis Streams i mocked processors
   - **TDD Test Cases**:
     ```python
     # tests/test_environment.py
     async def test_redis_streams_available():
         """Verify Redis Streams functionality."""
         redis = await aioredis.create_redis_pool('redis://localhost')

         # Test stream creation
         stream_id = await redis.xadd('test:stream', {'data': 'test'})
         assert stream_id is not None

         # Test consumer group
         await redis.xgroup_create('test:stream', 'test-group', '0')
         messages = await redis.xreadgroup('test-group', 'consumer-1', {'test:stream': '>'})
         assert len(messages) > 0

     async def test_trace_context_propagation():
         """Verify OpenTelemetry context propagation."""
         tracer = trace.get_tracer(__name__)
         with tracer.start_as_current_span("test") as span:
             assert span.get_span_context().trace_id != 0
     ```
   - **Validation Code**:
     ```bash
     # Run test suite
     pytest tests/test_environment.py -v
     # All tests should pass

     # Verify Redis Streams
     docker exec redis redis-cli XINFO STREAM test:stream
     ```
   - **Quality Gate**: 100% test pass, Redis Streams functional
   - **Czas**: 1h

2. **[ ] Utworzenie struktury projektu dla nowego frame-buffer**
   - **Metryka**: Nowa struktura katalogów z separation of concerns
   - **TDD Test**:
     ```python
     # tests/test_project_structure.py
     def test_project_structure():
         """Verify new project structure exists."""
         required_dirs = [
             'services/frame-buffer-v2/src/orchestrator',
             'services/frame-buffer-v2/src/processors',
             'services/frame-buffer-v2/src/backpressure',
             'services/frame-buffer-v2/src/health',
             'services/frame-buffer-v2/tests'
         ]
         for dir_path in required_dirs:
             assert Path(dir_path).exists(), f"Missing: {dir_path}"
     ```
   - **Structure**:
     ```
     services/frame-buffer-v2/
     ├── src/
     │   ├── orchestrator/
     │   │   ├── __init__.py
     │   │   ├── distributor.py
     │   │   └── router.py
     │   ├── processors/
     │   │   ├── __init__.py
     │   │   ├── registry.py
     │   │   └── client.py
     │   ├── backpressure/
     │   │   ├── __init__.py
     │   │   └── controller.py
     │   └── health/
     │       ├── __init__.py
     │       └── monitor.py
     ├── tests/
     └── Dockerfile
     ```
   - **Quality Gate**: All directories created, imports working
   - **Czas**: 0.5h

3. **[ ] Konfiguracja CI/CD pipeline dla TDD**
   - **Metryka**: Automated test execution on every commit
   - **TDD Test**:
     ```yaml
     # .github/workflows/frame-buffer-v2-tests.yml
     name: Frame Buffer V2 Tests
     on: [push, pull_request]
     jobs:
       test:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v3
           - name: Run tests
             run: |
               cd services/frame-buffer-v2
               docker-compose -f docker-compose.test.yml up --abort-on-container-exit
     ```
   - **Validation**:
     ```bash
     # Trigger test run
     git commit -m "test: trigger CI"
     git push

     # Check GitHub Actions
     gh run list --workflow=frame-buffer-v2-tests.yml
     ```
   - **Quality Gate**: Tests run automatically, coverage >80%
   - **Czas**: 1h

4. **[ ] Implementacja podstawowych data models**
   - **Metryka**: Type-safe models for frames, processors, events
   - **TDD Test First**:
     ```python
     # tests/test_models.py
     def test_frame_ready_event():
         """Test FrameReadyEvent model."""
         event = FrameReadyEvent(
             frame_id="test_123",
             camera_id="cam01",
             timestamp=datetime.now(),
             size_bytes=1024,
             width=1920,
             height=1080,
             format="jpeg",
             trace_context={"trace_id": "abc123"},
             priority=1
         )

         # Test serialization
         json_data = event.to_json()
         restored = FrameReadyEvent.from_json(json_data)
         assert restored.frame_id == event.frame_id
         assert restored.trace_context == event.trace_context

     def test_processor_registration():
         """Test ProcessorRegistration model."""
         reg = ProcessorRegistration(
             id="face-detector-1",
             capabilities=["face_detection", "person_detection"],
             capacity=100,
             queue="frames:ready:face-detector-1"
         )
         assert reg.can_process("face_detection")
         assert not reg.can_process("vehicle_detection")
     ```
   - **Implementation**:
     ```python
     # src/models.py
     from dataclasses import dataclass, field
     from datetime import datetime
     from typing import Dict, List, Any

     @dataclass
     class FrameReadyEvent:
         frame_id: str
         camera_id: str
         timestamp: datetime
         size_bytes: int
         width: int
         height: int
         format: str
         trace_context: Dict[str, str]
         priority: int = 0
         metadata: Dict[str, Any] = field(default_factory=dict)

         def to_json(self) -> dict:
             return {
                 "frame_id": self.frame_id,
                 "camera_id": self.camera_id,
                 "timestamp": self.timestamp.isoformat(),
                 "size_bytes": self.size_bytes,
                 "width": self.width,
                 "height": self.height,
                 "format": self.format,
                 "trace_context": self.trace_context,
                 "priority": self.priority,
                 "metadata": self.metadata
             }
     ```
   - **Quality Gate**: All models have validation, serialization, and 100% test coverage
   - **Czas**: 1.5h

### Metryki sukcesu bloku 0
- Test environment fully operational
- Project structure follows clean architecture
- CI/CD pipeline running tests automatically
- Core data models implemented with validation

---

## Block 1: Core Orchestrator (Phase 1)

### Zadania atomowe

1. **[ ] Processor Registry implementation**
   - **Metryka**: Processors can register/unregister with health tracking
   - **TDD Test First**:
     ```python
     # tests/test_processor_registry.py
     async def test_processor_registration():
         """Test processor registration and lookup."""
         registry = ProcessorRegistry()

         # Register processor
         processor = ProcessorInfo(
             id="test-proc-1",
             capabilities=["face_detection"],
             capacity=10,
             queue="frames:ready:test-proc-1"
         )
         await registry.register(processor)

         # Verify registration
         assert await registry.get_processor("test-proc-1") == processor
         assert len(await registry.get_processors_for_capability("face_detection")) == 1

         # Test health tracking
         await registry.mark_healthy("test-proc-1")
         healthy = await registry.get_healthy_processors()
         assert "test-proc-1" in [p.id for p in healthy]

         # Test unregistration
         await registry.unregister("test-proc-1")
         assert await registry.get_processor("test-proc-1") is None
     ```
   - **Implementation**:
     ```python
     # src/processors/registry.py
     class ProcessorRegistry:
         def __init__(self, redis_client):
             self.redis = redis_client
             self.processors: Dict[str, ProcessorInfo] = {}
             self.health_status: Dict[str, ProcessorHealth] = {}

         async def register(self, processor: ProcessorInfo) -> bool:
             # Store in Redis for persistence
             await self.redis.hset(
                 "processors:registry",
                 processor.id,
                 processor.to_json()
             )
             self.processors[processor.id] = processor
             return True
     ```
   - **Validation**:
     ```bash
     # Run specific test
     pytest tests/test_processor_registry.py::test_processor_registration -v

     # Check Redis state
     docker exec redis redis-cli HGETALL processors:registry
     ```
   - **Quality Gate**: Registry handles concurrent registrations, persists state
   - **Czas**: 2h

2. **[ ] Basic Frame Distributor**
   - **Metryka**: Distributes frames to processors based on capabilities
   - **TDD Test First**:
     ```python
     # tests/test_frame_distributor.py
     async def test_frame_distribution():
         """Test basic frame distribution logic."""
         registry = ProcessorRegistry()
         distributor = FrameDistributor(registry)

         # Register two processors
         await registry.register(ProcessorInfo(
             id="proc1",
             capabilities=["face_detection"],
             capacity=10
         ))
         await registry.register(ProcessorInfo(
             id="proc2",
             capabilities=["object_detection"],
             capacity=10
         ))

         # Test distribution
         face_frame = FrameReadyEvent(
             frame_id="f1",
             metadata={"detection_type": "face_detection"}
         )

         processor = await distributor.select_processor(face_frame)
         assert processor.id == "proc1"

         # Test load balancing
         results = []
         for i in range(100):
             proc = await distributor.select_processor(face_frame)
             results.append(proc.id)

         # Should distribute evenly
         assert 40 < results.count("proc1") < 60
     ```
   - **Implementation**:
     ```python
     # src/orchestrator/distributor.py
     class FrameDistributor:
         async def distribute_frame(self, frame: FrameReadyEvent) -> bool:
             # Get eligible processors
             processors = await self.get_eligible_processors(frame)
             if not processors:
                 return False

             # Select processor
             processor = await self.select_processor(processors, frame)

             # Dispatch to processor queue
             await self.dispatch_to_processor(processor, frame)

             # Update metrics
             self.metrics.frames_distributed.inc(
                 processor_id=processor.id,
                 camera_id=frame.camera_id
             )
             return True
     ```
   - **Quality Gate**: Distributes based on capabilities, handles no processor case
   - **Czas**: 2h

3. **[ ] REST API endpoints for processor management**
   - **Metryka**: Full CRUD API for processor registration
   - **TDD Test First**:
     ```python
     # tests/test_api.py
     async def test_processor_registration_api():
         """Test processor registration via API."""
         async with AsyncClient(app=app, base_url="http://test") as client:
             # Register processor
             response = await client.post("/processors/register", json={
                 "id": "test-proc",
                 "capabilities": ["face_detection"],
                 "capacity": 100,
                 "queue": "frames:ready:test-proc"
             })
             assert response.status_code == 201
             assert response.json()["id"] == "test-proc"

             # List processors
             response = await client.get("/processors")
             assert response.status_code == 200
             assert len(response.json()) == 1

             # Get specific processor
             response = await client.get("/processors/test-proc")
             assert response.status_code == 200
             assert response.json()["capabilities"] == ["face_detection"]

             # Unregister
             response = await client.delete("/processors/test-proc")
             assert response.status_code == 204
     ```
   - **Implementation**:
     ```python
     # src/api/processors.py
     @router.post("/processors/register", status_code=201)
     async def register_processor(registration: ProcessorRegistration):
         processor = ProcessorInfo.from_registration(registration)
         success = await registry.register(processor)
         if not success:
             raise HTTPException(409, "Processor already registered")
         return processor
     ```
   - **Quality Gate**: All endpoints have validation, error handling, OpenAPI docs
   - **Czas**: 1.5h

4. **[ ] Health monitoring system**
   - **Metryka**: Tracks processor health with automatic failover
   - **TDD Test First**:
     ```python
     # tests/test_health_monitor.py
     async def test_health_monitoring():
         """Test health check system."""
         monitor = HealthMonitor(check_interval=0.1)  # 100ms for tests

         # Register processor
         await monitor.add_processor("proc1", "http://proc1:8080/health")

         # Mock healthy response
         with aioresponses() as m:
             m.get("http://proc1:8080/health", payload={"status": "healthy"})

             # Start monitoring
             await monitor.start()
             await asyncio.sleep(0.2)

             # Check health status
             status = await monitor.get_status("proc1")
             assert status == "healthy"

         # Test failure detection
         with aioresponses() as m:
             m.get("http://proc1:8080/health", status=500)

             await asyncio.sleep(0.2)
             status = await monitor.get_status("proc1")
             assert status == "unhealthy"

         # Test circuit breaker
         assert await monitor.is_circuit_open("proc1")
     ```
   - **Implementation**:
     ```python
     # src/health/monitor.py
     class HealthMonitor:
         def __init__(self, check_interval: float = 10.0):
             self.check_interval = check_interval
             self.health_status: Dict[str, HealthStatus] = {}
             self.circuit_breakers: Dict[str, CircuitBreaker] = {}

         async def check_processor_health(self, processor_id: str):
             try:
                 response = await self.http_client.get(
                     f"{processor_url}/health",
                     timeout=5.0
                 )
                 if response.status_code == 200:
                     self.mark_healthy(processor_id)
                 else:
                     self.mark_unhealthy(processor_id)
             except Exception:
                 self.mark_unhealthy(processor_id)
     ```
   - **Quality Gate**: Detects failures within 2 check cycles, circuit breaker works
   - **Czas**: 2h

### Metryki sukcesu bloku 1
- Processor registry fully functional with persistence
- Basic distribution algorithm working
- REST API with full OpenAPI documentation
- Health monitoring with circuit breakers

---

## Block 2: Event-Driven Pipeline (Phase 2)

### Zadania atomowe

1. **[ ] Redis Streams consumer implementation**
   - **Metryka**: Consumes from capture stream with consumer groups
   - **TDD Test First**:
     ```python
     # tests/test_stream_consumer.py
     async def test_stream_consumption():
         """Test consuming from Redis Streams."""
         consumer = StreamConsumer(
             stream="frames:capture",
             group="frame-buffer",
             consumer_id="fb-1"
         )

         # Add test frames to stream
         redis = await aioredis.create_redis_pool('redis://localhost')
         for i in range(10):
             await redis.xadd("frames:capture", {
                 "frame_id": f"test_{i}",
                 "data": "test_data"
             })

         # Consume frames
         frames = []
         async for frame in consumer.consume(max_count=5):
             frames.append(frame)
             if len(frames) >= 5:
                 break

         assert len(frames) == 5
         assert frames[0]["frame_id"] == "test_0"

         # Test acknowledgment
         await consumer.ack_frames([f["id"] for f in frames])

         # Verify acknowledged
         pending = await redis.xpending("frames:capture", "frame-buffer")
         assert pending[0] == 5  # 5 frames still pending
     ```
   - **Implementation**:
     ```python
     # src/orchestrator/consumer.py
     class StreamConsumer:
         async def consume(self, max_count: int = 10):
             while True:
                 messages = await self.redis.xreadgroup(
                     self.group,
                     self.consumer_id,
                     {self.stream: '>'},
                     count=max_count,
                     block=1000  # 1 second
                 )

                 for stream, stream_messages in messages:
                     for msg_id, data in stream_messages:
                         yield {
                             "id": msg_id,
                             "stream": stream,
                             **data
                         }
     ```
   - **Quality Gate**: Handles reconnections, no message loss
   - **Czas**: 2h

2. **[ ] Processor work queue implementation**
   - **Metryka**: Each processor has dedicated queue in Redis Streams
   - **TDD Test First**:
     ```python
     # tests/test_work_queue.py
     async def test_processor_queue():
         """Test processor-specific work queues."""
         queue_manager = WorkQueueManager()

         # Create processor queue
         await queue_manager.create_queue("proc1")

         # Add frames to queue
         frame = FrameReadyEvent(frame_id="f1", camera_id="cam1")
         msg_id = await queue_manager.enqueue("proc1", frame)
         assert msg_id is not None

         # Consumer group for processor
         await queue_manager.create_consumer_group("proc1", "proc1-group")

         # Consume from queue
         messages = await queue_manager.consume(
             "proc1", "proc1-group", "consumer-1"
         )
         assert len(messages) == 1
         assert messages[0]["frame_id"] == "f1"

         # Test queue stats
         stats = await queue_manager.get_queue_stats("proc1")
         assert stats["length"] == 1
         assert stats["pending"] == 1
     ```
   - **Implementation**:
     ```python
     # src/orchestrator/queue_manager.py
     class WorkQueueManager:
         def __init__(self, redis_client):
             self.redis = redis_client

         async def enqueue(self, processor_id: str, frame: FrameReadyEvent):
             queue_name = f"frames:ready:{processor_id}"

             # Add trace context
             data = frame.to_json()
             data["enqueued_at"] = datetime.now().isoformat()

             msg_id = await self.redis.xadd(queue_name, data)

             # Update metrics
             self.metrics.queue_depth.labels(
                 processor_id=processor_id
             ).inc()

             return msg_id
     ```
   - **Quality Gate**: Queue overflow handling, metrics accurate
   - **Czas**: 1.5h

3. **[ ] Processor client library**
   - **Metryka**: Easy-to-use client for processor implementation
   - **TDD Test First**:
     ```python
     # tests/test_processor_client.py
     async def test_processor_client():
         """Test processor client library."""

         class TestProcessor(ProcessorClient):
             def __init__(self):
                 super().__init__(
                     processor_id="test-proc",
                     capabilities=["test_capability"],
                     orchestrator_url="http://localhost:8002"
                 )
                 self.processed_frames = []

             async def process_frame(self, frame_data: dict) -> dict:
                 self.processed_frames.append(frame_data["frame_id"])
                 return {"result": "processed"}

         # Test registration
         processor = TestProcessor()

         with aioresponses() as m:
             m.post("http://localhost:8002/processors/register",
                    payload={"id": "test-proc"})

             await processor.register()

             # Verify registration request
             history = m.requests[('POST', URL('http://localhost:8002/processors/register'))]
             assert len(history) == 1
             assert history[0].kwargs["json"]["id"] == "test-proc"

         # Test frame consumption
         # Add frame to processor queue
         redis = await aioredis.create_redis_pool('redis://localhost')
         await redis.xadd("frames:ready:test-proc", {
             "frame_id": "test_frame_1",
             "trace_context": json.dumps({"trace_id": "abc123"})
         })

         # Start processor (with timeout for test)
         consume_task = asyncio.create_task(processor.start())
         await asyncio.sleep(0.5)
         consume_task.cancel()

         # Verify processing
         assert "test_frame_1" in processor.processed_frames
     ```
   - **Implementation**:
     ```python
     # src/processors/client.py
     class ProcessorClient:
         def __init__(self, processor_id: str, capabilities: List[str],
                      orchestrator_url: str):
             self.id = processor_id
             self.capabilities = capabilities
             self.orchestrator_url = orchestrator_url
             self.queue_name = f"frames:ready:{processor_id}"

         async def start(self):
             # Register with orchestrator
             await self.register()

             # Start health reporting
             asyncio.create_task(self.health_reporter())

             # Start consuming frames
             await self.consume_frames()

         async def consume_frames(self):
             consumer = StreamConsumer(
                 stream=self.queue_name,
                 group=f"{self.id}-group",
                 consumer_id=f"{self.id}-1"
             )

             async for frame_data in consumer.consume():
                 # Extract trace context
                 trace_ctx = json.loads(frame_data.get("trace_context", "{}"))

                 with TraceContext.from_dict(trace_ctx):
                     result = await self.process_frame(frame_data)
                     await self.publish_result(result)
                     await consumer.ack_frame(frame_data["id"])
     ```
   - **Quality Gate**: Auto-reconnect, proper error handling, trace propagation
   - **Czas**: 2h

4. **[ ] Trace context propagation**
   - **Metryka**: Trace context preserved through entire pipeline
   - **TDD Test First**:
     ```python
     # tests/test_trace_propagation.py
     async def test_trace_propagation():
         """Test trace context flows through pipeline."""
         tracer = trace.get_tracer(__name__)

         # Create initial trace
         with tracer.start_as_current_span("capture_frame") as span:
             trace_id = span.get_span_context().trace_id
             span_id = span.get_span_context().span_id

             # Create frame with trace context
             frame = FrameReadyEvent(
                 frame_id="trace_test_1",
                 trace_context={
                     "trace_id": format(trace_id, '032x'),
                     "span_id": format(span_id, '016x'),
                     "trace_flags": "01"
                 }
             )

             # Simulate orchestrator processing
             orchestrator = FrameOrchestrator()

             # Process should continue trace
             with patch('opentelemetry.trace.get_current_span') as mock_span:
                 await orchestrator.process_frame(frame)

                 # Verify trace context was extracted
                 mock_span.return_value.get_span_context.assert_called()

         # Test end-to-end propagation
         redis = await aioredis.create_redis_pool('redis://localhost')

         # Add frame to capture stream with trace
         await redis.xadd("frames:capture", {
             "frame_id": "e2e_trace_test",
             "traceparent": f"00-{format(trace_id, '032x')}-{format(span_id, '016x')}-01"
         })

         # Consume and verify trace preserved
         consumer = StreamConsumer("frames:capture", "test-group", "test-1")
         async for frame in consumer.consume(max_count=1):
             assert "traceparent" in frame

             # Parse W3C trace context
             tp = frame["traceparent"]
             parts = tp.split('-')
             assert parts[1] == format(trace_id, '032x')
             break
     ```
   - **Implementation**:
     ```python
     # src/telemetry/propagation.py
     class TraceContextPropagation:
         @staticmethod
         def inject_to_frame(frame_data: dict) -> dict:
             """Inject current trace context into frame data."""
             span = trace.get_current_span()
             if span.is_recording():
                 ctx = span.get_span_context()
                 frame_data["trace_context"] = {
                     "trace_id": format(ctx.trace_id, '032x'),
                     "span_id": format(ctx.span_id, '016x'),
                     "trace_flags": format(ctx.trace_flags, '02x')
                 }
                 # W3C Trace Context format
                 frame_data["traceparent"] = (
                     f"00-{format(ctx.trace_id, '032x')}-"
                     f"{format(ctx.span_id, '016x')}-"
                     f"{format(ctx.trace_flags, '02x')}"
                 )
             return frame_data

         @staticmethod
         def extract_from_frame(frame_data: dict):
             """Extract trace context from frame data."""
             if "traceparent" in frame_data:
                 # Parse W3C format
                 return TraceContextTextMapPropagator().extract(
                     carrier={"traceparent": frame_data["traceparent"]}
                 )
             return None
     ```
   - **Quality Gate**: No trace context loss, proper parent-child relationships
   - **Czas**: 1.5h

### Metryki sukcesu bloku 2
- Consumer groups prevent message loss
- Each processor has isolated queue
- Client library simplifies processor development
- 100% trace context propagation

---

## Block 3: Advanced Features (Phase 3)

### Zadania atomowe

1. **[ ] Backpressure controller implementation**
   - **Metryka**: System slows/stops when queues fill up
   - **TDD Test First**:
     ```python
     # tests/test_backpressure.py
     async def test_backpressure_levels():
         """Test backpressure detection and response."""
         controller = BackpressureController(
             thresholds={
                 "low": 0.6,
                 "high": 0.8,
                 "critical": 0.95
             }
         )

         # Mock queue stats
         queue_stats = {
             "proc1": {"size": 30, "capacity": 100},  # 30%
             "proc2": {"size": 85, "capacity": 100},  # 85% - high
         }

         with patch.object(controller, 'get_queue_stats', return_value=queue_stats):
             level = await controller.check_pressure()
             assert level == PressureLevel.HIGH

             # Test response
             await controller.apply_backpressure(level)
             assert controller.consumption_rate == 0.5  # 50% slowdown

         # Test critical level
         queue_stats["proc2"]["size"] = 98  # 98%
         with patch.object(controller, 'get_queue_stats', return_value=queue_stats):
             level = await controller.check_pressure()
             assert level == PressureLevel.CRITICAL

             # Should pause consumption
             await controller.apply_backpressure(level)
             assert controller.is_paused == True
     ```
   - **Implementation**:
     ```python
     # src/backpressure/controller.py
     class BackpressureController:
         async def monitor_loop(self):
             """Main monitoring loop."""
             while True:
                 try:
                     level = await self.check_pressure()
                     await self.apply_backpressure(level)

                     # Update metrics
                     self.metrics.backpressure_level.set(level.value)

                     # Alert if critical
                     if level == PressureLevel.CRITICAL:
                         await self.send_alert(
                             "Critical backpressure detected",
                             queue_stats=await self.get_queue_stats()
                         )

                 except Exception as e:
                     logger.error(f"Backpressure monitoring error: {e}")

                 await asyncio.sleep(self.check_interval)
     ```
   - **Validation**:
     ```bash
     # Load test to trigger backpressure
     python scripts/load_test.py --fps 100 --duration 60

     # Monitor metrics
     curl http://localhost:8002/metrics | grep backpressure_level

     # Check consumption rate
     curl http://localhost:8002/control/status | jq '.consumption_rate'
     ```
   - **Quality Gate**: Responds within 5 seconds, no frame loss
   - **Czas**: 2h

2. **[ ] Smart routing algorithms**
   - **Metryka**: Intelligent frame routing based on processor load/affinity
   - **TDD Test First**:
     ```python
     # tests/test_routing.py
     async def test_affinity_routing():
         """Test camera affinity routing."""
         router = SmartRouter(strategy="affinity")

         # Register processors
         processors = [
             ProcessorInfo(id=f"proc{i}", capacity=100)
             for i in range(3)
         ]

         # Route frames from same camera
         frames = [
             FrameReadyEvent(frame_id=f"f{i}", camera_id="cam1")
             for i in range(10)
         ]

         assignments = []
         for frame in frames:
             proc = await router.route(frame, processors)
             assignments.append(proc.id)

         # All frames from cam1 should go to same processor
         assert len(set(assignments)) == 1

     async def test_least_loaded_routing():
         """Test least loaded routing."""
         router = SmartRouter(strategy="least_loaded")

         # Processors with different loads
         processors = [
             ProcessorInfo(id="proc1", current_load=0.8),  # 80% loaded
             ProcessorInfo(id="proc2", current_load=0.2),  # 20% loaded
             ProcessorInfo(id="proc3", current_load=0.5),  # 50% loaded
         ]

         # Should route to least loaded
         frame = FrameReadyEvent(frame_id="test")
         selected = await router.route(frame, processors)
         assert selected.id == "proc2"
     ```
   - **Implementation**:
     ```python
     # src/orchestrator/router.py
     class SmartRouter:
         def __init__(self, strategy: str = "least_loaded"):
             self.strategy = strategy
             self.affinity_map: Dict[str, str] = {}

         async def route(self, frame: FrameReadyEvent,
                        processors: List[ProcessorInfo]) -> ProcessorInfo:
             if self.strategy == "affinity":
                 return await self.route_by_affinity(frame, processors)
             elif self.strategy == "least_loaded":
                 return await self.route_by_load(frame, processors)
             elif self.strategy == "round_robin":
                 return await self.route_round_robin(frame, processors)
             else:
                 raise ValueError(f"Unknown strategy: {self.strategy}")

         async def route_by_affinity(self, frame: FrameReadyEvent,
                                   processors: List[ProcessorInfo]) -> ProcessorInfo:
             # Check if camera already assigned
             if frame.camera_id in self.affinity_map:
                 proc_id = self.affinity_map[frame.camera_id]
                 # Verify processor still available
                 for proc in processors:
                     if proc.id == proc_id:
                         return proc

             # Assign new processor
             selected = min(processors, key=lambda p: len([
                 cam for cam, pid in self.affinity_map.items()
                 if pid == p.id
             ]))
             self.affinity_map[frame.camera_id] = selected.id
             return selected
     ```
   - **Quality Gate**: <10ms routing decision, even distribution
   - **Czas**: 1.5h

3. **[ ] Circuit breaker implementation**
   - **Metryka**: Automatic processor isolation on failures
   - **TDD Test First**:
     ```python
     # tests/test_circuit_breaker.py
     async def test_circuit_breaker_states():
         """Test circuit breaker state transitions."""
         breaker = CircuitBreaker(
             failure_threshold=3,
             recovery_timeout=1.0,  # 1 second for tests
             success_threshold=2
         )

         # Initial state is closed
         assert breaker.state == CircuitState.CLOSED
         assert await breaker.call(lambda: "success") == "success"

         # Simulate failures
         for _ in range(3):
             with pytest.raises(Exception):
                 await breaker.call(lambda: exec('raise Exception("fail")'))

         # Should be open after threshold
         assert breaker.state == CircuitState.OPEN

         # Calls should fail fast when open
         with pytest.raises(CircuitOpenError):
             await breaker.call(lambda: "success")

         # Wait for recovery timeout
         await asyncio.sleep(1.1)

         # Should be half-open
         assert breaker.state == CircuitState.HALF_OPEN

         # Success should close circuit
         await breaker.call(lambda: "success")
         await breaker.call(lambda: "success")
         assert breaker.state == CircuitState.CLOSED
     ```
   - **Implementation**:
     ```python
     # src/orchestrator/circuit_breaker.py
     class CircuitBreaker:
         def __init__(self, failure_threshold: int = 5,
                      recovery_timeout: float = 60.0,
                      success_threshold: int = 3):
             self.failure_threshold = failure_threshold
             self.recovery_timeout = recovery_timeout
             self.success_threshold = success_threshold
             self.state = CircuitState.CLOSED
             self.failure_count = 0
             self.success_count = 0
             self.last_failure_time = None

         async def call(self, func: Callable):
             if self.state == CircuitState.OPEN:
                 if self._should_attempt_reset():
                     self.state = CircuitState.HALF_OPEN
                 else:
                     raise CircuitOpenError("Circuit breaker is open")

             try:
                 result = await func()
                 self._on_success()
                 return result
             except Exception as e:
                 self._on_failure()
                 raise
     ```
   - **Quality Gate**: Isolates failures within 3 attempts, recovers properly
   - **Czas**: 1.5h

4. **[ ] Priority queue support**
   - **Metryka**: High-priority frames processed first
   - **TDD Test First**:
     ```python
     # tests/test_priority_queue.py
     async def test_priority_processing():
         """Test priority-based frame processing."""
         queue = PriorityQueue()

         # Add frames with different priorities
         frames = [
             FrameReadyEvent(frame_id="low1", priority=0),
             FrameReadyEvent(frame_id="high1", priority=10),
             FrameReadyEvent(frame_id="med1", priority=5),
             FrameReadyEvent(frame_id="high2", priority=10),
             FrameReadyEvent(frame_id="low2", priority=0),
         ]

         for frame in frames:
             await queue.enqueue(frame)

         # Dequeue should return highest priority first
         order = []
         while not queue.empty():
             frame = await queue.dequeue()
             order.append(frame.frame_id)

         assert order == ["high1", "high2", "med1", "low1", "low2"]

         # Test starvation prevention
         # Add many high priority frames
         for i in range(100):
             await queue.enqueue(FrameReadyEvent(
                 frame_id=f"high{i}",
                 priority=10
             ))

         # Add one low priority
         await queue.enqueue(FrameReadyEvent(
             frame_id="low_starve",
             priority=0,
             timestamp=datetime.now() - timedelta(minutes=5)
         ))

         # Should eventually process old low priority frame
         processed = []
         for _ in range(50):
             frame = await queue.dequeue()
             processed.append(frame.frame_id)
             if frame.frame_id == "low_starve":
                 break

         assert "low_starve" in processed
     ```
   - **Implementation**:
     ```python
     # src/orchestrator/priority_queue.py
     class PriorityQueue:
         def __init__(self, starvation_threshold: int = 100):
             self.queues: Dict[int, asyncio.Queue] = {}
             self.starvation_threshold = starvation_threshold
             self.low_priority_count = 0

         async def enqueue(self, frame: FrameReadyEvent):
             priority = frame.priority
             if priority not in self.queues:
                 self.queues[priority] = asyncio.Queue()

             await self.queues[priority].put(frame)

         async def dequeue(self) -> FrameReadyEvent:
             # Check for starvation
             if self.low_priority_count > self.starvation_threshold:
                 # Force low priority processing
                 for priority in sorted(self.queues.keys()):
                     if not self.queues[priority].empty():
                         self.low_priority_count = 0
                         return await self.queues[priority].get()

             # Normal priority order
             for priority in sorted(self.queues.keys(), reverse=True):
                 if not self.queues[priority].empty():
                     frame = await self.queues[priority].get()
                     if priority == 0:
                         self.low_priority_count += 1
                     return frame
     ```
   - **Quality Gate**: No starvation, <1ms overhead
   - **Czas**: 1.5h

### Metryki sukcesu bloku 3
- Backpressure prevents overload
- Smart routing improves efficiency by 30%
- Circuit breakers isolate failures
- Priority processing works without starvation

---

## Block 4: Production Hardening (Phase 4)

### Zadania atomowe

1. **[ ] Comprehensive metrics implementation**
   - **Metryka**: Full Prometheus metrics for all operations
   - **TDD Test First**:
     ```python
     # tests/test_metrics.py
     async def test_metrics_collection():
         """Test comprehensive metrics."""
         # Reset metrics
         REGISTRY.clear()

         orchestrator = FrameOrchestrator()

         # Process some frames
         for i in range(10):
             frame = FrameReadyEvent(
                 frame_id=f"metric_test_{i}",
                 camera_id="cam1" if i < 5 else "cam2"
             )
             await orchestrator.process_frame(frame)

         # Check metrics
         metrics_output = generate_latest(REGISTRY).decode()

         # Verify key metrics exist
         assert "frame_buffer_frames_routed_total" in metrics_output
         assert "frame_buffer_routing_duration_seconds" in metrics_output
         assert "frame_buffer_backpressure_level" in metrics_output
         assert "frame_buffer_processor_queue_depth" in metrics_output

         # Parse specific metric
         for family in REGISTRY.collect():
             if family.name == "frame_buffer_frames_routed_total":
                 for sample in family.samples:
                     if sample.labels.get("camera_id") == "cam1":
                         assert sample.value == 5
     ```
   - **Implementation**:
     ```python
     # src/metrics.py
     from prometheus_client import Counter, Histogram, Gauge, Info

     # Orchestrator metrics
     frames_routed = Counter(
         "frame_buffer_frames_routed_total",
         "Total frames routed to processors",
         ["processor_id", "camera_id", "result"]
     )

     routing_duration = Histogram(
         "frame_buffer_routing_duration_seconds",
         "Time to route frame to processor",
         buckets=[.001, .005, .01, .025, .05, .1, .25, .5, 1.0]
     )

     backpressure_level = Gauge(
         "frame_buffer_backpressure_level",
         "Current backpressure level (0=normal, 3=critical)"
     )

     processor_queue_depth = Gauge(
         "frame_buffer_processor_queue_depth",
         "Current queue depth per processor",
         ["processor_id"]
     )

     orchestrator_info = Info(
         "frame_buffer_orchestrator",
         "Orchestrator information"
     )
     orchestrator_info.info({
         "version": "2.0.0",
         "routing_strategy": "least_loaded"
     })
     ```
   - **Quality Gate**: All operations have metrics, <1ms overhead
   - **Czas**: 1.5h

2. **[ ] Distributed tracing integration**
   - **Metryka**: Complete traces for every frame through orchestrator
   - **TDD Test First**:
     ```python
     # tests/test_tracing.py
     async def test_distributed_tracing():
         """Test OpenTelemetry integration."""
         # Setup test tracer
         tracer_provider = TracerProvider()
         trace.set_tracer_provider(tracer_provider)

         # Add span processor to capture spans
         spans = []
         tracer_provider.add_span_processor(
             SimpleSpanProcessor(InMemorySpanExporter(spans))
         )

         orchestrator = FrameOrchestrator()

         # Process frame with trace context
         with trace.get_tracer(__name__).start_as_current_span("test_root") as root:
             frame = FrameReadyEvent(
                 frame_id="trace_test",
                 trace_context={
                     "trace_id": format(root.get_span_context().trace_id, '032x'),
                     "span_id": format(root.get_span_context().span_id, '016x')
                 }
             )

             await orchestrator.process_frame(frame)

         # Verify spans created
         span_names = [span.name for span in spans]
         assert "frame_buffer_orchestrator_received" in span_names
         assert "route_frame" in span_names
         assert "dispatch_to_processor" in span_names

         # Verify trace context propagated
         route_span = next(s for s in spans if s.name == "route_frame")
         assert route_span.parent.span_id == root.get_span_context().span_id

         # Verify attributes
         assert route_span.attributes["frame.id"] == "trace_test"
         assert "selected_processor" in route_span.attributes
     ```
   - **Implementation**:
     ```python
     # src/telemetry/tracing.py
     from opentelemetry import trace
     from opentelemetry.instrumentation.aioredis import AioRedisInstrumentor
     from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

     class TracedOrchestrator:
         def __init__(self):
             self.tracer = trace.get_tracer(__name__)

             # Auto-instrument libraries
             AioRedisInstrumentor().instrument()
             HTTPXClientInstrumentor().instrument()

         async def process_frame(self, frame: FrameReadyEvent):
             # Extract parent context
             ctx = TraceContextPropagation.extract_from_frame(frame.to_json())

             with self.tracer.start_as_current_span(
                 "frame_buffer_orchestrator_received",
                 context=ctx
             ) as span:
                 span.set_attribute("frame.id", frame.frame_id)
                 span.set_attribute("frame.camera_id", frame.camera_id)
                 span.set_attribute("frame.priority", frame.priority)

                 # Route frame
                 with self.tracer.start_as_current_span("route_frame") as route_span:
                     processor = await self.select_processor(frame)
                     route_span.set_attribute("selected_processor", processor.id)
                     route_span.set_attribute("processor_load", processor.current_load)

                 # Dispatch
                 with self.tracer.start_as_current_span("dispatch_to_processor") as dispatch_span:
                     dispatch_span.set_attribute("processor.id", processor.id)
                     dispatch_span.set_attribute("queue.name", processor.queue)

                     # Inject context for next service
                     frame_data = frame.to_json()
                     TraceContextPropagation.inject_to_frame(frame_data)

                     await self.queue_manager.enqueue(processor.id, frame_data)
     ```
   - **Quality Gate**: No orphaned spans, context propagates correctly
   - **Czas**: 2h

3. **[ ] Integration tests suite**
   - **Metryka**: Full end-to-end tests with all components
   - **TDD Test First**:
     ```python
     # tests/integration/test_full_pipeline.py
     @pytest.mark.integration
     async def test_end_to_end_pipeline():
         """Test complete frame pipeline."""
         # Start all services
         async with AsyncExitStack() as stack:
             # Start orchestrator
             orchestrator = await stack.enter_async_context(
                 start_orchestrator()
             )

             # Start test processors
             processors = []
             for i in range(3):
                 proc = await stack.enter_async_context(
                     start_test_processor(f"proc{i}", ["object_detection"])
                 )
                 processors.append(proc)

             # Wait for registration
             await asyncio.sleep(1)

             # Verify processors registered
             response = await orchestrator.client.get("/processors")
             assert len(response.json()) == 3

             # Send frames through pipeline
             results = []
             for i in range(100):
                 frame_id = f"integration_test_{i}"

                 # Add to capture stream
                 await orchestrator.redis.xadd("frames:capture", {
                     "frame_id": frame_id,
                     "camera_id": f"cam{i % 2}",
                     "data": "test_frame_data"
                 })

             # Wait for processing
             await asyncio.sleep(5)

             # Verify all frames processed
             for proc in processors:
                 assert len(proc.processed_frames) > 20  # Even distribution

             # Verify no frame loss
             total_processed = sum(len(p.processed_frames) for p in processors)
             assert total_processed == 100

             # Check metrics
             metrics = await orchestrator.client.get("/metrics")
             assert "frames_routed_total{result=\"success\"} 100" in metrics.text
     ```
   - **Implementation**:
     ```python
     # tests/integration/fixtures.py
     @asynccontextmanager
     async def start_orchestrator():
         """Start orchestrator service for testing."""
         app = create_app()

         async with AsyncClient(
             app=app,
             base_url="http://test"
         ) as client:
             # Start background tasks
             app.state.orchestrator = FrameOrchestrator()
             consume_task = asyncio.create_task(
                 app.state.orchestrator.start()
             )

             try:
                 yield TestOrchestrator(
                     client=client,
                     redis=app.state.redis,
                     orchestrator=app.state.orchestrator
                 )
             finally:
                 consume_task.cancel()
                 await asyncio.gather(consume_task, return_exceptions=True)
     ```
   - **Quality Gate**: All integration tests pass, <5s total runtime
   - **Czas**: 2h

4. **[ ] Performance benchmarking**
   - **Metryka**: Validated performance targets met
   - **TDD Test First**:
     ```python
     # tests/performance/test_benchmarks.py
     @pytest.mark.benchmark
     async def test_routing_performance():
         """Benchmark routing performance."""
         router = SmartRouter()
         processors = [
             ProcessorInfo(id=f"proc{i}", capacity=100)
             for i in range(50)  # 50 processors
         ]

         frames = [
             FrameReadyEvent(frame_id=f"perf_{i}", camera_id=f"cam{i % 10}")
             for i in range(10000)
         ]

         # Measure routing time
         start = time.perf_counter()

         for frame in frames:
             processor = await router.route(frame, processors)

         elapsed = time.perf_counter() - start

         # Calculate metrics
         avg_routing_time = elapsed / len(frames) * 1000  # ms
         frames_per_second = len(frames) / elapsed

         print(f"Average routing time: {avg_routing_time:.3f}ms")
         print(f"Frames per second: {frames_per_second:.0f}")

         # Assertions
         assert avg_routing_time < 10  # <10ms per frame
         assert frames_per_second > 1000  # >1000 fps routing

     @pytest.mark.benchmark
     async def test_backpressure_response_time():
         """Test backpressure response time."""
         controller = BackpressureController(check_interval=0.1)

         # Simulate queue filling up
         start_time = time.perf_counter()
         response_time = None

         async def fill_queues():
             nonlocal response_time
             # Gradually fill queues
             for i in range(100):
                 controller._test_queue_size = i
                 if i >= 80 and response_time is None:
                     # Backpressure should trigger
                     if controller.consumption_rate < 1.0:
                         response_time = time.perf_counter() - start_time
                 await asyncio.sleep(0.05)

         fill_task = asyncio.create_task(fill_queues())
         monitor_task = asyncio.create_task(controller.monitor_loop())

         await asyncio.sleep(10)

         fill_task.cancel()
         monitor_task.cancel()

         assert response_time is not None
         assert response_time < 5  # Response within 5 seconds
         print(f"Backpressure response time: {response_time:.2f}s")
     ```
   - **Validation**:
     ```bash
     # Run performance tests
     pytest tests/performance/ -v -m benchmark

     # Profile critical paths
     python -m cProfile -o profile.stats src/orchestrator/main.py

     # Generate flame graph
     py-spy record -o profile.svg -- python src/orchestrator/main.py
     ```
   - **Quality Gate**: Meets all performance targets
   - **Czas**: 2h

### Metryki sukcesu bloku 4
- Comprehensive metrics dashboard available
- Full distributed tracing working
- Integration tests cover all scenarios
- Performance targets validated

---

## Block 5: Migration (Phase 5) <!-- dla LLM: jebać to, nic nie migrujemy, zaktualizuj ten blok w taki sposób, aby od razu wypierdolić starą usługę i odpalać nową -->

### Zadania atomowe

1. **[ ] Parallel deployment setup**
   - **Metryka**: Both frame-buffer versions running simultaneously
   - **TDD Test First**:
     ```python
     # tests/migration/test_parallel_deployment.py
     async def test_parallel_operation():
         """Test both frame-buffer versions can run in parallel."""
         # Start old frame-buffer
         old_fb = await start_service("frame-buffer", port=8002)

         # Start new frame-buffer
         new_fb = await start_service("frame-buffer-v2", port=8003)

         # Both should be healthy
         old_health = await old_fb.get("/health")
         assert old_health.status_code == 200

         new_health = await new_fb.get("/health")
         assert new_health.status_code == 200

         # Should consume from different consumer groups
         redis = await aioredis.create_redis_pool('redis://localhost')

         groups = await redis.xinfo_groups("frames:capture")
         group_names = [g["name"] for g in groups]

         assert "frame-buffer" in group_names  # old
         assert "frame-buffer-v2" in group_names  # new
     ```
   - **Implementation**:
     ```yaml
     # docker-compose.migration.yml
     services:
       frame-buffer:  # Old version
         image: ghcr.io/hretheum/detektr/frame-buffer:latest
         environment:
           - CONSUMER_GROUP=frame-buffer
           - PORT=8002

       frame-buffer-v2:  # New version
         image: ghcr.io/hretheum/detektr/frame-buffer:2.0
         environment:
           - CONSUMER_GROUP=frame-buffer-v2
           - PORT=8003
           - SHADOW_MODE=true  # Don't affect production
     ```
   - **Quality Gate**: Both services healthy, no interference
   - **Czas**: 1h

2. **[ ] Traffic splitting mechanism**
   - **Metryka**: Gradual traffic shift from old to new
   - **TDD Test First**:
     ```python
     # tests/migration/test_traffic_split.py
     async def test_traffic_splitting():
         """Test gradual traffic migration."""
         splitter = TrafficSplitter(
             old_endpoint="http://localhost:8002",
             new_endpoint="http://localhost:8003"
         )

         # Test different split ratios
         test_cases = [
             (0, 100, 0),      # 0% to new
             (10, 90, 10),     # 10% to new
             (50, 50, 50),     # 50% to new
             (90, 10, 90),     # 90% to new
             (100, 0, 100),    # 100% to new
         ]

         for new_percent, expected_old, expected_new in test_cases:
             splitter.set_split(new_percent)

             # Send 100 requests
             old_count = 0
             new_count = 0

             for _ in range(100):
                 endpoint = splitter.get_endpoint()
                 if "8002" in endpoint:
                     old_count += 1
                 else:
                     new_count += 1

             # Allow 10% variance
             assert abs(old_count - expected_old) <= 10
             assert abs(new_count - expected_new) <= 10
     ```
   - **Implementation**:
     ```python
     # src/migration/traffic_splitter.py
     class TrafficSplitter:
         def __init__(self, old_endpoint: str, new_endpoint: str):
             self.old_endpoint = old_endpoint
             self.new_endpoint = new_endpoint
             self.new_traffic_percent = 0

         def set_split(self, new_percent: int):
             """Set percentage of traffic to new service."""
             self.new_traffic_percent = max(0, min(100, new_percent))

         def get_endpoint(self) -> str:
             """Get endpoint based on current split."""
             if random.randint(1, 100) <= self.new_traffic_percent:
                 return self.new_endpoint
             return self.old_endpoint
     ```
   - **Quality Gate**: Accurate traffic split, configurable
   - **Czas**: 1h

3. **[ ] Processor migration tooling**
   - **Metryka**: Easy migration of processors to new API
   - **TDD Test First**:
     ```python
     # tests/migration/test_processor_migration.py
     async def test_processor_migration_tool():
         """Test processor migration helper."""
         migrator = ProcessorMigrator()

         # Mock old processor using polling
         old_processor_code = '''
         while True:
             response = requests.get("http://frame-buffer:8002/frames/dequeue")
             frames = response.json()["frames"]
             for frame in frames:
                 process_frame(frame)
             time.sleep(0.1)
         '''

         # Migrate to new pattern
         new_code = migrator.migrate_code(old_processor_code)

         # Verify new code uses ProcessorClient
         assert "ProcessorClient" in new_code
         assert "process_frame" in new_code  # Preserves logic
         assert "requests.get" not in new_code  # No more polling

         # Test configuration migration
         old_config = {
             "frame_buffer_url": "http://frame-buffer:8002",
             "poll_interval": 0.1
         }

         new_config = migrator.migrate_config(old_config)

         assert new_config["orchestrator_url"] == "http://frame-buffer-v2:8003"
         assert "processor_id" in new_config
         assert "capabilities" in new_config
     ```
   - **Implementation**:
     ```python
     # scripts/migrate_processor.py
     class ProcessorMigrator:
         def generate_migration_guide(self, processor_name: str) -> str:
             """Generate step-by-step migration guide."""
             return f"""
     # Migration Guide for {processor_name}

     ## Step 1: Update Dependencies
     ```bash
     pip install detektor-processor-client>=2.0
     ```

     ## Step 2: Update Code
     Replace polling loop with ProcessorClient:

     ```python
     from detektor.processor import ProcessorClient

     class {processor_name}(ProcessorClient):
         def __init__(self):
             super().__init__(
                 processor_id="{processor_name.lower()}-1",
                 capabilities=["your_capabilities_here"],
                 orchestrator_url=os.getenv("ORCHESTRATOR_URL")
             )

         async def process_frame(self, frame_data: dict) -> dict:
             # Your existing process_frame logic here
             result = your_processing_function(frame_data)
             return result
     ```

     ## Step 3: Update Configuration
     ```yaml
     environment:
       - ORCHESTRATOR_URL=http://frame-buffer-v2:8003
       - PROCESSOR_ID={processor_name.lower()}-1
     ```

     ## Step 4: Test
     ```bash
     python -m pytest tests/test_{processor_name.lower()}.py
     ```
     """
     ```
   - **Quality Gate**: Clear migration path, automated where possible
   - **Czas**: 1.5h

4. **[ ] Rollback procedures**
   - **Metryka**: Safe rollback possible at any point
   - **TDD Test First**:
     ```python
     # tests/migration/test_rollback.py
     async def test_rollback_procedure():
         """Test safe rollback from new to old."""
         rollback = RollbackManager()

         # Simulate partial migration state
         await rollback.save_state({
             "migrated_processors": ["proc1", "proc2"],
             "traffic_split": 30,
             "start_time": datetime.now().isoformat()
         })

         # Perform rollback
         await rollback.execute()

         # Verify rollback actions
         assert rollback.traffic_split == 0  # All traffic to old

         # Verify processors reverted
         for proc_id in ["proc1", "proc2"]:
             config = await rollback.get_processor_config(proc_id)
             assert config["frame_buffer_url"] == "http://frame-buffer:8002"

         # Verify state cleared
         assert await rollback.get_state() is None
     ```
   - **Implementation**:
     ```python
     # src/migration/rollback.py
     class RollbackManager:
         async def execute(self):
             """Execute rollback procedure."""
             state = await self.get_state()
             if not state:
                 logger.warning("No migration state found")
                 return

             logger.info(f"Starting rollback from state: {state}")

             # Step 1: Stop new traffic
             await self.set_traffic_split(0)
             logger.info("Traffic redirected to old frame-buffer")

             # Step 2: Drain new queues
             await self.drain_queues(state["migrated_processors"])
             logger.info("New queues drained")

             # Step 3: Revert processor configs
             for proc_id in state["migrated_processors"]:
                 await self.revert_processor(proc_id)
             logger.info("Processors reverted")

             # Step 4: Clear state
             await self.clear_state()
             logger.info("Rollback complete")
     ```
   - **Quality Gate**: Rollback completes in <5 minutes
   - **Czas**: 1.5h

5. **[ ] Decommission old frame-buffer**
   - **Metryka**: Safe removal of old service
   - **TDD Test First**:
     ```python
     # tests/migration/test_decommission.py
     async def test_safe_decommission():
         """Test safe decommissioning of old service."""
         decom = DecommissionManager()

         # Pre-checks should fail if still in use
         with pytest.raises(DecommissionError):
             await decom.pre_checks()

         # Simulate migration complete
         await decom.set_migration_complete()

         # Now pre-checks should pass
         result = await decom.pre_checks()
         assert result["traffic_to_old"] == 0
         assert result["active_connections"] == 0
         assert result["pending_frames"] == 0

         # Execute decommission
         await decom.execute()

         # Verify old service stopped
         with pytest.raises(ConnectionError):
             await old_client.get("/health")

         # Verify new service still healthy
         health = await new_client.get("/health")
         assert health.status_code == 200
     ```
   - **Implementation**:
     ```python
     # scripts/decommission_old_service.py
     class DecommissionManager:
         async def pre_checks(self) -> dict:
             """Run safety checks before decommission."""
             checks = {
                 "traffic_to_old": await self.check_traffic(),
                 "active_connections": await self.check_connections(),
                 "pending_frames": await self.check_pending_frames(),
                 "consumer_groups": await self.check_consumer_groups()
             }

             if any(v > 0 for v in checks.values()):
                 raise DecommissionError(
                     f"Cannot decommission, active resources: {checks}"
                 )

             return checks

         async def execute(self):
             """Safely decommission old service."""
             # Final checks
             await self.pre_checks()

             # Remove from service discovery
             await self.remove_from_registry("frame-buffer")

             # Stop container
             await self.stop_service("frame-buffer")

             # Clean up resources
             await self.cleanup_resources()

             # Archive logs
             await self.archive_logs()

             logger.info("Old frame-buffer successfully decommissioned")
     ```
   - **Quality Gate**: Zero data loss, clean shutdown
   - **Czas**: 1h

### Metryki sukcesu bloku 5
- Parallel deployment working
- Traffic gradually shifted (0% → 100%)
- All processors migrated successfully
- Old service safely decommissioned
- Zero downtime during migration

---

## Block 3.1: Service Integration & Pipeline Completion (NEW)

### Zadania atomowe

1. **[ ] Implementacja Face Recognition Processor z ProcessorClient**
   - **Metryka**: Face recognition service konsumuje klatki z frame-buffer-v2
   - **TDD Test Cases**:
     ```python
     # services/face-recognition/tests/test_processor.py
     async def test_face_recognition_processor():
         """Test face recognition processor implementation."""
         processor = FaceRecognitionProcessor(
             processor_id="face-recognition-1",
             orchestrator_url="http://localhost:8002",
             model_path="/models/face_recognition"
         )

         # Test frame processing
         frame_data = {
             b"frame_id": b"test_123",
             b"camera_id": b"cam01",
             b"image_data": base64.b64encode(test_image_bytes),
             b"width": b"1920",
             b"height": b"1080"
         }

         result = await processor.process_frame(frame_data)

         assert result["frame_id"] == "test_123"
         assert "faces" in result
         assert isinstance(result["faces"], list)

     async def test_face_embedding_extraction():
         """Test face embedding extraction."""
         processor = FaceRecognitionProcessor()

         # Load test image with known face
         test_image = load_test_face_image()

         faces = await processor.detect_and_extract(test_image)

         assert len(faces) > 0
         assert "embedding" in faces[0]
         assert len(faces[0]["embedding"]) == 512  # InsightFace embedding size
         assert "bbox" in faces[0]
         assert "confidence" in faces[0]
     ```
   - **Implementation**:
     ```python
     # services/face-recognition/src/main.py
     from base_processor import ProcessorClient
     import insightface
     import cv2
     import numpy as np

     class FaceRecognitionProcessor(ProcessorClient):
         def __init__(self, **kwargs):
             super().__init__(
                 capabilities=["face_detection", "face_recognition"],
                 result_stream="faces:detected",
                 **kwargs
             )
             self.model = insightface.app.FaceAnalysis(
                 name='buffalo_l',
                 providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
             )
             self.model.prepare(ctx_id=0, det_size=(640, 640))

         async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Dict:
             # Decode frame
             image_bytes = base64.b64decode(frame_data[b"image_data"])
             nparr = np.frombuffer(image_bytes, np.uint8)
             img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

             # Detect faces
             faces = self.model.get(img)

             return {
                 "frame_id": frame_data[b"frame_id"].decode(),
                 "camera_id": frame_data[b"camera_id"].decode(),
                 "faces": [
                     {
                         "bbox": face.bbox.tolist(),
                         "confidence": float(face.det_score),
                         "embedding": face.normed_embedding.tolist(),
                         "age": int(face.age) if hasattr(face, 'age') else None,
                         "gender": face.gender if hasattr(face, 'gender') else None
                     }
                     for face in faces
                 ],
                 "face_count": len(faces)
             }
     ```
   - **Validation Code**:
     ```bash
     # Test service locally
     cd services/face-recognition
     pytest tests/ -v

     # Build and run
     docker build -t face-recognition .
     docker run --gpus all -e ORCHESTRATOR_URL=http://frame-buffer-v2:8002 face-recognition

     # Verify registration
     curl http://localhost:8002/processors | jq '.[] | select(.id=="face-recognition-1")'
     ```
   - **Quality Gate**: GPU acceleration working, <100ms per frame, proper embedding extraction
   - **Czas**: 2h

2. **[ ] Implementacja Object Detection Processor z ProcessorClient**
   - **Metryka**: Object detection service z YOLO v8 konsumuje klatki
   - **TDD Test First**:
     ```python
     # services/object-detection/tests/test_processor.py
     async def test_object_detection_processor():
         """Test object detection with YOLO."""
         processor = ObjectDetectionProcessor(
             processor_id="object-detection-1",
             orchestrator_url="http://localhost:8002",
             model_name="yolov8n.pt"  # nano for tests
         )

         # Test with image containing person and car
         frame_data = {
             b"frame_id": b"test_456",
             b"camera_id": b"cam02",
             b"image_data": base64.b64encode(test_street_image),
             b"width": b"1920",
             b"height": b"1080"
         }

         result = await processor.process_frame(frame_data)

         assert result["frame_id"] == "test_456"
         assert "objects" in result
         assert len(result["objects"]) >= 2

         # Check object structure
         obj = result["objects"][0]
         assert "class" in obj
         assert "confidence" in obj
         assert "bbox" in obj
         assert len(obj["bbox"]) == 4  # x1, y1, x2, y2

     async def test_custom_detection_classes():
         """Test filtering specific object classes."""
         processor = ObjectDetectionProcessor(
             detect_classes=["person", "car", "bicycle"]
         )

         # Process frame
         result = await processor.process_frame(test_frame_data)

         # Verify only requested classes
         detected_classes = {obj["class"] for obj in result["objects"]}
         assert detected_classes.issubset({"person", "car", "bicycle"})
     ```
   - **Implementation**:
     ```python
     # services/object-detection/src/main.py
     from base_processor import ProcessorClient
     from ultralytics import YOLO
     import cv2
     import numpy as np

     class ObjectDetectionProcessor(ProcessorClient):
         def __init__(self, model_name="yolov8m.pt", detect_classes=None, **kwargs):
             super().__init__(
                 capabilities=["object_detection", "vehicle_detection", "person_detection"],
                 result_stream="objects:detected",
                 **kwargs
             )
             self.model = YOLO(model_name)
             self.detect_classes = detect_classes
             self.class_names = self.model.names

         async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Dict:
             # Decode image
             image_bytes = base64.b64decode(frame_data[b"image_data"])
             nparr = np.frombuffer(image_bytes, np.uint8)
             img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

             # Run inference
             results = self.model(img, stream=False, verbose=False)

             objects = []
             for r in results:
                 if r.boxes is not None:
                     for box in r.boxes:
                         cls = int(box.cls)
                         class_name = self.class_names[cls]

                         # Filter classes if specified
                         if self.detect_classes and class_name not in self.detect_classes:
                             continue

                         objects.append({
                             "class": class_name,
                             "confidence": float(box.conf),
                             "bbox": box.xyxy[0].tolist(),  # [x1, y1, x2, y2]
                             "track_id": int(box.id) if hasattr(box, 'id') else None
                         })

             return {
                 "frame_id": frame_data[b"frame_id"].decode(),
                 "camera_id": frame_data[b"camera_id"].decode(),
                 "objects": objects,
                 "object_count": len(objects)
             }
     ```
   - **Quality Gate**: GPU acceleration, <50ms inference time, accurate detections
   - **Czas**: 2h

3. **[ ] Migracja RTSP Capture do nowego frame flow**
   - **Metryka**: RTSP Capture publikuje klatki do Redis Stream z odpowiednim formatem
   - **TDD Test First**:
     ```python
     # services/rtsp-capture/tests/test_frame_publisher.py
     async def test_frame_publishing_format():
         """Test frame publishing to Redis Stream."""
         publisher = FramePublisher(redis_client)

         # Create test frame
         frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
         metadata = {
             "camera_id": "front_door",
             "motion_detected": True,
             "motion_score": 0.85
         }

         # Publish frame
         msg_id = await publisher.publish_frame(frame, metadata)

         # Verify in Redis
         messages = await redis_client.xread({"frames:captured": 0}, count=1)
         assert len(messages) > 0

         frame_data = messages[0][1][0][1]
         assert b"frame_id" in frame_data
         assert b"camera_id" in frame_data
         assert b"image_data" in frame_data
         assert b"width" in frame_data
         assert b"height" in frame_data
         assert b"timestamp" in frame_data
         assert b"trace_context" in frame_data

         # Verify trace context
         trace_ctx = json.loads(frame_data[b"trace_context"])
         assert "trace_id" in trace_ctx
         assert "span_id" in trace_ctx
     ```
   - **Implementation updates**:
     ```python
     # services/rtsp-capture/src/frame_publisher.py
     class FramePublisher:
         def __init__(self, redis_client, stream_name="frames:captured"):
             self.redis = redis_client
             self.stream = stream_name
             self.tracer = trace.get_tracer(__name__)

         async def publish_frame(self, frame: np.ndarray, metadata: Dict) -> str:
             """Publish frame to Redis Stream with proper format."""
             with self.tracer.start_as_current_span("publish_frame") as span:
                 # Generate frame ID
                 frame_id = f"{metadata['camera_id']}_{int(time.time()*1000000)}"

                 # Encode frame
                 _, buffer = cv2.imencode('.jpg', frame,
                     [cv2.IMWRITE_JPEG_QUALITY, 85])

                 # Prepare data
                 frame_data = {
                     "frame_id": frame_id,
                     "camera_id": metadata["camera_id"],
                     "timestamp": datetime.now().isoformat(),
                     "image_data": base64.b64encode(buffer).decode(),
                     "width": str(frame.shape[1]),
                     "height": str(frame.shape[0]),
                     "format": "jpeg",
                     "size_bytes": str(len(buffer)),
                     "metadata": json.dumps(metadata),
                     "trace_context": json.dumps({
                         "trace_id": format(span.get_span_context().trace_id, '032x'),
                         "span_id": format(span.get_span_context().span_id, '016x'),
                         "trace_flags": "01"
                     })
                 }

                 # Publish to stream
                 msg_id = await self.redis.xadd(self.stream, frame_data)

                 # Update metrics
                 frames_published.labels(camera_id=metadata["camera_id"]).inc()

                 return msg_id
     ```
   - **Quality Gate**: No frame loss, proper trace propagation, compatible format
   - **Czas**: 1.5h

4. **[ ] Home Assistant Bridge integration**
   - **Metryka**: HA Bridge konsumuje wyniki z procesorów i wysyła do HA
   - **TDD Test First**:
     ```python
     # services/ha-bridge/tests/test_result_consumer.py
     async def test_consume_detection_results():
         """Test consuming results from processors."""
         bridge = HABridge(
             ha_url="http://localhost:8123",
             result_streams=["faces:detected", "objects:detected"]
         )

         # Add test results to streams
         await redis.xadd("faces:detected", {
             "frame_id": "test_123",
             "camera_id": "front_door",
             "face_count": "2",
             "faces": json.dumps([
                 {"confidence": 0.95, "person_id": "john_doe"},
                 {"confidence": 0.88, "person_id": "unknown"}
             ])
         })

         # Process results
         events = await bridge.process_results()

         assert len(events) == 1
         assert events[0]["event_type"] == "detektor.face_detected"
         assert events[0]["camera_id"] == "front_door"
         assert events[0]["face_count"] == 2

     async def test_ha_event_publishing():
         """Test publishing events to Home Assistant."""
         bridge = HABridge()

         event = {
             "event_type": "detektor.person_detected",
             "camera_id": "front_door",
             "person_name": "John Doe",
             "confidence": 0.95
         }

         # Mock HA API
         with aioresponses() as m:
             m.post("http://localhost:8123/api/events/detektor.person_detected",
                    status=200)

             success = await bridge.publish_to_ha(event)

         assert success
         # Verify request was made with correct data
     ```
   - **Implementation**:
     ```python
     # services/ha-bridge/src/main.py
     class HABridge:
         def __init__(self, ha_url: str, ha_token: str, result_streams: List[str]):
             self.ha_url = ha_url
             self.ha_token = ha_token
             self.result_streams = result_streams
             self.redis = None
             self.consumer_groups = {}

         async def start(self):
             """Start consuming results and bridging to HA."""
             self.redis = await aioredis.from_url("redis://redis:6379")

             # Create consumer groups
             for stream in self.result_streams:
                 group_name = f"ha-bridge-{stream.replace(':', '-')}"
                 try:
                     await self.redis.xgroup_create(stream, group_name, id='0')
                 except aioredis.ResponseError:
                     pass
                 self.consumer_groups[stream] = group_name

             # Start consuming
             await self.consume_loop()

         async def consume_loop(self):
             """Main consumption loop."""
             while True:
                 try:
                     # Read from all streams
                     streams = {s: '>' for s in self.result_streams}
                     messages = await self.redis.xreadgroup(
                         "ha-bridge", "consumer-1",
                         streams,
                         count=10,
                         block=1000
                     )

                     for stream, stream_messages in messages:
                         for msg_id, data in stream_messages:
                             await self.process_result(stream.decode(), data)
                             await self.redis.xack(stream,
                                 self.consumer_groups[stream.decode()], msg_id)

                 except Exception as e:
                     logger.error(f"Error in consume loop: {e}")
                     await asyncio.sleep(1)
     ```
   - **Quality Gate**: All detection events reach HA, <100ms latency
   - **Czas**: 1.5h

5. **[ ] End-to-end integration tests**
   - **Metryka**: Pełny pipeline działa od kamery do Home Assistant
   - **TDD Test First**:
     ```python
     # tests/integration/test_full_pipeline.py
     @pytest.mark.integration
     async def test_complete_detection_pipeline():
         """Test full pipeline from camera to HA."""
         async with AsyncExitStack() as stack:
             # Start all services
             rtsp = await stack.enter_async_context(
                 start_service("rtsp-capture", env={"CAMERA_URL": "rtsp://test"})
             )

             fb_v2 = await stack.enter_async_context(
                 start_service("frame-buffer-v2")
             )

             face_proc = await stack.enter_async_context(
                 start_service("face-recognition",
                     env={"ORCHESTRATOR_URL": "http://frame-buffer-v2:8002"})
             )

             obj_proc = await stack.enter_async_context(
                 start_service("object-detection",
                     env={"ORCHESTRATOR_URL": "http://frame-buffer-v2:8002"})
             )

             ha_bridge = await stack.enter_async_context(
                 start_service("ha-bridge")
             )

             # Wait for services to initialize
             await asyncio.sleep(5)

             # Inject test frame to RTSP capture
             test_frame = load_test_image_with_faces_and_objects()
             await rtsp.inject_frame(test_frame, camera_id="test_cam")

             # Wait for processing
             await asyncio.sleep(3)

             # Verify results in HA
             ha_events = await ha_bridge.get_recent_events()

             # Should have both face and object detection events
             face_events = [e for e in ha_events
                           if e["event_type"] == "detektor.face_detected"]
             object_events = [e for e in ha_events
                            if e["event_type"] == "detektor.object_detected"]

             assert len(face_events) > 0
             assert len(object_events) > 0
             assert face_events[0]["camera_id"] == "test_cam"

     async def test_pipeline_performance():
         """Test pipeline meets performance requirements."""
         # Setup pipeline
         pipeline = await setup_test_pipeline()

         # Send 100 frames
         start_time = time.time()
         frame_ids = []

         for i in range(100):
             frame_id = await pipeline.inject_frame(
                 test_frame,
                 camera_id="perf_test"
             )
             frame_ids.append(frame_id)

         # Wait for all frames to be processed
         timeout = 30  # 30 seconds for 100 frames
         processed = await wait_for_frames_processed(frame_ids, timeout)

         elapsed = time.time() - start_time

         assert processed == 100
         assert elapsed < timeout

         # Calculate metrics
         fps = 100 / elapsed
         avg_latency = elapsed / 100

         print(f"Pipeline FPS: {fps:.2f}")
         print(f"Average latency: {avg_latency*1000:.2f}ms")

         assert fps > 10  # At least 10 FPS
         assert avg_latency < 0.5  # Less than 500ms per frame
     ```
   - **Quality Gate**: Full pipeline working, no frame loss, <500ms end-to-end latency
   - **Czas**: 2h

6. **[ ] Decommission stary frame-buffer**
   - **Metryka**: Stary frame-buffer bezpiecznie wyłączony
   - **TDD Test First**:
     ```python
     # tests/migration/test_decommission.py
     async def test_old_frame_buffer_decommission():
         """Test safe decommission of old frame-buffer."""
         # Verify no services depend on old API
         dependents = await find_services_using_endpoint("/frames/dequeue")
         assert len(dependents) == 0, f"Services still using old API: {dependents}"

         # Verify new frame-buffer handles all traffic
         fb_v2_metrics = await get_service_metrics("frame-buffer-v2")
         assert fb_v2_metrics["frames_routed_total"] > 0

         # Check old frame-buffer can be stopped
         old_fb = get_service("frame-buffer")
         if old_fb.is_running():
             await old_fb.stop()
             await asyncio.sleep(5)

             # Verify pipeline still works
             test_frame_id = await inject_test_frame()
             result = await wait_for_frame_processed(test_frame_id, timeout=10)
             assert result is not None
     ```
   - **Implementation**:
     ```yaml
     # docker-compose.yml updates
     services:
       # frame-buffer:  # REMOVED - replaced by frame-buffer-v2
       #   image: ghcr.io/hretheum/detektr/frame-buffer:latest

       frame-buffer-v2:
         image: ghcr.io/hretheum/detektr/frame-buffer:2.0
         container_name: frame-buffer  # Take over the name
         ports:
           - "8002:8002"
         environment:
           - INPUT_STREAM=frames:captured
           - CONSUMER_GROUP=frame-buffer-group
     ```
   - **Validation**:
     ```bash
     # Stop old frame-buffer
     docker-compose stop frame-buffer

     # Verify pipeline still works
     ./scripts/test-pipeline.sh

     # Remove old service
     docker-compose rm -f frame-buffer

     # Update compose file
     sed -i '/frame-buffer:/,/^[[:space:]]*$/d' docker-compose.yml
     ```
   - **Quality Gate**: Zero downtime, no service disruption
   - **Czas**: 1h

### Metryki sukcesu bloku 3.1
- Face recognition processor consuming frames via ProcessorClient
- Object detection processor with YOLO v8 working
- RTSP capture publishing to Redis Stream with proper format
- HA Bridge consuming and forwarding events
- Full pipeline operational with <500ms latency
- Old frame-buffer safely decommissioned

### Validation Script
```bash
#!/bin/bash
# scripts/validate-pipeline.sh

echo "Validating Detektor Pipeline..."

# Check all services are healthy
for service in rtsp-capture frame-buffer-v2 face-recognition object-detection ha-bridge; do
    echo -n "Checking $service... "
    if curl -sf "http://localhost:$(docker port $service 8080 | cut -d: -f2)/health" > /dev/null; then
        echo "OK"
    else
        echo "FAILED"
        exit 1
    fi
done

# Check processor registration
echo -n "Checking processor registrations... "
PROCESSORS=$(curl -s http://localhost:8002/processors | jq -r '.[].id')
if [[ "$PROCESSORS" == *"face-recognition"* ]] && [[ "$PROCESSORS" == *"object-detection"* ]]; then
    echo "OK"
else
    echo "FAILED - Missing processors"
    exit 1
fi

# Test frame flow
echo "Testing frame flow..."
FRAME_ID=$(date +%s%N)
redis-cli XADD frames:captured frame_id "$FRAME_ID" camera_id "test" image_data "base64data" > /dev/null

sleep 3

# Check if frame was processed
if redis-cli XRANGE faces:detected - + | grep -q "$FRAME_ID"; then
    echo "✓ Face detection working"
else
    echo "✗ Face detection not working"
fi

if redis-cli XRANGE objects:detected - + | grep -q "$FRAME_ID"; then
    echo "✓ Object detection working"
else
    echo "✗ Object detection not working"
fi

echo "Pipeline validation complete!"
```

---

## Overall Success Metrics

### Performance
- ✅ Handle 100+ fps sustained load
- ✅ <10ms routing decision latency
- ✅ <100ms end-to-end frame processing

### Reliability
- ✅ Zero frame loss under normal operation
- ✅ Graceful degradation under overload
- ✅ Automatic recovery from failures

### Scalability
- ✅ Support 50+ concurrent processors
- ✅ Horizontal scaling of orchestrators
- ✅ Linear performance scaling

### Observability
- ✅ Complete trace for every frame
- ✅ Real-time metrics and dashboards
- ✅ Proactive alerting on issues

## Risk Mitigation

| Risk | Mitigation | Monitoring |
|------|------------|------------|
| Performance regression | Benchmark tests in CI | P95 latency alerts |
| Message loss | Consumer groups, ACKs | Lost frame counter |
| Processor failures | Circuit breakers | Health check alerts |
| Migration issues | Gradual rollout | A/B metrics |

## Timeline Summary

- **Block 0**: 4h (Setup & Prerequisites)
- **Block 1**: 7.5h (Core Orchestrator)
- **Block 2**: 7h (Event-Driven Pipeline)
- **Block 3**: 6.5h (Advanced Features)
- **Block 4**: 7.5h (Production Hardening)
- **Block 5**: 6h (Migration)

**Total**: ~38.5h (approximately 5-6 days of focused work)

## Next Steps

After completing this implementation:
1. Deploy to staging environment
2. Run load tests with production-like traffic
3. Gradual rollout to production
4. Monitor metrics and traces
5. Optimize based on real-world usage
