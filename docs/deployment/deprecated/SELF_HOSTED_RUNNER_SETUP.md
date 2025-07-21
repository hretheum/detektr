# Self-hosted GitHub Actions Runner na Nebula

## Przegląd

Self-hosted runner to najczystsze rozwiązanie dla deployment na lokalny serwer Nebula. Runner działa w lokalnej sieci, ma dostęp do Nebula i może deployować bezpośrednio.

## Dlaczego Self-hosted Runner?

### ✅ Zalety
- **Bezpośredni dostęp do lokalnej sieci** - runner widzi Nebula
- **Pełna automatyzacja CI/CD** - deploy automatyczny po push
- **Bezpieczeństwo** - brak kodu źródłowego na produkcji
- **Szybkość** - lokalne transfery, cache Dockera
- **Kontrola** - pełna kontrola nad środowiskiem runner

### ❌ Alternatywy i dlaczego są gorsze
- **Manual deploy** - wymaga interwencji człowieka
- **VPN/Tunnel** - skomplikowane, dodatkowe punkty awarii
- **Kod na produkcji** - fundamentalny błąd bezpieczeństwa

## Architektura docelowa

```
GitHub → Push → GitHub Actions → Self-hosted Runner → Deploy to Nebula
                     ↓                    ↓
                Build images         (w tej samej sieci)
                     ↓                    ↓
                Push to GHCR         SSH/Docker → Nebula
```

## Prerequisites

### Na serwerze Runner (może być Nebula lub osobny)

1. **System operacyjny**
   - Ubuntu 20.04+ lub Debian 11+
   - Minimum 4GB RAM, 20GB dysku

2. **Docker**
   ```bash
   # Sprawdź
   docker --version
   docker compose version
   ```

3. **Dostęp sieciowy**
   - Dostęp do internetu (GitHub)
   - Dostęp do Nebula (SSH lub direct)

4. **Użytkownik dla runner**
   ```bash
   # Stwórz dedykowanego użytkownika
   sudo useradd -m -s /bin/bash github-runner
   sudo usermod -aG docker github-runner
   ```

## Krok 1: Przygotowanie GitHub Repository

### 1.1 Wygeneruj Runner Token

```bash
# W repozytorium na GitHub
Settings → Actions → Runners → New self-hosted runner
```

**ZAPISZ TOKEN** - będzie potrzebny tylko raz podczas setup

### 1.2 Przygotuj sekrety dla runner

```bash
# GitHub repo settings → Secrets and variables → Actions

# Dodaj (jeśli jeszcze nie ma):
NEBULA_HOST=192.168.x.x      # Local IP Nebula
NEBULA_USER=deploy            # User na Nebula
NEBULA_SSH_KEY=-----BEGIN...  # SSH key dla Nebula
SOPS_AGE_KEY=AGE-SECRET...    # Dla decrypt secrets
```

## Krok 2: Instalacja Runner

### 2.1 Pobierz i zainstaluj runner

```bash
# Jako github-runner user
sudo su - github-runner

# Stwórz katalog
mkdir actions-runner && cd actions-runner

# Pobierz najnowszy runner (sprawdź wersję na GitHub)
RUNNER_VERSION="2.317.0"
curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz \
  -L https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# Rozpakuj
tar xzf ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# Usuń archiwum
rm actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
```

### 2.2 Skonfiguruj runner

```bash
# Konfiguracja z tokenem z kroku 1.1
./config.sh \
  --url https://github.com/hretheum/detektr \
  --token YOUR_RUNNER_TOKEN \
  --name nebula-runner \
  --labels self-hosted,linux,x64,nebula \
  --work _work
```

### 2.3 Zainstaluj jako systemd service

```bash
# Jako root/sudo
cd /home/github-runner/actions-runner
sudo ./svc.sh install github-runner

# Start service
sudo ./svc.sh start

# Sprawdź status
sudo ./svc.sh status
```

### 2.4 Weryfikacja

