# ProcessorClient Migration Guide

## Overview

This guide explains how to migrate existing processor services from the old polling/direct Redis approach to the new ProcessorClient pattern introduced in frame-buffer-v2.

## What is ProcessorClient?

ProcessorClient is a base class that provides:
- Automatic registration with the frame-buffer-v2 orchestrator
- Dedicated Redis Stream queue per processor
- Built-in health reporting
- Automatic trace context propagation
- Graceful shutdown handling
- Connection retry logic

## Migration Steps

### 1. Update Service Dependencies

Add the ProcessorClient to your service:

```python
# services/<your-service>/src/main.py
from services.frame-buffer-v2.src.processors.client import ProcessorClient
```

### 2. Refactor Your Service Class

Transform your service from polling pattern to ProcessorClient:

**Before (Polling Pattern):**
```python
class FaceRecognitionService:
    def __init__(self):
        self.redis = redis.Redis()
        self.model = load_model()

    async def run(self):
        while True:
            # Poll for frames
            response = requests.get("http://frame-buffer:8002/frames/dequeue")
            frames = response.json()["frames"]

            for frame in frames:
                result = self.process_frame(frame)
                self.publish_result(result)

            await asyncio.sleep(0.1)
```

**After (ProcessorClient Pattern):**
```python
class FaceRecognitionProcessor(ProcessorClient):
    def __init__(self):
        super().__init__(
            processor_id="face-recognition-1",
            capabilities=["face_detection", "face_recognition"],
            orchestrator_url=os.getenv("ORCHESTRATOR_URL", "http://frame-buffer-v2:8002"),
            capacity=10,
            result_stream="faces:detected"
        )
        self.model = None

    async def start(self):
        # Load model before starting
        self.model = await self.load_model()
        await super().start()

    async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Dict:
        """Process a single frame - this is the only method you need to implement."""
        # Extract frame data
        frame_id = frame_data[b"frame_id"].decode()
        image_data = base64.b64decode(frame_data[b"image_data"])

        # Your processing logic here
        faces = await self.detect_faces(image_data)

        # Return results
        return {
            "frame_id": frame_id,
            "faces_detected": len(faces),
            "faces": faces,
            "processor_id": self.processor_id,
            "timestamp": time.time()
        }

    async def load_model(self):
        # Your model loading logic
        return load_face_detection_model()

    async def detect_faces(self, image_data):
        # Your face detection logic
        return self.model.detect(image_data)
```

### 3. Update Docker Compose Configuration

**Before:**
```yaml
services:
  face-recognition:
    image: ghcr.io/hretheum/detektr/face-recognition:latest
    environment:
      - FRAME_BUFFER_URL=http://frame-buffer:8002
      - POLL_INTERVAL=0.1
```

**After:**
```yaml
services:
  face-recognition:
    image: ghcr.io/hretheum/detektr/face-recognition:latest
    environment:
      - ORCHESTRATOR_URL=http://frame-buffer-v2:8002
      - PROCESSOR_ID=face-recognition-1
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      frame-buffer-v2:
        condition: service_healthy
```

### 4. Update Main Entry Point

**Before:**
```python
if __name__ == "__main__":
    service = FaceRecognitionService()
    asyncio.run(service.run())
```

**After:**
```python
if __name__ == "__main__":
    processor = FaceRecognitionProcessor()

    # Handle graceful shutdown
    def signal_handler(signum, frame):
        processor.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    asyncio.run(processor.start())
```

## ProcessorClient API Reference

### Constructor Parameters

```python
ProcessorClient(
    processor_id: str,           # Unique identifier for this processor instance
    capabilities: List[str],     # List of processing capabilities
    orchestrator_url: str,       # URL of frame-buffer-v2 orchestrator
    capacity: int = 10,         # Max concurrent processing tasks
    redis_client: Optional = None,  # Existing Redis client (optional)
    redis_url: str = "redis://localhost:6379",  # Redis connection URL
    result_stream: Optional[str] = None,  # Stream for publishing results
    health_port: Optional[int] = None,    # Port for health endpoint
    health_check_interval: float = 30.0   # Health reporting interval
)
```

### Required Method to Implement

```python
async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Optional[Dict]:
    """Process a single frame.

    Args:
        frame_data: Frame data from Redis (keys and values are bytes)

    Returns:
        Processing result dictionary or None
    """
    pass
```

