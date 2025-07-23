# Manual Deployment Guide

## Overview

Due to network architecture (GitHub Actions cannot access local Nebula server), we use a **manual deployment** approach:

1. **GitHub Actions**: Builds and pushes Docker images to GHCR
2. **Nebula Server**: Pulls images and deploys services locally

## Quick Start

### 1. On GitHub (Automatic)
```bash
git push origin main
# ✓ GitHub Actions builds and pushes images to ghcr.io
```

### 2. On Nebula Server (Manual)
```bash
# Pull latest code
git pull origin main

# Deploy all services
./scripts/manual-deploy.sh
```

## Manual Deploy Script

The `./scripts/manual-deploy.sh` script handles:

- ✅ Authentication with GitHub Container Registry
- ✅ Pulling latest Docker images
- ✅ Setting up environment (SOPS decryption if available)
- ✅ Generating production docker-compose.yml
- ✅ Starting infrastructure services (Prometheus, Jaeger, PostgreSQL)
- ✅ Deploying application services
- ✅ Health check verification
- ✅ Cleanup

## Script Usage

### Full Deployment
```bash
./scripts/manual-deploy.sh
```

### Partial Operations
```bash
# Pull images only
./scripts/manual-deploy.sh pull

# Deploy only (if images already pulled)
./scripts/manual-deploy.sh deploy

# Verify deployment only
./scripts/manual-deploy.sh verify
```

## Prerequisites

### On Nebula Server

1. **Docker installed and running**
   ```bash
   docker --version
   docker ps
   ```

2. **GitHub Container Registry authentication**
   ```bash
   # Create GitHub Personal Access Token with 'packages:read' scope
   docker login ghcr.io
   # Username: your-github-username
   # Password: ghp_your_token_here
   ```

3. **Project cloned**
   ```bash
   git clone https://github.com/hretheum/detektr.git /opt/detektor
   cd /opt/detektor
   ```

4. **SOPS for secrets (optional but recommended)**
   ```bash
   # Install SOPS
   wget https://github.com/getsops/sops/releases/download/v3.8.1/sops-v3.8.1.linux.amd64
   sudo mv sops-v3.8.1.linux.amd64 /usr/local/bin/sops
   sudo chmod +x /usr/local/bin/sops

   # Install age for encryption
   wget https://github.com/FiloSottile/age/releases/download/v1.1.1/age-v1.1.1-linux-amd64.tar.gz
   tar xzf age-v1.1.1-linux-amd64.tar.gz
   sudo mv age/age /usr/local/bin/
   sudo mv age/age-keygen /usr/local/bin/

   # Set SOPS_AGE_KEY environment variable
   export SOPS_AGE_KEY="AGE-SECRET-KEY-..."
   ```

## Services Deployed

### Application Services
- **example-otel**: Port 8005 - Example service with full observability
- **frame-tracking**: Port 8006 - Frame tracking with PostgreSQL
- **base-template**: Port 8010 - Template service with all patterns
- **echo-service**: Port 8007 - Simple echo service

### Infrastructure Services
- **Prometheus**: Port 9090 - Metrics collection
- **Jaeger**: Port 16686 - Distributed tracing
- **Grafana**: Port 3000 - Metrics visualization
- **PostgreSQL**: Port 5432 - Database
- **Redis**: Port 6379 - Cache and queuing

## Troubleshooting

### Authentication Issues
```bash
# Re-authenticate with GHCR
docker login ghcr.io

# Check if images exist
docker pull ghcr.io/hretheum/detektr/example-otel:latest
```

### Service Health Issues
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs example-otel

# Check individual service
curl http://localhost:8005/health

# Restart service
docker compose -f docker-compose.prod.yml restart example-otel
```

### Environment Issues
```bash
# Check if .env is decrypted properly
cat .env.local  # Should show decrypted values

# Manual environment setup
export DATABASE_URL="postgresql://..."
export OTEL_EXPORTER_OTLP_ENDPOINT="http://jaeger:4317"
```

### Network Issues
```bash
# Check Docker networks
docker network ls
docker network inspect detektor-network

# Recreate network
docker network rm detektor-network
docker network create detektor-network
```

## Complete Reset

If deployment gets into bad state:

```bash
# Stop all services
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.observability.yml down
docker compose -f docker-compose.storage.yml down

# Remove all containers and volumes
docker compose -f docker-compose.prod.yml down --rmi all -v

# Clean up Docker
docker system prune -a

# Start fresh
./scripts/manual-deploy.sh
```

## Development Workflow

### 1. Make Changes
```bash
# Edit code locally
vim services/example-otel/main.py
```

### 2. Test & Commit
```bash
git add .
git commit -m "feat: some improvement"
git push origin main
```

### 3. Wait for Build
```bash
# Check GitHub Actions
gh run list
# Wait for build to complete
```

### 4. Deploy
```bash
# On Nebula
git pull origin main
./scripts/manual-deploy.sh
```

## Future Improvements

### Option 1: Self-hosted Runner
```bash
# Install GitHub Actions runner on Nebula
# This would enable automatic deployment again
```

### Option 2: Webhook-based Deploy
```bash
# GitHub Actions → Webhook → Nebula
# Nebula pulls and deploys when notified
```

### Option 3: GitOps with ArgoCD
```bash
# Full GitOps workflow with ArgoCD
# Automatic sync of desired state
```

For now, manual deployment provides:
- ✅ Reliable builds in GitHub Actions
- ✅ Full control over deployment timing
- ✅ Easy debugging and troubleshooting
- ✅ No network connectivity issues