```bash
# Sprawdź logi
sudo journalctl -u actions.runner.hretheum-detektr.nebula-runner -f

# Na GitHub powinien być widoczny jako "Idle"
# Settings → Actions → Runners
```

## Krok 3: Konfiguracja środowiska runner

### 3.1 Zainstaluj wymagane narzędzia

```bash
# Jako root/sudo
# Docker compose plugin
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# SOPS dla secrets
SOPS_VERSION="3.8.1"
curl -LO "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64"
sudo mv sops-v${SOPS_VERSION}.linux.amd64 /usr/local/bin/sops
sudo chmod +x /usr/local/bin/sops

# Age dla encryption
AGE_VERSION="1.1.1"
curl -LO "https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz"
tar xzf age-v${AGE_VERSION}-linux-amd64.tar.gz
sudo mv age/age /usr/local/bin/
sudo mv age/age-keygen /usr/local/bin/
```

### 3.2 Skonfiguruj SSH do Nebula

```bash
# Jako github-runner
sudo su - github-runner

# Stwórz SSH key (jeśli runner nie jest na Nebula)
ssh-keygen -t ed25519 -f ~/.ssh/nebula_deploy -N ""

# Skopiuj public key na Nebula
ssh-copy-id -i ~/.ssh/nebula_deploy.pub deploy@nebula

# Test połączenia
ssh -i ~/.ssh/nebula_deploy deploy@nebula "echo 'SSH OK'"
```

### 3.3 Pre-cache Docker login

```bash
# Jako github-runner
sudo su - github-runner

# Login do GitHub Container Registry
# Użyj Personal Access Token z packages:read
docker login ghcr.io
```

## Krok 4: Aktualizacja GitHub Actions Workflow

### 4.1 Nowy workflow dla self-hosted runner

```yaml
# .github/workflows/deploy-self-hosted.yml
name: Build and Deploy (Self-hosted)

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: hretheum/bezrobocie-detektor

jobs:
  build-and-push:
    name: Build Docker Images
    runs-on: ubuntu-latest  # Build nadal w chmurze
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        service:
          - example-otel
          - frame-tracking
          - base-template
          - echo-service
    steps:
      # ... existing build steps ...

  deploy:
    name: Deploy to Nebula
    needs: build-and-push
    runs-on: [self-hosted, nebula]  # Runner lokalny!
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Nebula
        env:
          NEBULA_HOST: ${{ secrets.NEBULA_HOST }}
          NEBULA_USER: ${{ secrets.NEBULA_USER }}
        run: |
          # Pull images
          docker pull ghcr.io/hretheum/bezrobocie-detektor/example-otel:latest
          docker pull ghcr.io/hretheum/bezrobocie-detektor/frame-tracking:latest
          docker pull ghcr.io/hretheum/bezrobocie-detektor/base-template:latest
          docker pull ghcr.io/hretheum/bezrobocie-detektor/echo-service:latest

          # Deploy via SSH (jeśli runner nie jest na Nebula)
          ssh ${NEBULA_USER}@${NEBULA_HOST} << 'EOF'
            cd /opt/detektor
            docker compose pull
            docker compose up -d
            docker compose ps
          EOF
```

### 4.2 Deployment script dla runner

```bash
# scripts/deploy-from-runner.sh
#!/bin/bash
set -euo pipefail

# Ten skrypt uruchamia się na self-hosted runner

NEBULA_HOST="${NEBULA_HOST}"
NEBULA_USER="${NEBULA_USER}"
REGISTRY="ghcr.io"
IMAGE_PREFIX="hretheum/bezrobocie-detektor"

# Services
SERVICES=(
    "example-otel"
    "frame-tracking"
    "base-template"
    "echo-service"
)

# Pull images locally (runner ma cache)
for service in "${SERVICES[@]}"; do
    docker pull "${REGISTRY}/${IMAGE_PREFIX}/${service}:latest"
done

# Deploy to Nebula
ssh "${NEBULA_USER}@${NEBULA_HOST}" << 'DEPLOY_SCRIPT'
set -euo pipefail

# Ensure network
docker network create detektor-network 2>/dev/null || true

# Pull and deploy
cd /opt/detektor
docker compose -f docker-compose.observability.yml up -d
docker compose -f docker-compose.storage.yml up -d
docker compose pull
docker compose up -d

# Health check
sleep 10
docker compose ps
for port in 8005 8006 8007 8010; do
    curl -sf "http://localhost:${port}/health" && echo "Port ${port} - OK" || echo "Port ${port} - FAIL"
done
DEPLOY_SCRIPT
```

