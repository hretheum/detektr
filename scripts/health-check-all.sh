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
    
    if curl -f -s --max-time $timeout "$url" > /dev/null 2>&1; then
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
        local status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-health-check")
        
        case $status in
            "healthy")
                echo -e "${GREEN}✓ HEALTHY${NC}"
                return 0
                ;;
            "starting")
                echo -e "${YELLOW}⚠ STARTING${NC}"
                return 1
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
    echo "  🔧 Debug: docker logs rtsp-capture-service"

# GPU Demo Service  
check_service "GPU Demo" "http://localhost:8008/health" || \
    echo "  🔧 Debug: docker logs gpu-demo-service"

echo ""
echo "🐳 Container Status:"
echo "===================="

# Check all containers
check_container "rtsp-capture-service"
check_container "gpu-demo-service"
check_container "redis"
check_container "rabbitmq"

# Summary
echo ""
echo "📋 Summary:"
echo "=========="

# Get overall status
if check_service "RTSP Capture" "http://localhost:8001/health" 5 && \
   check_service "GPU Demo" "http://localhost:8008/health" 5; then
    echo -e "${GREEN}🎉 All services are healthy!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some services are unhealthy. Check logs above.${NC}"
    
    echo ""
    echo "🔧 Quick debugging commands:"
    echo "  docker ps -a"
    echo "  docker logs rtsp-capture-service"
    echo "  docker logs gpu-demo-service"
    echo "  docker-compose ps"
    
    exit 1
fi
