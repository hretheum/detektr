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

# Service Port Allocation - Single Source of Truth
# Sync with docs/deployment/PORT_ALLOCATION.md
# Define as string for easier remote execution
export SERVICE_PORTS_STRING='
    base-template:8000
    frame-buffer:8002
    face-recognition:8003
    object-detection:8004
    metadata-storage:8005
    echo-service:8007
    gpu-demo:8008
    example-otel:8009
    rtsp-capture:8080
    frame-events:8081
    cadvisor:8082
    adminer:8083
    sample-processor:8099
    grafana:3000
    postgres:5432
    redis:6379
    pgbouncer:6432
    prometheus:9090
    jaeger-ui:16686
'

# Parse into associative array for local use (kept for future use)
declare -A SERVICE_PORTS
while IFS=: read -r service port; do
    [[ -n "$service" ]] && SERVICE_PORTS["$service"]="$port"
done <<< "$SERVICE_PORTS_STRING"
export SERVICE_PORTS  # Export for potential use in other scripts

# Function to clean up containers using specific ports
cleanup_ports() {
    echo "Checking for containers using service ports..."
    while IFS=: read -r service port; do
        if [[ -n "$service" ]] && [[ -n "$port" ]]; then
            echo "Checking port $port ($service)..."
            container_on_port=$(docker ps --format "{{.Names}}" --filter "publish=$port" 2>/dev/null | head -1 || true)
            if [[ -n "$container_on_port" ]]; then
                echo "Port $port is used by container: $container_on_port - removing it"
                docker stop "$container_on_port" 2>/dev/null || true
                docker rm -f "$container_on_port" 2>/dev/null || true
            fi
        fi
    done <<< "$SERVICE_PORTS_STRING"
}

# Configuration
ENVIRONMENT="${1:-production}"
ACTION="${2:-deploy}"
ADDITIONAL_ARGS=("${@:3}")

