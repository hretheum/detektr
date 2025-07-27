# Processor Template Guide

This guide helps you create a new processor using the base-processor framework.

## Quick Start

### 1. Create Your Processor Directory

```bash
mkdir -p services/my-processor
cd services/my-processor
```

### 2. Copy Templates

```bash
# Copy Dockerfile template
cp ../shared/base-processor/Dockerfile.processor Dockerfile
sed -i 's/\[PROCESSOR_NAME\]/my-processor/g' Dockerfile

# Copy docker-compose template
cp ../shared/base-processor/docker-compose.processor.yml docker-compose.yml
sed -i 's/\[PROCESSOR_NAME\]/my-processor/g' docker-compose.yml
```

### 3. Create Processor Implementation

Create `main.py`:

```python
#!/usr/bin/env python3
"""My Processor - Description of what it does."""

import asyncio
import numpy as np
from typing import Dict, Any

from base_processor import BaseProcessor
from base_processor.exceptions import ValidationError


class MyProcessor(BaseProcessor):
    """Custom processor implementation."""

    def __init__(self, **kwargs):
        """Initialize processor with custom configuration."""
        super().__init__(
            name="my-processor",
            version="1.0.0",
            description="Description of what this processor does",
            **kwargs
        )
        self.model = None
        self.config = {}

    async def setup(self):
        """Initialize processor resources."""
        self.logger.info("Setting up processor")

        # Load configuration
        self.config = {
            "threshold": float(self.get_env("CONFIDENCE_THRESHOLD", "0.5")),
            "batch_size": int(self.get_env("BATCH_SIZE", "1")),
        }

        # Load model
        model_path = self.get_env("MODEL_PATH", "/app/models/default.onnx")
        self.model = await self.load_model(model_path)

        self.logger.info("Processor setup complete", extra={"config": self.config})

    async def validate_frame(self, frame: np.ndarray, metadata: Dict[str, Any]):
        """Validate input frame."""
        if frame is None:
            raise ValidationError("Frame is None")

        if frame.size == 0:
            raise ValidationError("Frame is empty")

        # Check dimensions
        if len(frame.shape) != 3:
            raise ValidationError(f"Invalid frame shape: {frame.shape}")

        # Check metadata
        required_fields = ["frame_id", "timestamp", "source"]
        for field in required_fields:
            if field not in metadata:
                raise ValidationError(f"Missing required metadata field: {field}")

    async def process_frame(self, frame: np.ndarray, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single frame."""
        # Preprocess frame
        processed_frame = await self.preprocess(frame)

        # Run inference
        with self.measure_time("inference"):
            predictions = await self.model.predict(processed_frame)

        # Filter by confidence
        filtered_predictions = [
            p for p in predictions
            if p["confidence"] >= self.config["threshold"]
        ]

        # Log results
        self.logger.info(
            "Frame processed",
            extra={
                "frame_id": metadata["frame_id"],
                "predictions_count": len(filtered_predictions),
            }
        )

        return {
            "predictions": filtered_predictions,
            "processing_time_ms": metadata.get("processing_time_ms", 0),
            "model_version": self.model.version,
        }

    async def cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up processor")

        if self.model:
            await self.model.unload()
            self.model = None

    async def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for model input."""
        # Example preprocessing
        # - Resize to model input size
        # - Normalize pixel values
        # - Convert color space if needed
        return frame

    async def load_model(self, model_path: str):
        """Load AI model."""
        # Implement model loading logic
        # This is just a placeholder
        class MockModel:
            version = "1.0.0"
            async def predict(self, frame):
                return [{"class": "example", "confidence": 0.95}]
            async def unload(self):
                pass

        return MockModel()

    def get_env(self, key: str, default: str = None) -> str:
        """Get environment variable with default."""
        import os
        return os.getenv(key, default)


async def main():
    """Main entry point."""
    # Create processor
    processor = MyProcessor(
        enable_metrics=True,
        enable_tracing=True,
        log_level="INFO"
    )

    try:
        # Initialize
        await processor.initialize()

        # Start health check server
        from aiohttp import web

        async def health_handler(request):
            health = await processor.health_check()
            status = 200 if health["status"] == "healthy" else 503
            return web.json_response(health, status=status)

        app = web.Application()
        app.router.add_get("/health", health_handler)

        # Start server
        runner = web.AppRunner(app)
        await runner.setup()

        port = int(processor.get_env("PORT", "8080"))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()

        print(f"Processor started on port {port}")

        # Keep running
        while True:
            await asyncio.sleep(60)
            # Log metrics periodically
            metrics = await processor.get_metrics()
            processor.logger.info("Metrics update", extra={"metrics": metrics})

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await processor.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Create Requirements File

Create `requirements.txt`:

```txt
# Base processor is installed in Dockerfile
aiohttp>=3.9.0
numpy>=1.24.0
# Add your processor-specific dependencies here
# opencv-python>=4.8.0
# onnxruntime>=1.16.0
# tensorflow>=2.13.0
# torch>=2.1.0
```

### 5. Build and Test

```bash
# Build image
docker build -f Dockerfile -t my-processor:latest ../..

