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

# Copy application code - ensure all subdirectories are included
COPY services/frame-buffer-v2/src/ ./src/

# Debug - list copied files
RUN find /app/src -name "*.py" | head -20

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
