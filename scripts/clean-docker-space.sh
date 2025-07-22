#!/bin/bash
# =============================================================================
# Skrypt czyszczenia przestrzeni Docker
# Używany gdy brakuje miejsca na dysku
# =============================================================================

set -euo pipefail

# Kolory
# RED='\033[0;31m'  # Unused for now
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

# Sprawdź miejsce przed
log "Przestrzeń dyskowa przed czyszczeniem:"
df -h /

# Usuń nieużywane obrazy
log "Usuwanie nieużywanych obrazów Docker..."
sudo docker image prune -af || true

# Usuń zatrzymane kontenery
log "Usuwanie zatrzymanych kontenerów..."
sudo docker container prune -f || true

# Usuń nieużywane wolumeny
log "Usuwanie nieużywanych wolumenów..."
sudo docker volume prune -f || true

# Usuń nieużywane sieci
log "Usuwanie nieużywanych sieci..."
sudo docker network prune -f || true

# Usuń build cache
log "Usuwanie build cache..."
sudo docker builder prune -af || true

# System prune (agresywne czyszczenie)
log "Wykonywanie docker system prune..."
sudo docker system df
sudo docker system prune -af --volumes || true

# Wyczyść APT cache
log "Czyszczenie APT cache..."
sudo apt-get autoremove -y || true
sudo apt-get clean || true

# Wyczyść journal logs
log "Czyszczenie journal logs..."
sudo journalctl --vacuum-time=3d || true

# Wyczyść GitHub Actions cache jeśli istnieje
if [ -d "/home/github-runner/actions-runner/_work/_temp" ]; then
    log "Czyszczenie GitHub Actions temp..."
    find /home/github-runner/actions-runner/_work/_temp -type f -mtime +1 -delete || true
fi

# Sprawdź miejsce po
log "Przestrzeń dyskowa po czyszczeniu:"
df -h /

# Pokaż co zajmuje najwięcej miejsca
log "Największe katalogi:"
sudo du -h / 2>/dev/null | sort -rh | head -20 || true
