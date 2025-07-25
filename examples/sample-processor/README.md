# Sample Processor

Example implementation of a frame processor using the base processor framework.

## Features Demonstrated

This sample processor demonstrates all key features of the base processor framework:

- **Object Detection Simulation**: Simulates AI object detection on frames
- **Batch Processing**: Efficient processing of multiple frames
- **Resource Management**: CPU/GPU allocation with limits
- **State Tracking**: Full frame lifecycle management
- **Observability**: Integrated metrics, tracing, and logging

## Architecture

```
SampleProcessor
├── BatchProcessorMixin     # Batch processing capabilities
├── ResourceManagerMixin    # CPU/GPU resource management
├── StateMachineMixin       # Frame state tracking
└── BaseProcessor           # Core processing framework
```

## Usage

### Basic Usage

```python
from sample_processor import SampleProcessor

# Create processor
processor = SampleProcessor(
    detection_threshold=0.6,
    simulate_gpu=False,
    processing_delay_ms=20
)

# Initialize
await processor.initialize()

# Process frame
result = await processor.process(frame, metadata)

# Shutdown
await processor.shutdown()
```

### Batch Processing

```python
# Process multiple frames efficiently
frames = [frame1, frame2, frame3, ...]
metadata_list = [meta1, meta2, meta3, ...]

results = await processor.process_frames_in_batches(frames, metadata_list)
```

### With Resource Management

```python
# Processor automatically manages resources
processor = SampleProcessor(
    cpu_cores=4,          # Limit to 4 CPU cores
    memory_limit_mb=1024, # Limit to 1GB memory
    prefer_gpu=True       # Use GPU if available
)
```

## Running the Demo

```bash
cd examples/sample-processor
python -m sample_processor.main
```

## Output Example

```
Sample Processor Demo
==================================================

1. Initializing processor...
   ✓ Processor initialized

2. Creating test frames...
   ✓ Created 5 test frames

3. Processing individual frames...
   Frame demo_frame_000: 0 objects detected
   Frame demo_frame_001: 1 objects detected

4. Processing frames in batch...
   ✓ Processed 5 frames in 1 batches
   ✓ Total objects detected: 7

5. Processor metrics:
   Frames processed: 7
   Success rate: 100.0%
   Average latency: 25.3ms

6. State machine statistics:
   Total frames tracked: 7
   COMPLETED: 7

7. Resource statistics:
   Active allocations: 0
   Available CPUs: 8
   Available memory: 512 MB

8. Shutting down...
   ✓ Processor shut down

==================================================
Demo completed successfully!
```

## Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `detection_threshold` | float | 0.5 | Confidence threshold for object detection |
| `simulate_gpu` | bool | False | Simulate GPU processing |
| `processing_delay_ms` | int | 10 | Simulated processing delay per frame |
| `batch_size` | int | 32 | Number of frames per batch |
| `cpu_cores` | int | 2 | CPU cores to allocate |
| `memory_limit_mb` | int | 512 | Memory limit in MB |
| `enable_metrics` | bool | True | Enable Prometheus metrics |
| `enable_tracing` | bool | True | Enable OpenTelemetry tracing |

## Metrics Exported

The processor automatically exports these metrics:

```promql
# Processing metrics
processor_frames_processed_total{processor="sample-processor"}
processor_processing_time_seconds{processor="sample-processor"}
processor_errors_total{processor="sample-processor",error_type="..."}

# Object detection specific
processor_custom_counter{processor="sample-processor",metric="objects_detected"}

# Resource usage
processor_memory_usage_bytes{processor="sample-processor"}
processor_active_frames{processor="sample-processor"}
```

## Extending the Sample

To create your own processor:

1. Inherit from `BaseProcessor` and desired mixins
2. Implement required abstract methods:
   - `setup()`: Initialize your model/resources
   - `validate_frame()`: Validate input frames
   - `process_frame()`: Your processing logic
   - `cleanup()`: Clean up resources

3. Optional: Override methods for custom behavior:
   - `supports_batch_processing()`: Return True for batch support
   - `prepare_batch()`: Prepare frames for batch processing

## Best Practices

1. **Always validate input**: Use `validate_frame()` to catch issues early
2. **Use resource management**: Wrap processing in `with_resources()` context
3. **Track frame states**: Use the state machine for lifecycle management
4. **Log with context**: Use `log_with_context()` for structured logging
5. **Export custom metrics**: Use `count_frames()` and `observe_value()`
6. **Handle errors gracefully**: Let the framework handle retries

## Performance Tips

- Enable batch processing for high throughput
- Use GPU simulation to test GPU code paths
- Monitor metrics to identify bottlenecks
- Adjust batch size based on workload
- Use resource limits to prevent OOM

## Integration with Production

In production, install the base processor package:

```bash
pip install base-processor==1.0.0
```

Then import normally:

```python
from base_processor import BaseProcessor
```

The sample shows sys.path manipulation only for demo purposes.
