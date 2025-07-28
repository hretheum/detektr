# Frame Buffer v2 - Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/frame-buffer-v2/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code including all subdirectories
COPY services/frame-buffer-v2/src/ ./src/

# Force creation of models directory and copy __init__.py content
RUN mkdir -p /app/src/models

# Copy models __init__.py separately to ensure it exists
COPY services/frame-buffer-v2/src/models/__init__.py /app/src/models/__init__.py

# Debug - verify everything is in place
RUN echo "=== Final directory structure ===" && \
    find /app/src -type d | sort && \
    echo "=== All Python files ===" && \
    find /app/src -name "*.py" | wc -l && \
    echo "=== Models directory content ===" && \
    ls -la /app/src/models/ && \
    echo "=== Test import ===" && \
    cd /app && python -c "from src.models import FrameReadyEvent; print('Import successful!')"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8002/health').raise_for_status()"

# Expose port
EXPOSE 8002

# Run the application
CMD ["python", "-m", "src.main"]
