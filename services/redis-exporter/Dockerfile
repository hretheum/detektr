# Using official redis_exporter image as base
FROM oliver006/redis_exporter:v1.55.0-alpine

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --spider -q http://localhost:9121/metrics || exit 1

# Run with default settings (configure via environment variables)
ENTRYPOINT ["/redis_exporter"]
