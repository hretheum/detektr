# Frame Buffer Architectural Issue

**Date Discovered**: 2025-01-27
**Severity**: Critical
**Impact**: 100% frame loss after buffer fills

## Problem Description

Frame buffer service has been enhanced with an active consumer that reads from Redis Stream, but the architecture is incomplete. The consumer successfully reads frames and buffers them in memory, but no downstream service consumes frames FROM the buffer, creating a dead-end in the pipeline.

## Current Architecture

```
┌──────────────┐     Redis Stream      ┌─────────────────┐
│ RTSP Capture │ ──────────────────> │  Frame Buffer   │
└──────────────┘   frames:metadata    │                 │
                                      │ ┌─────────────┐ │
                                      │ │  Consumer   │ │
                                      │ │  (Active)   │ │
                                      │ └──────┬──────┘ │
                                      │        ↓        │
                                      │ ┌─────────────┐ │
                                      │ │Memory Buffer│ │
                                      │ │ (Size:1000) │ │
                                      │ └─────────────┘ │
                                      └─────────────────┘
                                               ↓
                                               ❌
                                        (No consumer!)
```

## Symptoms

1. **Logs**:
   ```
   Buffer full, dropping frame 1753608701224_rtsp-capture_default_6258_ccade578
   Buffer full, dropping frame 1753608701327_rtsp-capture_default_6259_670cce53
   ```

2. **Metrics**:
   - `frame_buffer_consumer_frames_consumed_total`: Increasing (e.g., 1000)
   - `frame_buffer_consumer_frames_dropped_total`: Rapidly increasing
   - Buffer status: `{"size": 0, "max_size": 1000}` (misleading - actually full)

3. **Redis Stream**:
   - `frames:metadata` continues growing (10,000+ messages)
   - No secondary stream for buffered frames

## Root Cause

The frame-buffer service was designed with two interfaces:
- **Input**: Consumer reads from Redis Stream ✅ (implemented)
- **Output**: REST API for processors to pull frames ❌ (not integrated)

Sample-processor and other AI services are not configured to pull frames from the frame-buffer REST API (`GET /frames/dequeue`).

## Temporary Workarounds

### 1. Stop Frame Production
```bash
docker stop detektr-rtsp-capture-1
```

### 2. Clear Buffer (Data Loss!)
```bash
curl -X POST http://nebula:8002/buffer/clear
```

### 3. Monitor Buffer Status
```bash
watch -n 1 'curl -s http://nebula:8002/frames/status | jq .'
```

## Permanent Solutions

### Option 1: Configure Processors to Pull from API
Modify processors to periodically call frame-buffer API:
```python
# In processor main loop
async def consume_frames():
    while True:
        response = await http_client.get("http://frame-buffer:8002/frames/dequeue?count=10")
        frames = response.json()["frames"]
        for frame in frames:
            await process_frame(frame)
```

### Option 2: Add Publisher to Frame Buffer
After buffering, publish to new stream:
```python
# In frame_buffer consumer
await self.frame_buffer.put(frame_data)
await self.redis.xadd("frames:buffered", frame_data)
```

### Option 3: Remove Frame Buffer
Let processors consume directly from `frames:metadata`:
- Simpler architecture
- Less latency
- But loses buffering benefits

## Monitoring Commands

```bash
# Check buffer metrics
curl -s http://nebula:8002/metrics | grep frame_buffer

# Check Redis streams
docker exec detektr-redis-1 redis-cli XLEN frames:metadata

# Watch consumer errors
docker logs -f detektr-frame-buffer-1 2>&1 | grep -E "Error|dropping"
```

## Related Files

- `/services/frame-buffer/src/consumer.py` - Consumer implementation
- `/services/frame-buffer/src/main.py` - Service setup
- `/services/sample-processor/` - Needs modification to consume from buffer
- `/docs/ARCHITECTURE.md` - Shows intended flow (needs update)
