#!/bin/bash
set -euo pipefail

# Script to fix Redis deployment issues on Nebula
# This implements the temporary solution: stick with single Redis

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
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

# Step 1: Fix health-check script to remove sentinel checks
fix_health_check() {
    log "Fixing health-check-all.sh script..."

    cat > "$PROJECT_ROOT/scripts/health-check-all.sh" << 'EOF'
#!/bin/bash
# Health check script for all services on Nebula server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Starting health checks for all services..."

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    local timeout=${3:-10}

    echo -n "Checking $service_name..."

    if curl -f -s --max-time "$timeout" "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ HEALTHY${NC}"
        return 0
    else
        echo -e "${RED}✗ UNHEALTHY${NC}"
        return 1
    fi
}

# Function to check container status
check_container() {
    local container_name=$1

    echo -n "Checking container $container_name..."

    if docker ps --format "{{.Names}}" | grep -q "^$container_name$"; then
        local status
        status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-health-check")

        case $status in
            "healthy")
                echo -e "${GREEN}✓ HEALTHY${NC}"
                return 0
                ;;
            "starting")
                echo -e "${YELLOW}⚠ STARTING${NC}"
                return 0  # Don't fail for starting containers
                ;;
            "unhealthy")
                echo -e "${RED}✗ UNHEALTHY${NC}"
                return 1
                ;;
            *)
                echo -e "${GREEN}✓ RUNNING${NC}"
                return 0
                ;;
        esac
    else
        echo -e "${RED}✗ NOT RUNNING${NC}"
        return 1
    fi
}

# Check individual services
echo ""
echo "📊 Service Health Checks:"
echo "========================"

# Application Services
check_service "RTSP Capture" "http://localhost:8001/health"
check_service "Frame Buffer" "http://localhost:8002/health"
check_service "Example OTEL" "http://localhost:8005/health"
check_service "Frame Tracking" "http://localhost:8006/health"
check_service "Echo Service" "http://localhost:8007/health"
check_service "GPU Demo" "http://localhost:8008/health"

echo ""
echo "🔧 Infrastructure Services:"
echo "==========================="

# Infrastructure Services
check_service "Prometheus" "http://localhost:9090/-/healthy"
check_service "Jaeger UI" "http://localhost:16686/"
check_service "Grafana" "http://localhost:3000/api/health"

# Redis check (different because it's not HTTP)
echo -n "Checking Redis..."
if docker exec detektr-redis-1 redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ HEALTHY${NC}"
else
    echo -e "${RED}✗ UNHEALTHY${NC}"
fi

# PostgreSQL check
echo -n "Checking PostgreSQL..."
if docker exec detektr-postgres-1 pg_isready -U detektor > /dev/null 2>&1; then
    echo -e "${GREEN}✓ HEALTHY${NC}"
else
    echo -e "${RED}✗ UNHEALTHY${NC}"
fi

echo ""
echo "🐳 Container Status:"
echo "===================="

# Check all containers - using actual names
for container in \
    "detektr-rtsp-capture-1" \
    "detektr-frame-buffer-1" \
    "detektr-gpu-demo-1" \
    "detektr-redis-1" \
    "detektr-postgres-1" \
    "detektr-frame-tracking-1" \
    "detektr-example-otel-1" \
    "detektr-echo-service-1" \
    "detektr-prometheus-1" \
    "detektr-jaeger-1" \
    "detektr-grafana-1"; do

    check_container "$container"
done

# Summary
echo ""
echo "📋 Summary:"
echo "=========="

# Count healthy services
healthy_count=$(docker ps --filter "health=healthy" --format "{{.Names}}" | grep -c "detektr-" || true)
total_count=$(docker ps --format "{{.Names}}" | grep -c "detektr-" || true)

if [[ $healthy_count -eq $total_count ]] && [[ $total_count -gt 0 ]]; then
    echo -e "${GREEN}🎉 All $total_count services are healthy!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  $healthy_count/$total_count services are healthy${NC}"
    echo ""
    echo "🔧 Debugging tips:"
    echo "  - Check logs: docker logs <container-name>"
    echo "  - Check all containers: docker ps -a | grep detektr"
    echo "  - Check specific service: docker logs detektr-<service>-1"
    echo "  - Restart service: docker restart detektr-<service>-1"
    exit 1
fi
EOF

    chmod +x "$PROJECT_ROOT/scripts/health-check-all.sh"
    log "Health check script fixed ✓"
}

# Step 2: Create documentation about Redis HA status
create_redis_ha_docs() {
    log "Creating Redis HA documentation..."

    cat > "$PROJECT_ROOT/docs/infrastructure/REDIS_HA_STATUS.md" << 'EOF'
# Redis High Availability - Status and Future Plans

## Current Status (July 2025)

We are using a **single Redis instance** for the following reasons:

1. **Simplicity**: Single Redis is sufficient for current load and POC phase
2. **Development Focus**: Priority is on core service functionality
3. **Dependency**: Redis HA requires sentinel-aware clients in all services

## Future Redis HA Implementation

### When to implement
- After core services are stable (post-Phase 2)
- When reliability becomes critical
- Before production deployment

### Prerequisites
1. All services must support Redis Sentinel
2. Proper testing environment
3. Zero-downtime migration plan

### Files ready for Redis HA
- `docker-compose.redis-ha.yml` - Complete HA setup
- `config/redis-master.conf` - Master configuration
- `config/redis-slave.conf` - Slave configuration
- `config/sentinel.conf` - Sentinel configuration

### Migration checklist
- [ ] Update all services to use redis-sentinel library
- [ ] Test failover scenarios
- [ ] Create backup/restore procedures
- [ ] Update monitoring for HA setup
- [ ] Document operational procedures

## Current Redis Configuration

- **Type**: Single instance
- **Image**: redis:7-alpine
- **Port**: 6379
- **Persistence**: Enabled (AOF + RDB)
- **Memory**: 512MB limit
- **Health check**: redis-cli ping

## Monitoring

Current Redis metrics available at:
- Prometheus: http://nebula:9090 (search for "redis_")
- Grafana: http://nebula:3000 (Redis dashboard)
EOF

    log "Redis HA documentation created ✓"
}

# Step 3: Deploy fixed health check to Nebula
deploy_fixes() {
    log "Deploying fixes to Nebula..."

    # Copy fixed health check script
    scp "$PROJECT_ROOT/scripts/health-check-all.sh" nebula:/opt/detektor/scripts/
    ssh nebula "chmod +x /opt/detektor/scripts/health-check-all.sh"

    log "Fixes deployed to Nebula ✓"
}

# Step 4: Test the fix
test_health_check() {
    log "Testing health check on Nebula..."

    if ssh nebula "/opt/detektor/scripts/health-check-all.sh"; then
        log "Health check working correctly ✓"
    else
        warning "Some services may be unhealthy, but health check script is working"
    fi
}

# Main execution
main() {
    log "Starting Redis deployment fix..."

    fix_health_check
    create_redis_ha_docs
    deploy_fixes
    test_health_check

    log "Redis deployment fix completed!"
    log ""
    log "Summary:"
    log "- Health check script fixed (removed sentinel checks)"
    log "- Redis HA documented as future enhancement"
    log "- Single Redis instance continues to work"
    log ""
    log "Next steps:"
    log "1. Continue with service development"
    log "2. Implement Redis HA after Phase 2 completion"
}

main "$@"
