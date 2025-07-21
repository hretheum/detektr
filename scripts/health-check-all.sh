#!/bin/bash
set -euo pipefail

# Health check script for all Detektor services
# Includes infrastructure services and better error reporting

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# All services including infrastructure
declare -A SERVICES=(
    ["postgres"]="http://localhost:5432"
    ["redis"]="http://localhost:6379"
    ["prometheus"]="http://localhost:9090/-/healthy"
    ["grafana"]="http://localhost:3000/api/health"
    ["jaeger"]="http://localhost:16686/"
    ["example-otel"]="http://localhost:8005/health"
    ["frame-tracking"]="http://localhost:8006/health"
    ["echo-service"]="http://localhost:8007/health"
    ["gpu-demo"]="http://localhost:8008/health"
    ["rtsp-capture"]="http://localhost:8001/health"
)

# Track overall health
ALL_HEALTHY=true

echo "=========================================="
echo "  Detektor Services Health Check"
echo "=========================================="
echo

# Check infrastructure services first
echo -e "${BLUE}=== Infrastructure Services ===${NC}"
for service in postgres redis prometheus grafana jaeger; do
    url="${SERVICES[$service]}"

    case $service in
        postgres)
            if sudo docker exec detektor-postgres-1 pg_isready -U detektor &>/dev/null; then
                echo -e "${GREEN}✓${NC} $service - healthy"
            else
                echo -e "${RED}✗${NC} $service - unhealthy (PostgreSQL not ready)"
                ALL_HEALTHY=false
            fi
            ;;
        redis)
            if sudo docker exec detektor-redis-1 redis-cli ping &>/dev/null; then
                echo -e "${GREEN}✓${NC} $service - healthy"
            else
                echo -e "${RED}✗${NC} $service - unhealthy (Redis not responding)"
                ALL_HEALTHY=false
            fi
            ;;
        *)
            if curl -sf "$url" > /dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} $service - healthy"
            else
                echo -e "${RED}✗${NC} $service - unhealthy (${url})"
                ALL_HEALTHY=false
            fi
            ;;
    esac
done

echo

# Check application services
echo -e "${BLUE}=== Application Services ===${NC}"
for service in example-otel frame-tracking echo-service gpu-demo rtsp-capture; do
    url="${SERVICES[$service]}"

    # Wait a bit longer for services to start
    max_wait=10
    count=0

    while [[ $count -lt $max_wait ]]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $service - healthy"
            break
        else
            ((count++))
            if [[ $count -eq $max_wait ]]; then
                echo -e "${RED}✗${NC} $service - unhealthy (${url})"
                ALL_HEALTHY=false

                # Show container status
                container_name="detektor-${service}-1"
                status=$(sudo docker ps --filter "name=$container_name" --format "{{.Status}}" 2>/dev/null || echo "not found")
                echo -e "${YELLOW}   Container status: $status${NC}"

                # Show recent logs
                echo -e "${YELLOW}   Recent logs:${NC}"
                sudo docker logs --tail 5 "$container_name" 2>/dev/null | sed 's/^/     /' || true
            else
                sleep 2
            fi
        fi
    done
done

echo

# Check Docker containers
echo -e "${BLUE}=== Container Status ===${NC}"
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep -E "(detektor|postgres|redis|prometheus|grafana|jaeger)" || true

echo

# Check GPU if available
if command -v nvidia-smi &> /dev/null; then
    echo -e "${BLUE}=== GPU Status ===${NC}"
    if nvidia-smi --query-gpu=name,memory.used,memory.free,temperature.gpu --format=csv,noheader &>/dev/null; then
        nvidia-smi --query-gpu=name,memory.used,memory.free,temperature.gpu --format=csv,noheader
    else
        echo -e "${YELLOW}GPU available but not accessible${NC}"
    fi
    echo
fi

# Resource usage
echo -e "${BLUE}=== Resource Usage ===${NC}"
sudo docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | grep -E "(detektor|postgres|redis)" || true

echo

# Summary
echo "=========================================="
if [[ "$ALL_HEALTHY" == "true" ]]; then
    echo -e "${GREEN}✓ All services are healthy!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some services are unhealthy!${NC}"
    echo
    echo "To check logs, run:"
    echo "  docker logs detektor-[service-name]-1"
    echo
    echo "To restart services:"
    echo "  docker compose restart [service-name]"
    echo
    echo "To check detailed logs:"
    echo "  docker compose logs [service-name]"
    exit 1
fi
