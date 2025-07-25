# Base Processor Framework

A comprehensive framework for building AI frame processing services in the Detektor system.

## Features

- **Abstract base class** for standardized processor implementation
- **Full observability** with OpenTelemetry tracing and Prometheus metrics
- **Structured logging** with correlation IDs
- **Frame lifecycle management** with state machine
- **Resource management** for CPU/GPU allocation
- **Batch processing** support with optimization
- **Error handling** with retry logic
- **Performance optimized** with <1ms overhead

## Installation

```bash
# From source
pip install -e .

# From GitHub (when package is published)
pip install git+https://github.com/hretheum/detektr.git@v1.0.0#subdirectory=services/shared/base-processor

# From package registry (future)
pip install base-processor
```

## Quick Start

```python
from base_processor import BaseProcessor
import numpy as np
from typing import Dict, Any

class MyProcessor(BaseProcessor):
    """Custom processor implementation."""
    
    async def setup(self):
        """Initialize your processor."""
        self.model = await self.load_model()
        
    async def validate_frame(self, frame: np.ndarray, metadata: Dict[str, Any]):
        """Validate input frame."""
        if frame is None or frame.size == 0:
            raise ValidationError("Invalid frame")
            
    async def process_frame(self, frame: np.ndarray, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single frame."""
        # Your processing logic here
        result = await self.model.predict(frame)
        return {"predictions": result}
        
    async def cleanup(self):
        """Clean up resources."""
        await self.model.unload()

# Usage
processor = MyProcessor(
    name="my-processor",
    enable_metrics=True,
    enable_tracing=True
)

await processor.initialize()
result = await processor.process(frame, metadata)
await processor.shutdown()
```

## Advanced Features

### Batch Processing

```python
from base_processor.batch_processor import BatchProcessorMixin

class BatchProcessor(BatchProcessorMixin, BaseProcessor):
    def supports_batch_processing(self):
        return True
        
    async def prepare_batch(self, frames, metadata_list):
        # Prepare frames for batch processing
        return normalized_frames, metadata_list

# Process multiple frames efficiently
results = await processor.process_frames_in_batches(frames, metadata_list)
```

### Resource Management

```python
from base_processor.resource_manager import ResourceManagerMixin

class GPUProcessor(ResourceManagerMixin, BaseProcessor):
    def __init__(self, **kwargs):
        kwargs.update({
            "cpu_cores": 4,
            "memory_limit_mb": 2048,
            "prefer_gpu": True,
            "gpu_memory_mb": 4096
        })
        super().__init__(**kwargs)
        
    async def process_frame(self, frame, metadata):
        # Resources automatically allocated
        async with self.with_resources(metadata["frame_id"]):
            return await self.gpu_inference(frame)
```

### State Machine Integration

```python
from base_processor.state_machine import StateMachineMixin, StateTransition

class StatefulProcessor(StateMachineMixin, BaseProcessor):
    async def process_frame(self, frame, metadata):
        frame_id = metadata["frame_id"]
        
        # Track frame lifecycle
        await self.track_frame_lifecycle(frame_id, metadata)
        
        # Update state during processing
        await self.state_machine.transition(frame_id, StateTransition.START)
        
        result = await self.do_processing(frame)
        
        # Mark as complete
        await self.state_machine.transition(
            frame_id, 
            StateTransition.COMPLETE,
            result=result
        )
        
        return result
```

## Metrics

All processors automatically export Prometheus metrics:

```promql
# Frames processed
processor_frames_processed_total{processor="my-processor",status="success"}

# Processing time
histogram_quantile(0.95, rate(processor_processing_time_seconds_bucket{processor="my-processor"}[5m]))

# Active frames
processor_active_frames{processor="my-processor"}

# Errors
rate(processor_errors_total{processor="my-processor"}[5m])
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=base_processor

# Run benchmarks
pytest tests/benchmarks/ -v

# Run specific test
pytest tests/unit/test_base.py::TestBaseProcessor::test_initialization
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Format code
black src tests
isort src tests

# Lint
flake8 src tests
mypy src

# Run pre-commit checks
pre-commit run --all-files
```

## API Reference

### BaseProcessor

The main abstract base class that all processors must inherit from.

#### Methods to Override

- `setup()` - Initialize processor resources
- `validate_frame(frame, metadata)` - Validate input frame
- `process_frame(frame, metadata)` - Main processing logic
- `cleanup()` - Clean up resources

#### Provided Methods

- `initialize()` - Initialize processor with observability
- `process(frame, metadata)` - Process with full pipeline
- `shutdown()` - Graceful shutdown
- `get_metrics()` - Get current metrics
- `health_check()` - Check processor health

### Mixins

- `TracingMixin` - OpenTelemetry tracing
- `MetricsMixin` - Prometheus metrics
- `LoggingMixin` - Structured logging
- `BatchProcessorMixin` - Batch processing
- `ResourceManagerMixin` - Resource management
- `StateMachineMixin` - State tracking

## License

MIT License - see LICENSE file for details.