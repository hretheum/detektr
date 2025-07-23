FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir asyncpg

# Copy benchmark script
COPY benchmark.py /app/

# Make executable
RUN chmod +x /app/benchmark.py

CMD ["python", "/app/benchmark.py"]
