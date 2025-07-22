#!/bin/bash
# =============================================================================
# Skrypt sprawdzania zajętych portów
# =============================================================================

set -euo pipefail

# Kolory
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

# Porty używane przez Detektor
DETEKTOR_PORTS=(
    "5432:PostgreSQL"
    "6379:Redis"
    "8001:RTSP-Capture"
    "8005:Example-OTEL"
    "8006:Frame-Tracking"
    "8007:Echo-Service"
    "8008:GPU-Demo"
    "9090:Prometheus"
    "3000:Grafana"
    "16686:Jaeger"
)

check_port() {
    local port=$1
    local service=$2

    if sudo lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pid
        pid=$(sudo lsof -Pi :"$port" -sTCP:LISTEN -t)
        local process
        process=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        warning "Port $port ($service) jest zajęty przez proces: $process (PID: $pid)"

        # Sprawdź czy to kontener Docker
        if [[ "$process" == "docker-proxy" ]] || [[ "$process" == "docker" ]]; then
            local container
            container=$(sudo docker ps --format "table {{.Names}}\t{{.Ports}}" | grep ":$port->" | awk '{print $1}' | head -1)
            if [[ -n "$container" ]]; then
                warning "  → Kontener: $container"
            fi
        fi
        return 1
    else
        log "Port $port ($service) jest wolny ✓"
        return 0
    fi
}

main() {
    log "Sprawdzanie portów używanych przez Detektor..."

    local has_conflicts=false

    for port_info in "${DETEKTOR_PORTS[@]}"; do
        IFS=':' read -r port service <<< "$port_info"
        if ! check_port "$port" "$service"; then
            has_conflicts=true
        fi
    done

    echo ""

    if [[ "$has_conflicts" == true ]]; then
        error "Znaleziono konflikty portów!"
        echo ""
        echo "Aby zwolnić porty, możesz użyć:"
        echo "  1. docker stop \$(docker ps -q)"
        echo "  2. docker rm -f \$(docker ps -aq)"
        echo "  3. sudo kill -9 <PID>"
        return 1
    else
        log "Wszystkie porty są wolne! ✅"
        return 0
    fi
}

main "$@"
