# Phase 2 Quality Requirements & Standards

## 🔴 MANDATORY Quality Gates (od Fazy 2)

### 1. API Documentation (OpenAPI/Swagger)
**Każdy nowy endpoint MUSI mieć:**
```python
from fastapi import FastAPI, APIRouter, Depends
from pydantic import BaseModel, Field

class RTSPStreamRequest(BaseModel):
    """Request model for RTSP stream configuration"""
    stream_url: str = Field(..., description="RTSP stream URL", example="rtsp://192.168.1.100:554/stream1")
    camera_id: str = Field(..., description="Unique camera identifier", example="cam_front_door")
    fps_limit: int = Field(30, description="Maximum FPS to capture", ge=1, le=60)

@router.post(
    "/streams/connect",
    response_model=StreamConnectionResponse,
    summary="Connect to RTSP stream",
    description="Establishes connection to RTSP camera stream and starts frame capture",
    responses={
        200: {"description": "Successfully connected to stream"},
        400: {"description": "Invalid stream URL or parameters"},
        503: {"description": "Unable to connect to stream"}
    },
    tags=["streams"]
)
async def connect_stream(
    request: RTSPStreamRequest,
    service: RTSPService = Depends(get_rtsp_service)
) -> StreamConnectionResponse:
    """Connect to RTSP stream and begin frame capture."""
    return await service.connect(request)
```

### 2. Architectural Decision Records (ADRs)
**Template dla każdej decyzji:**
```markdown
# ADR-2025-01-20: Use Redis Streams for Frame Queue

## Status
Accepted

## Context
We need a message queue for frame distribution between services.

## Decision
Use Redis Streams instead of Kafka/RabbitMQ.

## Consequences
- ✅ Simpler deployment (already using Redis)
- ✅ Built-in consumer groups
- ✅ Automatic backpressure
- ❌ Less ecosystem than Kafka
- ❌ Single point of failure without cluster
```

### 3. Performance Baselines
**Każda operacja MUSI mieć baseline:**
```python
# tests/performance/test_rtsp_baseline.py
@pytest.mark.benchmark
async def test_frame_capture_baseline(benchmark_manager):
    baseline = await benchmark_manager.measure_operation(
        "rtsp_frame_capture",
        lambda: rtsp_service.capture_frame(),
        iterations=100
    )

    assert baseline.p95_ms < 33  # 30 FPS = 33ms per frame
    assert baseline.throughput_rps > 25  # At least 25 FPS

    # Save to baselines.json for regression detection
    benchmark_manager.save_baseline(baseline)
```

### 4. Method Complexity Limits
**Automatic refactoring gdy >30 linii:**
```python
# BAD: 50+ line method
async def process_rtsp_stream(self, url: str):
    # 50+ lines of mixed concerns...

# GOOD: Decomposed methods
async def process_rtsp_stream(self, url: str):
    """Orchestrate RTSP stream processing"""
    async with self._stream_context(url) as stream:
        config = await self._validate_stream_config(stream)
        capture = await self._initialize_capture(stream, config)

        async for frame in self._capture_frames(capture):
            await self._process_frame(frame)
```

### 5. Test-First Development
**Test PRZED kodem:**
```python
# KROK 1: Napisz test
async def test_rtsp_connection_with_invalid_url():
    service = RTSPService()

    with pytest.raises(InvalidStreamURLError):
        await service.connect("not-a-valid-url")

# KROK 2: Implementuj minimalny kod żeby test przeszedł
# KROK 3: Refactor
```

### 6. Correlation IDs
**Każdy request/operation:**
```python
from opentelemetry import baggage

async def capture_frame(self, stream_id: str):
    correlation_id = baggage.get_baggage("correlation_id") or str(uuid4())
    baggage.set_baggage("correlation_id", correlation_id)

    logger.info(
        "Capturing frame",
        extra={
            "correlation_id": correlation_id,
            "stream_id": stream_id
        }
    )
```

### 7. Feature Flags
**Dla features >1 dzień pracy:**
```python
from src.shared.feature_flags import feature_flag

@feature_flag("enable_gpu_decoding", default=False)
async def decode_frame(self, frame_data: bytes):
    if self.feature_flags.is_enabled("enable_gpu_decoding"):
        return await self._gpu_decode(frame_data)
    else:
        return await self._cpu_decode(frame_data)
```

