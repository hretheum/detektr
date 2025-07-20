#!/bin/bash
set -euo pipefail

# Deployment script for self-hosted runner
# This runs ON the runner and deploys TO Nebula

# Configuration from environment
NEBULA_HOST="${NEBULA_HOST:?NEBULA_HOST not set}"
NEBULA_USER="${NEBULA_USER:?NEBULA_USER not set}"
REGISTRY="${REGISTRY:-ghcr.io}"
IMAGE_PREFIX="${IMAGE_PREFIX:-hretheum/bezrobocie-detektor}"

# Services to deploy
SERVICES=(
    "example-otel"
    "frame-tracking"
    "base-template"
    "echo-service"
)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

# Check if we can reach Nebula
check_nebula_connectivity() {
    log "Checking connectivity to Nebula..."

    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        "${NEBULA_USER}@${NEBULA_HOST}" "echo 'Connected'" >/dev/null 2>&1; then
        log "Successfully connected to Nebula ✓"
    else
        error "Cannot connect to ${NEBULA_USER}@${NEBULA_HOST}"
        error "Check SSH configuration and network connectivity"
        exit 1
    fi
}

# Pull images locally on runner (for caching)
pull_images_locally() {
    log "Pulling images locally for cache..."

    for service in "${SERVICES[@]}"; do
        local image="${REGISTRY}/${IMAGE_PREFIX}/${service}:latest"
        log "Pulling ${service}..."

        if ! docker pull "$image"; then
            error "Failed to pull $image"
            exit 1
        fi
    done

    log "All images pulled to local cache ✓"
}

# Deploy to Nebula
deploy_to_nebula() {
    log "Deploying to Nebula..."

    # Execute deployment on Nebula
    ssh "${NEBULA_USER}@${NEBULA_HOST}" << 'DEPLOY_SCRIPT'
set -euo pipefail

# Colors for remote output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[NEBULA]${NC} $*"
}

error() {
    echo -e "${RED}[NEBULA ERROR]${NC} $*" >&2
}

# Configuration
DEPLOY_DIR="/opt/detektor"
REGISTRY="ghcr.io"
IMAGE_PREFIX="hretheum/bezrobocie-detektor"

# Ensure deployment directory
if [[ ! -d "$DEPLOY_DIR" ]]; then
    error "Deployment directory $DEPLOY_DIR does not exist"
    exit 1
fi

cd "$DEPLOY_DIR"

# Ensure Docker network exists
log "Creating Docker network..."
docker network create detektor-network 2>/dev/null || true

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

# Wait for infrastructure
log "Waiting for infrastructure to be ready..."
sleep 10

# Pull latest application images
log "Pulling application images..."
docker compose pull

# Deploy application services
log "Starting application services..."
docker compose up -d

# Wait for services to start
sleep 5

# Health check
log "Performing health checks..."
SERVICES=("example-otel:8005" "frame-tracking:8006" "base-template:8010" "echo-service:8007")
FAILED=0

for service_port in "${SERVICES[@]}"; do
    IFS=':' read -r service port <<< "$service_port"
    if curl -sf "http://localhost:${port}/health" >/dev/null 2>&1; then
        echo -e "  ✓ ${service} (port ${port})"
    else
        echo -e "  ✗ ${service} (port ${port})"
        FAILED=$((FAILED + 1))
    fi
done

# Check infrastructure
if curl -sf "http://localhost:9090/-/healthy" >/dev/null 2>&1; then
    echo -e "  ✓ Prometheus (port 9090)"
else
    echo -e "  ✗ Prometheus (port 9090)"
fi

if curl -sf "http://localhost:16686/" >/dev/null 2>&1; then
    echo -e "  ✓ Jaeger (port 16686)"
else
    echo -e "  ✗ Jaeger (port 16686)"
fi

if curl -sf "http://localhost:3000/" >/dev/null 2>&1; then
    echo -e "  ✓ Grafana (port 3000)"
else
    echo -e "  ✗ Grafana (port 3000)"
fi

# Summary
if [[ $FAILED -eq 0 ]]; then
    log "All services deployed successfully! 🎉"
else
    error "$FAILED services failed health checks"
    log "Check logs with: docker compose logs [service-name]"
    exit 1
fi

# Show running containers
log "Running containers:"
docker compose ps

DEPLOY_SCRIPT
}

# Cleanup old images on Nebula
cleanup_nebula() {
    log "Cleaning up old images on Nebula..."

    ssh "${NEBULA_USER}@${NEBULA_HOST}" << 'CLEANUP_SCRIPT'
# Remove unused images
docker image prune -f >/dev/null 2>&1 || true

# Remove images older than 7 days
docker images --format "{{.Repository}}:{{.Tag}}\t{{.CreatedSince}}" | \
    grep "weeks\|months" | \
    awk '{print $1}' | \
    xargs -r docker rmi 2>/dev/null || true
CLEANUP_SCRIPT

    log "Cleanup completed ✓"
}

# Main deployment flow
main() {
    log "Starting deployment from self-hosted runner to Nebula..."
    log "Target: ${NEBULA_USER}@${NEBULA_HOST}"

    check_nebula_connectivity
    pull_images_locally
    deploy_to_nebula
    cleanup_nebula

    log "Deployment completed successfully! 🚀"
}

# Run main
main "$@"
