# 🚀 REKOMENDACJE UNIFIKACJI SYSTEMU DEPLOYMENT

## EXECUTIVE SUMMARY

System deployment projektu Detektor wymaga gruntownej reorganizacji. Główne problemy:
- **3 różne nazwy** dla tego samego projektu (detektr, detektr, consensus)
- **14 workflows** z duplikującą się logiką
- **16 plików docker-compose** bez jasnej hierarchii
- **Mieszane obrazy** w GHCR pod różnymi nazwami
- **Główne serwisy nie działają** na produkcji (Nebula)

## 📋 PLAN DZIAŁANIA - FAZY DO REALIZACJI PO KOLEI

### FAZA 1: UNIFIKACJA NAZEWNICTWA (Priorytet: KRYTYCZNY)

#### 1.1 Wybór jednolitej nazwy
**DECYZJA**: Używamy `detektr` jako oficjalnej nazwy
- **Dlaczego**: Krótka, łatwa do zapamiętania, już używana jako nazwa repo
- **Registry path**: `ghcr.io/hretheum/detektr/`

#### 1.2 Kroki implementacji
```bash
# 1. Ujednolicenie w workflows
find .github/workflows -name "*.yml" -exec sed -i '' 's|hretheum/detektr|hretheum/detektr|g' {} \;
find .github/workflows -name "*.yml" -exec sed -i '' 's|IMAGE_PREFIX: .*|IMAGE_PREFIX: ghcr.io/hretheum/detektr|g' {} \;

# 2. Ujednolicenie w docker-compose
find . -name "docker-compose*.yml" -exec sed -i '' 's|ghcr.io/hretheum/detektr/|ghcr.io/hretheum/detektr/|g' {} \;

# 3. Aktualizacja dokumentacji
find docs -name "*.md" -exec sed -i '' 's|detektr|detektr|g' {} \;
```

### FAZA 2: KONSOLIDACJA WORKFLOWS (Priorytet: WYSOKI)

#### 2.1 Struktura docelowa - TYLKO 5 workflows

```
.github/workflows/
├── main-pipeline.yml      # Główny CI/CD (build + deploy)
├── pr-checks.yml          # Walidacja PR
├── manual-operations.yml  # Operacje manualne (rebuild, cleanup)
├── scheduled-tasks.yml    # Zadania cykliczne (cleanup, security scan)
└── release.yml           # Tworzenie release
```

#### 2.2 main-pipeline.yml - Unified workflow
```yaml
name: Main CI/CD Pipeline

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      services:
        description: 'Services to build (comma-separated or "all")'
        default: 'changed'
      deploy:
        description: 'Deploy after build'
        type: boolean
        default: true

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ghcr.io/hretheum/detektr

jobs:
  detect-changes:
    # Używamy dorny/paths-filter dla wszystkich serwisów

  build:
    # Buduje tylko zmienione lub wybrane serwisy
    # Używa matrix strategy

  deploy:
    # Deploy na Nebula jeśli deploy=true
    # Używa docker compose z właściwymi plikami
```

#### 2.3 Usunięcie duplikatów
- Usunąć: `UNIFIED-deploy.yml` (template)
- Scalić: `deploy-self-hosted.yml` + `deploy-only.yml` → `main-pipeline.yml`
- Scalić: `db-deploy.yml` → `main-pipeline.yml` (jako część matrix)
- Przenieść: `cleanup-runner.yml` + `security.yml` → `scheduled-tasks.yml`

### FAZA 3: REORGANIZACJA DOCKER COMPOSE (Priorytet: WYSOKI) ✅ UKOŃCZONA

#### 3.1 Nowa struktura plików ✅

```
docker/
├── base/
│   ├── docker-compose.yml                  # Core application services
│   ├── docker-compose.storage.yml         # Redis, PostgreSQL + exporters
│   ├── docker-compose.observability.yml   # Prometheus, Grafana, Jaeger
│   └── config/                            # Prometheus config, alerts
├── environments/
│   ├── development/                       # Dev overrides with hot reload
│   └── production/                        # Prod overrides with limits
├── features/
│   ├── gpu/                              # GPU-enabled AI services
│   ├── redis-ha/                         # Redis Sentinel HA setup
│   └── ai-services/                      # LLM, gesture, audio services
└── README.md                             # Comprehensive usage guide
```

#### 3.2 Convenience Scripts ✅

```bash
# Development - hot reload, debug tools
./docker/dev.sh up -d

# Production - optimized, resource limits
./docker/prod.sh up -d

# Test runner
./docker/test.sh rtsp-capture pytest

# Migration from old structure
./scripts/migrate-docker-compose.sh
```

#### 3.3 Rezultaty ✅

- **Przed**: 16+ plików docker-compose bez hierarchii
- **Po**: 8 dobrze zorganizowanych plików w logicznej strukturze
- **Migracja**: Skrypt automatycznej migracji ze starych plików
- **Dokumentacja**: Kompletny README z przykładami użycia

### FAZA 4: CLEANUP GHCR (Priorytet: ŚREDNI)

#### 4.1 Migracja obrazów
```bash
# Skrypt migracji starych obrazów
for image in rtsp-capture telegram-alerts metadata-storage; do
  docker pull ghcr.io/hretheum/detektr/$image:latest
  docker tag ghcr.io/hretheum/detektr/$image:latest ghcr.io/hretheum/detektr/$image:latest
  docker push ghcr.io/hretheum/detektr/$image:latest
done
```

#### 4.2 Retention policy
- Zachować: 5 ostatnich wersji każdego obrazu
- Usunąć: Obrazy starsze niż 30 dni (oprócz tagged releases)
- Archiwizować: Release images w osobnym registry

