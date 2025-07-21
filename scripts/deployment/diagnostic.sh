#!/bin/bash
# =============================================================================
# Skrypt diagnostyczny do automatycznej weryfikacji środowiska deploymentowego
# Uruchamiany automatycznie w GitHub Actions oraz lokalnie
# =============================================================================

set -euo pipefail

# Kolory
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Konfiguracja
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REQUIRED_ENVS=("production" "staging" "development")
REQUIRED_PORTS=(5432 6379 8000-8008 9090 3000 16686)

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

# Sprawdzenie systemu operacyjnego
check_os() {
    log "Sprawdzanie systemu operacyjnego..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        info "System: Linux ✓"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        info "System: macOS ✓"
    else
        warning "System: Nieznany system operacyjny - może wymagać dodatkowej konfiguracji"
    fi
}

# Sprawdzenie Docker
check_docker() {
    log "Sprawdzanie Docker..."

    if ! command -v docker &> /dev/null; then
        error "Docker nie jest zainstalowany"
        return 1
    fi

    if ! docker info &> /dev/null; then
        error "Docker daemon nie działa"
        return 1
    fi

    info "Docker: $(docker --version) ✓"

    # Sprawdzenie Docker Compose
    if docker compose version &> /dev/null; then
        info "Docker Compose: $(docker compose version) ✓"
    elif docker-compose --version &> /dev/null; then
        info "Docker Compose (legacy): $(docker-compose --version) ✓"
    else
        error "Docker Compose nie jest zainstalowany"
        return 1
    fi
}

# Sprawdzenie GPU
check_gpu() {
    log "Sprawdzanie dostępności GPU..."

    if command -v nvidia-smi &> /dev/null; then
        local gpu_info=$(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader,nounits 2>/dev/null || echo "")
        if [[ -n "$gpu_info" ]]; then
            info "GPU dostępna: $gpu_info ✓"
            return 0
        fi
    fi

    warning "GPU niedostępna - niektóre serwisy mogą działać w trybie CPU-only"
}

# Sprawdzenie wymaganych zmiennych środowiskowych
check_env_vars() {
    log "Sprawdzanie zmiennych środowiskowych..."

    local required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "RTSP_URL"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        warning "Brakujące zmienne środowiskowe: ${missing_vars[*]}"
        info "Użyj pliku .env lub ustaw zmienne ręcznie"
        return 1
    fi

    info "Wszystkie wymagane zmienne środowiskowe są ustawione ✓"
}

# Sprawdzenie wolnych portów
check_ports() {
    log "Sprawdzanie dostępności portów..."

    local conflict_found=false

    for port in "${REQUIRED_PORTS[@]}"; do
        if [[ "$port" == *-* ]]; then
            # Zakres portów
            local start_port=$(echo $port | cut -d'-' -f1)
            local end_port=$(echo $port | cut -d'-' -f2)

            for ((p=start_port; p<=end_port; p++)); do
                if lsof -i ":$p" &> /dev/null; then
                    warning "Port $p jest zajęty"
                    conflict_found=true
                fi
            done
        else
            # Pojedynczy port
            if lsof -i ":$port" &> /dev/null; then
                warning "Port $port jest zajęty"
                conflict_found=true
            fi
        fi
    done

    if [[ "$conflict_found" == "true" ]]; then
        error "Znaleziono konflikty portów"
        return 1
    fi

    info "Wszystkie wymagane porty są dostępne ✓"
}

# Sprawdzenie przestrzeni dyskowej
check_disk_space() {
    log "Sprawdzanie przestrzeni dyskowej..."

    local available=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    local usage=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $5}' | sed 's/%//')

    if [[ $usage -gt 80 ]]; then
        warning "Mało miejsca na dysku: ${usage}% użyte, ${available} dostępne"
    else
        info "Przestrzeń dyskowa OK: ${available} dostępne ✓"
    fi
}

# Sprawdzenie połączenia z internetem
check_internet() {
    log "Sprawdzanie połączenia z internetem..."

    if curl -sf https://ghcr.io &> /dev/null; then
        info "Połączenie z GitHub Container Registry OK ✓"
    else
        warning "Brak połączenia z GitHub Container Registry - obrazy mogą nie być dostępne"
    fi

    if curl -sf https://registry.hub.docker.com &> /dev/null; then
        info "Połączenie z Docker Hub OK ✓"
    else
        warning "Brak połączenia z Docker Hub"
    fi
}

# Sprawdzenie uprawnień
check_permissions() {
    log "Sprawdzanie uprawnień..."

    if [[ ! -w "$PROJECT_ROOT" ]]; then
        error "Brak uprawnień do zapisu w katalogu projektu"
        return 1
    fi

    if [[ ! -r "$PROJECT_ROOT/docker-compose.yml" ]]; then
        error "Brak uprawnień do odczytu pliku docker-compose.yml"
        return 1
    fi

    info "Uprawnienia OK ✓"
}

# Sprawdzenie wymaganych plików
check_required_files() {
    log "Sprawdzanie wymaganych plików..."

    local required_files=(
        "docker-compose.yml"
        "docker-compose.observability.yml"
        "docker-compose.storage.yml"
        ".env"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            error "Brakujący plik: $file"
            return 1
        fi
    done

    info "Wszystkie wymagane pliki są obecne ✓"
}

# Test szybkości dysku
check_disk_performance() {
    log "Sprawdzanie wydajności dysku..."

    local test_file="/tmp/detektor_disk_test_$$"

    if command -v dd &> /dev/null; then
        local write_speed=$(dd if=/dev/zero of="$test_file" bs=1M count=100 2>&1 | awk '/copied/ {print $(NF-1) " " $NF}')
        rm -f "$test_file"
        info "Prędkość zapisu: $write_speed"
    fi
}

# Główna funkcja diagnostyczna
main() {
    echo "=========================================="
    echo "  Diagnostyka środowiska Detektor"
    echo "=========================================="
    echo

    local exit_code=0

    # Lista wszystkich testów
    local tests=(
        check_os
        check_docker
        check_gpu
        check_env_vars
        check_ports
        check_disk_space
        check_internet
        check_permissions
        check_required_files
        check_disk_performance
    )

    for test in "${tests[@]}"; do
        echo
        if ! $test; then
            exit_code=1
        fi
    done

    echo
    echo "=========================================="
    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}✓ Wszystkie testy przeszły pomyślnie!${NC}"
        echo "Środowisko jest gotowe do deploymentu."
    else
        echo -e "${RED}✗ Wykryto problemy!${NC}"
        echo "Napraw problemy przed kontynuacją deploymentu."
    fi
    echo "=========================================="

    exit $exit_code
}

# Uruchom jeśli skrypt jest wykonywany bezpośrednio
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
