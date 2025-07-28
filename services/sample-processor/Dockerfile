FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules first
COPY services/shared /app/services/shared

# Copy processor code
COPY services/sample-processor/src /app/services/sample-processor/src

# Set Python path to include app directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8099/health')" || exit 1

# Run the processor
CMD ["python", "-m", "services.sample_processor.src.main"]
