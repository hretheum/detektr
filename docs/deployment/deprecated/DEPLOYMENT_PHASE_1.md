# Deployment Guide - Faza 1 Completed

## 🎯 Overview

Faza 1 projektu Detektor została ukończona z pełną infrastrukturą CI/CD i observability. Ten dokument opisuje aktualny stan deployment oraz jak z niego korzystać.

## ✅ Co zostało zrealizowane

### 1. Infrastruktura Observability
- **Prometheus** (port 9090) - metryki
- **Jaeger** (port 16686) - distributed tracing
- **Grafana** (port 3000) - dashboards
- **Loki** - centralne logi (przez Grafana)

### 2. CI/CD Pipeline
- **GitHub Actions** - automatyczne budowanie obrazów
- **GitHub Container Registry** - przechowywanie obrazów
- **Deployment Script** - automatyzacja wdrożeń na Nebula

### 3. Przykładowe Serwisy
- **example-otel** - demonstracja pełnego observability
- **frame-tracking** - śledzenie klatek (template)
- **echo-service** - base service template
- **gpu-demo** - wykorzystanie GPU (template)

## 🚀 Deployment Workflow

### Automatyczny deployment (rekomendowany)

```bash
# 1. Wprowadź zmiany w kodzie
vim services/my-service/main.py

# 2. Commit i push
git add .
git commit -m "feat: add new feature"
git push origin main

# 3. GitHub Actions automatycznie:
#    - Buduje obrazy Docker
#    - Publikuje do ghcr.io
#    - (opcjonalnie) Deployuje na Nebula

# 4. Sprawdź status
ssh nebula "/opt/detektor/scripts/health-check-all.sh"
```

### Manual deployment

```bash
# Jeśli chcesz zdeployować istniejące obrazy
./scripts/deploy-to-nebula.sh

# Skrypt automatycznie:
# - Pobiera najnowsze obrazy z registry
# - Deszyfruje sekrety (SOPS)
# - Aktualizuje docker-compose
# - Restartuje serwisy
# - Wykonuje health checks
```

## 📦 Struktura na serwerze Nebula

```
/opt/detektor/
├── docker-compose.yml           # Główny compose (z registry)
├── docker-compose.observability.yml
├── docker-compose.storage.yml
├── .env                        # Zaszyfrowane sekrety
├── scripts/
│   ├── health-check-all.sh
│   └── ...
└── data/                       # Persistent volumes
```

## 🔑 Secrets Management

### Edycja sekretów

```bash
# Lokalnie (wymaga klucza age)
make secrets-edit

# Lub bezpośrednio
sops .env

# Dodaj/zmień sekrety w edytorze
# Zapisz i zamknij - automatyczne szyfrowanie
```

### Używanie w serwisach

```python
import os

# DOBRZE - używanie zmiennych środowiskowych
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY not set")

# ŹLE - nigdy nie hardkoduj!
# api_key = "sk-12345..."  # ❌
```

## 🏃 Uruchamianie nowych serwisów

### 1. Skopiuj template

```bash
cp -r services/base-template services/new-service
```

### 2. Dostosuj Dockerfile

```dockerfile
FROM python:3.11-slim

# ... standardowa konfiguracja ...

# Health check obowiązkowy!
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8000/health || exit 1
```

### 3. Dodaj do CI/CD

Edytuj `.github/workflows/deploy.yml`:

```yaml
strategy:
  matrix:
    service:
      - example-otel
      - frame-tracking
      - new-service  # <-- Dodaj tutaj
```

### 4. Deploy

```bash
git add .
git commit -m "feat: add new-service"
git push origin main
```

## 📊 Monitoring

### Sprawdzanie logów

```bash
# Wszystkie serwisy
ssh nebula "cd /opt/detektor && docker-compose logs"

# Konkretny serwis
ssh nebula "cd /opt/detektor && docker-compose logs example-otel"

# Follow mode
ssh nebula "cd /opt/detektor && docker-compose logs -f example-otel"
```

### Metryki i dashboards

1. **Prometheus**: http://nebula:9090
   - Query: `up{job="detektor"}`
   - Wszystkie metryki serwisów

2. **Grafana**: http://nebula:3000
   - Login: admin/admin
   - Dashboards dla każdego serwisu

3. **Jaeger**: http://nebula:16686
   - Traces wszystkich operacji
   - Latency analysis

## 🛠️ Troubleshooting

### Problem: Serwis nie startuje

```bash
# 1. Sprawdź logi
ssh nebula "docker logs detektor-example-otel-1"

# 2. Sprawdź czy obraz istnieje
ssh nebula "docker images | grep example-otel"

# 3. Pull manually jeśli brak
ssh nebula "docker pull ghcr.io/hretheum/detektr/example-otel:latest"
```

### Problem: Health check failing

```bash
# Test bezpośrednio
ssh nebula "curl -v http://localhost:8005/health"

# Sprawdź network
ssh nebula "docker network ls | grep detektor"
```

### Problem: Brak metryk

```bash
# Sprawdź prometheus targets
curl http://nebula:9090/targets

# Verify service metrics endpoint
ssh nebula "curl http://localhost:8005/metrics"
```

## 🔄 Rollback Procedure

```bash
# 1. Lista dostępnych tagów
ssh nebula "docker images | grep example-otel"

# 2. Zatrzymaj problematyczny serwis
ssh nebula "cd /opt/detektor && docker-compose stop example-otel"

# 3. Zmień tag w docker-compose.yml lub pull konkretny
ssh nebula "docker pull ghcr.io/hretheum/detektr/example-otel:previous-sha"

# 4. Restart
ssh nebula "cd /opt/detektor && docker-compose up -d example-otel"
```

## 📋 Checklist dla nowych serwisów

- [ ] Dockerfile z health check
- [ ] OpenTelemetry instrumentation
- [ ] Prometheus metrics endpoint (/metrics)
- [ ] Structured logging z correlation ID
- [ ] Testy (unit + integration)
- [ ] Dodany do CI/CD matrix
- [ ] Dokumentacja API (OpenAPI/Swagger)
- [ ] Secrets przez env vars (nie hardcoded!)
- [ ] Resource limits w docker-compose
- [ ] Grafana dashboard

## 🚦 Status wszystkich komponentów

```bash
# Uruchom health check
ssh nebula "/opt/detektor/scripts/health-check-all.sh"

# Expected output:
# ✓ example-otel - healthy
# ✓ prometheus - healthy
# ✓ grafana - healthy
# ✓ jaeger - healthy
# ...
```

## 📞 Wsparcie

- **Dokumentacja CI/CD**: `/docs/CI_CD_SETUP.md`
- **Secrets management**: `/docs/SECRETS_MANAGEMENT.md`
- **Główna architektura**: `/architektura_systemu.md`
- **Zasady projektu**: `/CLAUDE.md`

---

**Faza 1 Status**: ✅ COMPLETED - gotowe jako solidny fundament dla Fazy 2!