# Run locally
docker run --rm -p 8080:8080 my-processor:latest

# Test health endpoint
curl http://localhost:8080/health
```

### 6. Deploy

```bash
# Tag for registry
docker tag my-processor:latest ghcr.io/hretheum/detektr/my-processor:latest

# Push (done by CI/CD)
git add .
git commit -m "feat: add my-processor service"
git push origin main
```

## Advanced Features

### Batch Processing

```python
from base_processor.batch_processor import BatchProcessorMixin

class MyBatchProcessor(BatchProcessorMixin, BaseProcessor):
    def supports_batch_processing(self):
        return True

    def get_batch_size(self):
        return int(self.get_env("BATCH_SIZE", "8"))

    async def prepare_batch(self, frames, metadata_list):
        # Stack frames for batch processing
        batch = np.stack([self.preprocess(f) for f in frames])
        return batch, metadata_list

    async def process_batch(self, batch, metadata_list):
        # Process entire batch at once
        predictions = await self.model.predict_batch(batch)

        # Split results back to individual frames
        results = []
        for i, (pred, meta) in enumerate(zip(predictions, metadata_list)):
            results.append({
                "frame_id": meta["frame_id"],
                "predictions": pred
            })

        return results
```

### GPU Support

```python
from base_processor.resource_manager import ResourceManagerMixin

class MyGPUProcessor(ResourceManagerMixin, BaseProcessor):
    def __init__(self, **kwargs):
        kwargs.update({
            "prefer_gpu": True,
            "gpu_memory_mb": 4096,
            "fallback_to_cpu": True
        })
        super().__init__(**kwargs)

    async def setup(self):
        await super().setup()

        # Check GPU availability
        if self.has_gpu():
            self.logger.info("GPU available, using GPU acceleration")
            self.device = "cuda"
        else:
            self.logger.info("No GPU available, using CPU")
            self.device = "cpu"
```

### State Tracking

```python
from base_processor.state_machine import StateMachineMixin, StateTransition

class MyStatefulProcessor(StateMachineMixin, BaseProcessor):
    async def process_frame(self, frame, metadata):
        frame_id = metadata["frame_id"]

        # Track frame lifecycle
        await self.track_frame_lifecycle(frame_id, metadata)

        try:
            # Transition to processing
            await self.state_machine.transition(frame_id, StateTransition.START)

            # Do processing
            result = await self._do_processing(frame, metadata)

            # Mark as complete
            await self.state_machine.transition(
                frame_id,
                StateTransition.COMPLETE,
                result=result
            )

            return result

        except Exception as e:
            # Mark as failed
            await self.state_machine.transition(
                frame_id,
                StateTransition.FAIL,
                error=str(e)
            )
            raise
```

## Deployment Configuration

### Environment Variables

```bash
# Base processor configuration
PROCESSOR_NAME=my-processor
ENABLE_METRICS=true
ENABLE_TRACING=true
LOG_LEVEL=INFO

# OpenTelemetry
OTEL_SERVICE_NAME=my-processor
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

# Service ports
PORT=8080
METRICS_PORT=9090