## 🟡 Additional Requirements for Phase 2

### Frame Buffer Requirements
- Redis Streams for frame queue
- 30-second buffer per camera
- Automatic cleanup of old frames
- Backpressure handling

### RTSP Connection Management
- Automatic reconnection with exponential backoff
- Connection pooling for multiple cameras
- Health checks every 30s
- Graceful degradation on connection loss

### Monitoring Requirements
- Frame capture rate metric
- Connection stability metric
- Buffer utilization metric
- Decode performance metric

## 📋 Phase 2 Specific Checklist

- [ ] RTSP Service with OpenAPI docs
- [ ] ADR: Why OpenCV vs GStreamer
- [ ] ADR: Frame buffer size decisions
- [ ] Performance baselines for 1080p@30fps
- [ ] Connection retry logic with tests
- [ ] Correlation IDs in all frame events
- [ ] Feature flag for GPU acceleration
- [ ] Dashboard: Frame Pipeline Monitoring
- [ ] Alerts: Connection loss, buffer overflow

## 🚀 Quick Start for Phase 2

1. Copy this template for each service
2. Write tests FIRST
3. Document API BEFORE implementation
4. Measure performance IMMEDIATELY
5. Create ADR for EACH major decision

## 🏭 Production Deployment Requirements

### Deployment Quality Gates
**Każdy serwis MUSI spełnić przed deployment na Nebula:**

1. **CI/CD Pipeline Success**
   ```bash
   # All checks must pass
   - Unit tests: 100% pass rate
   - Integration tests: 100% pass rate
   - Docker build: Success
   - Security scan: No critical vulnerabilities
   ```

2. **Health Check Endpoint**
   ```python
   @app.get("/health", response_model=HealthResponse)
   async def health_check():
       return {
           "status": "healthy",
           "timestamp": datetime.utcnow(),
           "version": settings.VERSION,
           "checks": {
               "database": await check_db_connection(),
               "redis": await check_redis_connection(),
               "dependencies": await check_external_deps()
           }
       }
   ```

3. **Production Configuration**
   ```yaml
   # docker-compose.prod.yml
   services:
     rtsp-capture:
       image: ghcr.io/hretheum/detektr/rtsp-capture:latest
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
         interval: 30s
         timeout: 10s
         retries: 3
       environment:
         - LOG_LEVEL=INFO
         - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
   ```

### Production Validation Checklist
**Po deployment na Nebula:**

```bash
# 1. Service health
ssh nebula "curl -s http://localhost:8001/health | jq"

# 2. Metrics available
ssh nebula "curl -s http://localhost:9090/api/v1/query?query=up{job='rtsp-capture'}"

# 3. Traces visible
ssh nebula "curl -s http://localhost:16686/api/traces?service=rtsp-capture"

# 4. Logs flowing
ssh nebula "docker logs rtsp-capture --tail 50"

# 5. Resource usage acceptable
ssh nebula "docker stats rtsp-capture --no-stream"
```

### Rollback Plan
**Każdy deployment MUSI mieć:**

1. **Previous version tag saved**
   ```bash
   export PREVIOUS_VERSION=$(ssh nebula "docker inspect rtsp-capture --format='{{.Config.Image}}' | cut -d: -f2")
   ```

2. **Quick rollback script**
   ```bash
   # scripts/rollback-service.sh
   SERVICE=$1
   VERSION=$2
   ssh nebula "docker pull ghcr.io/hretheum/detektr/${SERVICE}:${VERSION}"
   ssh nebula "docker stop ${SERVICE} && docker rm ${SERVICE}"
   ssh nebula "cd /opt/detektor && docker-compose up -d ${SERVICE}"
   ```

3. **Validation after rollback**
   ```bash
   ssh nebula "curl -s http://localhost:8001/health | jq '.status'"
   # Should return "healthy"
   ```

### Performance Guardrails for Production
**Limity które nie mogą być przekroczone:**

- CPU usage: <80% sustained
- Memory: <2GB per service
- Response time p99: <100ms
- Error rate: <0.1%
- Restart frequency: <1 per hour

**Monitoring:**
```bash
# Alert configuration
- name: HighCPUUsage
  expr: rate(container_cpu_usage_seconds_total[5m]) > 0.8
  for: 5m
  annotations:
    summary: "High CPU usage for {{ $labels.container_name }}"
```
