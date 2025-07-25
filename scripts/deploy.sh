#!/bin/bash
# deploy.sh - Unified deployment script for Detektor project
#
# Usage:
#   ./scripts/deploy.sh [environment] [action] [options]
#
# Examples:
#   ./scripts/deploy.sh production deploy
#   ./scripts/deploy.sh staging status
#   ./scripts/deploy.sh local logs --follow
#
# Environments: production, staging, local
# Actions: deploy, status, logs, restart, rollback, cleanup

set -euo pipefail

# Always use consistent project name
export COMPOSE_PROJECT_NAME=detektor

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source common functions
if [[ -f "$SCRIPT_DIR/common.sh" ]]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/common.sh"
else
    # Basic color definitions if common.sh not found
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'

    log() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*"; }
    error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
    warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
    info() { echo -e "${BLUE}[INFO]${NC} $*"; }
fi

# Configuration
ENVIRONMENT="${1:-production}"
ACTION="${2:-deploy}"
ADDITIONAL_ARGS=("${@:3}")

# Environment-specific configuration
case "$ENVIRONMENT" in
    production|prod)
        COMPOSE_FILES=(
            "-f" "$PROJECT_ROOT/docker/base/docker-compose.yml"
            "-f" "$PROJECT_ROOT/docker/base/docker-compose.storage.yml"
            "-f" "$PROJECT_ROOT/docker/base/docker-compose.observability.yml"
            "-f" "$PROJECT_ROOT/docker/environments/production/docker-compose.yml"
        )
        # If running on GitHub Actions self-hosted runner, use localhost
        if [[ "${GITHUB_ACTIONS:-false}" == "true" ]] || [[ "$(hostname)" == "nebula" ]]; then
            TARGET_HOST="localhost"
        else
            TARGET_HOST="nebula"
        fi
        TARGET_DIR="/opt/detektor-clean"
        ENABLE_GPU=true
        ;;
    staging)
        COMPOSE_FILES=(
            "-f" "$PROJECT_ROOT/docker/base/docker-compose.yml"
            "-f" "$PROJECT_ROOT/docker/base/docker-compose.storage.yml"
            "-f" "$PROJECT_ROOT/docker/environments/staging/docker-compose.yml"
        )
        TARGET_HOST="${STAGING_HOST:-staging}"
        TARGET_DIR="/opt/detektor-staging"
        ENABLE_GPU=false
        ;;
    local|development|dev)
        COMPOSE_FILES=(
            "-f" "$PROJECT_ROOT/docker/base/docker-compose.yml"
            "-f" "$PROJECT_ROOT/docker/base/docker-compose.storage.yml"
            "-f" "$PROJECT_ROOT/docker/base/docker-compose.observability.yml"
            "-f" "$PROJECT_ROOT/docker/environments/development/docker-compose.yml"
        )
        TARGET_HOST="localhost"
        TARGET_DIR="$PROJECT_ROOT"
        ENABLE_GPU=false
        # Set default env vars for local development
        export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-dev_password}"
        export GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin}"
        ;;
    *)
        error "Unknown environment: $ENVIRONMENT"
        echo "Valid environments: production, staging, local"
        exit 1
        ;;
esac

# Add GPU support if enabled
if [[ "$ENABLE_GPU" == "true" ]] && [[ -f "$PROJECT_ROOT/docker/features/gpu/docker-compose.yml" ]]; then
    COMPOSE_FILES+=("-f" "$PROJECT_ROOT/docker/features/gpu/docker-compose.yml")
fi

# Functions
check_prerequisites() {
    log "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi

    # Check SSH for remote deployments
    if [[ "$TARGET_HOST" != "localhost" ]]; then
        if ! ssh -o ConnectTimeout=5 "$TARGET_HOST" "echo 'SSH connection successful'" &> /dev/null; then
            error "Cannot connect to $TARGET_HOST via SSH"
            exit 1
        fi
    fi

    # Check SOPS for secrets
    if ! command -v sops &> /dev/null; then
        warning "SOPS not installed - secrets decryption will be skipped"
    fi

    # Check for .env.sops
    if [[ -f "$PROJECT_ROOT/.env.sops" ]] && command -v sops &> /dev/null; then
        info "Decrypting secrets..."
        sops --input-type dotenv --output-type dotenv -d "$PROJECT_ROOT/.env.sops" > "$PROJECT_ROOT/.env"
    fi
}

get_compose_command() {
    if [[ "$TARGET_HOST" == "localhost" ]]; then
        echo "COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]}"
    else
        echo "ssh $TARGET_HOST 'cd $TARGET_DIR && COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]}'"
    fi
}

