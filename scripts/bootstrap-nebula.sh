#!/bin/bash
# =============================================================================
# Bootstrap Script dla Inicjalizacji Infrastruktury na Nebula
# Używa lokalnego dockera na GitHub Actions Runnerze
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Kolory
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

# Sprawdzenie czy jesteśmy na GitHub Actions
is_github_actions() {
    [[ -n "${GITHUB_ACTIONS:-}" ]]
}

# Inicjalizacja systemu
init_system() {
    log "Inicjalizacja systemu Detektor na Nebula..."

    # Sprawdzenie wymagań
    info "Sprawdzanie wymagań systemowych..."

    # Sprawdzenie Docker
    if ! command -v docker &> /dev/null; then
        error "Docker nie jest zainstalowany"
        exit 1
    fi

    # Sprawdzenie Docker Compose
    if ! docker compose version &> /dev/null; then
        error "Docker Compose nie jest zainstalowany"
        exit 1
    fi

    # Sprawdzenie dostępnych zasobów
    local cpu_cores=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "unknown")
    local memory_gb=$(free -g | awk '/^Mem:/ {print $2}' 2>/dev/null || echo "unknown")

    info "CPU cores: $cpu_cores"
    info "Memory: ${memory_gb}GB"

    log "Wymagania systemowe spełnione ✓"
}

# Konfiguracja dockera
configure_docker() {
    log "Konfiguracja Docker..."

    # Utworzenie network dla projektu
    docker network create detektor-network 2>/dev/null || true

    # Pull bazowych obrazów
    info "Pobieranie bazowych obrazów..."
    docker pull postgres:15-alpine
    docker pull redis:7-alpine
    docker pull prom/prometheus:latest
    docker pull grafana/grafana:latest
    docker pull jaegertracing/all-in-one:latest

    log "Obrazy bazowe pobrane ✓"
}

# Inicjalizacja storage
init_storage() {
    log "Inicjalizacja storage..."

    # Utworzenie katalogów danych
    mkdir -p "$PROJECT_ROOT/data/postgres"
    mkdir -p "$PROJECT_ROOT/data/redis"
    mkdir -p "$PROJECT_ROOT/data/grafana"
    mkdir -p "$PROJECT_ROOT/data/prometheus"

    # Ustawienie uprawnień
    chmod 755 "$PROJECT_ROOT/data"
    chmod 700 "$PROJECT_ROOT/data/postgres"
    chmod 700 "$PROJECT_ROOT/data/redis"

    log "Storage zainicjalizowany ✓"
}

# Konfiguracja monitoringu
init_monitoring() {
    log "Inicjalizacja monitoringu..."

    # Uruchomienie infrastruktury monitoringu
    docker compose -f "$PROJECT_ROOT/docker-compose.observability.yml" up -d

    # Czekanie na gotowość
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf http://localhost:9090/-/healthy &>/dev/null && \
           curl -sf http://localhost:16686/ &>/dev/null && \
           curl -sf http://localhost:3000/api/health &>/dev/null; then
            log "Monitoring gotowy ✓"
            break
        fi

        log "Czekam na monitoring... próba $attempt/$max_attempts"
        sleep 5
        ((attempt++))
    done

    if [[ $attempt -gt $max_attempts ]]; then
        warning "Monitoring nie jest gotowy po 150 sekundach"
    fi
}

# Konfiguracja bazy danych
init_database() {
    log "Inicjalizacja bazy danych..."

    # Uruchomienie PostgreSQL
    docker compose -f "$PROJECT_ROOT/docker-compose.storage.yml" up -d postgres

    # Czekanie na gotowość
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if docker compose -f "$PROJECT_ROOT/docker-compose.storage.yml" exec -T postgres pg_isready -U detektor &>/dev/null; then
            log "PostgreSQL gotowy ✓"
            break
        fi

        log "Czekam na PostgreSQL... próba $attempt/$max_attempts"
        sleep 5
        ((attempt++))
    done

    if [[ $attempt -gt $max_attempts ]]; then
        error "PostgreSQL nie jest gotowy po 150 sekundach"
        exit 1
    fi

    # Inicjalizacja schematu
    if [[ -f "$PROJECT_ROOT/init-scripts/postgres/01-init-timescaledb.sql" ]]; then
        info "Inicjalizacja schematu TimescaleDB..."
        docker compose -f "$PROJECT_ROOT/docker-compose.storage.yml" exec -T postgres psql -U detektor -d detektor_db -f /docker-entrypoint-initdb.d/01-init-timescaledb.sql
    fi

    log "Baza danych zainicjalizowana ✓"
}

# Konfiguracja Redis
init_redis() {
    log "Inicjalizacja Redis..."

    # Uruchomienie Redis
    docker compose -f "$PROJECT_ROOT/docker-compose.storage.yml" up -d redis

    # Test połączenia
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if docker compose -f "$PROJECT_ROOT/docker-compose.storage.yml" exec -T redis redis-cli ping &>/dev/null; then
            log "Redis gotowy ✓"
            break
        fi

        log "Czekam na Redis... próba $attempt/$max_attempts"
        sleep 5
        ((attempt++))
    done

    if [[ $attempt -gt $max_attempts ]]; then
        error "Redis nie jest gotowy po 150 sekundach"
        exit 1
    fi

    log "Redis zainicjalizowany ✓"
}

# Konfiguracja GitHub Container Registry
configure_ghcr() {
    log "Konfiguracja GitHub Container Registry..."

    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        echo "$GITHUB_TOKEN" | docker login ghcr.io -u hretheum --password-stdin
        log "Zalogowano do GHCR ✓"
    else
        warning "GITHUB_TOKEN nie ustawiony - obrazy będą budowane lokalnie"
    fi
}

# Główna funkcja bootstrap
bootstrap() {
    log "Rozpoczynam bootstrap Detektor na Nebula..."

    init_system
    configure_docker
    init_storage
    configure_ghcr
    init_database
    init_redis
    init_monitoring

    log "Bootstrap zakończony sukcesem! 🎉"
    log ""
    log "System jest gotowy do użycia."
    log "Użyj './scripts/deploy-local-on-nebula.sh' aby uruchomić serwisy"
    log ""
    log "Dostępne serwisy:"
    log "  - PostgreSQL: localhost:5432"
    log "  - Redis: localhost:6379"
    log "  - Prometheus: http://localhost:9090"
    log "  - Grafana: http://localhost:3000 (admin/admin)"
    log "  - Jaeger: http://localhost:16686"
}

# Obsługa różnych komend
case "${1:-bootstrap}" in
    bootstrap)
        bootstrap
        ;;
    storage)
        init_storage && init_database && init_redis
        ;;
    monitoring)
        init_monitoring
        ;;
    system)
        init_system && configure_docker
        ;;
    *)
        echo "Użycie: $0 {bootstrap|storage|monitoring|system}"
        exit 1
        ;;
esac
