#!/bin/bash
set -euo pipefail
shopt -s expand_aliases

# Deployment verification script for Nebula
# This script verifies all services are running and healthy

# Configuration
DEPLOY_DIR="/opt/detektor"
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

# Service endpoints to check
declare -A SERVICES=(
    ["example-otel"]="http://localhost:8005/health"
    ["frame-tracking"]="http://localhost:8006/health"
    ["echo-service"]="http://localhost:8007/health"
    ["base-template"]="http://localhost:8010/health"
    ["rtsp-capture"]="http://localhost:8001/health"
)

# Check if service is healthy
check_service_health() {
    local service_name=$1
    local endpoint=$2

    log "Checking $service_name health..."

    if curl -sf "$endpoint" > /dev/null 2>&1; then
        log "✓ $service_name is healthy"
        return 0
    else
        error "✗ $service_name health check failed"
        return 1
    fi
}

# Check Docker services
check_docker_services() {
    log "Checking Docker services..."

    local failed=0

    for service in "${!SERVICES[@]}"; do
        if docker compose ps "$service" | grep -q "Up (healthy)"; then
            log "✓ $service container is running and healthy"
        elif docker compose ps "$service" | grep -q "Up"; then
            warning "⚠ $service container is running but not yet healthy"
            ((failed++))
        else
            error "✗ $service container is not running"
            ((failed++))
        fi
    done

    return $failed
}

# Check infrastructure services
check_infrastructure() {
    log "Checking infrastructure services..."

    local failed=0

    # Check PostgreSQL
    if docker exec detektor-postgres-1 pg_isready -U detektor -d detektor_db > /dev/null 2>&1; then
        log "✓ PostgreSQL is healthy"
    else
        error "✗ PostgreSQL health check failed"
        ((failed++))
    fi

    # Check Redis
    if docker exec detektor-redis-1 redis-cli ping > /dev/null 2>&1; then
        log "✓ Redis is healthy"
    else
        error "✗ Redis health check failed"
        ((failed++))
    fi

    return $failed
}

# Show service logs for debugging
show_service_logs() {
    local service_name=$1
    log "Showing last 50 lines for $service_name..."
    docker compose logs --tail=50 "$service_name"
}

# Main verification function
verify_deployment() {
    log "Starting deployment verification..."

    cd "$DEPLOY_DIR"

    local total_failed=0

    # Check infrastructure first
    check_infrastructure || total_failed=$((total_failed + $?))

    # Check Docker services
    check_docker_services || total_failed=$((total_failed + $?))

    # Check individual service health endpoints
    for service in "${!SERVICES[@]}"; do
        check_service_health "$service" "${SERVICES[$service]}" || total_failed=$((total_failed + $?))
    done

    # Summary
    if [[ $total_failed -eq 0 ]]; then
        log "🎉 All services are running and healthy!"
        return 0
    else
        error "❌ $total_failed service(s) have issues"

        # Show logs for failed services
        log "Showing logs for failed services..."
        for service in "${!SERVICES[@]}"; do
            if ! curl -sf "${SERVICES[$service]}" > /dev/null 2>&1; then
                show_service_logs "$service"
            fi
        done

        return 1
    fi
}

# Clean up orphaned containers and images
cleanup_orphaned() {
    log "Cleaning up orphaned containers and images..."

    # Stop and remove stopped containers
    docker container prune -f

    # Remove unused images
    docker image prune -f

    # Remove unused networks
    docker network prune -f

    # Remove unused volumes (with caution)
    docker volume prune -f

    log "Cleanup completed"
}

# Wait for services to be ready
wait_for_services() {
    local max_attempts=30
    local attempt=1

    log "Waiting for services to be ready..."

    while [[ $attempt -le $max_attempts ]]; do
        if verify_deployment > /dev/null 2>&1; then
            log "All services are ready!"
            return 0
        fi

        log "Attempt $attempt/$max_attempts - services not ready yet, waiting 10s..."
        sleep 10
        ((attempt++))
    done

    error "Services failed to become ready within $max_attempts attempts"
    return 1
}

# Main execution
main() {
    case "${1:-verify}" in
        "verify")
            verify_deployment
            ;;
        "cleanup")
            cleanup_orphaned
            ;;
        "wait")
            wait_for_services
            ;;
        *)
            echo "Usage: $0 {verify|cleanup|wait}"
            echo "  verify - Check all services are healthy"
            echo "  cleanup - Remove orphaned containers and images"
            echo "  wait - Wait for all services to be ready"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
