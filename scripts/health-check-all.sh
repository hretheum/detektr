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
                echo -e "${YELLOW}⚠ NO HEALTH CHECK${NC}"
                return 1
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

# RTSP Capture Service
check_service "RTSP Capture" "http://localhost:8001/health" || \
    echo "  🔧 Debug: docker logs detektr-rtsp-capture-1"

# GPU Demo Service
check_service "GPU Demo" "http://localhost:8008/health" || \
    echo "  🔧 Debug: docker logs detektr-gpu-demo-1"

# Example OTEL Service
check_service "Example OTEL" "http://localhost:8005/health" || \
    echo "  🔧 Debug: docker logs detektr-example-otel-1"

# Frame Tracking Service
check_service "Frame Tracking" "http://localhost:8006/health" || \
    echo "  🔧 Debug: docker logs detektr-frame-tracking-1"

# Echo Service
check_service "Echo Service" "http://localhost:8007/health" || \
    echo "  🔧 Debug: docker logs detektr-echo-service-1"

echo ""
echo "🐳 Container Status:"
echo "===================="

# Check all containers - używamy rzeczywistych nazw z docker-compose
check_container "detektr-rtsp-capture-1"
check_container "detektr-gpu-demo-1"
check_container "detektr-redis-1"
check_container "detektr-postgres-1"
check_container "detektr-frame-tracking-1"
check_container "detektr-frame-buffer-1"
check_container "detektr-example-otel-1"
check_container "detektr-echo-service-1"
check_container "detektr-telegram-alerts-1"

# Summary
echo ""
echo "📋 Summary:"
echo "=========="

# Get overall status
all_healthy=true
any_starting=false

# Check all key services
for service_check in \
    "RTSP Capture:http://localhost:8001/health" \
    "GPU Demo:http://localhost:8008/health" \
    "Example OTEL:http://localhost:8005/health" \
    "Frame Tracking:http://localhost:8006/health" \
    "Echo Service:http://localhost:8007/health"; do

    IFS=':' read -r name url <<< "$service_check"
    if ! check_service "$name" "$url" 5; then
        all_healthy=false
    fi
done

# Check container statuses for STARTING
for container in \
    "detektr-frame-tracking-1" \
    "detektr-gpu-demo-1" \
    "detektr-rtsp-capture-1"; do

    if docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null | grep -q "starting"; then
        any_starting=true
    fi
done

if [[ "$all_healthy" == true ]]; then
    echo -e "${GREEN}🎉 All services are healthy!${NC}"
    exit 0
elif [[ "$any_starting" == true ]]; then
    echo -e "${YELLOW}⏳ Some services are still starting. This is normal for Frame Tracking.${NC}"
    echo -e "${YELLOW}   Wait a bit and run health check again.${NC}"
    exit 0  # Don't fail if services are starting
else
    echo -e "${RED}❌ Some services are unhealthy. Check logs above.${NC}"

    echo ""
    echo "🔧 Quick debugging commands:"
    echo "  docker ps -a"
    echo "  docker logs detektr-rtsp-capture-1"
    echo "  docker logs detektr-gpu-demo-1"
    echo "  docker-compose ps"
    echo "  docker logs detektr-[service-name]-1"

    exit 1
fi
