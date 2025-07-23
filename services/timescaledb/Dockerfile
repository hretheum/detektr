# TimescaleDB with Detektor schema and migrations
FROM timescale/timescaledb:latest-pg15

# Install additional tools
RUN apt-get update && apt-get install -y \
    postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*

# Copy initialization scripts
COPY ./services/timescaledb/scripts/00-init-extensions.sql /docker-entrypoint-initdb.d/
COPY ./services/timescaledb/scripts/01-create-schemas.sql /docker-entrypoint-initdb.d/
COPY ./services/timescaledb/scripts/02-create-hypertables.sql /docker-entrypoint-initdb.d/
COPY ./services/timescaledb/scripts/03-create-continuous-aggregates.sql /docker-entrypoint-initdb.d/
COPY ./services/timescaledb/scripts/04-create-policies.sql /docker-entrypoint-initdb.d/
COPY ./services/timescaledb/scripts/05-create-indexes.sql /docker-entrypoint-initdb.d/

# Copy migration scripts
COPY ./services/timescaledb/migrations /migrations

# Set proper permissions
RUN chmod -R 755 /docker-entrypoint-initdb.d

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-detektor} || exit 1

# Labels for GitHub registry
LABEL org.opencontainers.image.source="https://github.com/hretheum/bezrobocie-detektor"
LABEL org.opencontainers.image.description="TimescaleDB for Detektor project with schema and migrations"
LABEL org.opencontainers.image.licenses="MIT"
