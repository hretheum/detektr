# 🚀 Deployment Guide - RZECZYWISTA DOKUMENTACJA

> **WAŻNE**: Ta dokumentacja odzwierciedla FAKTYCZNY stan deployment na Nebula (self-hosted runner + Docker Compose)

## 📋 Spis treści

1. [Quick Start](#quick-start)
2. [Architektura Deployment](#architektura-deployment)
3. [Workflows CI/CD](#workflows-cicd)
4. [Zarządzanie Sekretami](#zarządzanie-sekretami)
5. [Monitoring i Troubleshooting](#monitoring-i-troubleshooting)

## 🚀 Quick Start

### Stara metoda (legacy)
```bash
# Deploy wszystkiego
git push origin main

# Sprawdź status
ssh nebula "cd /opt/detektor && docker compose ps"
```

### NOWA metoda (hierarchiczna struktura)
```bash
# Deploy produkcyjny
ssh nebula "cd /opt/detektor && ./docker/prod.sh up -d"

# Sprawdź status
ssh nebula "cd /opt/detektor && ./docker/prod.sh ps"

# Sprawdź logi
ssh nebula "cd /opt/detektor && ./docker/prod.sh logs -f [service-name]"

# Migracja ze starej struktury
ssh nebula "cd /opt/detektor && ./scripts/migrate-docker-compose.sh"
```

## 🏗️ Architektura Deployment

### Infrastruktura
- **Serwer**: Nebula (self-hosted)
- **Container Runtime**: Docker + Docker Compose
- **Registry**: GitHub Container Registry (ghcr.io)
- **CI/CD**: GitHub Actions z self-hosted runner

### Struktura na serwerze
```
/opt/detektor/
├── docker/                      # NOWA struktura hierarchiczna
│   ├── base/                    # Podstawowe definicje
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.storage.yml
│   │   └── docker-compose.observability.yml
│   ├── environments/            # Override dla środowisk
│   │   ├── development/
│   │   └── production/
│   └── features/                # Opcjonalne funkcje
│       ├── gpu/
│       ├── redis-ha/
│       └── ai-services/
├── docker-compose.yml           # Legacy (dla kompatybilności)
├── .env (encrypted with SOPS)   # Sekrety
└── scripts/                     # Skrypty pomocnicze
    └── migrate-docker-compose.sh # Migracja do nowej struktury
```

## 📦 Workflows CI/CD

### Główne Workflows (PO KONSOLIDACJI - Faza 2)

#### 1. `main-pipeline.yml` - Zunifikowany CI/CD
- **Trigger**: Push do main, PR, manual
- **Funkcja**: Buduje i deployuje na podstawie zmian
- **Możliwości**:
  - build-and-deploy (domyślnie)
  - build-only
  - deploy-only
- **Smart detection**: Buduje tylko zmienione serwisy

#### 2. `pr-checks.yml` - Walidacja PR
- **Trigger**: Pull requests
- **Funkcja**: Linting, testy, security scan
- **Rozszerzone**: Testy Python, Docker build validation

#### 3. `manual-operations.yml` - Operacje manualne
- **Trigger**: workflow_dispatch
- **Funkcja**: Cleanup, diagnostyka, rebuild
- **Konsoliduje**: cleanup-runner, test-runner, diagnostic

#### 4. `scheduled-tasks.yml` - Zadania cykliczne
- **Trigger**: Cron schedule
- **Funkcja**:
  - Daily cleanup (2 AM UTC)
  - Weekly rebuild (Sunday 3 AM)
  - Monthly security scan (1st day 4 AM)

#### 5. `release.yml` - Zarządzanie wersjami
- **Trigger**: Tag push (v*)
- **Funkcja**: Tworzenie release, changelog, deployment

## 🔐 Zarządzanie Sekretami

### SOPS + Age
```bash
# Edytuj sekrety
make secrets-edit

# Deploy z sekretami
make deploy  # Automatycznie odszyfrowuje

# Ręczne odszyfrowanie
sops -d .env > .env.decrypted
```

### Sekrety w .env
```
POSTGRES_PASSWORD
REDIS_PASSWORD
GRAFANA_ADMIN_PASSWORD
OPENAI_API_KEY
RTSP_CAMERA_PASSWORD
```

## 📊 Monitoring i Troubleshooting

### Endpoints
- **Grafana**: http://nebula:3000 (admin/admin)
- **Prometheus**: http://nebula:9090
- **Jaeger**: http://nebula:16686

### Health Checks
```bash
# Sprawdź wszystkie serwisy
curl http://nebula:8001/health  # rtsp-capture
curl http://nebula:8002/health  # frame-buffer
curl http://nebula:8006/health  # frame-tracking
curl http://nebula:9187/metrics  # postgres-exporter
```

### Logi
```bash
# Wszystkie logi
ssh nebula "cd /opt/detektor && docker compose logs -f"

# Konkretny serwis
ssh nebula "cd /opt/detektor && docker compose logs -f [service-name]"
```

### Restart serwisu
```bash
ssh nebula "cd /opt/detektor && docker compose restart [service-name]"
```

## ⚠️ Znane Problemy

1. **GitHub Runner permissions** - czasem trzeba naprawić:
   ```bash
   ssh nebula "sudo chown -R github-runner:github-runner /opt/detektor"
   ```

2. **Image pull errors** - sprawdź czy runner ma dostęp do registry:
   ```bash
   ssh nebula "docker pull ghcr.io/hretheum/detektr/[service]:latest"
   ```

3. **SOPS decryption** - upewnij się że age key jest na miejscu:
   ```bash
   ssh nebula "ls -la /home/github-runner/.config/sops/age/keys.txt"
   ```

## 📚 Dokumentacja Serwisów

- [RTSP Capture](services/rtsp-capture.md)
- [Frame Buffer](services/frame-buffer.md)
- [Frame Tracking](services/frame-tracking.md)
- [PostgreSQL/TimescaleDB](services/postgresql-timescale.md)
- [Message Broker](services/message-broker.md)

## 🔧 Dodawanie Nowego Serwisu

Zobacz: [New Service Guide](guides/new-service.md)

---

**UWAGA**: Ignoruj wszelkie wzmianki o Kubernetes, kubectl, helm - używamy Docker Compose!
