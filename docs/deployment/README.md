# 🚀 Deployment Guide - RZECZYWISTA DOKUMENTACJA

> **WAŻNE**: Ta dokumentacja odzwierciedla FAKTYCZNY stan deployment na Nebula (self-hosted runner + Docker Compose)

## 📋 Spis treści

1. [Quick Start](#quick-start)
2. [Architektura Deployment](#architektura-deployment)
3. [Workflows CI/CD](#workflows-cicd)
4. [Zarządzanie Sekretami](#zarządzanie-sekretami)
5. [Monitoring i Troubleshooting](#monitoring-i-troubleshooting)

## 🚀 Quick Start

```bash
# Deploy wszystkiego
git push origin main

# Sprawdź status
ssh nebula "cd /opt/detektor && docker compose ps"

# Sprawdź logi
ssh nebula "cd /opt/detektor && docker compose logs [service-name]"
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
├── docker-compose.yml           # Główny compose z serwisami
├── docker-compose.storage.yml   # PostgreSQL, Redis
├── docker-compose.observability.yml  # Grafana, Prometheus, Jaeger
├── .env (encrypted with SOPS)   # Sekrety
└── scripts/                     # Skrypty pomocnicze
```

## 📦 Workflows CI/CD

### Główne Workflows (FAKTYCZNIE UŻYWANE)

#### 1. `deploy-self-hosted.yml` - Główny workflow
- **Trigger**: Push do main lub manual
- **Funkcja**: Buduje i deployuje zmienione serwisy
- **Używa**: Buildx, cache, multi-stage builds
- **Deploy**: Automatyczny na Nebula

#### 2. `db-deploy.yml` - Deploy bazy danych
- **Trigger**: Zmiany w services/timescaledb/** lub pgbouncer/**
- **Funkcja**: Buduje obrazy TimescaleDB i PgBouncer
- **Problem**: Tworzy Dockerfile w runtime (do naprawy!)

#### 3. `deploy-only.yml` - Sam deployment
- **Trigger**: Manual
- **Funkcja**: Tylko pull i restart serwisów (bez budowania)

### Pomocnicze Workflows

- `ci.yml` - Linting i testy
- `cleanup-runner.yml` - Czyszczenie dysku (co 6h)
- `manual-service-build.yml` - Ręczne budowanie pojedynczego serwisu
- `security.yml` - Skanowanie CVE

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
   ssh nebula "docker pull ghcr.io/hretheum/bezrobocie-detektor/[service]:latest"
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
