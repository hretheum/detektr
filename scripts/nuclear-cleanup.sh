#!/bin/bash
# =============================================================================
# NUCLEAR CLEANUP - Usuwa WSZYSTKIE kontenery Docker i zwalnia porty
# UWAGA: To usunie WSZYSTKIE kontenery, nie tylko z projektu Detektor!
# =============================================================================

set -euo pipefail

# Kolory
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

# Porty używane przez Detektor - WSZYSTKIE z docker-compose
DETEKTOR_PORTS=(
    5432    # PostgreSQL
    5050    # pgAdmin
    6379    # Redis
    6380    # Redis slave
    26379   # Redis Sentinel 1
    26380   # Redis Sentinel 2
    26381   # Redis Sentinel 3
    8001    # RTSP Capture
    8005    # Example OTEL
    8006    # Frame Tracking
    8007    # Echo Service
    8008    # GPU Demo
    9090    # Prometheus
    9121    # Redis Exporter
    9400    # DCGM Exporter
    3000    # Grafana
    3100    # Loki
    16686   # Jaeger UI
    14268   # Jaeger Thrift
    4317    # OTLP gRPC
    4318    # OTLP HTTP
)

main() {
    warning "=== NUCLEAR CLEANUP ==="
    warning "To usunie WSZYSTKIE kontenery Docker!"
    warning "Kontynuować? (y/N)"

    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log "Anulowano"
        exit 0
    fi

    log "Zatrzymuję WSZYSTKIE kontenery Docker..."
    # shellcheck disable=SC2046
    sudo docker stop $(sudo docker ps -q) 2>/dev/null || true

    log "Usuwam WSZYSTKIE kontenery..."
    # shellcheck disable=SC2046
    sudo docker rm -f $(sudo docker ps -aq) 2>/dev/null || true

    log "Usuwam nieużywane wolumeny..."
    sudo docker volume prune -f 2>/dev/null || true

    log "Usuwam nieużywane sieci..."
    sudo docker network prune -f 2>/dev/null || true

    log "Sprawdzam porty Detektor..."
    local has_issues=false

    for port in "${DETEKTOR_PORTS[@]}"; do
        if sudo lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
            local pid
            pid=$(sudo lsof -Pi :"$port" -sTCP:LISTEN -t 2>/dev/null | head -1)
            local process
            process=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")

            error "Port $port nadal zajęty przez: $process (PID: $pid)"
            has_issues=true

            # Jeśli to nie Docker, możemy spróbować zabić proces
            if [[ "$process" != "docker"* ]]; then
                warning "Próbuję zabić proces $pid..."
                sudo kill -9 "$pid" 2>/dev/null || true
                sleep 1

                # Sprawdź ponownie
                if ! sudo lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
                    log "Port $port zwolniony ✓"
                else
                    error "Nie mogę zwolnić portu $port!"
                fi
            fi
        else
            log "Port $port wolny ✓"
        fi
    done

    echo ""

    if [[ "$has_issues" == false ]]; then
        log "Czyszczenie zakończone! Wszystkie porty są wolne ✅"
    else
        error "Niektóre porty nadal są zajęte!"
        error "Może to być spowodowane przez:"
        error "1. Procesy systemowe (PostgreSQL, Redis zainstalowane lokalnie)"
        error "2. Inne aplikacje używające tych portów"
        echo ""
        echo "Sprawdź ręcznie:"
        echo "  sudo systemctl status postgresql"
        echo "  sudo systemctl status redis"
        echo "  sudo lsof -i :PORT"
    fi

    echo ""
    log "Stan Docker:"
    sudo docker ps -a
}

main "$@"
