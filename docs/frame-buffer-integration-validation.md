# Frame Buffer Integration Validation Plan

## Overview

This document defines validation tasks to ensure proper integration between RTSP Capture and Frame Buffer v2 through Redis Streams.

## Current Architecture

```
┌──────────────┐     Redis Stream      ┌─────────────────┐
│ RTSP Capture │ ──────────────────────▶│ Frame Buffer v2 │
└──────────────┘   frames:metadata      └─────────────────┘
                                                 │
                                                 ▼
                                         ┌──────────────┐
                                         │  Processors  │
                                         └──────────────┘
```

## Validation Tasks

### Task 1: Verify RTSP Capture → Redis Stream Flow

**[ ] Test RTSP publishes to correct stream**
- **Metryka**: RTSP Capture publikuje do `frames:metadata` stream
- **Test**:
  ```python
  # tests/integration/test_rtsp_redis_flow.py
  async def test_rtsp_publishes_to_redis_stream():
      """Verify RTSP Capture publishes frames to Redis Stream."""
      # Start RTSP Capture
      rtsp = await start_rtsp_capture()

      # Monitor Redis Stream
      redis_client = await aioredis.create_redis_pool('redis://localhost')

      # Wait for frames
      frames = []
      start_time = time.time()
      while len(frames) < 10 and (time.time() - start_time) < 10:
          messages = await redis_client.xread(
              ['frames:metadata'],
              latest_ids=['$']
          )
          if messages:
              frames.extend(messages[0][1])
          await asyncio.sleep(0.1)

      # Verify frames published
      assert len(frames) >= 10, "Expected at least 10 frames in 10 seconds"

      # Verify frame structure
      frame = frames[0]
      assert b'frame_id' in frame
      assert b'camera_id' in frame
      assert b'timestamp' in frame
      assert b'traceparent' in frame  # Trace context
  ```
- **Validation script**:
  ```bash
  # scripts/validate-rtsp-stream.sh
  #!/bin/bash
  echo "Monitoring RTSP → Redis Stream flow..."

  # Check stream exists
  redis-cli EXISTS frames:metadata

  # Monitor stream for 10 seconds
  timeout 10 redis-cli XREAD BLOCK 0 STREAMS frames:metadata $ | \
    grep -c "frame_id" | \
    awk '{print "Frames received in 10s: " $1}'
  ```
- **Czas**: 1h

### Task 2: Verify Frame Buffer v2 Consumes from Stream

**[ ] Test Frame Buffer v2 consumer group**
- **Metryka**: Frame Buffer v2 konsumuje z `frames:metadata` jako consumer group
- **Test**:
  ```python
  # tests/integration/test_frame_buffer_consumer.py
  async def test_frame_buffer_consumes_stream():
      """Verify Frame Buffer v2 consumes from Redis Stream."""
      # Inject test frames
      redis = await aioredis.create_redis_pool('redis://localhost')
      for i in range(5):
          await redis.xadd('frames:metadata', {
              'frame_id': f'test_{i}',
              'camera_id': 'test_cam',
              'timestamp': time.time()
          })

      # Start Frame Buffer v2
      await start_frame_buffer_v2()

      # Wait for consumption
      await asyncio.sleep(2)

      # Check consumer group info
      info = await redis.xinfo_consumers('frames:metadata', 'frame-buffer-group')

      # Verify consumer exists and is active
      assert len(info) > 0, "No consumers in group"
      consumer = info[0]
      assert consumer['pending'] == 0, "Frames not processed"
      assert consumer['idle'] < 2000, "Consumer not active"
  ```
- **Validation script**:
  ```bash
  # scripts/validate-frame-buffer-consumer.sh
  #!/bin/bash

  # Check consumer group exists
  redis-cli XINFO GROUPS frames:metadata | grep frame-buffer

  # Check active consumers
  redis-cli XINFO CONSUMERS frames:metadata frame-buffer-group

  # Monitor consumption
  echo "Checking consumption rate..."
  BEFORE=$(redis-cli XLEN frames:metadata)
  sleep 5
  AFTER=$(redis-cli XLEN frames:metadata)
  echo "Stream length change: $((AFTER - BEFORE))"
  ```
