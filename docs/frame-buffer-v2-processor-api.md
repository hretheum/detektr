# Frame Buffer v2 - Processor API Requirements

## Current Status

Frame Buffer v2 has processor registration endpoints:
- `/api/v1/processors/register` - Register processor
- `/api/v1/processors/` - List processors
- `/api/v1/processors/{processor_id}` - Get processor details
- `/api/v1/processors/search/` - Search processors

However, sample-processor is still using old polling pattern (`/frames/dequeue`) which doesn't exist in Frame Buffer v2.

## Required Changes

### 1. Frame Buffer v2 Must Distribute Frames

Frame Buffer v2 needs to:
1. Accept processor registrations ✅ (already has API)
2. Distribute frames to registered processors ❌ (missing)
3. Track processor health/heartbeat ❌ (missing)

Currently, Frame Buffer v2 only consumes from `frames:metadata` but doesn't distribute to processor-specific queues.

### 2. Distribution Mechanism

When Frame Buffer v2 receives a frame from `frames:metadata`, it should:

```python
async def distribute_frame(self, frame_data: dict):
    """Distribute frame to appropriate processor."""
    # 1. Select processor based on capabilities/load
    processor = await self.select_processor(frame_data)

    # 2. Publish to processor's dedicated queue
    processor_queue = f"frames:ready:{processor.id}"
    await self.redis.xadd(processor_queue, frame_data)

    # 3. Update metrics
    self.frames_distributed += 1
```

### 3. ProcessorClient Pattern

Processors using ProcessorClient will:
1. Register with Frame Buffer v2 ✅
2. Consume from their dedicated Redis stream ✅
3. Send heartbeats ✅
4. Publish results to result stream ✅

## Implementation Status

✅ **Completed**:
- ProcessorClient base class created
- Sample-processor migrated to use ProcessorClient
- Registration API exists in Frame Buffer v2

❌ **Missing**:
- Frame Buffer v2 doesn't distribute frames to processor queues
- Frame Buffer v2 doesn't handle processor heartbeats
- No routing/load balancing logic

## Quick Fix for Testing

Until Frame Buffer v2 is updated, we can test by:

1. **Manual frame injection**:
```bash
# Inject frames directly to processor queue
docker exec detektr-redis-1 redis-cli XADD frames:ready:sample-processor-1 \
    frame_id test_123 \
    camera_id cam01 \
    timestamp $(date +%s)
```

2. **Temporary consumer group**:
```bash
# Create consumer group for processor
docker exec detektr-redis-1 redis-cli XGROUP CREATE \
    frames:ready:sample-processor-1 frame-processors $ MKSTREAM
```

## Next Steps

1. Update Frame Buffer v2 to implement frame distribution
2. Add processor health tracking
3. Implement routing strategies (round-robin, least-loaded, etc.)
4. Add metrics for distribution performance