### Frame Data Format

The `frame_data` dictionary contains:
- `b"frame_id"`: Unique frame identifier
- `b"camera_id"`: Source camera identifier
- `b"timestamp"`: ISO format timestamp
- `b"image_data"`: Base64 encoded image data
- `b"width"`: Frame width in pixels
- `b"height"`: Frame height in pixels
- `b"format"`: Image format (e.g., "jpeg")
- `b"metadata"`: JSON string with additional metadata
- `b"trace_context"`: JSON string with OpenTelemetry trace context

## Benefits of ProcessorClient

1. **Automatic Registration**: No need to manually register with orchestrator
2. **Health Monitoring**: Built-in health reporting and circuit breaker support
3. **Load Balancing**: Orchestrator distributes frames based on processor capacity
4. **Trace Propagation**: Automatic OpenTelemetry context propagation
5. **Error Handling**: Built-in retry logic and graceful degradation
6. **Resource Management**: Automatic connection pooling and cleanup

## Common Migration Issues

### Issue 1: Missing ProcessorClient Import
**Solution**: Ensure frame-buffer-v2 is deployed and add it to Python path or copy the client.py file to shared libraries.

### Issue 2: Frame Format Differences
**Solution**: Use the provided byte keys (e.g., `frame_data[b"frame_id"]`) and decode as needed.

### Issue 3: Result Publishing
**Solution**: Return results from `process_frame()` - ProcessorClient handles publishing to the configured result stream.

### Issue 4: Health Endpoint Conflicts
**Solution**: Either use ProcessorClient's built-in health endpoint or integrate your existing health checks.

## Testing Your Migration

1. **Unit Tests**: Mock the ProcessorClient base class
```python
@patch('services.frame_buffer_v2.src.processors.client.ProcessorClient')
async def test_face_detection(mock_client):
    processor = FaceRecognitionProcessor()
    result = await processor.process_frame({
        b"frame_id": b"test_123",
        b"image_data": b"base64_encoded_image"
    })
    assert result["faces_detected"] >= 0
```

2. **Integration Tests**: Use docker-compose to test full pipeline
```bash
docker-compose up frame-buffer-v2 redis face-recognition
# In another terminal
python scripts/inject_test_frame.py
# Check results
redis-cli XREAD STREAMS faces:detected 0
```

3. **Load Tests**: Verify performance under load
```bash
# Inject many frames
for i in {1..1000}; do
    python scripts/inject_frame.py --camera-id test --rate 30
done

# Monitor processing
watch 'docker logs face-recognition --tail 20'
```

## Processor Service Examples

### Face Recognition
- **Capabilities**: ["face_detection", "face_recognition"]
- **Result Stream**: "faces:detected"
- **Capacity**: 10 (GPU limited)

### Object Detection
- **Capabilities**: ["object_detection", "yolo_v8"]
- **Result Stream**: "objects:detected"
- **Capacity**: 8 (batch processing)

### Gesture Detection
- **Capabilities**: ["gesture_detection", "hand_tracking"]
- **Result Stream**: "gestures:detected"
- **Capacity**: 5 (complex processing)

## Phase-Specific Updates

### Phase 3: AI Services
All services in this phase should use ProcessorClient:
- face-recognition-service
- object-detection (YOLO)
- gesture-detection (future)

### Phase 4: Integration
Services that process detection results:
- ha-bridge (consumes from result streams)
- automation-engine (reacts to events)

### Phase 5: Advanced AI
New processors following the pattern:
- voice-processor
- llm-intent-processor

### Phase 6: Optimization
Performance improvements to ProcessorClient itself:
- Dynamic capacity adjustment
- Predictive frame routing
- GPU-aware scheduling

## Rollback Plan

If issues arise with ProcessorClient:

1. **Quick Fix**: Increase `health_check_interval` and reduce `capacity`
2. **Temporary Rollback**:
   - Keep ProcessorClient registration but add polling fallback
   - Monitor both paths and gradually migrate traffic
3. **Full Rollback**:
   - Revert to previous service version
   - Update docker-compose to use old environment variables
   - Ensure frame-buffer (v1) is still running

## Next Steps

1. Start with sample-processor as reference implementation
2. Migrate one service at a time
3. Run services in parallel during migration
4. Monitor metrics and traces
5. Gradually decommission old polling endpoints
