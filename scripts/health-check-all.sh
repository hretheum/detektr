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
check_service "Base Template" "http://localhost:8000/health"
check_service "Frame Buffer" "http://localhost:8002/health"
check_service "Metadata Storage" "http://localhost:8005/health"
check_service "Echo Service" "http://localhost:8007/health"
check_service "GPU Demo" "http://localhost:8008/health"
check_service "Example OTEL" "http://localhost:8009/health"
check_service "RTSP Capture" "http://localhost:8080/health"
check_service "Frame Events" "http://localhost:8081/health"
check_service "Sample Processor" "http://localhost:8099/health"

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

# Check all containers - using actual names (COMPOSE_PROJECT_NAME=detektr)
for container in \
    "detektr-rtsp-capture-1" \
    "detektr-frame-buffer-1" \
    "detektr-gpu-demo-1" \
    "detektr-redis-1" \
    "detektr-postgres-1" \
    "detektr-frame-events-1" \
    "detektr-example-otel-1" \
    "detektr-echo-service-1" \
    "detektr-base-template-1" \
    "detektr-metadata-storage-1" \
    "detektr-sample-processor-1" \
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
