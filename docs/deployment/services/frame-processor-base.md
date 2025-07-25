# Service: Frame Processor Base

## 🚀 Quick Deploy (Unified Pipeline)

### Package Publishing
```bash
# Tag i push do publikacji package
git tag v1.0.0
git push origin v1.0.0

# Lub manual trigger
gh workflow run release.yml
```

### Example Processor Deployment
```bash
# Deploy example processor
gh workflow run main-pipeline.yml -f services=example-processor

# Lub przy push do main
git push origin main
```

## 📋 Configuration

### Base Processor Package
- **Package Name**: `base-processor`
- **Registry**: GitHub Packages
- **Location**: `services/shared/base-processor/`
- **Import**: `from base_processor import BaseProcessor`

### Example Processor Service
- **Service Name**: `example-processor`
- **Port**: `8099` (zobacz [PORT_ALLOCATION.md](../PORT_ALLOCATION.md))
- **Registry**: `ghcr.io/hretheum/detektr/example-processor`
- **Health Check**: `http://localhost:8099/health`
- **Metrics**: `http://localhost:8099/metrics`

## 📦 Package Structure

### Publishing Python Package
```yaml
# .github/workflows/release.yml handles package publishing
on:
  push:
    tags:
      - 'v*.*.*'
jobs:
  publish:
    steps:
      - name: Build package
        run: |
          cd services/shared/base-processor
          python -m build

      - name: Publish to GitHub Packages
        run: |
          python -m twine upload dist/*
```

### Using in Services
```python
# requirements.txt
base-processor @ git+https://github.com/hretheum/detektr.git@v1.0.0#subdirectory=services/shared/base-processor

# Or from GitHub Packages (when configured)
base-processor==1.0.0
```

### Dockerfile Template
```dockerfile
# Dockerfile.processor
FROM python:3.11-slim

# Install base processor
COPY services/shared/base-processor /tmp/base-processor
RUN pip install /tmp/base-processor

# Or from package
# RUN pip install base-processor==1.0.0

# Your service code
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "-m", "your_service"]
```

## 🔧 Deployment Methods

### 1. Deploy Example Processor
```bash
# Via unified pipeline
gh workflow run main-pipeline.yml -f services=example-processor

# Verify deployment
curl http://nebula:8099/health
```

### 2. Create New Processor Service
```bash
# 1. Copy example structure
cp -r examples/sample-processor services/my-processor

# 2. Update configuration
cd services/my-processor
# Edit main.py to extend BaseProcessor

# 3. Add to docker-compose
# Edit docker/base/docker-compose.yml

# 4. Deploy
git add .
git commit -m "feat: add my-processor service"
git push origin main
```

## 📊 Monitoring

### Prometheus Metrics
```bash
# Verify base processor metrics
curl http://nebula:9090/api/v1/query?query=processor_frames_processed_total

# Example queries
processor_frames_processed_total{service="example-processor"}
processor_processing_time_seconds{service="example-processor"}
processor_errors_total{service="example-processor"}
```

### Jaeger Tracing
```bash
# Check traces
curl http://nebula:16686/api/traces?service=example-processor

# Or via UI
# http://nebula:16686
```

## 🧪 Performance Testing

### Run Benchmarks
```bash
# Local benchmarks
cd services/shared/base-processor
pytest tests/benchmarks/ -v

# CI/CD benchmarks (automatic on PR)
# Check GitHub Actions for results
```

### Baseline Requirements
- **Overhead**: <1ms per frame
- **Throughput**: >1000 fps (minimal processor)
- **Memory**: <10MB overhead per frame

## 🔧 Troubleshooting

### Package Import Fails
```bash
# Check package installation
pip show base-processor

# Install from source
cd services/shared/base-processor
pip install -e .
```

### Example Processor Not Running
```bash
# Check service status
docker ps | grep example-processor

# Check logs
docker logs example-processor

# Verify port allocation
netstat -tlnp | grep 8099
```

### Missing Metrics
```bash
# Check metrics endpoint
curl http://localhost:8099/metrics

# Verify Prometheus scraping
curl http://nebula:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="example-processor")'
```

## 🔗 Related Documentation

- [Base Processor Development](../../../services/shared/base-processor/README.md)
- [Sample Processor Example](../../../examples/sample-processor/README.md)
- [Python Service Standards](../../standards/python-services.md)
- [Adding New AI Service](../guides/new-ai-service.md)
