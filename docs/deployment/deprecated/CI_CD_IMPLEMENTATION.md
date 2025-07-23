# CI/CD Implementation - Detektor System

**Date**: 2025-07-20
**Status**: ✅ COMPLETED

## Overview

The Detektor project now has a fully automated CI/CD pipeline using GitHub Actions with a self-hosted runner deployed on the Nebula server. This enables automatic builds and deployments triggered by pushes to the main branch.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌───────────┐
│  Developer  │────▶│    GitHub    │────▶│ GitHub Actions  │────▶│   GHCR    │
│   (push)    │     │    (main)    │     │ (cloud build)   │     │ (images)  │
└─────────────┘     └──────────────┘     └─────────────────┘     └───────────┘
                                                                          │
                                          ┌─────────────────┐            │
                                          │  Self-hosted    │◀───────────┘
                                          │     Runner      │
                                          │   (on Nebula)   │
                                          └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │     Nebula      │
                                          │  (Production)   │
                                          └─────────────────┘
```

## Components

### 1. GitHub Actions Workflows

#### Build and Deploy Workflow (`.github/workflows/deploy.yml`)
- Triggers on push to main branch
- Builds Docker images for all services
- Pushes images to GitHub Container Registry (GHCR)
- Triggers deployment via self-hosted runner

#### Key Features:
- Matrix build strategy for parallel service builds
- Docker layer caching for faster builds
- Metadata extraction for proper tagging
- Conditional deployment (only on main branch)

### 2. Self-hosted Runner

#### Installation Details:
- **Location**: Nebula server (192.168.x.x)
- **User**: github-runner
- **Service**: systemd (actions.runner.hretheum-detektr.nebula-runner)
- **Version**: 2.326.0
- **Labels**: self-hosted, linux, x64, nebula

#### Configuration:
```bash
# Service status
sudo systemctl status actions.runner.hretheum-detektr.nebula-runner

# Service location
/home/github-runner/actions-runner/

# Runner configuration
- URL: https://github.com/hretheum/detektr
- Name: nebula-runner
- Work directory: _work
```

#### Security:
- Runs as dedicated user (github-runner)
- Full sudo access (NOPASSWD:ALL) in /etc/sudoers.d/github-runner
- Member of docker group for container management
- SSH keys not required (runs locally)

### 3. Deployment Script

#### `scripts/deploy-local.sh`
- Executed by self-hosted runner with sudo
- Creates docker-compose.prod.yml dynamically
- Manages service lifecycle (stop, pull, start)
- Performs health checks after deployment
- Cleans up old Docker images

#### Key Operations:
1. Stop old containers
2. Pull latest images from GHCR
3. Create production compose file
4. Start infrastructure services
5. Deploy application services
6. Run health checks
7. Report deployment status

### 4. Service Configuration

#### Port Mappings:
- example-otel: 8005 → 8000 (internal)
- frame-tracking: 8006 → 8006
- echo-service: 8007 → 8007
- base-template: 8010 → 8000 (internal)

#### Networks:
- detektor-network (external)
- All services connected to same network
- Infrastructure services accessible

## Deployment Flow

### 1. Developer Push
```bash
git add .
git commit -m "feat: new feature"
git push origin main
```

### 2. GitHub Actions (Cloud)
- Receives webhook from push
- Starts workflow on ubuntu-latest runners
- Builds all service images in parallel
- Pushes to ghcr.io/hretheum/detektr/*

### 3. Self-hosted Runner (Nebula)
- Picks up deployment job
- Pulls latest images from GHCR
- Executes deploy-local.sh with sudo
- Reports status back to GitHub

### 4. Verification
```bash
# Check deployment status
ssh nebula "cd /opt/detektor && docker compose ps"

# Check service health
for port in 8005 8006 8007 8010; do
  ssh nebula "curl -s http://localhost:$port/health | jq"
done
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Runner Offline
```bash
# Check service
sudo systemctl status actions.runner.hretheum-detektr.nebula-runner

# Restart if needed
sudo systemctl restart actions.runner.hretheum-detektr.nebula-runner

# Check logs
sudo journalctl -u actions.runner.hretheum-detektr.nebula-runner -f
```

#### 2. Build Failures
- Check Dockerfile paths (must be relative to repo root)
- Verify all COPY commands use correct context
- Ensure requirements.txt files are up to date

#### 3. Deployment Failures
- Verify port availability (no conflicts)
- Check docker-compose.prod.yml syntax
- Ensure all required networks exist
- Verify GHCR authentication

#### 4. Service Health Check Failures
- Check internal vs external port mappings
- Verify health check endpoints match service configuration
- Review service logs: `docker logs <service-name>`

## Maintenance

### Regular Tasks

#### 1. Update Runner (Monthly)
```bash
# GitHub will notify when update available
# Runner auto-updates during quiet period
```

#### 2. Clean Docker Cache (Weekly)
```bash
ssh nebula "docker system prune -af --volumes"
ssh nebula "docker image prune -af"
```

#### 3. Monitor Disk Space
```bash
ssh nebula "df -h /var/lib/docker"
```

#### 4. Review Deployment Logs
```bash
# GitHub Actions logs retained for 90 days
# Download important logs for long-term storage
```

## Security Considerations

### 1. Secrets Management
- All secrets in GitHub Secrets
- No hardcoded values in workflows
- SOPS for local secret encryption

### 2. Network Security
- Runner only accessible within local network
- No external SSH access required
- GHCR uses token authentication

### 3. Access Control
- Runner has minimal required permissions
- Deployment directory owned by appropriate user
- Service containers run as non-root

## Future Improvements

### 1. Deployment Strategies
- [ ] Blue-green deployments
- [ ] Canary releases
- [ ] Rollback mechanisms

### 2. Monitoring
- [ ] Deployment metrics to Prometheus
- [ ] Grafana dashboard for CI/CD
- [ ] Alert on deployment failures

### 3. Optimization
- [ ] Multi-architecture builds (arm64)
- [ ] Build cache optimization
- [ ] Parallel deployment strategies

## Conclusion

The CI/CD implementation provides a robust, automated deployment pipeline that:
- Reduces manual intervention
- Ensures consistent deployments
- Maintains security best practices
- Enables rapid iteration

The self-hosted runner solution elegantly solves the local network access problem while maintaining the benefits of GitHub Actions integration.
