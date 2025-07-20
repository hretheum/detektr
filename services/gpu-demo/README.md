# GPU Demo Service

A simple ML inference service demonstrating GPU utilization with YOLO object detection.

## Features

- ✅ GPU-accelerated inference with PyTorch
- ✅ YOLOv8 object detection
- ✅ Automatic CPU fallback when GPU unavailable
- ✅ Full observability (OpenTelemetry tracing, Prometheus metrics)
- ✅ GPU metrics monitoring (memory, temperature)
- ✅ Health checks with GPU status
- ✅ Correlation ID propagation
- ✅ Multi-stage Docker build with CUDA support

## Quick Start

### Local Development (CPU)

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

### Docker with GPU

```bash
# Build image
docker build -t gpu-demo .

# Run with GPU support
docker run --gpus all -p 8008:8008 gpu-demo
```

## API Endpoints

- `POST /api/v1/inference` - Run object detection on uploaded image
- `GET /api/v1/gpu/info` - Get current GPU status and memory usage
- `GET /health` - Health check with GPU availability
- `GET /metrics` - Prometheus metrics endpoint
- `GET /` - Service info and available endpoints

## Example Usage

```bash
# Upload image for object detection
curl -X POST http://localhost:8008/api/v1/inference \
  -F "image=@test-image.jpg" \
  | jq

# Check GPU status
curl http://localhost:8008/api/v1/gpu/info | jq

# Health check
curl http://localhost:8008/health | jq
```

## GPU Metrics

The service exposes the following GPU-specific metrics:

- `gpu_inference_total` - Total inference operations by device
- `gpu_inference_duration_seconds` - Inference duration histogram
- `gpu_memory_usage_bytes` - Current GPU memory usage
- `gpu_temperature_celsius` - GPU temperature (if available)
- `model_load_duration_seconds` - Time to load the model

## Environment Variables

- `SERVICE_NAME` - Service name (default: gpu-demo)
- `SERVICE_VERSION` - Version (default: 0.1.0)
- `PORT` - HTTP port (default: 8008)
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry collector endpoint
- `LOG_LEVEL` - Logging level (default: info)

## Model

Uses YOLOv8n (nano) model for demonstration:
- Small size (~6MB)
- Fast inference
- 80 object classes (COCO dataset)
- Good balance of speed and accuracy

## GPU Requirements

- NVIDIA GPU with CUDA 12.0+ support
- NVIDIA Container Toolkit for Docker
- Minimum 2GB GPU memory

## CPU Fallback

If no GPU is available, the service automatically falls back to CPU inference with appropriate logging.

## Performance

Typical inference times:
- GPU (RTX 3090): ~10-20ms per image
- GPU (Tesla T4): ~30-50ms per image
- CPU (Intel i7): ~100-200ms per image

## Troubleshooting

### GPU not detected in container

```bash
# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# Check Docker daemon config
cat /etc/docker/daemon.json | grep nvidia
```

### Out of GPU memory

- Model loads ~200MB into GPU memory
- Each inference uses additional ~50-100MB
- Monitor with `nvidia-smi` or `/api/v1/gpu/info`

### Slow first inference

First inference includes:
- Model warmup
- CUDA kernel compilation
- Memory allocation

Subsequent inferences are much faster.
