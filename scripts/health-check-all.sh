#!/bin/bash
set -euo pipefail

# Health check script for all Detektor services
# Exits with 0 if all healthy, 1 if any unhealthy

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Service endpoints
declare -A SERVICES=(
    ["example-otel"]="http://localhost:8005/health"
    ["frame-tracking"]="http://localhost:8006/health"
    ["echo-service"]="http://localhost:8007/health"
    ["gpu-demo"]="http://localhost:8008/health"
    ["prometheus"]="http://localhost:9090/-/healthy"
    ["grafana"]="http://localhost:3000/api/health"
    ["jaeger"]="http://localhost:16686/"
)

# Track overall health
ALL_HEALTHY=true

echo "=== Detektor Services Health Check ==="
echo

# Check each service
for service in "${!SERVICES[@]}"; do
    url="${SERVICES[$service]}"

    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service - healthy"
    else
        echo -e "${RED}✗${NC} $service - unhealthy (${url})"
        ALL_HEALTHY=false
    fi
done

echo

# Check Docker containers
echo "=== Docker Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(detektor|telemetry)" || true

echo

# Check GPU if available
if command -v nvidia-smi &> /dev/null; then
    echo "=== GPU Status ==="
    nvidia-smi --query-gpu=name,memory.used,memory.free,temperature.gpu --format=csv,noheader || echo "GPU check failed"
    echo
fi

# Summary
if [[ "$ALL_HEALTHY" == "true" ]]; then
    echo -e "${GREEN}All services are healthy!${NC}"
    exit 0
else
    echo -e "${RED}Some services are unhealthy!${NC}"
    echo
    echo "To check logs, run:"
    echo "  docker-compose logs [service-name]"
    exit 1
fi
