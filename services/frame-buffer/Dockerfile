# Multi-stage Dockerfile for Frame Buffer Service
# Optimized for small size and security

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Create wheels directory
WORKDIR /wheels

# Copy requirements
COPY services/frame-buffer/requirements.txt .

# Build wheels for non-local dependencies
RUN pip install --upgrade pip setuptools wheel && \
    grep -v "^frame-tracking" requirements.txt | pip wheel --no-cache-dir --wheel-dir /wheels -r /dev/stdin

# Stage 2: Runtime image
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy frame-tracking library first
COPY --chown=appuser:appuser services/shared/frame-tracking /app/services/shared/frame-tracking

# Install Python packages from wheels
COPY --from=builder /wheels /wheels
COPY services/frame-buffer/requirements.txt .
RUN grep -v "^frame-tracking\|^#\|^$" requirements.txt > /tmp/requirements_filtered.txt && \
    pip install --no-cache-dir --no-index --find-links /wheels -r /tmp/requirements_filtered.txt && \
    pip install -e /app/services/shared/frame-tracking && \
    rm -rf /wheels /tmp/requirements_filtered.txt

# Copy application code
COPY --chown=appuser:appuser services/frame-buffer/src/ ./

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
