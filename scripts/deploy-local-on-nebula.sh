#!/bin/bash
# =============================================================================
# Skrypt deployment dla GitHub Actions Runner (local deployment na Nebula)
# Bez użycia SSH - używa lokalnego dockera na runnerze
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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

# Sprawdzenie czy mamy dostęp do dockera
check_docker_access() {
    log "Sprawdzanie dostępu do Docker..."

    if ! command -v docker &> /dev/null; then
        error "Docker nie jest dostępny"
        exit 1
    fi

    if ! sudo docker info &> /dev/null; then
        error "Brak uprawnień do Docker"
        exit 1
    fi

    log "Dostęp do Docker potwierdzony ✓"
}

# Sprawdzenie wymaganych plików
check_required_files() {
    log "Sprawdzanie wymaganych plików..."

    local required_files=(
        "docker/base/docker-compose.yml"
        "docker/base/docker-compose.observability.yml"
        "docker/base/docker-compose.storage.yml"
        "docker/environments/production/docker-compose.yml"
        "docker/base/config/prometheus.yml"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            error "Brakujący plik: $file"
            exit 1
        fi
    done

    log "Wszystkie pliki są obecne ✓"
}

# Przygotowanie zmiennych środowiskowych
prepare_environment() {
    log "Przygotowywanie zmiennych środowiskowych..."

    # Upewnij się że .env istnieje
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        warning "Brak pliku .env, używam .env.example jako szablonu"
        if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        else
            error "Brak .env oraz .env.example"
            exit 1
        fi
    fi

    # Source .env
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a

    log "Zmienne środowiskowe przygotowane ✓"
}

# Uruchomienie infrastruktury
start_infrastructure() {
    log "Sprawdzanie stanu infrastruktury..."

    # Utwórz network jeśli nie istnieje
    sudo docker network create detektor-network 2>/dev/null || true

    # Ensure consistent project name
    export COMPOSE_PROJECT_NAME=detektr

    # Sprawdź czy infrastruktura już działa
    local infra_running=true

    # Sprawdź kontenery storage
    if ! sudo COMPOSE_PROJECT_NAME=detektr docker compose -f "$PROJECT_ROOT/docker/base/docker-compose.storage.yml" ps --format json | grep -q '"State":"running"'; then
        infra_running=false
    fi

    # Sprawdź kontenery observability
    if ! sudo COMPOSE_PROJECT_NAME=detektr docker compose -f "$PROJECT_ROOT/docker/base/docker-compose.observability.yml" ps --format json | grep -q '"State":"running"'; then
        infra_running=false
    fi

    if [ "$infra_running" = true ]; then
        log "Infrastruktura już działa, pomijam uruchamianie ✓"
        return 0
    fi

    # Najpierw utwórz sieć jeśli nie istnieje
    log "Tworzenie sieci Docker jeśli nie istnieje..."
    sudo docker network create detektor-network 2>/dev/null || true

    # Uruchom storage (PostgreSQL, Redis)
    log "Uruchamianie storage services..."
    sudo COMPOSE_PROJECT_NAME=detektr docker compose \
        -f "$PROJECT_ROOT/docker/base/docker-compose.storage.yml" \
        -f "$PROJECT_ROOT/docker/environments/production/docker-compose.yml" \
        up -d --remove-orphans || {
        warning "Niektóre kontenery storage mogą już działać, kontynuuję..."
    }

    # Uruchom observability (Prometheus, Jaeger, Grafana)
    log "Uruchamianie observability services..."
    sudo COMPOSE_PROJECT_NAME=detektr docker compose \
        -f "$PROJECT_ROOT/docker/base/docker-compose.observability.yml" \
        -f "$PROJECT_ROOT/docker/environments/production/docker-compose.yml" \
        up -d --remove-orphans || {
        warning "Niektóre kontenery observability mogą już działać, kontynuuję..."
    }

    # Czekaj na gotowość infrastruktury
    log "Czekam na gotowość infrastruktury..."
    sleep 15

    # Sprawdź health check
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf http://localhost:9090/-/healthy &>/dev/null && \
           curl -sf http://localhost:16686/ &>/dev/null && \
           curl -sf http://localhost:3000/api/health &>/dev/null; then
            log "Infrastruktura gotowa ✓"
            break
        fi

        log "Czekam... próba $attempt/$max_attempts"
        sleep 5
        ((attempt++))
    done

    if [[ $attempt -gt $max_attempts ]]; then
        error "Infrastruktura nie jest gotowa po 150 sekundach"
        return 1
    fi
}

# Uruchomienie serwisów aplikacji
start_services() {
    log "Uruchamianie serwisów aplikacji..."

    # Sprawdź czy mamy określone konkretne serwisy do restartu
    if [[ -n "${SERVICES_TO_RESTART:-}" ]]; then
        log "Restartowanie wybranych serwisów: $SERVICES_TO_RESTART"

        # Konwertuj przecinki na spacje
        SERVICES_LIST=$(echo "$SERVICES_TO_RESTART" | tr ',' ' ')

        # Dla każdego serwisu: stop, remove, pull, start
        for service in $SERVICES_LIST; do
            log "Przetwarzanie serwisu: $service"

            # Zatrzymaj stary kontener
            log "  → Zatrzymywanie starego kontenera..."
            sudo COMPOSE_PROJECT_NAME=detektr docker compose \
                -f "$PROJECT_ROOT/docker/base/docker-compose.yml" \
                -f "$PROJECT_ROOT/docker/environments/production/docker-compose.yml" \
                stop "$service" 2>/dev/null || true

            # Usuń stary kontener
            log "  → Usuwanie starego kontenera..."
            sudo COMPOSE_PROJECT_NAME=detektr docker compose \
                -f "$PROJECT_ROOT/docker/base/docker-compose.yml" \
                -f "$PROJECT_ROOT/docker/environments/production/docker-compose.yml" \
                rm -f "$service" 2>/dev/null || true

            # Pobierz najnowszy obraz
            log "  → Pobieranie najnowszego obrazu..."
            sudo COMPOSE_PROJECT_NAME=detektr docker compose \
                -f "$PROJECT_ROOT/docker/base/docker-compose.yml" \
                -f "$PROJECT_ROOT/docker/environments/production/docker-compose.yml" \
                pull "$service"

            # Uruchom nowy kontener
            log "  → Uruchamianie nowego kontenera..."
            sudo COMPOSE_PROJECT_NAME=detektr docker compose \
                -f "$PROJECT_ROOT/docker/base/docker-compose.yml" \
                -f "$PROJECT_ROOT/docker/environments/production/docker-compose.yml" \
                up -d --no-deps "$service"
        done
    else
        # Pełny deployment - zatrzymaj, usuń i uruchom wszystko
        log "Pełny restart wszystkich serwisów..."

        # Najpierw zatrzymaj WSZYSTKIE kontenery projektu aby zwolnić porty
        log "Zatrzymywanie wszystkich kontenerów projektu detektor..."
        sudo docker ps -q --filter "label=com.docker.compose.project=detektr" | xargs -r sudo docker stop || true
        sudo docker ps -aq --filter "label=com.docker.compose.project=detektr" | xargs -r sudo docker rm -f || true

        # Dodatkowo usuń kontenery które mogą mieć stare nazwy
        log "Usuwanie starych kontenerów..."
        sudo docker rm -f gpu-demo detektr-redis-1 detektr-postgres-1 detektr-loki-1 detektr-prometheus-1 detektr-grafana-1 detektr-jaeger-1 2>/dev/null || true

        # Zatrzymaj wszystkie kontenery przez docker-compose
        log "Zatrzymywanie kontenerów przez docker-compose..."
        sudo COMPOSE_PROJECT_NAME=detektr docker compose \
            -f "$PROJECT_ROOT/docker/base/docker-compose.yml" \
            -f "$PROJECT_ROOT/docker/base/docker-compose.storage.yml" \
            -f "$PROJECT_ROOT/docker/base/docker-compose.observability.yml" \
            -f "$PROJECT_ROOT/docker/environments/production/docker-compose.yml" \
            down --remove-orphans --volumes || true

        # Pull wszystkich obrazów
        log "Pobieranie najnowszych obrazów..."
        sudo COMPOSE_PROJECT_NAME=detektr docker compose \
            -f "$PROJECT_ROOT/docker/base/docker-compose.yml" \
            -f "$PROJECT_ROOT/docker/base/docker-compose.storage.yml" \
            -f "$PROJECT_ROOT/docker/base/docker-compose.observability.yml" \
            -f "$PROJECT_ROOT/docker/environments/production/docker-compose.yml" \
            pull

        # Uruchom wszystkie serwisy
        log "Uruchamianie wszystkich serwisów..."
        sudo COMPOSE_PROJECT_NAME=detektr docker compose \
            -f "$PROJECT_ROOT/docker/base/docker-compose.yml" \
            -f "$PROJECT_ROOT/docker/base/docker-compose.storage.yml" \
            -f "$PROJECT_ROOT/docker/base/docker-compose.observability.yml" \
            -f "$PROJECT_ROOT/docker/environments/production/docker-compose.yml" \
            up -d
    fi

    log "Serwisy aplikacji uruchomione ✓"
}

# Sprawdzenie health check wszystkich serwisów
health_check_all() {
    log "Sprawdzanie health check wszystkich serwisów..."

    "$PROJECT_ROOT/scripts/health-check-all.sh"
}

# Główna funkcja
check_ports() {
    log "Sprawdzanie dostępności portów..."

    # Sprawdź kluczowe porty - WSZYSTKIE z docker-compose
    # UWAGA: Port 9400 (DCGM Exporter) jest częścią infrastruktury i pozostaje uruchomiony
    local ports_to_check=(
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
        # 9400  # DCGM Exporter - SKIP (infrastruktura)
        3000    # Grafana
        3100    # Loki
        16686   # Jaeger UI
        14268   # Jaeger Thrift
        4317    # OTLP gRPC
        4318    # OTLP HTTP
    )
    local has_conflicts=false

    for port in "${ports_to_check[@]}"; do
        if sudo lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
            warning "Port $port jest zajęty!"
            has_conflicts=true

            # Znajdź proces używający portu
            local pid
            pid=$(sudo lsof -Pi :"$port" -sTCP:LISTEN -t 2>/dev/null | head -1)

            if [[ -n "$pid" ]]; then
                local process_info
                process_info=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
                warning "  → Proces: $process_info (PID: $pid)"

                # Jeśli to docker-proxy, znajdź kontener
                if [[ "$process_info" == "docker-proxy" ]] || [[ "$process_info" == "docker" ]]; then
                    # Szukaj kontenera używającego tego portu
                    local container
                    container=$(sudo docker ps -a --format "{{.Names}}" | while read -r name; do
                        if sudo docker port "$name" 2>/dev/null | grep -q ":$port"; then
                            echo "$name"
                            break
                        fi
                    done)

                    if [[ -n "$container" ]]; then
                        warning "  → Zatrzymuję kontener: $container"
                        sudo docker stop "$container" 2>/dev/null || true
                        sudo docker rm -f "$container" 2>/dev/null || true
                    fi
                fi
            fi
        fi
    done

    if [[ "$has_conflicts" == true ]]; then
        warning "Porty były zajęte, próbuję inteligentne czyszczenie..."

        # Najpierw zatrzymaj tylko kontenery projektu detektr (new project name)
        warning "Zatrzymuję kontenery projektu detektr..."
        # shellcheck disable=SC2046
        sudo docker stop $(sudo docker ps -q --filter "label=com.docker.compose.project=detektr") 2>/dev/null || true
        # shellcheck disable=SC2046
        sudo docker rm -f $(sudo docker ps -aq --filter "label=com.docker.compose.project=detektr") 2>/dev/null || true

        # Also clean up old project name containers
        # shellcheck disable=SC2046
        sudo docker stop $(sudo docker ps -q --filter "label=com.docker.compose.project=detektor") 2>/dev/null || true
        # shellcheck disable=SC2046
        sudo docker rm -f $(sudo docker ps -aq --filter "label=com.docker.compose.project=detektor") 2>/dev/null || true

        # Usuń też kontenery które mogą być z innych plików compose
        warning "Usuwam stare kontenery Redis HA i inne..."
        sudo docker rm -f sentinel-1 sentinel-2 sentinel-3 redis-slave redis-master 2>/dev/null || true
        sudo docker rm -f detektor-telegram-alerts detektor-loki-1 2>/dev/null || true

        # NIE usuwamy kontenerów infrastruktury monitoring - są częścią observability z Fazy 1
        warning "UWAGA: Kontenery infrastruktury (dcgm_exporter, alertmanager, etc.) pozostają uruchomione"
        warning "Są częścią observability stack z Fazy 1 i używają host networking"

        # Daj czas na zwolnienie portów
        sleep 5

        # Sprawdź ponownie
        local still_occupied=false
        for port in "${ports_to_check[@]}"; do
            if sudo lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
                error "Port $port NADAL jest zajęty po czyszczeniu!"
                still_occupied=true
            fi
        done

        if [[ "$still_occupied" == true ]]; then
            error "Niektóre porty nadal są zajęte. Możliwe, że działają procesy spoza Docker."
            error "Sprawdź ręcznie: sudo lsof -i :6379 (i inne porty)"
        fi
    else
        log "Wszystkie porty są wolne ✓"
    fi
}

main() {
    log "Rozpoczynam deployment na GitHub Actions Runner..."

    check_docker_access
    check_required_files
    prepare_environment
    check_ports

    # Jeśli deployujemy tylko konkretne serwisy, sprawdź czy infrastruktura działa
    if [[ -n "${SERVICES_TO_RESTART:-}" ]]; then
        log "Tryb selective deployment: $SERVICES_TO_RESTART"
        # Dla selective deployment tylko sprawdzamy infrastrukturę
        if ! curl -sf http://localhost:9090/-/healthy &>/dev/null; then
            log "Infrastruktura nie działa, uruchamiam..."
            start_infrastructure
        else
            log "Infrastruktura już działa ✓"
        fi
    else
        # Pełny deployment - restart wszystkiego
        start_infrastructure
    fi

    start_services

    # Czekaj na stabilizację
    log "Czekam na stabilizację serwisów..."
    sleep 30

    # Dodatkowy czas dla Frame Tracking (potrzebuje połączenia z DB)
    log "Dodatkowy czas dla serwisów wymagających bazy danych..."
    sleep 30

    # Health check
    if health_check_all; then
        log "Deployment zakończony sukcesem! 🎉"
        log "Dostęp do serwisów:"
        log "  - RTSP Capture: http://localhost:8001"
        log "  - Example OTEL: http://localhost:8005"
        log "  - Frame Tracking: http://localhost:8006"
        log "  - Echo Service: http://localhost:8007"
        log "  - GPU Demo: http://localhost:8008"
        log "  - Prometheus: http://localhost:9090"
        log "  - Grafana: http://localhost:3000"
        log "  - Jaeger: http://localhost:16686"
    else
        error "Health check nie powiódł się"
        return 1
    fi
}

# Uruchom główną funkcję
main "$@"
