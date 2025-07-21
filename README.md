# System Detekcji i Automatyzacji Wizyjnej

[![CI](https://github.com/hretheum/bezrobocie-detektor/actions/workflows/ci.yml/badge.svg)](https://github.com/hretheum/bezrobocie-detektor/actions/workflows/ci.yml)
[![Deploy](https://github.com/hretheum/bezrobocie-detektor/actions/workflows/deploy.yml/badge.svg)](https://github.com/hretheum/bezrobocie-detektor/actions/workflows/deploy.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Hobbystyczny system przechwytywania obrazu z kamery IP z wykorzystaniem AI do rozpoznawania i automatyzacji Home Assistant.

## 🚨 **DOKUMENTACJA DEPLOYMENT - NOWA LOKALIZACJA**

### **📍 DLA WSZYSTKICH LLM - ZACZNIJ TUTAJ:**
**Wszystkie aktualne dokumentacje deploymentu** przeniesione do: `docs/deployment/`

### **🔗 Kluczowe Linki:**
- **[Przewodnik Deploymentu](docs/deployment/README.md)** - Główny przewodnik
- **[Szybki Start](docs/deployment/quick-start.md)** - 30-sekundowe wdrożenie
- **[RTSP Capture Service](docs/deployment/services/rtsp-capture.md)** - Konkretna usługa
- **[Szablon Nowej Usługi](docs/deployment/templates/service-template.md)** - Kopiuj i użyj

### **🤖 Instrukcje dla LLM:**
1. **Zawsze zacznij od**: `docs/deployment/README.md`
2. **Dla nowych usług**: Użyj szablonu `service-template.md`
3. **Deployment**: Tylko `git push origin main` (CI/CD)
4. **Problemy**: `docs/deployment/troubleshooting/common-issues.md`

## Cel Projektu

Stworzenie kompletnego systemu który:

- Przechwytuje strumień RTSP z kamer IP
- Rozpoznaje twarze, gesty i obiekty za pomocą AI
- Integruje się z Home Assistant dla automatyzacji
- Obsługuje interakcję głosową z LLM
- Zapewnia pełną observability od początku

## Stack Technologiczny

- **Serwer**: Ubuntu z GTX 4070 Super (16GB VRAM), i7, 64GB RAM (hostname: nebula)
- **Infrastruktura**: Docker, Docker Compose, container-first
- **CI/CD**: GitHub Actions + Self-hosted Runner + GHCR
- **Języki**: Python 3.11+, FastAPI
- **AI/ML**: YOLO v8, MediaPipe, InsightFace, Whisper
- **LLM**: OpenAI/Anthropic API
- **Observability**: Jaeger, Prometheus, Grafana
- **Architektura**: Clean Architecture, DDD, Event Sourcing, TDD
- **Secrets**: SOPS z age encryption

## Architektura

System składa się z 7 faz implementacji:

```
Faza 0: Dokumentacja i planowanie          ✅ [UKOŃCZONA]
Faza 1: Fundament z observability          ✅ [UKOŃCZONA + CI/CD]
  ✅ Docker & NVIDIA setup
  ✅ Git repository & struktura
  ✅ Observability stack (Jaeger, Prometheus, Grafana, Loki)
  ✅ OpenTelemetry SDK
  ✅ Frame tracking design
  ✅ TDD setup
  ✅ Monitoring dashboard
  ✅ CI/CD Pipeline (GitHub Actions + Self-hosted Runner)
  ✅ Automated deployment (push to main = auto deploy)
  ✅ Example services z pełnym observability
  ✅ GPU demo service (YOLO v8)
Faza 2: Akwizycja i storage                🚧 [W TRAKCIE]
  ✅ RTSP Capture Service (Bloki 0-5 ukończone, deployed on Nebula)
    - Service running: http://nebula:8001
    - Reolink camera configured with /Preview_01_main
    - Status: "degraded" (Redis not initialized - expected)
  ✅ Frame Buffer Service (Blok 5 ukończony, deployed on Nebula)
    - Service running: http://nebula:8002
    - Redis Streams backend with persistence
    - Full observability (Prometheus + OpenTelemetry)
    - DLQ support, 80k fps, 0.01ms latency
  ⏳ Redis/RabbitMQ Configuration
  ⏳ PostgreSQL/TimescaleDB
  ⏳ Frame tracking implementation
Faza 3: AI services podstawy               ⏳ [ZAPLANOWANA]
Faza 4: Integracja z Home Assistant        ⏳ [ZAPLANOWANA]
Faza 5: Zaawansowane AI i voice            ⏳ [ZAPLANOWANA]
Faza 6: Optymalizacja i refinement         ⏳ [ZAPLANOWANA]
```

## Quick Start

### Lokalne development

```bash
# Klonowanie
git clone git@github.com:hretheum/bezrobocie-detektor.git
cd detektor

# Setup environment
make secrets-init
make secrets-edit  # Dodaj swoje klucze API

# Uruchomienie stacku lokalnie
make up

# Monitoring
open http://localhost:3000    # Grafana
open http://localhost:16686   # Jaeger
open http://localhost:9090    # Prometheus
```

### Deployment na produkcję (Nebula)

```bash
# Automatyczny deployment przy push!
git push origin main

# GitHub Actions automatycznie:
# 1. Buduje obrazy Docker
# 2. Pushuje do GitHub Container Registry
# 3. Self-hosted runner deployuje na Nebula

# Sprawdzenie statusu
ssh nebula "cd /opt/detektor && docker compose ps"

# Health check wszystkich serwisów
ssh nebula "curl -s http://localhost:8001/health | jq"  # rtsp-capture (✅ deployed)
ssh nebula "curl -s http://localhost:8005/health | jq"  # example-otel
ssh nebula "curl -s http://localhost:8006/health | jq"  # frame-tracking
ssh nebula "curl -s http://localhost:8007/health | jq"  # echo-service
ssh nebula "curl -s http://localhost:8010/health | jq"  # base-template
```

## 📋 **NOWA DOKUMENTACJA - STRUKTURA HYBRYDOWA**

### **Dla Developerów:**
- **[Przewodnik Deploymentu](docs/deployment/README.md)** - Kompletny przewodnik
- **[Szybki Start](docs/deployment/quick-start.md)** - 30-sekundowe wdrożenie
- **[Szablony Usług](docs/deployment/templates/)** - Gotowe do kopiowania

### **Dla Usług:**
- **[RTSP Capture Service](docs/deployment/services/rtsp-capture.md)** - Szczegółowa dokumentacja
- **[Frame Tracking Service](docs/deployment/services/frame-tracking.md)** - Szczegółowa dokumentacja
- **[Szablon Nowej Usługi](docs/deployment/templates/service-template.md)** - Kopiuj i użyj

### **Dla Rozwiązywania Problemów:**
- **[Problemy i Rozwiązania](docs/deployment/troubleshooting/common-issues.md)** - 15+ problemów
- **[Procedury Awaryjne](docs/deployment/troubleshooting/emergency.md)** - Krok-po-kroku

## 🚨 **DOKUMENTACJA PRZESTARZAŁA - IGNORUJ**
- `docs/CI_CD_*.md` - PRZESTARZAŁE
- `docs/DEPLOYMENT_*.md` - PRZESTARZAŁE
- `docs/MANUAL_DEPLOYMENT.md` - PRZESTARZAŁE
- **Wszystkie aktualne dokumentacje**: `docs/deployment/`

## Kluczowe Zasady

1. **🚨 ZASADA ZERO**: NIGDY nie hardkoduj sekretów (używaj SOPS!)
2. **TDD**: Test-driven development od początku
3. **Observability First**: Tracing i metryki w każdym serwisie
4. **Clean Architecture**: Separacja warstw, DDD patterns
5. **Container First**: Wszystko w Docker
6. **CI/CD First**: Build w GitHub Actions, deploy z registry (NIGDY build na produkcji!)

## Zarządzanie Sekretami

Projekt wykorzystuje **SOPS + age** dla bezpiecznego zarządzania sekretami:

```bash
# Edycja sekretów
make secrets-edit

# Automatyczne uruchomienie z odszyfrowaniem
make up

# Status
make secrets-status
```

## Development Workflow

```bash
# Wybierz fazę w architektura_systemu.md
# Znajdź zadanie [ ] (nieukończone)
# Otwórz dekompozycję (link "Szczegóły →")
# Wykonaj blok:
/nakurwiaj <numer_bloku>

# Po każdym bloku:
make test     # Uruchom testy
make lint     # Sprawdź kod
git commit    # Zapisz zmiany
```

## Porty Serwisów

- **8001**: rtsp-capture ✅ (deployed on Nebula, status: degraded)
- **8002**: face-recognition
- **8003**: object-detection
- **8004**: ha-bridge
- **8005**: example-otel ✅ (działający przykład)
- **8006**: frame-tracking ✅
- **8007**: echo-service ✅
- **8008**: gpu-demo ✅
- **8010**: base-template ✅
- **9090**: Prometheus ✅
- **16686**: Jaeger ✅
- **3000**: Grafana ✅

## Status Projektu

**Aktualny stan**: Faza 1 COMPLETED ✅ - Faza 2 w trakcie

**Faza 1 - Ukończone komponenty**:
- ✅ Infrastruktura observability (Prometheus, Jaeger, Grafana)
- ✅ CI/CD pipeline (GitHub Actions + GHCR)
- ✅ Deployment automation (scripts/deploy-to-nebula.sh)
- ✅ Example service z pełnym observability (example-otel)
- ✅ Secrets management (SOPS z age)
- ✅ Health monitoring (scripts/health-check-all.sh)
- ✅ **NOWA DOKUMENTACJA**: Unified deployment docs (`docs/deployment/`)

**Faza 2 - W trakcie**:
- ✅ Frame Buffer (80k fps, 0.01ms latency, DLQ)
- ✅ RTSP Capture Service (Bloki 0-5 ukończone, deployed on Nebula)
  - Deployment successful via CI/CD pipeline
  - Reolink camera properly configured (rtsp://192.168.1.195:554/Preview_01_main)
  - Service health: "degraded" (Redis not initialized - expected at this stage)
- ✅ **NOWA DOKUMENTACJA**: Hybrydowa struktura deploymentu

## Kontrybuowanie

Ten projekt realizuje podejście **observability-first** i **TDD**.

**Dla LLM - zawsze zacznij od**: `docs/deployment/README.md`

Przed rozpoczęciem pracy:
1. Przeczytaj **NOWĄ dokumentację**: `docs/deployment/README.md`
2. Sprawdź **szablon usługi**: `docs/deployment/templates/service-template.md`
3. Użyj `/nakurwiaj` dla automatycznego wykonania bloków zadań

## Licencja

MIT License - projekt hobbystyczny/edukacyjny.

---

🤖 **Projekt realizowany z Claude Code** - [claude.ai/code](https://claude.ai/code)
