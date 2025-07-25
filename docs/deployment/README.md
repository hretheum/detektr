# 🚀 Deployment Guide - Unified Pipeline

> **✅ AKTUALIZACJA**: Ta dokumentacja odzwierciedla aktualny stan po konsolidacji workflows (Faza 2) i migracji GHCR (Faza 4)

## 📋 Spis treści

1. [Quick Start](#quick-start)
2. [Architektura Deployment](#architektura-deployment)
3. [Workflows CI/CD](#workflows-cicd)
4. [Zarządzanie Sekretami](#zarządzanie-sekretami)
5. [Monitoring i Troubleshooting](#monitoring-i-troubleshooting)
6. [Dodawanie Nowego Serwisu](#dodawanie-nowego-serwisu)

## 🚀 Quick Start

### Unified Deployment (ZALECANE)
```bash
# Deploy produkcyjny - automatyczny przy push do main
git push origin main

# Lub użyj skryptu pomocniczego
./scripts/deploy.sh production deploy

# Sprawdź status
./scripts/deploy.sh production status

# Sprawdź logi
./scripts/deploy.sh production logs [service-name]

# Weryfikuj health wszystkich serwisów
./scripts/deploy.sh production verify
```

### Manualne wywołanie workflow
```bash
# Build i deploy wszystkich serwisów
gh workflow run main-pipeline.yml

# Tylko build
gh workflow run main-pipeline.yml -f action=build-only

# Tylko deploy
gh workflow run main-pipeline.yml -f action=deploy-only

# Konkretny serwis
gh workflow run main-pipeline.yml -f services=rtsp-capture,frame-buffer
```

## 🏗️ Architektura Deployment

### Infrastruktura
- **Serwer**: Nebula (self-hosted)
- **Container Runtime**: Docker + Docker Compose
- **Registry**: GitHub Container Registry (ghcr.io/hretheum/detektr/*)
- **CI/CD**: GitHub Actions z self-hosted runner

### Struktura na serwerze (po Fazie 3)
```
/opt/detektor/
├── docker/                      # Hierarchiczna struktura
│   ├── base/                    # Podstawowe definicje
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.storage.yml
│   │   └── docker-compose.observability.yml
│   ├── environments/            # Override dla środowisk
│   │   ├── development/
│   │   └── production/
│   ├── features/                # Opcjonalne funkcje
│   │   ├── gpu/
│   │   ├── redis-ha/
│   │   └── ai-services/
│   ├── dev.sh                   # Skrypt pomocniczy dev
│   └── prod.sh                  # Skrypt pomocniczy prod
├── .env (encrypted with SOPS)   # Sekrety
└── scripts/                     # Skrypty pomocnicze
```

## 📦 Workflows CI/CD (Po konsolidacji - Faza 2)

### 1. **main-pipeline.yml** - Główny pipeline CI/CD
- **Trigger**: Push do main, manual dispatch
- **Funkcje**:
  - Smart detection - buduje tylko zmienione serwisy
  - Trzy tryby: build-and-deploy (domyślnie), build-only, deploy-only
  - Równoległe budowanie dla wydajności
- **Użycie**:
  ```bash
  # Automatycznie przy push
  git push origin main

  # Manualnie
  gh workflow run main-pipeline.yml -f action=build-only
  ```

### 2. **pr-checks.yml** - Walidacja Pull Requests
- **Trigger**: Pull requests
- **Funkcje**:
  - Linting (black, isort, flake8, mypy)
  - Testy jednostkowe Python
  - Security scanning
  - Docker build validation
- **Rozszerzone**: Automatyczne komentarze z wynikami

### 3. **manual-operations.yml** - Operacje manualne
- **Trigger**: workflow_dispatch
- **Funkcje**:
  - cleanup-docker: Czyszczenie nieużywanych obrazów
  - diagnostic: Diagnostyka środowiska
  - backup: Backup danych
  - restore: Przywracanie z backup
- **Użycie**:
  ```bash
  gh workflow run manual-operations.yml -f operation=cleanup-docker
  ```

### 4. **scheduled-tasks.yml** - Zadania cykliczne
- **Trigger**: Schedule (cron)
- **Harmonogram**:
  - Daily cleanup: 2:00 UTC
  - Weekly rebuild: Niedziela 3:00 UTC
  - Monthly security scan: 1. dzień miesiąca 4:00 UTC
  - GHCR cleanup: Niedziela 4:00 UTC (zintegrowane)
- **Użycie manulane**:
  ```bash
  gh workflow run scheduled-tasks.yml -f task=ghcr-cleanup
  ```

### 5. **release.yml** - Zarządzanie wersjami
- **Trigger**: Tag push (v*.*.*)
- **Funkcje**:
  - Tworzenie GitHub Release
  - Generowanie changelog
  - Deployment wersji stable
  - Archiwizacja artefaktów

## 🔐 Zarządzanie Sekretami

### SOPS + Age
```bash
# Edytuj sekrety
make secrets-edit

# Deploy z sekretami (automatyczne odszyfrowanie)
make deploy

# Ręczne odszyfrowanie
sops -d .env.sops > .env.decrypted
```

### Kluczowe sekrety
- `POSTGRES_PASSWORD` - Hasło do PostgreSQL
- `REDIS_PASSWORD` - Hasło do Redis
- `GRAFANA_ADMIN_PASSWORD` - Hasło admina Grafana
- `OPENAI_API_KEY` - Klucz API OpenAI
- `RTSP_CAMERA_PASSWORD` - Hasło do kamer RTSP

## 📊 Monitoring i Troubleshooting

### Endpoints monitoringu
| Serwis | URL | Opis |
|--------|-----|------|
| Grafana | http://nebula:3000 | Dashboardy i wizualizacje |
| Prometheus | http://nebula:9090 | Metryki i zapytania |
| Jaeger | http://nebula:16686 | Distributed tracing |

### Health Checks serwisów
```bash
# Sprawdź wszystkie serwisy
for port in 8080 8081 8082 8083 8084 8085 8086 8087 8088 8089; do
  echo "Checking port $port..."
  curl -s http://nebula:$port/health || echo "No service on $port"
done

# Konkretny serwis
curl http://nebula:8080/health  # rtsp-capture
curl http://nebula:8081/health  # frame-tracking
curl http://nebula:8082/health  # frame-buffer
```

### Diagnostyka
```bash
# Status wszystkich serwisów
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Logi konkretnego serwisu
docker logs -f --tail 100 [service-name]

# Zasoby systemowe
docker stats --no-stream

# GHCR status
gh api "/users/hretheum/packages?package_type=container" | jq -r '.[].name' | grep detektr
```

## 🆕 Dodawanie Nowego Serwisu

### 1. Sprawdź przed rozpoczęciem
- [ ] Przeczytaj [PORT_ALLOCATION.md](./PORT_ALLOCATION.md) - lista zajętych portów
- [ ] Zobacz [Service Template](./templates/service-template.md) - wzorzec dokumentacji
- [ ] Zapoznaj się z [Troubleshooting Guide](./troubleshooting/common-issues.md)

### 2. Kroki implementacji
```bash
# 1. Stwórz strukturę serwisu
mkdir -p services/my-new-service
cd services/my-new-service

# 2. Dodaj Dockerfile i kod
# ... implementacja ...

# 3. Dodaj do docker-compose
# Edytuj odpowiedni plik w docker/base/ lub docker/features/

# 4. Stwórz dokumentację
cp docs/deployment/templates/service-template.md \
   docs/deployment/services/my-new-service.md

# 5. Deploy
git add .
git commit -m "feat: add my-new-service"
git push origin main
```

### 3. Weryfikacja
```bash
# Sprawdź build w GitHub Actions
# https://github.com/hretheum/detektr/actions

# Sprawdź deployment
curl http://nebula:[assigned-port]/health

# Sprawdź metryki
curl http://nebula:[assigned-port]/metrics
```

## ⚠️ Znane Problemy i Rozwiązania

### 1. GitHub Runner permissions
```bash
ssh nebula "sudo chown -R github-runner:github-runner /opt/detektor"
```

### 2. Image pull errors
```bash
# Sprawdź dostęp do registry
docker pull ghcr.io/hretheum/detektr/[service]:latest

# Login do GHCR jeśli potrzebny
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

### 3. SOPS decryption
```bash
# Sprawdź age key
ssh nebula "ls -la /home/github-runner/.config/sops/age/keys.txt"

# Regeneruj jeśli brak
age-keygen -o keys.txt
```

## 📚 Dokumentacja Serwisów

### Podstawowe serwisy
- [RTSP Capture](services/rtsp-capture.md) - Port 8080
- [Frame Tracking](services/frame-tracking.md) - Port 8081
- [Frame Buffer](services/frame-buffer.md) - Port 8082
- [Metadata Storage](services/metadata-storage.md) - Port 8085
- [Base Template](services/base-template.md) - Port 8000
- [Echo Service](services/echo-service.md) - Port 8007

### Storage i Messaging
- [PostgreSQL/TimescaleDB](services/postgresql-timescale.md) - Port 5432
- [PgBouncer](services/pgbouncer.md) - Port 6432
- [Redis](services/redis.md) - Port 6379

### Observability
- [Prometheus](services/prometheus.md) - Port 9090
- [Grafana](services/grafana.md) - Port 3000
- [Jaeger](services/jaeger.md) - Port 16686

## 🔗 Przydatne linki

- [GitHub Actions](https://github.com/hretheum/detektr/actions) - Status CI/CD
- [GitHub Packages](https://github.com/hretheum/detektr/packages) - Registry obrazów
- [Project Board](https://github.com/users/hretheum/projects/X) - Status zadań

---

**📌 UWAGA**: Ta dokumentacja jest aktualizowana wraz z rozwojem projektu. W razie wątpliwości sprawdź najnowsze commity lub zapytaj na Slacku #detektor-dev
