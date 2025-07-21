#!/bin/bash
set -euo pipefail

# Temporary fix script for RTSP service deployment
# This script addresses the missing opentelemetry-instrumentation-redis dependency

# Configuration
REGISTRY="${REGISTRY:-ghcr.io}"
IMAGE_PREFIX="${IMAGE_PREFIX:-hretheum/bezrobocie-detektor}"
RTSP_IMAGE="${REGISTRY}/${IMAGE_PREFIX}/rtsp-capture:latest"

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

# Main fix function
main() {
    log "Starting RTSP service deployment fix..."

    # Navigate to project root
    cd "$(dirname "$0")/.."

    log "Building RTSP service with no cache to ensure fresh dependencies..."

    # Build the RTSP service with no cache
    docker build \
        --no-cache \
        -t rtsp-capture:fix \
        -f services/rtsp-capture/Dockerfile \
        services/rtsp-capture/

    log "Verifying the package is installed in the built image..."

    # Test the package import in the container
    if docker run --rm rtsp-capture:fix python -c "import opentelemetry.instrumentation.redis; print('✓ Redis instrumentation package verified')"; then
        log "✓ Package verification successful!"
    else
        error "✗ Package verification failed - package not found in container"
        exit 1
    fi

    log "Tagging image for registry..."
    docker tag rtsp-capture:fix "${RTSP_IMAGE}"

    log "Optionally pushing to registry..."
    read -p "Push image to registry? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if docker push "${RTSP_IMAGE}"; then
            log "✓ Image pushed successfully"
        else
            error "✗ Failed to push image"
            exit 1
        fi
    fi

    log "Stopping and removing existing RTSP container..."
    docker compose stop rtsp-capture 2>/dev/null || true
    docker compose rm -f rtsp-capture 2>/dev/null || true

    log "Starting RTSP service with updated image..."
    docker compose up -d rtsp-capture

    log "Waiting for service to start..."
    sleep 15

    log "Performing health check..."
    if curl -sf http://localhost:8001/health >/dev/null; then
        log "✓ RTSP service is healthy and running!"
    else
        error "✗ RTSP service health check failed"
        docker logs detektor-rtsp-capture-1 2>&1 | tail -20
        exit 1
    fi

    log "RTSP service deployment fix completed successfully!"
}

# Run main function
main "$@"