# Actions
action_deploy() {
    log "Deploying to $ENVIRONMENT environment..."

    # Ensure consistent project name
    export COMPOSE_PROJECT_NAME=detektor

    # Check circuit breaker
    if [[ -x "$PROJECT_ROOT/scripts/deployment-circuit-breaker.sh" ]]; then
        if ! "$PROJECT_ROOT/scripts/deployment-circuit-breaker.sh" check; then
            error "Deployment blocked by circuit breaker"
            "$PROJECT_ROOT/scripts/deployment-circuit-breaker.sh" status
            exit 1
        fi
    fi

    check_prerequisites

    # Pull latest images
    log "Pulling latest images..."

    # Login to GitHub Container Registry if we have a token
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        log "Logging in to GitHub Container Registry..."
        echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin || {
            warning "Failed to login to ghcr.io - continuing anyway"
        }
    fi

    # Remove old images to ensure we use fresh ones
    log "Removing old images to ensure fresh deployment..."
    if [[ "$TARGET_HOST" == "localhost" ]]; then
        # Stop services that will be redeployed
        if [[ -n "${DEPLOY_SERVICES:-}" ]]; then
            for service in $DEPLOY_SERVICES; do
                COMPOSE_PROJECT_NAME=detektor docker compose "${COMPOSE_FILES[@]}" stop "$service" 2>/dev/null || true
                COMPOSE_PROJECT_NAME=detektor docker compose "${COMPOSE_FILES[@]}" rm -f "$service" 2>/dev/null || true
            done
        else
            COMPOSE_PROJECT_NAME=detektor docker compose "${COMPOSE_FILES[@]}" down
        fi

        # Option to remove images too if FORCE_IMAGE_CLEANUP is set
        if [[ "${FORCE_IMAGE_CLEANUP:-false}" == "true" ]]; then
            log "Force removing old images..."
            COMPOSE_PROJECT_NAME=detektor COMPOSE_PROJECT_NAME=detektor docker compose "${COMPOSE_FILES[@]}" down --rmi local 2>/dev/null || true
        fi

        # Pull fresh images
        COMPOSE_PROJECT_NAME=detektor docker compose "${COMPOSE_FILES[@]}" pull
    else
        # Copy necessary files first
        log "Copying deployment files to $TARGET_HOST..."
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "mkdir -p $TARGET_DIR/docker/{base,environments,features}"
        scp -r "$PROJECT_ROOT/docker/"* "$TARGET_HOST:$TARGET_DIR/docker/" 2>/dev/null || true

        # Copy .env file if it exists
        if [[ -f "$PROJECT_ROOT/.env" ]]; then
            scp "$PROJECT_ROOT/.env" "$TARGET_HOST:$TARGET_DIR/.env"
        fi

        # Stop and remove old containers on remote
        log "Removing old containers on remote host..."
        if [[ -n "${DEPLOY_SERVICES:-}" ]]; then
            log "Stopping and removing specific services: $DEPLOY_SERVICES"
            for service in $DEPLOY_SERVICES; do
                # shellcheck disable=SC2029
                ssh "$TARGET_HOST" "cd $TARGET_DIR && COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]} stop $service 2>/dev/null || true"
                # shellcheck disable=SC2029
                ssh "$TARGET_HOST" "cd $TARGET_DIR && COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]} rm -f $service 2>/dev/null || true"
                # Remove the old image for this service to ensure fresh pull
                # shellcheck disable=SC2029
                ssh "$TARGET_HOST" "docker rmi ghcr.io/hretheum/detektr/$service:latest 2>/dev/null || true"
            done
        else
            log "No specific services specified - using rolling update strategy"
            # Don't use 'down' which kills everything - just let 'up -d' handle updates
        fi

        # Option to remove images too if FORCE_IMAGE_CLEANUP is set
        if [[ "${FORCE_IMAGE_CLEANUP:-false}" == "true" ]]; then
            log "Force removing old images..."
            # shellcheck disable=SC2029
            ssh "$TARGET_HOST" "cd $TARGET_DIR && COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]} down --rmi local 2>/dev/null || true"
        fi

        # Pull fresh images on remote
        if [[ -n "${DEPLOY_SERVICES:-}" ]]; then
            # Pull only specific services
            # shellcheck disable=SC2029
            ssh "$TARGET_HOST" "cd $TARGET_DIR && COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]} pull $DEPLOY_SERVICES"
        else
            # Pull all images
            # shellcheck disable=SC2029
            ssh "$TARGET_HOST" "cd $TARGET_DIR && COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]} pull"
        fi
    fi

    # Deploy services
    log "Starting services..."
    if [[ "$TARGET_HOST" == "localhost" ]]; then
        COMPOSE_PROJECT_NAME=detektor docker compose "${COMPOSE_FILES[@]}" up -d --remove-orphans
    else
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "cd $TARGET_DIR && COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]} up -d --remove-orphans"
    fi

    # Wait for services to start
    sleep 5

    # Verify deployment
    if action_verify; then
        # Record success if circuit breaker is enabled
        if [[ -x "$PROJECT_ROOT/scripts/deployment-circuit-breaker.sh" ]]; then
            "$PROJECT_ROOT/scripts/deployment-circuit-breaker.sh" success
        fi
        log "Deployment completed successfully"
    else
        # Record failure if circuit breaker is enabled
        if [[ -x "$PROJECT_ROOT/scripts/deployment-circuit-breaker.sh" ]]; then
            "$PROJECT_ROOT/scripts/deployment-circuit-breaker.sh" failure
        fi
        error "Deployment verification failed"
        exit 1
    fi
}

