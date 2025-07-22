FROM redis:7-alpine

# Copy custom Redis configuration
COPY config/redis.conf /usr/local/etc/redis/redis.conf

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD redis-cli ping || exit 1

# Run Redis with custom config
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
# Force CI/CD trigger