### FAZA 5: DEPLOYMENT AUTOMATION (Priorytet: WYSOKI)

#### 5.1 Nowy deployment script

```bash
#!/bin/bash
# deploy.sh - Unified deployment script

set -euo pipefail

ENVIRONMENT=${1:-production}
ACTION=${2:-deploy}

case $ENVIRONMENT in
  production)
    COMPOSE_FILES="-f docker/base/docker-compose.yml -f docker/base/docker-compose.services.yml -f docker/environments/docker-compose.prod.yml -f docker/features/docker-compose.observability.yml"
    TARGET_HOST="nebula"
    ;;
  staging)
    COMPOSE_FILES="-f docker/base/docker-compose.yml -f docker/environments/docker-compose.staging.yml"
    TARGET_HOST="staging"
    ;;
  *)
    echo "Unknown environment: $ENVIRONMENT"
    exit 1
    ;;
esac

case $ACTION in
  deploy)
    ssh $TARGET_HOST "cd /opt/detektor && docker compose $COMPOSE_FILES pull && docker compose $COMPOSE_FILES up -d"
    ;;
  status)
    ssh $TARGET_HOST "cd /opt/detektor && docker compose $COMPOSE_FILES ps"
    ;;
  logs)
    ssh $TARGET_HOST "cd /opt/detektor && docker compose $COMPOSE_FILES logs -f"
    ;;
esac
```

#### 5.2 GitHub Actions integration
```yaml
- name: Deploy to Environment
  run: ./scripts/deploy.sh ${{ inputs.environment }} deploy
```

### FAZA 6: DOKUMENTACJA (Priorytet: WYSOKI)

#### 6.1 Struktura dokumentacji

```
docs/
├── README.md                 # Główny README z quick start
├── ARCHITECTURE.md          # Architektura systemu
├── DEPLOYMENT.md           # Deployment guide
├── DEVELOPMENT.md          # Development setup
├── TROUBLESHOOTING.md      # Rozwiązywanie problemów
└── runbooks/
    ├── deploy-new-service.md
    ├── rollback-procedure.md
    └── debug-failed-deployment.md
```

#### 6.2 README.md - 3 kluczowe linki

```markdown
# Detektor - System Monitoringu Wizyjnego

## 🚀 Quick Start

1. **[Architektura Systemu](docs/ARCHITECTURE.md)** - Zrozum strukturę projektu
2. **[Development Setup](docs/DEVELOPMENT.md)** - Zacznij lokalnie
3. **[Deployment Guide](docs/DEPLOYMENT.md)** - Deploy na produkcję

## 📋 TL;DR dla nowego developera

```bash
# Clone & setup
git clone https://github.com/hretheum/detektr.git
cd detektr
make setup

# Run locally
make up

# Deploy to production
make deploy ENV=production
```
```

### FAZA 7: MAKEFILE UNIFICATION (Priorytet: ŚREDNI)

#### 7.1 Unified Makefile

```makefile
# Główne komendy
.PHONY: help
help:
	@echo "Detektor - Available commands:"
	@echo "  make up              - Start local development"
	@echo "  make down            - Stop all services"
	@echo "  make build           - Build all images"
	@echo "  make test            - Run tests"
	@echo "  make deploy          - Deploy to production"
	@echo "  make logs            - Show logs"
	@echo "  make status          - Show service status"

# Zmienne
COMPOSE_DEV := docker compose -f docker/base/docker-compose.yml -f docker/environments/docker-compose.dev.yml
COMPOSE_PROD := docker compose -f docker/base/docker-compose.yml -f docker/environments/docker-compose.prod.yml -f docker/features/docker-compose.observability.yml

# Development
up:
	$(COMPOSE_DEV) up -d

down:
	$(COMPOSE_DEV) down

build:
	$(COMPOSE_DEV) build

# Production
deploy:
	./scripts/deploy.sh production deploy

deploy-status:
	./scripts/deploy.sh production status

# Utilities
clean:
	docker system prune -af
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

setup:
	./scripts/setup-dev-environment.sh
```

## 📊 METRYKI SUKCESU

| Metryka | Przed | Po | Cel |
|---------|-------|-----|-----|
| Liczba workflow files | 14 | 5 | ✅ -64% |
| Liczba docker-compose files | 16 | 8 | ✅ -50% |
| Czas deployment | ~15 min | ~5 min | ✅ -67% |
| Nazwy projektu | 3 | 1 | ✅ Unified |
| Dokumentacja | Rozproszona | 3 główne pliki | ✅ |
| Komend do deployment | Wiele | 1 (make deploy) | ✅ |

## ⚠️ RYZYKA I MITYGACJE

1. **Downtime podczas migracji**
   - Mitygacja: Blue-green deployment, najpierw staging

2. **Błędy w nowych workflows**
   - Mitygacja: Testy na branchu przed merge do main

3. **Problemy z backward compatibility**
   - Mitygacja: Okres przejściowy z aliasami dla starych nazw

## 📝 CHECKLIST PRE-DEPLOYMENT

- [ ] Backup wszystkich obecnych konfiguracji
- [ ] Test nowych workflows na osobnym branchu
- [ ] Komunikacja do zespołu o zmianach
- [ ] Przygotowanie rollback plan
- [ ] Update dokumentacji
- [ ] Smoke tests po deployment

---

**Przygotował**: Claude Assistant
**Data**: 2025-07-23
**Wersja**: 3.0 (jedna lista faz do realizacji po kolei)