action_status() {
    log "Checking service status in $ENVIRONMENT..."

    if [[ "$TARGET_HOST" == "localhost" ]]; then
        COMPOSE_PROJECT_NAME=detektor docker compose "${COMPOSE_FILES[@]}" ps
    else
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "cd $TARGET_DIR && COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]} ps"
    fi
}

action_logs() {
    log "Showing logs for $ENVIRONMENT..."

    if [[ "$TARGET_HOST" == "localhost" ]]; then
        COMPOSE_PROJECT_NAME=detektor docker compose "${COMPOSE_FILES[@]}" logs "${ADDITIONAL_ARGS[@]}"
    else
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "cd $TARGET_DIR && COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]} logs ${ADDITIONAL_ARGS[*]}"
    fi
}

action_restart() {
    log "Restarting services in $ENVIRONMENT..."

    if [[ "$TARGET_HOST" == "localhost" ]]; then
        docker compose "${COMPOSE_FILES[@]}" restart "${ADDITIONAL_ARGS[@]}"
    else
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "cd $TARGET_DIR && docker compose ${COMPOSE_FILES[*]} restart ${ADDITIONAL_ARGS[*]}"
    fi
}

action_stop() {
    log "Stopping services in $ENVIRONMENT..."

    if [[ "$TARGET_HOST" == "localhost" ]]; then
        COMPOSE_PROJECT_NAME=detektor docker compose "${COMPOSE_FILES[@]}" down
    else
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "cd $TARGET_DIR && COMPOSE_PROJECT_NAME=detektor docker compose ${COMPOSE_FILES[*]} down"
    fi
}

action_verify() {
    log "Verifying deployment health..."

    # Define services and their health endpoints
    declare -A services=(
        ["rtsp-capture"]="8001"
        ["frame-tracking"]="8006"
        ["metadata-storage"]="8005"
        ["base-template"]="8000"
    )

    declare -A infrastructure=(
        ["prometheus"]="9090/-/healthy"
        ["grafana"]="3000/api/health"
        ["jaeger"]="16686/"
    )

    local failed=0

    # Check application services
    for service in "${!services[@]}"; do
        port="${services[$service]}"
        if [[ "$TARGET_HOST" == "localhost" ]]; then
            url="http://localhost:$port/health"
        else
            url="http://$TARGET_HOST:$port/health"
        fi

        if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $service is healthy"
        else
            echo -e "${RED}✗${NC} $service is not responding"
            ((failed++))
        fi
    done

    # Check infrastructure services
    for service in "${!infrastructure[@]}"; do
        endpoint="${infrastructure[$service]}"
        if [[ "$TARGET_HOST" == "localhost" ]]; then
            url="http://localhost:$endpoint"
        else
            url="http://$TARGET_HOST:$endpoint"
        fi

        if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $service is healthy"
        else
            echo -e "${YELLOW}⚠${NC} $service might not be ready yet"
        fi
    done

    if [[ $failed -gt 0 ]]; then
        warning "$failed service(s) are not responding"
        return 1
    else
        log "All services are healthy!"
        return 0
    fi
}

action_cleanup() {
    log "Cleaning up old images and volumes..."

    if [[ "$TARGET_HOST" == "localhost" ]]; then
        # Remove stopped containers
        docker container prune -f

        # Remove unused images
        docker image prune -af --filter "until=72h"

        # Remove unused volumes (careful!)
        if [[ "${FORCE_CLEANUP:-false}" == "true" ]]; then
            docker volume prune -f
        fi
    else
        ssh "$TARGET_HOST" "
            docker container prune -f
            docker image prune -af --filter 'until=72h'
        "
    fi

    log "Cleanup completed"
}

action_rollback() {
    error "Rollback not yet implemented"
    info "To rollback manually:"
    echo "  1. Check previous image tags in deployment history"
    echo "  2. Update docker-compose files with previous tags"
    echo "  3. Run: $0 $ENVIRONMENT deploy"
    exit 1
}

# Main execution
case "$ACTION" in
    deploy)
        action_deploy
        ;;
    status|ps)
        action_status
        ;;
    logs)
        action_logs
        ;;
    restart)
        action_restart
        ;;
    stop|down)
        action_stop
        ;;
    verify|health)
        action_verify
        ;;
    cleanup|clean)
        action_cleanup
        ;;
    rollback)
        action_rollback
        ;;
    *)
        error "Unknown action: $ACTION"
        echo "Valid actions: deploy, status, logs, restart, stop, verify, cleanup, rollback"
        exit 1
        ;;
esac
