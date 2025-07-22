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
        "docker-compose.yml"
        "docker-compose.observability.yml"
        "docker-compose.storage.yml"
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

    # Sprawdź czy infrastruktura już działa
    local infra_running=true

    # Sprawdź kontenery storage
    if ! sudo docker compose -f "$PROJECT_ROOT/docker-compose.storage.yml" ps --format json | grep -q '"State":"running"'; then
        infra_running=false
    fi

    # Sprawdź kontenery observability
    if ! sudo docker compose -f "$PROJECT_ROOT/docker-compose.observability.yml" ps --format json | grep -q '"State":"running"'; then
        infra_running=false
    fi

    if [ "$infra_running" = true ]; then
        log "Infrastruktura już działa, pomijam uruchamianie ✓"
        return 0
    fi

    # Uruchom storage (PostgreSQL, Redis)
    log "Uruchamianie storage services..."
    sudo docker compose -f "$PROJECT_ROOT/docker-compose.storage.yml" up -d || {
        warning "Niektóre kontenery storage mogą już działać, kontynuuję..."
    }

    # Uruchom observability (Prometheus, Jaeger, Grafana)
    log "Uruchamianie observability services..."
    sudo docker compose -f "$PROJECT_ROOT/docker-compose.observability.yml" up -d || {
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

        # Pull najnowszych obrazów dla wybranych serwisów
        for service in $SERVICES_LIST; do
            log "Pobieranie najnowszego obrazu dla $service..."
            sudo docker compose -f "$PROJECT_ROOT/docker-compose.yml" pull "$service" || true
        done

        # Restart tylko wybranych serwisów
        # shellcheck disable=SC2086
        sudo docker compose -f "$PROJECT_ROOT/docker-compose.yml" up -d --no-deps $SERVICES_LIST
    else
        # Uruchom wszystkie serwisy
        log "Uruchamianie wszystkich serwisów..."
        sudo docker compose -f "$PROJECT_ROOT/docker-compose.yml" up -d
    fi

    log "Serwisy aplikacji uruchomione ✓"
}

# Sprawdzenie health check wszystkich serwisów
health_check_all() {
    log "Sprawdzanie health check wszystkich serwisów..."

    "$PROJECT_ROOT/scripts/health-check-all.sh"
}

# Główna funkcja
main() {
    log "Rozpoczynam deployment na GitHub Actions Runner..."

    check_docker_access
    check_required_files
    prepare_environment

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