# Environment-specific configuration
case "$ENVIRONMENT" in
    production|prod)
        # If running on GitHub Actions self-hosted runner, use localhost
        if [[ "${GITHUB_ACTIONS:-false}" == "true" ]] || [[ "$(hostname)" == "nebula" ]]; then
            TARGET_HOST="localhost"
            TARGET_DIR="/opt/detektor-clean"
            # Use target directory for compose files when on production server
            COMPOSE_FILES=(
                "-f" "$TARGET_DIR/docker/base/docker-compose.yml"
                "-f" "$TARGET_DIR/docker/base/docker-compose.storage.yml"
                "-f" "$TARGET_DIR/docker/base/docker-compose.observability.yml"
                "-f" "$TARGET_DIR/docker/environments/production/docker-compose.yml"
            )
        else
            TARGET_HOST="nebula"
            TARGET_DIR="/opt/detektor-clean"
            # Use project root for compose files when deploying remotely
            COMPOSE_FILES=(
                "-f" "$PROJECT_ROOT/docker/base/docker-compose.yml"
                "-f" "$PROJECT_ROOT/docker/base/docker-compose.storage.yml"
                "-f" "$PROJECT_ROOT/docker/base/docker-compose.observability.yml"
                "-f" "$PROJECT_ROOT/docker/environments/production/docker-compose.yml"
            )
        fi
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
        TARGET_HOST="localhost"
        TARGET_DIR="$PROJECT_ROOT"
        # When running locally, we need to check if we're in the right directory
        if [[ "$PWD" == "$TARGET_DIR" ]] || [[ -f "./docker/base/docker-compose.yml" ]]; then
            # We're in the project directory, use relative paths
            COMPOSE_FILES=(
                "-f" "./docker/base/docker-compose.yml"
                "-f" "./docker/base/docker-compose.storage.yml"
                "-f" "./docker/base/docker-compose.observability.yml"
                "-f" "./docker/environments/development/docker-compose.yml"
            )
        else
            # We're elsewhere, use absolute paths
            COMPOSE_FILES=(
                "-f" "$PROJECT_ROOT/docker/base/docker-compose.yml"
                "-f" "$PROJECT_ROOT/docker/base/docker-compose.storage.yml"
                "-f" "$PROJECT_ROOT/docker/base/docker-compose.observability.yml"
                "-f" "$PROJECT_ROOT/docker/environments/development/docker-compose.yml"
            )
        fi
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
        echo "COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]}"
    else
        echo "ssh $TARGET_HOST 'cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]}'"
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

    # Change to target directory for localhost deployment
    if [[ "$TARGET_HOST" == "localhost" ]] && [[ "$PWD" != "$TARGET_DIR" ]]; then
        log "Changing to target directory: $TARGET_DIR"
        cd "$TARGET_DIR" || {
            error "Cannot change to target directory: $TARGET_DIR"
            exit 1
        }
    fi

    # Ensure network exists
    if [[ "$TARGET_HOST" == "localhost" ]]; then
        if ! docker network ls | grep -q "detektor-network"; then
            log "Creating detektor-network..."
            docker network create detektor-network || true
        fi
    else
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "docker network ls | grep -q 'detektor-network' || docker network create detektor-network"
    fi

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
        # Stop and remove services that will be redeployed
        if [[ -n "${DEPLOY_SERVICES:-}" ]]; then
            log "Cleaning up specific services: $DEPLOY_SERVICES"
            for service in $DEPLOY_SERVICES; do
                log "Stopping and removing $service..."
                # Use subshell to prevent script exit on error
                (
                    COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" stop "$service" 2>&1 | grep -v "no such service" || true
                    COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" rm -f "$service" 2>&1 | grep -v "no such service" || true
                ) || log "Service $service may not exist, continuing..."

                # Also remove by container name pattern if compose missed it
                docker ps -a --format "{{.Names}}" | grep -E "^detektor-${service}(-[0-9]+)?$" | while read -r container; do
                    log "Removing stale container: $container"
                    docker stop "$container" 2>/dev/null || true
                    docker rm -f "$container" 2>/dev/null || true
                done

                # Extra aggressive cleanup - remove any container using the service image
                docker ps -a --format "{{.ID}} {{.Image}}" | grep "ghcr.io/hretheum/detektr/${service}:" | awk '{print $1}' | while read -r container_id; do
                    log "Removing container by image: $container_id"
                    docker stop "$container_id" 2>/dev/null || true
                    docker rm -f "$container_id" 2>/dev/null || true
                done
                # Remove old image to ensure fresh pull
                docker rmi "ghcr.io/hretheum/detektr/$service:latest" 2>/dev/null || true
                log "Removed old image for $service"

                # Log current image ID before pull
                OLD_IMAGE_ID=$(docker images -q "ghcr.io/hretheum/detektr/$service:latest" 2>/dev/null || echo "none")
                log "Old image ID for $service: $OLD_IMAGE_ID"
            done
        else
            COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" down
        fi

        # Option to remove images too if FORCE_IMAGE_CLEANUP is set
        if [[ "${FORCE_IMAGE_CLEANUP:-false}" == "true" ]]; then
            log "Force removing old images..."
            COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" down --rmi local 2>/dev/null || true
        fi

        # Handle volume conflicts by removing orphans
        log "Cleaning up any orphaned resources..."
        COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" down --remove-orphans 2>/dev/null || true

        # Clean up containers using specific ports
        log "Cleaning up containers using service ports..."
        cleanup_ports

        # Check for volume conflicts and fix ownership issues
        log "Checking for volume conflicts..."
        for vol in detektor_postgres_data detektor_redis_data; do
            if docker volume inspect "$vol" >/dev/null 2>&1; then
                log "Volume $vol exists, checking ownership..."
                # Get the mount point
                mount_point=$(docker volume inspect "$vol" --format '{{.Mountpoint}}')
                if [[ -n "$mount_point" ]] && [[ -d "$mount_point" ]]; then
                    # Fix permissions if running as root (GitHub Actions runner)
                    if [[ "$EUID" -eq 0 ]] || sudo -n true 2>/dev/null; then
                        log "Fixing permissions for $vol..."
                        sudo chown -R 999:999 "$mount_point" 2>/dev/null || true
                    fi
                fi
            fi
        done

        # Remove conflicting volumes if they exist (be careful with data!)
        if [[ "${FORCE_VOLUME_RECREATE:-false}" == "true" ]]; then
            log "Force removing volumes (WARNING: Data will be lost!)"
            docker volume ls -q | grep "^detektor_" | xargs -r docker volume rm 2>/dev/null || true
        fi

        # Force recreate volumes if needed - disable interactive mode
        export DOCKER_CLI_HINTS=false
        export COMPOSE_INTERACTIVE_NO_CLI=1
        export DOCKER_BUILDKIT=0  # Disable BuildKit which can cause interactive prompts

        # Pull fresh images with force and timeout
        log "Pulling images with --pull always flag..."
        if [[ -n "${DEPLOY_SERVICES:-}" ]]; then
            # Pull specific services one by one
            for service in $DEPLOY_SERVICES; do
                log "Pulling image for $service..."
                DOCKER_CLIENT_TIMEOUT=300 COMPOSE_HTTP_TIMEOUT=300 COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" pull --policy always "$service" || {
                    log "Warning: Failed to pull $service, will retry..."
                    sleep 2
                    DOCKER_CLIENT_TIMEOUT=300 COMPOSE_HTTP_TIMEOUT=300 COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" pull --policy always "$service" || true
                }
            done
        else
            DOCKER_CLIENT_TIMEOUT=300 COMPOSE_HTTP_TIMEOUT=300 COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" pull --policy always
        fi

        # Log new image IDs after pull
        if [[ -n "${DEPLOY_SERVICES:-}" ]]; then
            for service in $DEPLOY_SERVICES; do
                NEW_IMAGE_ID=$(docker images -q "ghcr.io/hretheum/detektr/$service:latest" 2>/dev/null || echo "none")
                NEW_IMAGE_DIGEST=$(docker images --digests "ghcr.io/hretheum/detektr/$service:latest" | grep -v REPOSITORY | awk '{print $3}' | head -1)
                log "New image ID for $service: $NEW_IMAGE_ID (digest: ${NEW_IMAGE_DIGEST:-unknown})"
            done
        fi
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

        # Clean up containers using specific ports on remote
        log "Checking for containers using service ports on remote..."
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "$(declare -f cleanup_ports); export SERVICE_PORTS_STRING='$SERVICE_PORTS_STRING'; cleanup_ports"

        if [[ -n "${DEPLOY_SERVICES:-}" ]]; then
            log "Stopping and removing specific services: $DEPLOY_SERVICES"
            for service in $DEPLOY_SERVICES; do
                log "Stopping and removing $service on remote..."
                # shellcheck disable=SC2029
                ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && (COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} stop $service 2>&1 | grep -v 'no such service' || true)" || log "Service $service may not exist on remote, continuing..."
                # shellcheck disable=SC2029
                ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && (COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} rm -f $service 2>&1 | grep -v 'no such service' || true)" || log "Service $service removal may have failed, continuing..."

                # Also remove by container name pattern if compose missed it
                # shellcheck disable=SC2029
                ssh "$TARGET_HOST" "docker ps -a --format '{{.Names}}' | grep -E '^detektor-${service}(-[0-9]+)?$' | while read container; do docker stop \"\$container\" 2>/dev/null || true; docker rm -f \"\$container\" 2>/dev/null || true; done"

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
            ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} down --rmi local 2>/dev/null || true"
        fi

        # Pull fresh images on remote with retry logic
        if [[ -n "${DEPLOY_SERVICES:-}" ]]; then
            # Pull only specific services one by one for better reliability
            for service in $DEPLOY_SERVICES; do
                log "Pulling image for $service..."
                # shellcheck disable=SC2029
                ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} pull $service" || {
                    log "Warning: Failed to pull $service, will retry..."
                    sleep 2
                    ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} pull $service" || true
                }
            done
        else
            # Pull all images with increased timeout
            # shellcheck disable=SC2029
            ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && DOCKER_CLIENT_TIMEOUT=300 COMPOSE_HTTP_TIMEOUT=300 COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} pull"
        fi
    fi

    # Deploy services
    log "Starting services..."

    # Extra cleanup to ensure ports are free
    if [[ "$TARGET_HOST" == "localhost" ]]; then
        log "Ensuring all old containers are stopped..."
        log "Working directory: $(pwd)"

        # Stop all containers in the project first
        COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" down >/dev/null 2>&1 || true
        # Kill any stuck containers
        docker ps -a --filter "label=com.docker.compose.project=detektor" --format "{{.ID}}" | xargs -r docker rm -f >/dev/null 2>&1 || true

        # Check for containers using our ports and stop them
        log "Final port conflict check..."
        cleanup_ports
        log "Port conflict check completed"
    else
        log "Ensuring all old containers are stopped on remote..."
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} down >/dev/null 2>&1 || true"
        ssh "$TARGET_HOST" "docker ps -a --filter 'label=com.docker.compose.project=detektor' --format '{{.ID}}' | xargs -r docker rm -f >/dev/null 2>&1 || true"

        # Check for port conflicts on remote
        log "Checking for port conflicts on remote..."
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "$(declare -f cleanup_ports); export SERVICE_PORTS_STRING='$SERVICE_PORTS_STRING'; cleanup_ports"
    fi

    if [[ -n "${DEPLOY_SERVICES:-}" ]]; then
        log "Deploying specific services: $DEPLOY_SERVICES"
        if [[ "$TARGET_HOST" == "localhost" ]]; then
            # shellcheck disable=SC2086
            yes n | DOCKER_CLI_HINTS=false COMPOSE_INTERACTIVE_NO_CLI=1 COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" up -d --remove-orphans --pull always --force-recreate --no-build $DEPLOY_SERVICES 2>&1 | grep -v "Recreate"
        else
            # shellcheck disable=SC2029,SC2086
            ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && DOCKER_CLI_HINTS=false COMPOSE_INTERACTIVE_NO_CLI=1 COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} up -d --remove-orphans --force-recreate $DEPLOY_SERVICES < /dev/null"
        fi
    else
        log "Deploying all services"
        if [[ "$TARGET_HOST" == "localhost" ]]; then
            yes n | DOCKER_CLI_HINTS=false COMPOSE_INTERACTIVE_NO_CLI=1 COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" up -d --remove-orphans --pull always --force-recreate --no-build 2>&1 | grep -v "Recreate"
        else
            # shellcheck disable=SC2029
            ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && DOCKER_CLI_HINTS=false COMPOSE_INTERACTIVE_NO_CLI=1 COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} up -d --remove-orphans --force-recreate < /dev/null"
        fi
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
        COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" ps
    else
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} ps"
    fi
}

