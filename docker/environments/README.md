# Environment-Specific Docker Compose Configurations

This directory contains environment-specific overrides for Docker Compose configurations.

## Structure

```
environments/
├── development/     # Local development with hot reload
├── staging/        # Staging environment
└── production/     # Production environment with resource limits
```

## Usage

Each environment configuration is designed to be used in combination with the base configurations:

### Development
```bash
docker compose \
  -f docker/base/docker-compose.yml \
  -f docker/base/docker-compose.storage.yml \
  -f docker/base/docker-compose.observability.yml \
  -f docker/environments/development/docker-compose.yml \
  up -d
```

Features:
- Hot reload enabled
- Debug logging
- All ports exposed for local access
- Additional development tools (Adminer, Redis Commander)
- No resource limits
- Volumes for code mounting

### Staging
```bash
docker compose \
  -f docker/base/docker-compose.yml \
  -f docker/base/docker-compose.storage.yml \
  -f docker/environments/staging/docker-compose.yml \
  up -d
```

Features:
- Moderate resource limits
- Debug logging
- Shorter data retention
- Separate data volumes from production

### Production
```bash
docker compose \
  -f docker/base/docker-compose.yml \
  -f docker/base/docker-compose.storage.yml \
  -f docker/base/docker-compose.observability.yml \
  -f docker/environments/production/docker-compose.yml \
  up -d
```

Features:
- Strict resource limits
- Production logging levels
- Long-term data retention
- Volume backup labels
- Optimized PostgreSQL configuration
- GPU support for AI services

## Environment Variables

Each environment expects certain environment variables:

### Common
- `IMAGE_TAG`: Docker image tag (default: latest/staging/dev)
- `COMPOSE_PROJECT_NAME`: Project name (default: detektor)

### Production
- `GRAFANA_ADMIN_PASSWORD`: Grafana admin password
- Various service-specific production configs

### Development
- Uses default passwords for easy local development
- All services accessible on localhost

## Resource Limits

### Production
- Application services: 512MB-2GB RAM
- PostgreSQL: 2GB RAM, 2 CPUs
- Redis: 1.5GB RAM, 1 CPU
- Monitoring: 512MB-2GB RAM

### Staging
- Application services: 256MB-1GB RAM
- PostgreSQL: 1GB RAM, 1 CPU
- Redis: 768MB RAM, 0.5 CPU
- Monitoring: 256MB-1GB RAM

### Development
- No limits (uses all available resources)

## Convenience Scripts

Use the provided scripts for easier deployment:

```bash
# Development
./docker/dev.sh up -d

# Production
./docker/prod.sh up -d

# Or use the unified deployment script
./scripts/deploy.sh [environment] deploy
```
