# Docker Compose Hierarchical Structure

This directory contains the reorganized Docker Compose configuration for the Detektor project.

## Directory Structure

```
docker/
├── base/                      # Base service definitions
│   ├── docker-compose.yml     # Core application services
│   ├── docker-compose.storage.yml    # Storage services (Redis, PostgreSQL)
│   ├── docker-compose.observability.yml  # Monitoring stack
│   ├── config/               # Configuration files
│   └── init-scripts/         # Database initialization scripts
├── environments/             # Environment-specific overrides
│   ├── development/          # Development settings
│   ├── staging/              # Staging settings
│   └── production/           # Production settings
└── features/                 # Optional feature sets
    ├── gpu/                  # GPU-enabled services
    ├── redis-ha/             # Redis High Availability
    └── ai-services/          # Additional AI services
```

## Usage Examples

### Development Environment

Full stack with hot reload and development tools:

```bash
docker-compose \
  -f docker/base/docker-compose.yml \
  -f docker/base/docker-compose.storage.yml \
  -f docker/base/docker-compose.observability.yml \
  -f docker/environments/development/docker-compose.override.yml \
  up -d
```

Or use the convenience script:
```bash
./docker/dev.sh up -d
```

### Production Environment

Optimized settings with resource limits:

```bash
docker-compose \
  -f docker/base/docker-compose.yml \
  -f docker/base/docker-compose.storage.yml \
  -f docker/base/docker-compose.observability.yml \
  -f docker/environments/production/docker-compose.override.yml \
  up -d
```

Or use the convenience script:
```bash
./docker/prod.sh up -d
```

### With GPU Support

Add GPU-enabled AI services:

```bash
docker-compose \
  -f docker/base/docker-compose.yml \
  -f docker/base/docker-compose.storage.yml \
  -f docker/features/gpu/docker-compose.gpu.yml \
  up -d
```

### With Redis High Availability

Enable Redis Sentinel for HA:

```bash
docker-compose \
  -f docker/base/docker-compose.yml \
  -f docker/features/redis-ha/docker-compose.redis-ha.yml \
  up -d
```

### Minimal Setup

Just core services without storage or monitoring:

```bash
docker-compose -f docker/base/docker-compose.yml up -d
```

## Service Organization

### Base Services (`docker-compose.yml`)
- rtsp-capture
- frame-buffer
- frame-tracking
- metadata-storage
- example-otel (profile: examples)
- echo-service (profile: examples)

### Storage Services (`docker-compose.storage.yml`)
- redis
- postgres (TimescaleDB)
- redis-exporter (profile: monitoring)
- postgres-exporter (profile: monitoring)

### Observability Stack (`docker-compose.observability.yml`)
- jaeger
- prometheus
- grafana
- alertmanager (profile: monitoring)
- node-exporter (profile: monitoring)
- cadvisor (profile: monitoring)

### GPU Services (`features/gpu/docker-compose.gpu.yml`)
- face-recognition
- object-detection
- gpu-demo
- nvidia-gpu-exporter

### AI Services (`features/ai-services/docker-compose.ai.yml`)
- llm-intent
- gesture-detection
- audio-analysis
- scene-understanding
- ha-bridge
- telegram-alerts

## Convenience Scripts

- `docker/dev.sh` - Development environment wrapper
- `docker/prod.sh` - Production environment wrapper
- `docker/test.sh` - Test runner wrapper

Examples:
```bash
# Start development
./docker/dev.sh up -d

# View logs
./docker/dev.sh logs -f rtsp-capture

# Stop all services
./docker/dev.sh down

# Run tests
./docker/test.sh rtsp-capture pytest
```

## Migration from Old Structure

If you're migrating from the old structure, run:

```bash
./scripts/migrate-docker-compose.sh
```

This will:
1. Backup existing docker-compose files
2. Create new directory structure
3. Migrate configuration files
4. Create convenience scripts
5. Update Makefile with new targets

## Environment Variables

All services use environment variables from `.env` file (encrypted with SOPS).

Common variables:
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `GRAFANA_USER`, `GRAFANA_PASSWORD`
- Service-specific API keys and settings

## Profiles

Docker Compose profiles are used to control which services start:

- `examples` - Example services (example-otel, echo-service)
- `monitoring` - Extended monitoring services
- `backup` - Backup services

Enable profiles:
```bash
docker-compose --profile monitoring up -d
```

## Resource Management

Production environment includes resource limits:
- CPU limits and reservations
- Memory limits and reservations
- Restart policies
- Health checks with proper timings

## Networking

All services use the `detektor-network` which must be created first:

```bash
docker network create detektor-network
```

## Volumes

Persistent data volumes:
- `redis-data` - Redis persistence
- `postgres-data` - PostgreSQL data
- `prometheus-data` - Metrics history
- `grafana-data` - Dashboards and settings
- Model volumes for AI services

## Best Practices

1. **Development**: Use development override for hot reload and debugging
2. **Production**: Always use production override with proper resource limits
3. **Secrets**: Never commit unencrypted `.env` files
4. **Updates**: Pull latest images before deploying
5. **Monitoring**: Always include observability stack in production
6. **Backups**: Enable backup profile in production environments
