# Detektor - System Monitoringu Wizyjnego

[![CI/CD Pipeline](https://github.com/hretheum/detektr/actions/workflows/main-pipeline.yml/badge.svg)](https://github.com/hretheum/detektr/actions/workflows/main-pipeline.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Registry](https://img.shields.io/badge/registry-ghcr.io%2Fhretheum%2Fdetektr-blue)](https://github.com/hretheum/detektr/packages)

System przechwytywania obrazu z kamer IP z wykorzystaniem AI do rozpoznawania obiektów i automatyzacji Home Assistant.

## 🚀 Quick Start

1. **[Architektura Systemu](docs/ARCHITECTURE.md)** - Zrozum strukturę projektu
2. **[Development Setup](docs/DEVELOPMENT.md)** - Zacznij lokalnie
3. **[Deployment Guide](docs/deployment/unified-deployment.md)** - Deploy na produkcję

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

## 🎯 Co to jest Detektor?

Detektor to hobbystyczny system monitoringu wizyjnego który:
- 📹 Przechwytuje strumień RTSP z kamer IP (np. Reolink)
- 🤖 Rozpoznaje twarze, gesty i obiekty używając AI (YOLO v8, MediaPipe)
- 🏠 Integruje się z Home Assistant dla automatyzacji
- 🎤 Obsługuje interakcję głosową z LLM (OpenAI/Anthropic)
- 📊 Zapewnia pełną observability (Prometheus, Grafana, Jaeger)

## 🏗️ Architektura

System wykorzystuje:
- **Infrastruktura**: Docker, Kubernetes-ready, GPU support (NVIDIA)
- **Backend**: Python 3.11+, FastAPI, Clean Architecture
- **AI/ML**: YOLO v8, MediaPipe, InsightFace, Whisper
- **Message Bus**: Redis Streams
- **Storage**: PostgreSQL/TimescaleDB
- **Monitoring**: Prometheus, Grafana, Jaeger, OpenTelemetry
- **CI/CD**: GitHub Actions + GitHub Container Registry

Szczegóły: [Architecture Documentation](docs/ARCHITECTURE.md)

## 📊 Dashboard Links

| Dashboard | URL | Opis |
|-----------|-----|------|
| Grafana | http://nebula:3000 | Główny dashboard z metrykami |
| Prometheus | http://nebula:9090 | Metrics explorer |
| Jaeger | http://nebula:16686 | Distributed tracing |

## 🏃 Status projektu (2025-07-25)

- ✅ **Faza 0**: Dokumentacja i planowanie
- ✅ **Faza 1**: Fundament z observability (CI/CD, monitoring)
- 🚧 **Faza 2**: Akwizycja i storage (5/8 zadań ukończonych)
  - ✅ RTSP Capture, Frame Buffer, Redis, PostgreSQL, Base Processor Framework
  - 📋 TODO: Frame tracking, Dashboard, Alerty
- 🔜 **Faza 3**: AI services podstawy
- 🔜 **Faza 4**: Integracja z Home Assistant

**Działające serwisy**: 11 usług w produkcji na Nebula, wszystkie healthy

## 🛠️ Development

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- NVIDIA GPU (opcjonalnie, dla AI features)
- Make

### Local Setup

```bash
# Setup environment
make setup

# Start development stack
make up

# Run tests
make test

# Check code quality
make lint

# View logs
make logs SERVICE=rtsp-capture
```

Więcej: [Development Guide](docs/DEVELOPMENT.md)

## 🚀 Deployment

### Używając unified deployment script

```bash
# Deploy to production
./scripts/deploy.sh production deploy

# Check status
./scripts/deploy.sh production status

# View logs
./scripts/deploy.sh production logs
```

### Automatyczny deployment

```bash
# Push to main = auto deploy via CI/CD
git push origin main
```

Więcej: [Deployment Documentation](docs/deployment/unified-deployment.md)

## 📦 Serwisy

| Serwis | Port | Status | Opis |
|--------|------|--------|------|
| rtsp-capture | 8001 | ✅ Production | Przechwytywanie RTSP |
| frame-tracking | 8006 | ✅ Production | Tracking ramek |
| example-otel | 8005 | ✅ Production | Przykład z OpenTelemetry |
| face-recognition | 8002 | 🚧 Development | Rozpoznawanie twarzy |
| object-detection | 8003 | 🚧 Development | Detekcja obiektów |
| ha-bridge | 8004 | 📅 Planned | Integracja z Home Assistant |

## 🔐 Zarządzanie sekretami

Projekt używa SOPS z age encryption:

```bash
# Edit secrets
make secrets-edit

# Decrypt for local use
make secrets-decrypt

# Check status
make secrets-status
```

## 📈 Status Projektu

### ✅ Ukończone fazy

1. **Dokumentacja i planowanie** - Kompletna architektura
2. **Fundament z observability** - CI/CD, monitoring, tracing
3. **Unified deployment** - Jeden skrypt dla wszystkich środowisk
4. **Docker reorganization** - Hierarchiczna struktura
5. **GHCR cleanup** - Uporządkowane obrazy

### 🚧 W trakcie

- **Akwizycja i storage** - RTSP capture, frame buffering
- **AI services** - Face recognition, object detection

### 📅 Zaplanowane

- **Home Assistant integration**
- **Voice interaction with LLM**
- **Advanced AI features**

## 🤝 Contributing

1. Przeczytaj [Architecture](docs/ARCHITECTURE.md)
2. Setup lokalnie według [Development Guide](docs/DEVELOPMENT.md)
3. Używaj TDD - test first, code second
4. Zapewnij observability w każdym serwisie
5. Dokumentuj zmiany

## 📚 Dokumentacja

- [Architecture](docs/ARCHITECTURE.md) - Jak działa system
- [Development](docs/DEVELOPMENT.md) - Jak rozwijać projekt
- [Deployment](docs/deployment/unified-deployment.md) - Jak deployować
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Rozwiązywanie problemów
- [API Reference](docs/api/) - Dokumentacja API

## 📝 License

MIT License - projekt hobbystyczny/edukacyjny

---

🤖 **Developed with [Claude Code](https://claude.ai/code)**
