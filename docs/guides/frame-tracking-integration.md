# Frame Tracking Integration Guide

This guide explains how to integrate the frame-tracking library into your services in the Detektor system.

## Overview

Frame tracking provides distributed tracing capabilities for tracking frames through the entire processing pipeline. It consists of two components:

1. **Frame-tracking Service** (port 8081) - Event sourcing for frame lifecycle audit
2. **Frame-tracking Library** (`services/shared/frame-tracking`) - Distributed tracing with OpenTelemetry

## Library Installation

### In Dockerfile

```dockerfile
# Copy shared libraries
COPY services/shared /app/services/shared

# Install frame-tracking library
RUN pip install -e /app/services/shared/frame-tracking
```

### In requirements.txt

```txt
# Local frame-tracking library
-e /app/services/shared/frame-tracking
```

## Basic Usage

### 1. Import and Check Availability

```python
# Graceful import with fallback
try:
    from frame_tracking import FrameID, FrameMetadata, TraceContext
    FRAME_TRACKING_AVAILABLE = True
except ImportError:
    FRAME_TRACKING_AVAILABLE = False
    print("Frame tracking not available - running without distributed tracing")
```

### 2. Generate Frame IDs

```python
if FRAME_TRACKING_AVAILABLE:
    frame_id = FrameID.generate(camera_id="cam01", source="rtsp-capture")
else:
    # Fallback ID generation
    frame_id = f"{datetime.now().isoformat()}_{camera_id}_{uuid.uuid4().hex[:8]}"
```

### 3. Create and Use Trace Context

```python
if FRAME_TRACKING_AVAILABLE:
    with TraceContext.inject(frame_id) as ctx:
        ctx.add_event("processing_started")
        ctx.set_attribute("camera.id", camera_id)
        ctx.set_attribute("frame.size", len(frame_data))

        # Process frame
        result = process_frame(frame_data)

        # Propagate context to next service
        ctx.inject_to_carrier(result)
else:
    # Process without tracing
    result = process_frame(frame_data)
```

## Integration Patterns

### Pattern 1: Service with Redis Queue

```python
from redis import Redis
from frame_tracking import TraceContext

redis_client = Redis(host="redis", port=6379)

async def enqueue_frame(frame_data: dict):
    if FRAME_TRACKING_AVAILABLE:
        with TraceContext.inject(frame_data.get("frame_id", "unknown")) as ctx:
            ctx.add_event("frame_enqueued")
            ctx.set_attribute("queue.name", "frame_buffer")

            # Inject trace context into message
            ctx.inject_to_carrier(frame_data)

    # Send to Redis
    redis_client.xadd("frames:queue", frame_data)

async def dequeue_frame():
    # Read from Redis
    messages = redis_client.xread({"frames:queue": "$"}, block=1000)

    for stream, items in messages:
        for msg_id, data in items:
            if FRAME_TRACKING_AVAILABLE:
                # Extract trace context from message
                with TraceContext.extract_from_carrier(data) as ctx:
                    ctx.add_event("frame_dequeued")
                    process_frame(data, ctx)
            else:
                process_frame(data, None)
```

### Pattern 2: Base Processor Integration

```python
from base_processor import BaseProcessor

class MyProcessor(BaseProcessor):
    async def process_frame(self, frame: np.ndarray, metadata: dict):
        # Your processing logic
        result = await detect_objects(frame)

        # Base processor handles trace context automatically
        # if you use process_frame_with_tracking
        return result

# Usage
processor = MyProcessor(name="object-detector")

# With automatic tracing
result = await processor.process_frame_with_tracking(frame, metadata, frame_id)
```

### Pattern 3: HTTP Service Integration

```python
from fastapi import FastAPI, Header
from frame_tracking import TraceContext

app = FastAPI()

@app.post("/process")
async def process_frame(
    data: dict,
    traceparent: Optional[str] = Header(None)
):
    if FRAME_TRACKING_AVAILABLE and traceparent:
        # Extract context from HTTP header
        with TraceContext.extract_from_header(traceparent) as ctx:
            ctx.add_event("http_request_received")
            result = await process(data)

            # Add trace header to response
            return JSONResponse(
                content=result,
                headers={"traceparent": ctx.to_header()}
            )
    else:
        return await process(data)
```

## Complete Example: Frame Buffer Service

