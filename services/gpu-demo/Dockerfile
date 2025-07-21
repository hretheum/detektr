# Multi-stage build for GPU demo service
# Optimized for faster builds - models downloaded at runtime

# Use slim Python image for faster builds
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching - context is project root
COPY services/gpu-demo/requirements.txt .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage - using slim image for fast builds
# Note: This won't have CUDA support out of the box
# For GPU support, use nvidia/cuda base image
FROM python:3.11-slim

# Install runtime dependencies for OpenCV and GUI libraries
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    libglu1-mesa \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxss1 \
    libgtk-3-0 \
    libasound2 \
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
