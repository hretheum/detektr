#!/bin/bash
set -euo pipefail

# Emergency fix for RTSP service - directly install missing package
# This can be run directly on nebula without rebuilding the entire image

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

main() {
    log "Starting emergency RTSP service fix..."

    # Check if RTSP container exists
    if ! docker ps -a --format '{{.Names}}' | grep -q "rtsp-capture"; then
        error "RTSP container not found. Starting service..."
        docker compose up -d rtsp-capture
        sleep 10
    fi

    # Get container ID
    CONTAINER_ID=$(docker ps --format '{{.Names}}' | grep "rtsp-capture" | head -1)

    if [ -z "$CONTAINER_ID" ]; then
        error "RTSP container not running"
        exit 1
    fi

    log "Found RTSP container: $CONTAINER_ID"

    # Install missing package directly in running container
    log "Installing missing opentelemetry-instrumentation-redis package..."
    docker exec "$CONTAINER_ID" pip install opentelemetry-instrumentation-redis==0.43b0

    # Verify package installation
    if docker exec "$CONTAINER_ID" python -c "import opentelemetry.instrumentation.redis; print('✓ Package installed successfully')"; then
        log "✓ Package installed and verified"
    else
        error "✗ Package installation failed"
        exit 1
    fi

    # Restart the service to apply changes
    log "Restarting RTSP service..."
    docker restart "$CONTAINER_ID"

    log "Waiting for service to restart..."
    sleep 15

    # Health check
    log "Performing health check..."
    if curl -sf http://localhost:8001/health >/dev/null; then
        log "✓ RTSP service is healthy!"
    else
        error "✗ Health check failed"
        docker logs "$CONTAINER_ID" 2>&1 | tail -10
    fi

    log "Emergency fix completed!"
}

main "$@"
