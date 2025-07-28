# Sample Processor Migration to ProcessorClient

## Overview

This document describes the migration of sample-processor from polling-based architecture to ProcessorClient pattern.

## Changes Made

### 1. Docker Compose Configuration

#### Before (Polling)
```yaml
sample-processor:
  environment:
    - ENABLE_FRAME_CONSUMER=true
    - FRAME_BUFFER_URL=http://frame-buffer-v2:8002
    - POLL_INTERVAL_MS=100
    - CONSUMER_BATCH_SIZE=10
    - MAX_RETRIES=3
    - BACKOFF_MS=1000
```

#### After (ProcessorClient)
```yaml
sample-processor:
  environment:
    - ORCHESTRATOR_URL=http://frame-buffer-v2:8002
    - PROCESSOR_ID=sample-processor-1
    - REDIS_HOST=redis
    - REDIS_PORT=6379
  depends_on:
    frame-buffer-v2:
      condition: service_healthy
```

### 2. Key Differences

| Aspect | Old (Polling) | New (ProcessorClient) |
|--------|--------------|---------------------|
| Frame Source | HTTP polling `/frames/dequeue` | Push from orchestrator |
| Registration | None | Registers with orchestrator |
| Load Distribution | Random | Orchestrator-managed |
| Backpressure | Client-side retry | Built-in flow control |
| Observability | Limited | Full trace propagation |

### 3. Benefits

1. **Performance**: No polling overhead, frames pushed directly
2. **Scalability**: Orchestrator manages load distribution
3. **Reliability**: Automatic reconnection and health monitoring
4. **Observability**: Integrated tracing and metrics

## Validation

Run the validation script to ensure proper migration:

```bash
./scripts/validate-sample-processor.sh
```

Expected output:
- ✓ Sample processor registered with orchestrator
- ✓ Health endpoint responding
- ✓ Metrics available for processor
- ✓ No polling behavior in logs

## Rollback Plan

If issues occur:

1. Revert docker-compose changes
2. Set `ENABLE_FRAME_CONSUMER=true`
3. Remove `ORCHESTRATOR_URL`
4. Restart sample-processor

## Monitoring

After migration, monitor:

1. **Registration Status**: Check `/processors` endpoint
2. **Frame Distribution**: Monitor processor queue depth
3. **Performance**: Compare processing rates before/after
4. **Errors**: Check logs for connection issues

## Next Steps

1. Monitor for 24h to ensure stability
2. Apply same pattern to other processors
3. Deprecate polling endpoints in frame-buffer-v2
