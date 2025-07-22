FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    aiohttp==3.9.1 \
    docker==7.0.0 \
    redis==5.0.1 \
    psutil==5.9.6

# Copy monitoring script and dependencies
COPY services/telegram-alerts/telegram-monitor.py /app/
COPY services/telegram-alerts/redis_sentinel.py /app/

# Make executable
RUN chmod +x /app/telegram-monitor.py

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import psutil; print('OK')" || exit 1

# Run monitor
CMD ["python", "-u", "/app/telegram-monitor.py"]
