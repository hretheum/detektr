# Multi-stage build for smaller final image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash detektor

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/detektor/.local

# Copy application code
COPY --chown=detektor:detektor src/ ./src/
COPY --chown=detektor:detektor config/ ./config/

# Set Python path
ENV PYTHONPATH=/app
ENV PATH=/home/detektor/.local/bin:$PATH

# Switch to non-root user
USER detektor

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import src; print('OK')" || exit 1

# Default command (override in docker-compose)
CMD ["python", "-m", "src.interfaces.api"]