```python
import asyncio
from typing import Optional
from datetime import datetime
from fastapi import FastAPI
from redis import Redis

try:
    from frame_tracking import FrameID, TraceContext
    FRAME_TRACKING_AVAILABLE = True
except ImportError:
    FRAME_TRACKING_AVAILABLE = False

app = FastAPI()
redis_client = Redis(host="redis", port=6379)

@app.post("/enqueue")
async def enqueue_frame(frame_data: dict):
    # Generate or use existing frame ID
    frame_id = frame_data.get("frame_id")
    if not frame_id and FRAME_TRACKING_AVAILABLE:
        frame_id = FrameID.generate(camera_id=frame_data.get("camera_id", "unknown"))
        frame_data["frame_id"] = frame_id

    # Add to queue with tracing
    if FRAME_TRACKING_AVAILABLE:
        with TraceContext.inject(frame_id) as ctx:
            ctx.add_event("frame_buffer_enqueue")
            ctx.set_attribute("buffer.size", get_queue_size())
            ctx.inject_to_carrier(frame_data)

    redis_client.xadd("frames:queue", frame_data)
    return {"status": "enqueued", "frame_id": frame_id}

@app.get("/dequeue")
async def dequeue_frame():
    messages = redis_client.xread({"frames:queue": "$"}, count=1, block=1000)

    if not messages:
        return {"status": "empty"}

    for stream, items in messages:
        for msg_id, data in items:
            if FRAME_TRACKING_AVAILABLE:
                with TraceContext.extract_from_carrier(data) as ctx:
                    ctx.add_event("frame_buffer_dequeue")
                    return {"frame": data, "trace_id": ctx.trace_id}
            else:
                return {"frame": data}
```

## Trace Context Propagation

### Through Redis Streams

```python
# Producer
ctx.inject_to_carrier(message_dict)  # Adds _traceparent field
redis_client.xadd("stream", message_dict)

# Consumer
data = redis_client.xread(...)
with TraceContext.extract_from_carrier(data) as ctx:
    # Context restored from _traceparent field
    pass
```

### Through HTTP Headers

```python
# Client
headers = {"traceparent": ctx.to_header()}
response = requests.post(url, json=data, headers=headers)

# Server
traceparent = request.headers.get("traceparent")
with TraceContext.extract_from_header(traceparent) as ctx:
    pass
```

### Through Message Metadata

```python
# Add to metadata
metadata["trace_context"] = {
    "trace_id": ctx.trace_id,
    "span_id": ctx.span_id,
    "traceparent": ctx.to_header()
}

# Restore from metadata
trace_data = metadata.get("trace_context", {})
with TraceContext.from_dict(trace_data) as ctx:
    pass
```

## Debugging and Monitoring

### View Traces in Jaeger

1. Open Jaeger UI: http://nebula:16686
2. Select your service from dropdown
3. Search by frame ID using tag: `frame.id=<your_frame_id>`

### Check Service Integration

```bash
# Verify library is installed
docker exec <service_name> python -c "import frame_tracking; print('OK')"

# Check if service is sending traces
curl -s "http://nebula:16686/api/services" | grep <service_name>

# Find traces with frame IDs
curl -s "http://nebula:16686/api/traces?service=<service_name>&limit=10" | \
  jq '.[].spans[].tags[] | select(.key == "frame.id")'
```

### Common Issues

1. **ImportError: No module named 'frame_tracking'**
   - Ensure library is copied in Dockerfile
   - Check pip install command includes `-e /app/services/shared/frame-tracking`

2. **No traces in Jaeger**
   - Verify OTEL environment variables are set
   - Check service can reach Jaeger collector
   - Ensure `OTEL_SDK_DISABLED` is not set to true

3. **Trace context not propagating**
   - Check `_traceparent` field in Redis messages
   - Verify HTTP `traceparent` header is being passed
   - Use debug logging to trace context flow

## Best Practices

1. **Always use graceful degradation** - Service should work without frame-tracking
2. **Add meaningful events** - Use `ctx.add_event()` for important operations
3. **Set relevant attributes** - Add service-specific attributes for debugging
4. **Propagate context** - Always pass context to downstream services
5. **Use consistent frame IDs** - Generate once, use everywhere

## Performance Considerations

- Overhead: <1ms per operation
- Memory: ~1KB per active trace context
- Network: One HTTP call per span batch (async)
- Storage: ~2KB per trace in Jaeger

## Further Reading

- [OpenTelemetry Python Docs](https://opentelemetry-python.readthedocs.io/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
