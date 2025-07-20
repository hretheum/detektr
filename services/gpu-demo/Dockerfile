# Multi-stage build for GPU demo service
# Uses NVIDIA CUDA base image for GPU support

# Build stage
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS builder

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /app

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching - context is project root
COPY services/gpu-demo/requirements.txt .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Install Python runtime and required libraries
RUN apt-get update && apt-get install -y \
    python3.11 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

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
