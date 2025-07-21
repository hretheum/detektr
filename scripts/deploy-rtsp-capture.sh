#!/bin/bash
# RTSP Capture Service Deployment Script
# This script deploys the RTSP capture service using CI/CD pipeline

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

# Main deployment function
main() {
    log "Starting RTSP Capture Service deployment via CI/CD..."
    log "Using unified deployment process from docs/deployment/"

    # Check if we're running on Nebula
    if [[ "$(hostname)" != "nebula" ]]; then
        error "This script should only be run on Nebula server!"
        error "Current hostname: $(hostname)"
        exit 1
    fi

    log "✓ Running on Nebula server"

    # Update documentation status
    log "RTSP Capture Service deployment is now handled by CI/CD pipeline"
    log "See: docs/deployment/services/rtsp-capture.md for full instructions"

    log "To deploy RTSP capture service:"
    log "1. Ensure code is committed"
    log "2. Run: git push origin main"
    log "3. Monitor GitHub Actions at: https://github.com/hretheum/bezrobocie-detektor/actions"

    # Check if service is already running
    if docker ps | grep -q "rtsp-capture"; then
        log "✓ RTSP capture service is currently running"
        docker ps | grep "rtsp-capture"
    else
        log "ℹ RTSP capture service is not running - will be deployed via CI/CD"
    fi

    # Health check endpoint
    log "Health check endpoint: http://localhost:8080/health"
    log "Metrics endpoint: http://localhost:8080/metrics"

    log "Deployment via CI/CD is ready!"
    log "See docs/deployment/services/rtsp-capture.md for troubleshooting"
}

# Execute main function
main "$@"
