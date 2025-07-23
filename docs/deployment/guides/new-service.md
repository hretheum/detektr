# 🆕 Adding New Service - Complete Guide

This guide shows you how to add a new service to the Detektor system from scratch.

## Prerequisites

- [ ] Service name decided (e.g., `face-recognition`)
- [ ] Port number allocated (check [Port Allocation](../README.md#-port-allocation))
- [ ] Dependencies identified (Redis, PostgreSQL, etc.)

## Step-by-Step Process

### 1. Create Service Structure

```bash
# Set your service name
SERVICE_NAME="face-recognition"
PORT="8002"

# Create directory structure
mkdir -p services/${SERVICE_NAME}/{src,tests}

# Create base files
touch services/${SERVICE_NAME}/Dockerfile
touch services/${SERVICE_NAME}/requirements.txt
touch services/${SERVICE_NAME}/requirements-dev.txt
touch services/${SERVICE_NAME}/src/__init__.py
touch services/${SERVICE_NAME}/src/main.py
touch services/${SERVICE_NAME}/tests/test_health.py
```

### 2. Create Minimal Service Implementation

`services/${SERVICE_NAME}/src/main.py`:

```python
#!/usr/bin/env python3
"""Main entry point for ${SERVICE_NAME} service."""

import os
import logging
from datetime import datetime
from typing import Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Prometheus metrics
request_count = Counter(
    "${SERVICE_NAME}_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"],
)
request_duration = Histogram(
    "${SERVICE_NAME}_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
)

# Create FastAPI app
app = FastAPI(
    title="${SERVICE_NAME.title()} Service",
    description="Service description here",
    version="1.0.0",
)

# Service state
class ServiceState:
    def __init__(self):
        self.healthy = True
        self.start_time = datetime.now()

state = ServiceState()

@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint."""
    if not state.healthy:
        raise HTTPException(status_code=503, detail="Service unhealthy")

    return {
        "status": "healthy",
        "service": "${SERVICE_NAME}",
        "uptime_seconds": (datetime.now() - state.start_time).total_seconds(),
        "timestamp": datetime.now().isoformat(),
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "${SERVICE_NAME}",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "${PORT}"))

    logger.info(f"Starting ${SERVICE_NAME} service on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
```

### 3. Create Dockerfile

`services/${SERVICE_NAME}/Dockerfile`:

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN useradd -m -s /bin/bash detektor && \
    chown -R detektor:detektor /app

USER detektor

# Environment variables
ENV PYTHONPATH=/app \
    SERVICE_NAME=${SERVICE_NAME} \
    PORT=${PORT} \
    ENVIRONMENT=production

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Start service
CMD ["python", "-m", "src.main"]
```

### 4. Create Requirements Files

`services/${SERVICE_NAME}/requirements.txt`:

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
prometheus-client==0.19.0
pydantic==2.5.0
python-dotenv==1.0.0
httpx==0.25.2
```

`services/${SERVICE_NAME}/requirements-dev.txt`:

```
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.12.1
flake8==6.1.0
mypy==1.7.1
httpx==0.25.2
```

### 5. Create Basic Test

`services/${SERVICE_NAME}/tests/test_health.py`:

```python
"""Health endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test health endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "${SERVICE_NAME}"

def test_metrics_endpoint():
    """Test metrics endpoint returns 200."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

def test_root_endpoint():
    """Test root endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "${SERVICE_NAME}"
    assert data["status"] == "running"
```

### 6. Update GitHub Workflows

#### Edit `.github/workflows/deploy-self-hosted.yml`:

1. Add to filters (around line 55):
```yaml
${SERVICE_NAME}:
  - 'services/${SERVICE_NAME}/**'
  - 'services/base-template/**'
```

2. Add to matrix (around line 200):
```yaml
- ${SERVICE_NAME}
```

#### Edit `.github/workflows/manual-service-build.yml`:

Add to options (around line 10):
```yaml
- ${SERVICE_NAME}
```

### 7. Add to Docker Compose

Edit `docker-compose.yml`:

```yaml
  ${SERVICE_NAME}:
    image: ghcr.io/hretheum/detektr/${SERVICE_NAME}:latest
    container_name: ${SERVICE_NAME}
    restart: unless-stopped
    ports:
      - "${PORT}:${PORT}"
    environment:
      SERVICE_NAME: ${SERVICE_NAME}
      PORT: ${PORT}
      REDIS_HOST: redis  # If needed
      REDIS_PORT: 6379   # If needed
    networks:
      - detektor-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${PORT}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    depends_on:
      - redis  # Add dependencies as needed
```

### 8. Test Locally

```bash
# Build locally
cd services/${SERVICE_NAME}
docker build -t ${SERVICE_NAME}:test .

# Run locally
docker run -p ${PORT}:${PORT} ${SERVICE_NAME}:test

# Test endpoints
curl http://localhost:${PORT}/health
curl http://localhost:${PORT}/metrics
```

### 9. Deploy

```bash
# Commit all changes
git add .
git commit -m "feat: add ${SERVICE_NAME} service

- Implement basic FastAPI service with health/metrics
- Add Dockerfile and requirements
- Update workflows and docker-compose
- Add basic tests"

# Push to trigger deployment
git push origin main
```

### 10. Verify Deployment

```bash
# Check GitHub Actions
gh run list --workflow=deploy-self-hosted.yml --limit=1

# Wait for deployment
sleep 300  # ~5 minutes

# Check service health
curl http://nebula:${PORT}/health

# Check container status
ssh nebula "docker ps | grep ${SERVICE_NAME}"

# Check logs
ssh nebula "docker logs ${SERVICE_NAME} --tail 20"
```

## Common Patterns

### Adding Redis Connection

```python
import redis.asyncio as redis

# In your service startup
redis_client = await redis.from_url(
    f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}"
)
```

### Adding PostgreSQL Connection

```python
import asyncpg

# In your service startup
pool = await asyncpg.create_pool(
    os.getenv('DATABASE_URL', 'postgresql://user:pass@postgres/db')
)
```

### Adding OpenTelemetry Tracing

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
    agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
```

## Checklist

- [ ] Service directory created
- [ ] Dockerfile created
- [ ] Health endpoint implemented
- [ ] Metrics endpoint implemented
- [ ] Basic tests written
- [ ] Added to deploy-self-hosted.yml filters
- [ ] Added to deploy-self-hosted.yml matrix
- [ ] Added to manual-service-build.yml
- [ ] Added to docker-compose.yml
- [ ] Tested locally
- [ ] Pushed to main
- [ ] Verified deployment

## Next Steps

1. Add service-specific functionality
2. Create comprehensive tests
3. Add monitoring dashboards
4. Document API endpoints
5. Set up alerts

## Troubleshooting

### Service Not Building

Check GitHub Actions logs:
```bash
gh run view --log-failed
```

### Service Not Starting

Check container logs:
```bash
ssh nebula "docker logs ${SERVICE_NAME}"
```

### Port Already in Use

Find what's using the port:
```bash
ssh nebula "sudo lsof -i :${PORT}"
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
