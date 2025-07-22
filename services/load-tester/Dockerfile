FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    redis[hiredis]==5.0.1 \
    psutil==5.9.6

# Copy load test script
COPY load_test_broker.py /app/
RUN chmod +x /app/load_test_broker.py

# Run load test
ENTRYPOINT ["python", "-u", "/app/load_test_broker.py"]
