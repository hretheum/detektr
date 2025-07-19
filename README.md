# System Detekcji i Automatyzacji Wizyjnej

[![CI](https://github.com/hretheum/bezrobocie-detektor/actions/workflows/ci.yml/badge.svg)](https://github.com/hretheum/bezrobocie-detektor/actions/workflows/ci.yml)
[![Deploy](https://github.com/hretheum/bezrobocie-detektor/actions/workflows/deploy.yml/badge.svg)](https://github.com/hretheum/bezrobocie-detektor/actions/workflows/deploy.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Hobbystyczny system przechwytywania obrazu z kamery IP z wykorzystaniem AI do rozpoznawania i automatyzacji Home Assistant.

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
- **CI/CD**: GitHub Actions + GitHub Container Registry (ghcr.io)
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
Faza 1: Fundament z observability          ✅ [UKOŃCZONA]
  ✅ Docker & NVIDIA setup
  ✅ Git repository & struktura
  ✅ Observability stack (Jaeger, Prometheus, Grafana, Loki)
  ✅ OpenTelemetry SDK
  ✅ Frame tracking design
  ✅ TDD setup
  ✅ Monitoring dashboard
  ✅ CI/CD Pipeline (GitHub Actions + GHCR)
  ✅ Automated deployment (registry-based)
  ✅ Example services z pełnym observability
Faza 2: Akwizycja i storage                🚧 [W TRAKCIE]
  ✅ Frame Buffer (80k fps, 0.01ms latency, DLQ)
  ⏳ RTSP Capture Service
  ⏳ PostgreSQL/TimescaleDB
  ⏳ Frame tracking
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
# Wszystko przez CI/CD!
git push origin main

# Lub manual deployment
./scripts/deploy-to-nebula.sh

# Sprawdzenie statusu
ssh nebula "/opt/detektor/scripts/health-check-all.sh"
```

## Dokumentacja

- 📋 **[Architektura Systemu](./architektura_systemu.md)** - Główny dokument projektu
- 🛠️ **[Zasady Projektu (CLAUDE.md)](./CLAUDE.md)** - Wzorce i standardy (zawiera CI/CD guidelines!)
- 🚀 **[CI/CD Setup](./docs/CI_CD_SETUP.md)** - Konfiguracja pipeline
- 📊 **[Deployment Phase 1](./docs/DEPLOYMENT_PHASE_1.md)** - Status i instrukcje
- 📁 **[Dekompozycje Zadań](./docs/)** - Szczegółowe plany implementacji
- 🔍 **[Analiza eofek/detektor](./docs/analysis/eofek-detektor-analysis.md)** - Inspiracje i patterns

## Kluczowe Zasady

1. **🚨 ZASADA ZERO**: NIGDY nie hardkoduj sekretów (używaj SOPS!)
2. **TDD**: Test-driven development od początku
3. **Observability First**: Tracing i metryki w każdym serwisie
4. **Clean Architecture**: Separacja warstw, DDD patterns
5. **Container First**: Wszystko w Docker
6. **CI/CD First**: Build w GitHub Actions, deploy z registry (NIGDY build na produkcji!)

## Influences i Inspiracje

Ten projekt czerpie proven patterns z:

### 🎯 [eofek/detektor](https://github.com/eofek/detektor)

*Repozytorium autorskie - kod dostępny do wykorzystania*

**Adoptowane patterns**:

- Metrics abstraction layer dla Prometheus
- Redis Streams event-driven architecture
- GPU monitoring z comprehensive checks
- Docker organization (dev/prod configs)
- Event acknowledgement dla reliability

**Ulepszenia względem eofek/detektor**:

- Uproszczona architektura (mniej over-engineering)
- Rozszerzenie AI models (YOLO, gesture detection)
- Home Assistant integration (czego brakuje w oryginale)
- Better developer experience (TDD, pre-commit hooks)

## Zarządzanie Sekretami

Projekt wykorzystuje **SOPS + age** dla bezpiecznego zarządzania sekretów:

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

- **8001**: rtsp-capture
- **8002**: face-recognition
- **8003**: object-detection
- **8004**: ha-bridge
- **8005**: example-otel ✅ (działający przykład)
- **8006**: frame-tracking
- **8007**: echo-service
- **8008**: gpu-demo
- **9090**: Prometheus ✅
- **16686**: Jaeger ✅
- **3000**: Grafana ✅

## Bounded Contexts

1. **Frame Processing** - Capture, buffering, storage
2. **AI Detection** - Face, gesture, object recognition
3. **Home Automation** - HA integration, action execution

## Status Projektu

**Aktualny stan**: Faza 1 COMPLETED ✅ - Faza 2 w trakcie

**Faza 1 - Ukończone komponenty**:
- ✅ Infrastruktura observability (Prometheus, Jaeger, Grafana)
- ✅ CI/CD pipeline (GitHub Actions + GHCR)
- ✅ Deployment automation (scripts/deploy-to-nebula.sh)
- ✅ Example service z pełnym observability (example-otel)
- ✅ Secrets management (SOPS z age)
- ✅ Health monitoring (scripts/health-check-all.sh)

**Strategia deployment (obowiązkowa)**:
1. Build: Obrazy budowane w GitHub Actions
2. Registry: Publikacja do ghcr.io/hretheum/bezrobocie-detektor/
3. Deploy: Pull z registry na Nebula (NIGDY build na produkcji!)
4. Monitor: Health checks i observability od początku

**Faza 2 - W trakcie**:
- ✅ Frame Buffer (80k fps, 0.01ms latency, DLQ)
- 🚧 RTSP Capture Service (Block 0 completed)
- ⏳ PostgreSQL/TimescaleDB
- ⏳ Frame tracking implementation

## Kontrybuowanie

Ten projekt realizuje podejście **observability-first** i **TDD**.

Przed rozpoczęciem pracy:

1. Przeczytaj [CLAUDE.md](./CLAUDE.md) - zasady projektu
2. Sprawdź aktualną fazę w [architektura_systemu.md](./architektura_systemu.md)
3. Użyj `/nakurwiaj` dla automatycznego wykonania bloków zadań

## Licencja

MIT License - projekt hobbystyczny/edukacyjny.

---

🤖 **Projekt realizowany z Claude Code** - [claude.ai/code](https://claude.ai/code)
