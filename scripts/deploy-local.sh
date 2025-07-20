#!/bin/bash
set -euo pipefail

# Script for local deployment on Nebula via self-hosted runner
# This script is executed by the GitHub Actions runner on the Nebula server

# Configuration
DEPLOY_DIR="/opt/detektor"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# Ensure we're in the deployment directory
cd ${DEPLOY_DIR} || {
    error "Cannot access deployment directory: ${DEPLOY_DIR}"
    exit 1
}

log "Starting deployment in ${DEPLOY_DIR}..."

# Stop old containers
log "Stopping old containers..."
docker compose down || true

# Create docker-compose.prod.yml
log "Creating production docker-compose file..."
cat > docker-compose.prod.yml << 'EOF'
services:
  example-otel:
    image: ghcr.io/hretheum/bezrobocie-detektor/example-otel:latest
    container_name: example-otel
    ports:
      - "8005:8005"
    environment:
      - SERVICE_NAME=example-otel
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
    networks:
      - detektor-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frame-tracking:
    image: ghcr.io/hretheum/bezrobocie-detektor/frame-tracking:latest
    container_name: frame-tracking
    ports:
      - "8006:8006"
    environment:
      - SERVICE_NAME=frame-tracking
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
    networks:
      - detektor-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8006/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  base-template:
    image: ghcr.io/hretheum/bezrobocie-detektor/base-template:latest
    container_name: base-template
    ports:
      - "8010:8010"
    environment:
      - SERVICE_NAME=base-template
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
    networks:
      - detektor-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  echo-service:
    image: ghcr.io/hretheum/bezrobocie-detektor/echo-service:latest
    container_name: echo-service
    ports:
      - "8007:8007"
    environment:
      - SERVICE_NAME=echo-service
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
    networks:
      - detektor-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8007/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  detektor-network:
    external: true
EOF

# Ensure network exists
log "Creating Docker network..."
docker network create detektor-network 2>/dev/null || true

# Infrastructure files should already be in deployment directory
# (copied by the workflow)

# Start infrastructure services
log "Starting infrastructure services..."
if [[ -f docker-compose.observability.yml ]]; then
    docker compose -f docker-compose.observability.yml up -d
else
    error "docker-compose.observability.yml not found"
fi

if [[ -f docker-compose.storage.yml ]]; then
    docker compose -f docker-compose.storage.yml up -d
else
    error "docker-compose.storage.yml not found"
fi

# Wait for infrastructure to be ready
log "Waiting for infrastructure services to start..."
sleep 15

# Deploy application services
log "Deploying application services..."
docker compose -f docker-compose.prod.yml up -d

# Wait for services to start
log "Waiting for services to start..."
sleep 10

# Health check
log "Performing health checks..."
FAILED=0

# Application services
for service_port in "example-otel:8005" "frame-tracking:8006" "base-template:8010" "echo-service:8007"; do
    IFS=':' read -r service port <<< "$service_port"
    if curl -sf "http://localhost:${port}/health" >/dev/null 2>&1; then
        echo -e "  ✅ ${service} (port ${port})"
    else
        echo -e "  ❌ ${service} (port ${port})"
        FAILED=$((FAILED + 1))
    fi
done

# Infrastructure services
echo ""
log "Checking infrastructure services..."
if curl -sf "http://localhost:9090/-/healthy" >/dev/null 2>&1; then
    echo -e "  ✅ Prometheus (port 9090)"
else
    echo -e "  ❌ Prometheus (port 9090)"
fi

if curl -sf "http://localhost:16686/" >/dev/null 2>&1; then
    echo -e "  ✅ Jaeger (port 16686)"
else
    echo -e "  ❌ Jaeger (port 16686)"
fi

if curl -sf "http://localhost:3000/api/health" >/dev/null 2>&1; then
    echo -e "  ✅ Grafana (port 3000)"
else
    echo -e "  ❌ Grafana (port 3000)"
fi

# Summary
echo ""
if [[ $FAILED -eq 0 ]]; then
    log "All services deployed successfully! 🎉"
else
    error "$FAILED services failed health checks"
    log "Check logs with: docker compose logs [service-name]"
    exit 1
fi

# Show running containers
echo ""
log "Running containers:"
docker compose -f docker-compose.prod.yml ps

# Clean up old images
log "Cleaning up old images..."
docker image prune -f >/dev/null 2>&1 || true

log "Deployment completed! ✅"
