# Frame Tracking Implementation Guide

## Overview

The Frame Tracking system provides complete observability for every frame processed through the Detektor pipeline. It implements Event Sourcing patterns with distributed tracing, allowing you to track any frame's journey from capture to completion.

## Architecture

### Domain Model

```python
from src.shared.kernel.domain import Frame, ProcessingState

# Frame lifecycle states
class ProcessingState(Enum):
    CAPTURED = "captured"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
```

### Event Sourcing

Every state change generates an event:
- `FrameCaptured` - Frame received from camera
- `FrameQueued` - Frame added to processing queue
- `ProcessingStarted` - Processing begun
- `ProcessingCompleted` - Successfully processed
- `ProcessingFailed` - Error during processing

## Implementation

### 1. Setting Frame Context

```python
from src.shared.telemetry.frame_tracking import set_frame_context

# In your service
async def process_frame(self, frame: Frame):
    # Set context for automatic propagation
    set_frame_context(frame)

    # All subsequent spans will include frame_id and camera_id
    with tracer.start_as_current_span("process"):
        # Your processing logic
        pass
```

### 2. Recording Metrics with Exemplars

```python
from src.shared.telemetry.metrics import get_metrics

metrics = get_metrics("my_service")

# Metrics automatically include trace context
metrics.increment_frames_processed(
    attributes={"camera_id": frame.camera_id}
)

# Duration tracking with trace linkage
with TimingContext(frame.camera_id, "face_detection") as timer:
    # Process...
    pass  # Duration recorded with trace_id
```

### 3. Querying Frame History

```python
from src.contexts.monitoring.domain.frame_tracking import FrameTrackingQueries

queries = FrameTrackingQueries(repository)

# Get complete frame journey
journey = await queries.get_frame_journey("frame_id_123")
# Returns: timeline, events, stages, trace links

# Find slow frames
slow_frames = await queries.find_slow_frames(
    threshold_ms=1000,
    hours=1
)

# Analyze failures
failures = await queries.get_failure_analysis(hours=24)
```

## Storage

### TimescaleDB Schema

Frame metadata is stored in TimescaleDB hypertables:

```sql
-- Main metadata table (hypertable)
frame_metadata (
    frame_id,
    camera_id,
    timestamp,
    state,
    metadata,
    total_processing_time_ms
)

-- Processing stages
processing_stages (
    frame_id,
    stage_name,
    duration_ms,
    status
)

-- Event store
frame_events (
    event_type,
    frame_id,
    occurred_at,
    data
)
```

### Continuous Aggregates

Pre-computed statistics for performance:
- `frame_stats_hourly` - Hourly statistics per camera
- `performance_stats` - Processing performance metrics

## Observability

### Grafana Dashboards

1. **Frame Pipeline Dashboard** (`frame-pipeline.json`)
   - Real-time processing rates
   - Error rates and latency percentiles
   - Camera statistics
   - State distribution

2. **Frame Search Dashboard** (`frame-search.json`)
   - Search by frame ID
   - View complete journey logs
   - Linked traces in Jaeger
   - Processing metrics

### Finding a Frame

1. Enter frame ID in Grafana Frame Search dashboard
2. View:
   - All logs containing frame_id
   - Processing metrics with trace links
   - Complete distributed trace
   - Timeline of events

### Trace Exemplars

Metrics include trace context for correlation:

```promql
# Query with exemplars
frame_processing_duration_seconds_bucket{camera_id="cam01"}

# Results include trace_id and span_id labels
# Click trace_id to jump to Jaeger
```

## Best Practices

### 1. Always Set Frame Context

```python
# ✅ Good - context set early
async def handle_frame(frame):
    set_frame_context(frame)
    # All subsequent operations tracked

# ❌ Bad - no context
async def handle_frame(frame):
    # Processing without context
```

### 2. Use Structured Logging

```python
logger.info("Processing frame",
    frame_id=str(frame.id),
    camera_id=frame.camera_id,
    stage="face_detection"
)
```

### 3. Record All State Transitions

```python
# Always transition through state machine
frame.transition_to(ProcessingState.PROCESSING)
await repo.save(frame)
await repo.save_event(ProcessingStarted(...))
```

### 4. Handle Errors Gracefully

```python
try:
    # Process
except Exception as e:
    frame.mark_as_failed(str(e))
    metrics.increment_errors(
        type(e).__name__,
        attributes={"stage": current_stage}
    )
    raise
```

## Performance Considerations

1. **Frame ID Cardinality**: Don't use frame_id as metric label for counters
2. **Retention**: Configure TimescaleDB retention policies
3. **Sampling**: Use trace sampling for high-volume scenarios
4. **Indexing**: Ensure proper indexes on frame_id and timestamp

## Example: Complete Frame Processing

```python
from src.shared.telemetry import traced
from src.shared.telemetry.frame_tracking import set_frame_context
from src.shared.telemetry.metrics import get_metrics

class FrameProcessor:
    def __init__(self):
        self.metrics = get_metrics("processor")
        self.repo = FrameMetadataRepository(pool)

    @traced(span_name="process_frame")
    async def process(self, frame: Frame):
        # Set context
        set_frame_context(frame)

        # Record received
        self.metrics.increment_frames_processed(
            attributes={"camera_id": frame.camera_id}
        )

        # State transition
        frame.transition_to(ProcessingState.PROCESSING)
        await self.repo.save(frame)

        # Process stages
        for stage_name in ["detect", "analyze", "notify"]:
            stage = frame.start_processing_stage(stage_name)

            try:
                # Stage processing
                await self._process_stage(stage_name, frame)
                stage.complete()

            except Exception as e:
                stage.fail(str(e))
                frame.mark_as_failed(str(e))
                raise

        # Complete
        frame.mark_as_completed()
        await self.repo.save(frame)

        # Record metrics
        self.metrics.observe_processing_duration(
            frame.camera_id,
            "total",
            frame.total_processing_time_ms / 1000
        )
```

## Troubleshooting

### Frame Not Found
1. Check if frame was actually processed
2. Verify TimescaleDB connection
3. Check retention policies

### Missing Traces
1. Ensure OpenTelemetry is configured
2. Verify OTLP endpoint is reachable
3. Check sampling configuration

### High Cardinality
1. Don't use frame_id in metric names
2. Use exemplars for correlation
3. Configure appropriate retention

## Next Steps

1. Implement custom alerts based on frame metrics
2. Add ML-based anomaly detection
3. Create frame replay capabilities
4. Build frame debugging UI