- **Czas**: 1h

### Task 3: End-to-End Flow Validation

**[ ] Test complete flow from RTSP to Processors**
- **Metryka**: Klatki przepływają od RTSP przez Frame Buffer do Procesorów
- **Test**:
  ```python
  # tests/integration/test_e2e_flow.py
  async def test_end_to_end_frame_flow():
      """Test complete flow from RTSP to processor."""
      # Start all services
      await start_services(['rtsp-capture', 'frame-buffer-v2', 'sample-processor'])

      # Wait for services to stabilize
      await wait_for_health_checks()

      # Monitor processor metrics before
      metrics_before = await get_processor_metrics('sample-processor')
      frames_before = metrics_before.get('frames_processed', 0)

      # Wait for processing
      await asyncio.sleep(10)

      # Check processor received frames
      metrics_after = await get_processor_metrics('sample-processor')
      frames_after = metrics_after.get('frames_processed', 0)

      assert frames_after > frames_before, "No frames processed"
      assert frames_after - frames_before >= 50, "Processing rate too low"

      # Verify traces
      traces = await get_traces(service='frame-buffer-v2')
      assert len(traces) > 0, "No traces found"

      # Verify no frame loss
      published = await get_rtsp_metrics()['frames_published']
      consumed = await get_frame_buffer_metrics()['frames_consumed']
      assert abs(published - consumed) < 10, "Significant frame loss detected"
  ```
- **Czas**: 2h

### Task 4: Performance Validation

**[ ] Load test with production-like traffic**
- **Metryka**: System handles 30+ FPS without frame loss
- **Test**:
  ```python
  # tests/load/test_frame_flow_performance.py
  async def test_high_throughput_flow():
      """Test system under load."""
      # Configure RTSP for 30 FPS
      await configure_rtsp(fps=30)

      # Run for 60 seconds
      start_time = time.time()
      start_metrics = await collect_all_metrics()

      await asyncio.sleep(60)

      end_metrics = await collect_all_metrics()
      duration = time.time() - start_time

      # Calculate rates
      frames_published = end_metrics['rtsp']['frames'] - start_metrics['rtsp']['frames']
      frames_processed = end_metrics['processors']['frames'] - start_metrics['processors']['frames']

      publish_rate = frames_published / duration
      process_rate = frames_processed / duration

      # Verify performance
      assert publish_rate >= 29, f"Publish rate too low: {publish_rate}"
      assert process_rate >= 28, f"Process rate too low: {process_rate}"
      assert (frames_published - frames_processed) / frames_published < 0.01, "Frame loss >1%"
  ```
- **Czas**: 2h

### Task 5: Failure Scenarios

**[ ] Test resilience to component failures**
- **Metryka**: System recovers gracefully from failures
- **Test scenarios**:
  1. Frame Buffer v2 restart - no frame loss
  2. Redis connection drop - buffering works
  3. Processor failure - frames redistributed
  4. RTSP reconnection - continues from where it left off
- **Czas**: 2h

## Monitoring Dashboard

**[ ] Create integration monitoring dashboard**
- Stream length gauge
- Consumption rate
- Frame loss percentage
- End-to-end latency histogram
- Component health status

## Success Criteria

1. **Zero frame loss** under normal operation
2. **<100ms end-to-end latency** (RTSP → Processor)
3. **30+ FPS sustained throughput**
4. **Automatic recovery** from transient failures
5. **Complete observability** via metrics and traces

## Rollback Plan

If integration fails:
1. Frame Buffer v2 can fall back to polling mode
2. Processors can connect directly to Redis
3. RTSP Capture continues to work independently

## Timeline

- Task 1-2: 2h (Stream validation)
- Task 3: 2h (E2E validation)
- Task 4: 2h (Performance)
- Task 5: 2h (Failure scenarios)
- Dashboard: 1h

**Total: 9h**
