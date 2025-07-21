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

    if ! docker info &> /dev/null; then
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
    source "$PROJECT_ROOT/.env"
    set +a

    log "Zmienne środowiskowe przygotowane ✓"
}

# Uruchomienie infrastruktury
start_infrastructure() {
    log "Uruchamianie infrastruktury..."

    # Utwórz network jeśli nie istnieje
    docker network create detektor-network 2>/dev/null || true

    # Uruchom storage (PostgreSQL, Redis)
    log "Uruchamianie storage services..."
    docker compose -f "$PROJECT_ROOT/docker-compose.storage.yml" up -d

    # Uruchom observability (Prometheus, Jaeger, Grafana)
    log "Uruchamianie observability services..."
    docker compose -f "$PROJECT_ROOT/docker-compose.observability.yml" up -d

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

    # Użyj głównego docker-compose.yml
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" up -d

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

    start_infrastructure
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
        log "  - Prometheus: http://localhost
