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

# Copy requirements
COPY services/rtsp-capture/requirements.txt .
COPY services/rtsp-capture/requirements-docker.txt .

# Build wheels for dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

# Install minimal runtime dependencies
# OpenCV requires these libraries for video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Copy requirements
COPY services/rtsp-capture/requirements.txt .
COPY services/rtsp-capture/requirements-docker.txt .

# Install dependencies from wheels
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --no-index --find-links /wheels -r requirements.txt && \
    rm -rf /wheels

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser services/rtsp-capture/src/ ./

# Copy frame-tracking source
COPY --chown=appuser:appuser services/shared/frame-tracking /app/services/shared/frame-tracking

# Install frame-tracking in development mode
RUN pip install -e /app/services/shared/frame-tracking

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Health check using curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
