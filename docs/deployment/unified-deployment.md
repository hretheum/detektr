# 🚀 Unified Deployment System

## Overview

The Detektor project now uses a unified deployment system that simplifies and standardizes deployments across all environments.

## Key Components

### 1. Unified Deployment Script
- **Location**: `/scripts/deploy.sh`
- **Purpose**: Single entry point for all deployment operations
- **Environments**: production, staging, local/development

### 2. Environment-Specific Configurations
- **Location**: `/docker/environments/`
- **Structure**:
  ```
  docker/environments/
  ├── production/     # Production with resource limits
  ├── staging/        # Staging with moderate limits
  └── development/    # Development with hot reload
  ```

### 3. GitHub Actions Integration
- **Workflow**: `.github/workflows/main-pipeline.yml`
- **Automated**: Build → Push to GHCR → Deploy via unified script

## Usage

### Basic Commands

```bash
# Deploy to environment
./scripts/deploy.sh [environment] deploy

# Check status
./scripts/deploy.sh [environment] status

# View logs
./scripts/deploy.sh [environment] logs

# Verify health
./scripts/deploy.sh [environment] verify

# Restart services
./scripts/deploy.sh [environment] restart

# Stop services
./scripts/deploy.sh [environment] stop

# Cleanup old images
./scripts/deploy.sh [environment] cleanup
```

### Environment-Specific Examples

#### Local Development
```bash
# Start local development stack
./scripts/deploy.sh local deploy

# Check health
./scripts/deploy.sh local verify

# View logs with follow
./scripts/deploy.sh local logs --follow
```

#### Staging
```bash
# Deploy to staging
./scripts/deploy.sh staging deploy

# Check specific service
./scripts/deploy.sh staging logs rtsp-capture
```

#### Production
```bash
# Deploy to production
./scripts/deploy.sh production deploy

# Verify all services
./scripts/deploy.sh production verify

# Cleanup old images (careful!)
./scripts/deploy.sh production cleanup
```

## Environment Features

### Production
- **Resource Limits**: Strict CPU/Memory limits
- **Logging**: JSON format with rotation
- **Data**: Persistent volumes with backup labels
- **GPU**: Enabled for AI services
- **Network**: External `detektor-network`
- **PostgreSQL**: Optimized configuration

### Staging
- **Resource Limits**: Moderate limits
- **Logging**: Debug level enabled
- **Data**: Separate volumes from production
- **GPU**: Disabled
- **Network**: Isolated `detektor-staging`

### Development
- **Resource Limits**: None (use all available)
- **Hot Reload**: Enabled for all services
- **Extra Tools**: Adminer, Redis Commander
- **Ports**: All services exposed locally
- **Volumes**: Code mounted for live editing

## CI/CD Integration

The deployment script is fully integrated with GitHub Actions:

```yaml
# In .github/workflows/main-pipeline.yml
- name: Deploy using unified script
  run: |
    /tmp/deploy.sh "$ENVIRONMENT" deploy
    /tmp/deploy.sh "$ENVIRONMENT" verify
```

## Configuration

### Environment Variables

Required for production:
```bash
GRAFANA_ADMIN_PASSWORD=secure_password
POSTGRES_PASSWORD=secure_password
IMAGE_TAG=latest
```

Development defaults are provided automatically.

### Docker Compose Files

The script automatically selects the right combination:

```bash
# Production
docker/base/docker-compose.yml
docker/base/docker-compose.storage.yml
docker/base/docker-compose.observability.yml
docker/environments/production/docker-compose.yml

# Staging
docker/base/docker-compose.yml
docker/base/docker-compose.storage.yml
docker/environments/staging/docker-compose.yml

# Development
docker/base/docker-compose.yml
docker/base/docker-compose.storage.yml
docker/base/docker-compose.observability.yml
docker/environments/development/docker-compose.yml
```

## Service Health Checks

The unified script checks these endpoints:

### Application Services
- example-otel: http://host:8005/health
- frame-tracking: http://host:8006/health
- echo-service: http://host:8007/health
- gpu-demo: http://host:8008/health
- rtsp-capture: http://host:8001/health
- base-template: http://host:8010/health

### Infrastructure
- Prometheus: http://host:9090/-/healthy
- Grafana: http://host:3000/api/health
- Jaeger: http://host:16686/

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   ```bash
   # Check SSH access
   ssh nebula echo "Connection OK"
   ```

2. **Services Not Starting**
   ```bash
   # Check logs
   ./scripts/deploy.sh production logs [service-name]
   ```

3. **Health Checks Failing**
   ```bash
   # Verify individually
   curl http://nebula:8005/health
   ```

4. **Resource Limits**
   ```bash
   # Check container resources
   docker stats
   ```

### Debug Mode

Enable debug output:
```bash
DEBUG=1 ./scripts/deploy.sh production deploy
```

## Migration from Old System

If you're migrating from the old deployment system:

1. **Stop old services**:
   ```bash
   cd /opt/detektor
   docker compose down
   ```

2. **Deploy with new system**:
   ```bash
   ./scripts/deploy.sh production deploy
   ```

3. **Verify migration**:
   ```bash
   ./scripts/deploy.sh production verify
   ```

## Best Practices

1. **Always verify after deployment**
2. **Use staging before production**
3. **Monitor resource usage**
4. **Keep secrets encrypted with SOPS**
5. **Regular cleanup of old images**
6. **Check logs for errors**

## Future Enhancements

- [ ] Blue-green deployments
- [ ] Automatic rollback on failure
- [ ] Deployment notifications
- [ ] Performance metrics dashboard
- [ ] Automated backup integration
