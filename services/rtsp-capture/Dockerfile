# Multi-stage Dockerfile for RTSP Capture Service
# Optimized for small size and security

# Stage 1: Build Python wheels
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Create wheels directory
WORKDIR /wheels

# Copy requirements and build wheels
COPY requirements-prod.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --wheel-dir /wheels \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    pydantic==2.5.0 \
    requests==2.31.0 \
    opentelemetry-api==1.22.0 \
    opentelemetry-sdk==1.22.0 \
    opentelemetry-exporter-otlp==1.22.0 \
    opentelemetry-instrumentation-fastapi==0.43b0 \
    prometheus-client==0.19.0 \
    aioredis==2.0.1

# Stage 2: Runtime image
FROM python:3.11-slim

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --no-index --find-links=/wheels \
    fastapi uvicorn pydantic requests \
    opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-redis \
    prometheus-client aioredis && \
    rm -rf /wheels

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser src/ ./src/

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8001

# Health check using curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
