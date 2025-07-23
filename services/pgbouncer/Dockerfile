FROM edoburu/pgbouncer:latest

# Install health check dependencies
USER root
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Custom PgBouncer configuration template
COPY pgbouncer.ini.template /etc/pgbouncer/

# Startup script to handle environment variables
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Switch back to pgbouncer user
USER pgbouncer

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD pg_isready -h localhost -p 5432 || exit 1

# Labels
LABEL org.opencontainers.image.source="https://github.com/hretheum/bezrobocie-detektor"
LABEL org.opencontainers.image.description="PgBouncer connection pooler for Detektor"
LABEL org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