# Resource limits
CPU_CORES=4
MEMORY_LIMIT_MB=2048
PREFER_GPU=true
GPU_MEMORY_MB=4096

# Processor-specific
MODEL_PATH=/app/models/my-model.onnx
CONFIDENCE_THRESHOLD=0.7
BATCH_SIZE=8
```

### Docker Compose Override

Create `docker-compose.override.yml` for local development:

```yaml
version: '3.8'

services:
  my-processor:
    volumes:
      - ./models:/app/models:ro
      - ./config:/app/config:ro
      - ./src:/app/src:ro  # For development
    environment:
      - LOG_LEVEL=DEBUG
      - RELOAD=true
```

## Testing

### Unit Tests

Create `tests/test_processor.py`:

```python
import pytest
import numpy as np
from my_processor import MyProcessor

@pytest.fixture
async def processor():
    p = MyProcessor(enable_metrics=False, enable_tracing=False)
    await p.initialize()
    yield p
    await p.shutdown()

@pytest.mark.asyncio
async def test_process_frame(processor):
    # Create test frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    metadata = {
        "frame_id": "test-001",
        "timestamp": "2024-01-01T00:00:00Z",
        "source": "test"
    }

    # Process frame
    result = await processor.process(frame, metadata)

    # Verify result
    assert "predictions" in result
    assert "processing_time_ms" in result
    assert result["processing_time_ms"] >= 0

@pytest.mark.asyncio
async def test_validation_error(processor):
    # Invalid frame
    frame = None
    metadata = {"frame_id": "test-001"}

    # Should raise validation error
    with pytest.raises(ValidationError):
        await processor.process(frame, metadata)
```

### Integration Tests

```python
import aiohttp
import pytest

@pytest.mark.asyncio
async def test_health_endpoint():
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8080/health") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "healthy"
            assert "version" in data
            assert "uptime_seconds" in data
```

## Monitoring

### Prometheus Queries

```promql
# Processing rate
rate(processor_frames_processed_total{processor="my-processor"}[5m])

# Processing latency (95th percentile)
histogram_quantile(0.95, rate(processor_processing_time_seconds_bucket{processor="my-processor"}[5m]))

# Error rate
rate(processor_errors_total{processor="my-processor"}[5m])

# Active frames
processor_active_frames{processor="my-processor"}

# Resource usage
processor_cpu_usage_percent{processor="my-processor"}
processor_memory_usage_mb{processor="my-processor"}
```

### Grafana Dashboard

Import the base processor dashboard and customize for your processor:

1. Copy `services/shared/base-processor/grafana/dashboard.json`
2. Update processor name filters
3. Add processor-specific metrics
4. Import to Grafana

## Troubleshooting

### Common Issues

1. **Import Error: No module named 'base_processor'**
   - Ensure base-processor is installed in Dockerfile
   - Check PYTHONPATH includes /app

2. **Health check failing**
   - Verify PORT environment variable
   - Check logs: `docker logs my-processor`
   - Test manually: `curl http://localhost:8080/health`

3. **Memory issues**
   - Increase MEMORY_LIMIT_MB
   - Enable batch processing to reduce memory usage
   - Profile memory usage with memory_profiler

4. **GPU not detected**
   - Ensure nvidia-docker runtime is installed
   - Add GPU device mapping in docker-compose
   - Check CUDA compatibility

### Debug Mode

Enable debug logging:

```yaml
environment:
  - LOG_LEVEL=DEBUG
  - PYTHONUNBUFFERED=1
  - PYTHONASYNCIODEBUG=1
```

### Performance Tuning

1. **Enable batch processing** for better throughput
2. **Adjust worker count** based on CPU cores
3. **Use connection pooling** for external services
4. **Profile with cProfile** to find bottlenecks
5. **Monitor metrics** to identify issues

## Next Steps

1. Implement your processing logic
2. Add comprehensive tests
3. Create processor-specific documentation
4. Set up monitoring dashboards
5. Deploy to staging environment
6. Performance test with realistic load
7. Deploy to production

For more examples, see:
- `services/object-detector/` - Object detection processor
- `services/face-detector/` - Face detection processor
- `services/ocr-processor/` - OCR text extraction processor
