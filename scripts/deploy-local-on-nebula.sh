#!/bin/bash
set -euo pipefail

# Deployment script for running LOCALLY on Nebula (from self-hosted runner)
# This executes directly on the Nebula server, no SSH needed

# Configuration
DEPLOY_DIR="/opt/detektor"
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

# Main deployment
main() {
    log "Starting LOCAL deployment on Nebula..."

    # Check if running on Nebula
    if [[ $(hostname) != "nebula" ]]; then
        error "This script should only run on Nebula server!"
        exit 1
    fi

    # Check deployment directory
    if [[ ! -d "$DEPLOY_DIR" ]]; then
        error "Deployment directory $DEPLOY_DIR does not exist"
        exit 1
    fi

    cd "$DEPLOY_DIR"
    log "Working in $DEPLOY_DIR"

    # Ensure Docker network exists
    log "Creating Docker network..."
    docker network create detektor-network 2>/dev/null || true

    # Start infrastructure services
    log "Starting infrastructure services..."
    if [[ -f docker-compose.observability.yml ]]; then
        docker compose -f docker-compose.observability.yml up -d
    else
        warning "docker-compose.observability.yml not found"
    fi

    if [[ -f docker-compose.storage.yml ]]; then
        docker compose -f docker-compose.storage.yml up -d
    else
        warning "docker-compose.storage.yml not found"
    fi

    # Wait for infrastructure
    log "Waiting for infrastructure to be ready..."
    sleep 10

    # Pull latest application images
    log "Pulling application images..."
    for service in "${SERVICES[@]}"; do
        local image="${REGISTRY}/${IMAGE_PREFIX}/${service}:latest"
        log "Pulling ${service}..."

        if ! docker pull "$image"; then
            error "Failed to pull $image"
            exit 1
        fi
    done

    # Deploy application services
    log "Starting application services..."
    docker compose up -d

    # Wait for services to start
    sleep 5

    # Health check
    log "Performing health checks..."
    local failed=0

    # Check example-otel
    if curl -sf http://localhost:8005/health >/dev/null; then
        log "✓ example-otel is healthy"
    else
        error "✗ example-otel health check failed"
        ((failed++))
    fi

    # Check frame-tracking
    if curl -sf http://localhost:8006/health >/dev/null; then
        log "✓ frame-tracking is healthy"
    else
        error "✗ frame-tracking health check failed"
        ((failed++))
    fi

    # Check echo-service
    if curl -sf http://localhost:8007/health >/dev/null; then
        log "✓ echo-service is healthy"
    else
        error "✗ echo-service health check failed"
        ((failed++))
    fi

    # Check base-template
    if curl -sf http://localhost:8010/health >/dev/null; then
        log "✓ base-template is healthy"
    else
        error "✗ base-template health check failed"
        ((failed++))
    fi

    # Check Redis
    if docker exec detektor-redis-1 redis-cli ping >/dev/null 2>&1; then
        log "✓ Redis is healthy"
    else
        error "✗ Redis health check failed"
        ((failed++))
    fi

    # Check PostgreSQL
    if docker exec detektor-postgres-1 pg_isready >/dev/null 2>&1; then
        log "✓ PostgreSQL is healthy"
    else
        error "✗ PostgreSQL health check failed"
        ((failed++))
    fi

    # Summary
    if [[ $failed -eq 0 ]]; then
        log "Deployment completed successfully! ✓"
    else
        error "Deployment completed with $failed failed health checks"
        exit 1
    fi

    # Show running services
    log "Currently running services:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep detektor
}

# Run main function
main "$@"