action_logs() {
    log "Showing logs for $ENVIRONMENT..."

    if [[ "$TARGET_HOST" == "localhost" ]]; then
        COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" logs "${ADDITIONAL_ARGS[@]}"
    else
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} logs ${ADDITIONAL_ARGS[*]}"
    fi
}

action_restart() {
    log "Restarting services in $ENVIRONMENT..."

    if [[ "$TARGET_HOST" == "localhost" ]]; then
        docker compose --env-file .env "${COMPOSE_FILES[@]}" restart "${ADDITIONAL_ARGS[@]}"
    else
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && docker compose --env-file .env ${COMPOSE_FILES[*]} restart ${ADDITIONAL_ARGS[*]}"
    fi
}

action_stop() {
    log "Stopping services in $ENVIRONMENT..."

    if [[ "$TARGET_HOST" == "localhost" ]]; then
        COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env "${COMPOSE_FILES[@]}" down
    else
        # shellcheck disable=SC2029
        ssh "$TARGET_HOST" "cd $TARGET_DIR && set -a && source .env 2>/dev/null || true && set +a && COMPOSE_PROJECT_NAME=detektor docker compose --env-file .env ${COMPOSE_FILES[*]} down"
    fi
}

action_verify() {
    log "Verifying deployment health..."

    # Define all possible services and their health endpoints
    # Using the same SERVICE_PORTS as defined at the beginning
    declare -A all_services=(
        ["base-template"]="8000"
        ["frame-buffer"]="8002"
        ["metadata-storage"]="8005"
        ["rtsp-capture"]="8080"
        ["frame-events"]="8081"
        ["sample-processor"]="8099"
    )

    # Filter to only check deployed services
    declare -A services=()
    if [[ -n "${DEPLOY_SERVICES:-}" ]]; then
        for service in $DEPLOY_SERVICES; do
            if [[ -n "${all_services[$service]:-}" ]]; then
                services[$service]="${all_services[$service]}"
            fi
        done
    else
        # If no specific services, check all
        for key in "${!all_services[@]}"; do
            services[$key]="${all_services[$key]}"
        done
    fi

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