## Krok 5: Testowanie

### 5.1 Test runner

```bash
# Trigger test workflow
gh workflow run test-runner.yml

# Sprawdź logi runner
sudo journalctl -u actions.runner.hretheum-detektr.nebula-runner -f
```

### 5.2 Test pełnego deployment

```bash
# Push zmian
git add .
git commit -m "test: self-hosted runner deployment"
git push origin main

# Obserwuj:
# 1. GitHub Actions - build w chmurze
# 2. Self-hosted runner - deploy lokalnie
# 3. Nebula - serwisy uruchomione
```

## Krok 6: Monitoring i Maintenance

### 6.1 Monitoring runner

```bash
# Status service
sudo systemctl status actions.runner.hretheum-detektr.nebula-runner

# Logi
sudo journalctl -u actions.runner.hretheum-detektr.nebula-runner -n 100

# Restart jeśli potrzeba
sudo ./svc.sh stop
sudo ./svc.sh start
```

### 6.2 Aktualizacja runner

```bash
# GitHub poinformuje gdy jest nowa wersja
cd /home/github-runner/actions-runner
sudo ./svc.sh stop
./config.sh remove --token REMOVAL_TOKEN
# Pobierz nową wersję i skonfiguruj ponownie
```

### 6.3 Backup konfiguracji

```bash
# Backup runner config
sudo tar -czf runner-backup-$(date +%Y%m%d).tar.gz \
  /home/github-runner/actions-runner/.credentials \
  /home/github-runner/actions-runner/.runner \
  /home/github-runner/.ssh/
```

## Troubleshooting

### Problem: Runner offline

```bash
# Sprawdź service
sudo systemctl status actions.runner.hretheum-detektr.nebula-runner

# Sprawdź połączenie z GitHub
curl -I https://api.github.com

# Restart
sudo systemctl restart actions.runner.hretheum-detektr.nebula-runner
```

### Problem: Permission denied Docker

```bash
# Dodaj runner do docker group
sudo usermod -aG docker github-runner

# Restart runner
sudo systemctl restart actions.runner.hretheum-detektr.nebula-runner
```

### Problem: SSH do Nebula nie działa

```bash
# Test jako github-runner
sudo su - github-runner
ssh -v deploy@nebula

# Sprawdź klucze
ls -la ~/.ssh/
cat ~/.ssh/known_hosts
```

## Security Best Practices

### ✅ DO

1. **Dedykowany użytkownik** - runner jako osobny user
2. **Minimal permissions** - tylko to co potrzebne
3. **Secrets w GitHub** - nie hardcoduj w skryptach
4. **Network isolation** - runner w secure network
5. **Regular updates** - aktualizuj runner i dependencies

### ❌ DON'T

1. **Root runner** - nigdy nie uruchamiaj jako root
2. **Public runner** - tylko trusted workflows
3. **Shared runner** - dedykowany dla projektu
4. **Store secrets** - używaj GitHub secrets
5. **Skip monitoring** - zawsze monitoruj runner

## Podsumowanie

Po wykonaniu tych kroków będziesz miał:

1. ✅ **Self-hosted runner** w lokalnej sieci
2. ✅ **Automatyczny deployment** po push na main
3. ✅ **Bezpieczny setup** bez kodu na produkcji
4. ✅ **Pełna automatyzacja** CI/CD
5. ✅ **Lokalny cache** Docker images

Workflow:
```
Developer → git push → GitHub Actions (build) → Self-hosted Runner (deploy) → Nebula
```

Czas setup: ~1-2h
Maintenance: ~15min/miesiąc
