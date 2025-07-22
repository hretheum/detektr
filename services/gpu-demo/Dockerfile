# Multi-stage optimized build for GPU demo service
# Optimized for faster builds with wheel caching

# Stage 1: Download wheels separately for better caching
FROM python:3.11-slim AS wheel-downloader

WORKDIR /wheels

# Copy only requirements to maximize cache hit
COPY services/gpu-demo/requirements.txt .

# Download wheels without installing - this can be cached
RUN pip download --only-binary :all: -d /wheels -r requirements.txt || \
    pip download -d /wheels -r requirements.txt

# Stage 2: Builder with pre-downloaded wheels
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy wheels from previous stage
COPY --from=wheel-downloader /wheels /wheels

# Copy requirements
COPY services/gpu-demo/requirements.txt .

# Install from pre-downloaded wheels (much faster)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --find-links /wheels -r requirements.txt

# Production stage - using slim image for fast builds
# Note: This won't have CUDA support out of the box
# For GPU support, use nvidia/cuda base image
FROM python:3.11-slim

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y \
    # OpenCV minimal dependencies
    libglib2.0-0 \
    libgl1-mesa-glx \
    libgomp1 \
    # System monitoring
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code - context is project root
COPY --chown=appuser:appuser services/gpu-demo/ .

# Create directory for model cache
RUN mkdir -p /app/.cache && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8008

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=gpu-demo
ENV SERVICE_VERSION=0.1.0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8008/health || exit 1

# Run the application
CMD ["python3", "-u", "main.py"]
