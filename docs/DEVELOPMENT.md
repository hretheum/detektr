# 🛠️ Development Guide

## Spis treści

1. [Prerequisites](#prerequisites)
2. [Lokalne środowisko](#lokalne-środowisko)
3. [Development Workflow](#development-workflow)
4. [Struktura projektu](#struktura-projektu)
5. [Dodawanie nowego serwisu](#dodawanie-nowego-serwisu)
6. [Testing](#testing)
7. [Code Quality](#code-quality)
8. [Debugging](#debugging)
9. [Best Practices](#best-practices)

## Prerequisites

### Wymagane narzędzia

- **Docker** 20.10+ & Docker Compose 2.0+
- **Python** 3.11+
- **Make** (GNU Make)
- **Git** 2.0+
- **SOPS** (dla sekretów)
- **age** (encryption key)

### Opcjonalne narzędzia

- **NVIDIA GPU** + CUDA drivers (dla AI features)
- **VS Code** lub PyCharm
- **k9s** (Kubernetes CLI)
- **httpie** lub **curl**

### System Requirements

- **RAM**: Minimum 8GB (16GB zalecane)
- **Storage**: 50GB wolnego miejsca
- **OS**: Linux, macOS, WSL2

## Lokalne środowisko

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/hretheum/detektr.git
cd detektr
```

### 2. Setup środowiska

```bash
# Automatyczny setup
make setup

# Co robi make setup:
# 1. Tworzy Python virtual environment
# 2. Instaluje dependencies
# 3. Konfiguruje pre-commit hooks
# 4. Inicjalizuje SOPS
# 5. Tworzy .env z przykładowych wartości
```

### 3. Konfiguracja sekretów

```bash
# Edycja sekretów (wymaga klucza age)
make secrets-edit

# Dla nowych developerów - poproś o klucz age lub użyj dev secrets
cp .env.example .env
```

### 4. Uruchomienie stacku

```bash
# Start wszystkich serwisów
make up

# Lub używając convenience scripts
./docker/dev.sh up -d

# Sprawdzenie statusu
make status

# Logi
make logs
make logs SERVICE=rtsp-capture
```

### 5. Weryfikacja

```bash
# Health checks
curl http://localhost:8001/health  # rtsp-capture
curl http://localhost:8005/health  # example-otel
curl http://localhost:8006/health  # frame-tracking

# Dashboards
open http://localhost:3000    # Grafana (admin/admin)
open http://localhost:16686   # Jaeger
open http://localhost:9090    # Prometheus
```

## Development Workflow

### 1. Branching Strategy

```bash
# Feature branch
git checkout -b feature/nazwa-funkcji

# Bugfix
git checkout -b bugfix/opis-buga

# Hotfix
git checkout -b hotfix/krytyczny-fix
```

### 2. Commit Convention

Używamy [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Features
git commit -m "feat: dodanie rozpoznawania gestów"

# Bug fixes
git commit -m "fix: naprawa memory leak w RTSP capture"

# Documentation
git commit -m "docs: aktualizacja README"

# Refactoring
git commit -m "refactor: wydzielenie frame processor"

# Tests
git commit -m "test: dodanie testów dla face recognition"
```

### 3. Development Cycle

```bash
# 1. Napisz test (TDD)
make test-watch SERVICE=rtsp-capture

# 2. Implementuj feature
# Edytuj kod w services/rtsp-capture/

# 3. Sprawdź jakość kodu
make lint
make format

# 4. Uruchom wszystkie testy
make test

# 5. Commit z pre-commit hooks
git add .
git commit -m "feat: opis zmian"

# 6. Push i PR
git push origin feature/nazwa
```

## Struktura projektu

```
detektr/
├── .github/
│   └── workflows/           # GitHub Actions CI/CD
├── docker/
│   ├── base/               # Podstawowe docker-compose
│   ├── environments/       # Env-specific configs
│   └── features/           # Opcjonalne features (GPU, HA)
├── docs/
│   ├── deployment/         # Dokumentacja deployment
│   ├── ARCHITECTURE.md     # Ten dokument
│   └── api/               # API documentation
├── scripts/
│   ├── deploy.sh          # Unified deployment script
│   └── setup/             # Setup scripts
├── services/
│   ├── rtsp-capture/      # RTSP capture service
│   ├── frame-tracking/    # Frame tracking service
│   ├── face-recognition/  # Face recognition AI
│   └── ...               # Inne serwisy
├── shared/
│   ├── python/           # Wspólne biblioteki Python
│   └── proto/            # Protobuf definitions
├── tests/
│   ├── integration/      # Testy integracyjne
│   └── e2e/             # Testy end-to-end
├── Makefile             # Główne komendy
└── pyproject.toml       # Python project config
```

### Struktura serwisu

Każdy serwis ma identyczną strukturę:

```
services/example-service/
├── Dockerfile              # Multi-stage build
├── pyproject.toml         # Dependencies
├── src/
│   ├── __init__.py
│   ├── main.py           # FastAPI app
│   ├── config.py         # Configuration
│   ├── api/              # REST endpoints
│   ├── core/             # Business logic
│   ├── infrastructure/   # External services
│   └── domain/           # Domain models
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
└── README.md
```

## Dodawanie nowego serwisu

### 1. Użyj template

```bash
# Skopiuj template
cp -r services/base-template services/my-new-service

# Zaktualizuj nazwy
cd services/my-new-service
find . -type f -exec sed -i 's/base-template/my-new-service/g' {} \;
```

### 2. Konfiguracja

```python
# src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "my-new-service"
    port: int = 8009
    redis_url: str = "redis://redis:6379"

    class Config:
        env_file = ".env"
```

### 3. Dodaj do docker-compose

```yaml
# docker/base/docker-compose.yml
services:
  my-new-service:
    build: ./services/my-new-service
    ports:
      - "8009:8009"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
```

### 4. Implementuj logikę

```python
# src/main.py
from fastapi import FastAPI
from .config import Settings
from shared.observability import setup_observability

settings = Settings()
app = FastAPI(title=settings.service_name)

setup_observability(app, settings.service_name)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}
```

## Testing

### Unit Tests

```bash
# Run unit tests dla konkretnego serwisu
make test SERVICE=rtsp-capture

# Watch mode
make test-watch SERVICE=rtsp-capture

# Coverage report
make test-coverage SERVICE=rtsp-capture
```

### Integration Tests

```bash
# Run integration tests
make test-integration

# Specific test
pytest tests/integration/test_redis_connection.py -v
```

### E2E Tests

```bash
# Run end-to-end tests
make test-e2e

# With specific environment
ENVIRONMENT=staging make test-e2e
```

### Test Structure

```python
# tests/unit/test_frame_processor.py
import pytest
from src.core.frame_processor import FrameProcessor

class TestFrameProcessor:
    @pytest.fixture
    def processor(self):
        return FrameProcessor()

    def test_process_frame_success(self, processor):
        # Given
        frame = create_test_frame()

        # When
        result = processor.process(frame)

        # Then
        assert result.status == "processed"
        assert result.metadata is not None
```

## Code Quality

### Linting & Formatting

```bash
# Format code (black + isort)
make format

# Lint check (flake8 + mypy)
make lint

# Pre-commit hooks (automatic)
pre-commit run --all-files
```

### Code Standards

1. **Black** - code formatting
2. **isort** - import sorting
3. **flake8** - style guide enforcement
4. **mypy** - static type checking
5. **bandit** - security linting

### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

## Debugging

### Local Debugging

```bash
# Attach to running container
docker exec -it detektor-rtsp-capture-1 bash

# Python debugger
docker exec -it detektor-rtsp-capture-1 python -m pdb
```

### VS Code Configuration

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Remote Attach",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}/services/rtsp-capture",
          "remoteRoot": "/app"
        }
      ]
    }
  ]
}
```

### Logging

```python
# Use structured logging
import structlog

logger = structlog.get_logger()

logger.info(
    "frame_processed",
    frame_id=frame.id,
    duration_ms=duration,
    camera_id=camera.id
)
```

### Profiling

```bash
# CPU profiling
make profile SERVICE=rtsp-capture

# Memory profiling
make profile-memory SERVICE=rtsp-capture
```

## Best Practices

### 1. Service Design

- **Single Responsibility**: Każdy serwis ma jedną, dobrze zdefiniowaną odpowiedzialność
- **Stateless**: Serwisy nie trzymają stanu w pamięci
- **Idempotent**: Operacje można bezpiecznie powtarzać
- **Resilient**: Graceful degradation, circuit breakers

### 2. API Design

```python
# Good API design
@app.post("/api/v1/frames", response_model=FrameResponse)
async def create_frame(
    frame: FrameCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new frame entry."""
    # Implementation
```

### 3. Error Handling

```python
# Proper error handling
from fastapi import HTTPException

@app.get("/frames/{frame_id}")
async def get_frame(frame_id: str):
    try:
        frame = await frame_service.get(frame_id)
        if not frame:
            raise HTTPException(
                status_code=404,
                detail=f"Frame {frame_id} not found"
            )
        return frame
    except ServiceException as e:
        logger.error("service_error", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")
```

### 4. Testing

- **TDD**: Zawsze test first
- **Mocking**: Mock external dependencies
- **Fixtures**: Reusable test data
- **Parametrize**: Test multiple scenarios

### 5. Performance

```python
# Use async where possible
async def process_frames(frames: List[Frame]):
    tasks = [process_single_frame(f) for f in frames]
    results = await asyncio.gather(*tasks)
    return results

# Connection pooling
from aioredis import create_redis_pool

redis_pool = await create_redis_pool(
    'redis://localhost',
    minsize=5,
    maxsize=10
)
```

### 6. Security

- Validate all inputs
- Use environment variables for secrets
- Never log sensitive data
- Implement rate limiting
- Use HTTPS in production

## Useful Commands

```bash
# Development
make dev              # Start development environment
make dev-logs         # Show logs
make dev-shell        # Shell into service

# Testing
make test            # Run all tests
make test-watch      # Watch mode
make test-coverage   # Coverage report

# Code Quality
make lint            # Run linters
make format          # Format code
make security        # Security scan

# Docker
make build           # Build all images
make clean           # Clean up containers/volumes

# Database
make db-migrate      # Run migrations
make db-shell        # PostgreSQL shell

# Debugging
make debug SERVICE=x # Enable debug mode
make profile         # Run profiler
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Python Packaging](https://packaging.python.org/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Redis Streams](https://redis.io/docs/data-types/streams/)

---

Następne kroki:
1. [Architecture Overview](ARCHITECTURE.md)
2. [Deployment Guide](deployment/unified-deployment.md)
3. [Troubleshooting](TROUBLESHOOTING.md)
