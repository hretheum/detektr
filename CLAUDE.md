# Projekt Detektor - Zasady i Wzorce

<!--
LLM PROJECT CONTEXT:
Ten plik jest "pamięcią projektu" - zawiera kluczowe decyzje i wzorce.
Używaj go gdy:
1. Implementujesz nowy serwis/komponent
2. Nie wiesz jak coś zrobić "the project way"
3. Potrzebujesz quick reference dla komend/standardów

WORKFLOW STARTOWY:
1. Przeczytaj ten plik w całości
2. Sprawdź aktualną fazę w architektura_systemu.md
3. Znajdź zadanie do wykonania ([ ] checkbox)
4. Otwórz jego dekompozycję (link "Szczegóły →")
5. Użyj /nakurwiaj <blok> do automatycznego wykonania
-->

## 🐍 Python Environment Management

**UŻYWAMY VENV** - Standardowe środowiska wirtualne Python

```bash
# Tworzenie środowiska
python3 -m venv venv

# Aktywacja
source venv/bin/activate  # Mac/Linux
# lub
. venv/bin/activate

# Instalacja zależności
pip install -r requirements.txt
pip install -r requirements-dev.txt  # dla developerów

# Deaktywacja
deactivate
```

**DLACZEGO VENV?**

- Wbudowane w Python (nie wymaga dodatkowych narzędzi)
- Proste i przewidywalne
- Dobrze wspierane przez IDE
- Łatwe do odtworzenia w Docker/CI
- Kompatybilne ze wszystkimi systemami

**KONWENCJE:**

- Nazwa środowiska: `venv` (nie `.venv` - chcemy widzieć folder)
- Dodaj `venv/` do `.gitignore`
- Używaj `requirements.txt` dla głównych zależności
- Używaj `requirements-dev.txt` dla narzędzi developerskich
- Pin wersje dokładnie (np. `black==23.12.1`)

## Główne Zasady Projektu

### 🚨 ZASADA ZERO - NAJWYŻSZY PRIORYTET 🚨

**NO HARDCODED SECRETS - ABSOLUTNY ZAKAZ**

- NIGDY nie hardkoduj kluczy API, haseł, tokenów, connection strings
- NIGDY nie używaj sekretów jako fallback/default values
- WSZYSTKIE sekrety TYLKO w plikach .env (zaszyfrowanych przez SOPS)
- Przykład DOBRY: `api_key = os.getenv('OPENAI_API_KEY')`
- Przykład ZŁY: `api_key = os.getenv('OPENAI_API_KEY', 'sk-12345...')` ❌

**🔐 UŻYWAMY SOPS - Workflow dla nowych sekretów:**

1. **Edytuj zaszyfrowany .env**: `make secrets-edit` lub `sops .env`
2. **Dodaj nowy sekret** w edytorze
3. **Zapisz i zamknij** - SOPS automatycznie zaszyfruje
4. **Commituj zaszyfrowany .env** - to jest bezpieczne!
5. **Używaj w kodzie**: `os.getenv('NOWY_SEKRET')`

### Pozostałe zasady (w kolejności ważności)

1. **Test-Driven Development (TDD)** - ZAWSZE pisz test przed implementacją
2. **Observability First** - Każdy serwis ma wbudowany tracing i metryki od początku
3. **Clean Architecture** - Separacja warstw: domain, infrastructure, application
4. **Domain-Driven Design** - Bounded contexts, aggregates, domain events
5. **SOLID Principles** - Każda klasa/moduł zgodny z SOLID
6. **Container First** - Wszystko w kontenerach Docker
7. **CI/CD First** - Obrazy budowane w GitHub Actions, deploy z registry

## Wzorce do Stosowania

<!--
LLM IMPLEMENTATION GUIDE:
Poniższe wzorce są OBOWIĄZKOWE dla każdego nowego komponentu.
Copy-paste i dostosuj do swojego serwisu.
-->

### Architektura Serwisu

```
service-name/
├── domain/           # Pure business logic
├── infrastructure/   # External dependencies
├── application/      # Use case orchestration
└── tests/           # TDD tests
```

### Bazowa Klasa Serwisu

Każdy serwis dziedziczy po `BaseService` z automatycznym observability.

### Testowanie

- Unit: 80% coverage, <100ms/test
- Integration: Granice serwisów
- E2E: Scenariusze biznesowe
- Performance: Baseline metrics

### Tracking Klatek

Format ID: `{timestamp}_{camera_id}_{sequence_number}`
Każda klatka ma pełną historię (Event Sourcing).

### Wzorce Projektowe

- Repository Pattern dla dostępu do danych
- Circuit Breaker dla external services
- Event Sourcing dla frame tracking
- Dependency Injection

### Standards

- Type hints everywhere
- Docstrings w formacie Google
- Pre-commit hooks (black, flake8, mypy)
- CI/CD z GitHub Actions

## Komendy do Pamiętania

<!--
LLM QUICK REFERENCE:
Te komendy używaj podczas development i debugging.
Każdy serwis ma te same porty względne:
- 8001: rtsp-capture
- 8002: face-recognition
- 8003: object-detection
- 8004: ha-bridge
- 8005: llm-intent
-->

```bash
# Uruchom testy
docker-compose -f docker-compose.test.yml up

# Sprawdź metryki
curl http://localhost:9090/metrics

# Zobacz trace
open http://localhost:16686

# Logi
docker-compose logs -f service-name

# Health check serwisu
curl http://localhost:800X/health

# Benchmark serwisu
python -m service_name.benchmark --duration 60

# Sprawdź GPU
docker exec -it service-name nvidia-smi
```

## Bounded Contexts

1. **Frame Processing** - Capture, buffering, storage
2. **AI Detection** - Face, gesture, object recognition
3. **Home Automation** - HA integration, action execution

## Ważne Decyzje

- GPU tylko dla AI services
- LLM w chmurze (OpenAI/Anthropic)
- Lokalne modele: YOLO, MediaPipe, Whisper
- Message bus: Redis Streams (pattern z eofek/detektor)
- Observability: Jaeger + Prometheus + Grafana

## 📋 Continuous Quality Standards (NOWE REGUŁY - od Fazy 2)

<!--
LLM QUALITY GATES:
Te standardy są OBOWIĄZKOWE od Fazy 2 i mają zapobiec długowi technicznemu.
Każdy nowy kod MUSI spełniać te kryteria PRZED commitem.
-->

### 🔴 MANDATORY dla każdego nowego kodu:

1. **API Documentation (OpenAPI/Swagger)**
   - KAŻDY endpoint HTTP MUSI mieć pełną dokumentację OpenAPI
   - Generowana automatycznie z kodu (FastAPI automatic docs)
   - Przykład:
   ```python
   @app.post("/frames/process", response_model=ProcessingResult, tags=["frames"])
   async def process_frame(
       frame: Frame,
       background_tasks: BackgroundTasks,
       service: FrameService = Depends(get_frame_service)
   ) -> ProcessingResult:
       """
       Process a single frame through the detection pipeline.

       - **frame**: Frame data with image and metadata
       - **returns**: Processing results including detections
       """
       return await service.process_frame(frame)
   ```

2. **Architectural Decision Records (ADRs)**
   - KAŻDA znacząca decyzja architektoniczna MUSI mieć ADR
   - Template: `docs/templates/adr/adr-template.md`
   - Lokalizacja: `docs/adr/YYYY-MM-DD-title.md`
   - Przykład: "Dlaczego Redis Streams zamiast Kafka"

3. **Performance Baselines**
   - KAŻDA nowa operacja MUSI mieć baseline metrics
   - Automated regression tests w CI
   - Alert gdy performance degraduje >20%

4. **Method Complexity Limits**
   - MAX 30 linii na metodę (target: 20)
   - MAX cyclomatic complexity: 10
   - Extract method gdy przekroczone

5. **Test-First Development**
   - Test MUSI istnieć PRZED implementacją
   - Minimum 3 test cases: happy path, edge case, error case
   - Integration test dla każdego nowego service

6. **Correlation IDs**
   - KAŻDY request/operation MUSI mieć correlation ID
   - Propagowany przez wszystkie service calls
   - Logowany w structured logs

7. **Feature Flags**
   - Nowe features za feature flags (gdy >1 dzień pracy)
   - Gradual rollout capability
   - Quick rollback mechanism

### 🟡 BEST PRACTICES (silnie rekomendowane):

8. **Domain Events**
   - Każda zmiana stanu = domain event
   - Event sourcing dla audit trail
   - Async event handlers

9. **Dependency Injection**
   - No hardcoded dependencies
   - Constructor injection preferred
   - Testable by design

10. **Monitoring First**
    - Metrics PRZED implementacją
    - Custom dashboard dla każdego nowego service
    - Alerts dla SLA violations

## Patterns z eofek/detektor do Adoptowania

**Reference**: `docs/analysis/eofek-detektor-analysis.md`
**Source Repository**: <https://github.com/eofek/detektor> (autorskie - kod dostępny do wykorzystania)

### ✅ CO ADOPTUJEMY

- **Metrics abstraction layer** - ich pattern dla Prometheus
- **Redis Streams** zamiast Kafka - prostsze, proven solution
- **GPU monitoring patterns** - comprehensive GPU checks
- **Docker organization** - env-specific configs
- **Event acknowledgement** - dla reliability

### 🚫 CZEGO UNIKAMY

- **Over-engineering** - za dużo mikroservisów
- **External dependencies lock-in** - tight coupling z Telegram/Cloudflare
- **Complex event flows** - trudne do debug

### 🔧 KONKRETNE IMPLEMENTACJE

```python
# Metrics adapter pattern (z eofek/detektor)
class DetectionMetrics:
    def increment_detections(self):
        detection_metrics.increment_detections()

    def observe_detection_time(self, time):
        detection_metrics.observe_detection_time(time)

# Event publishing (Redis Streams)
async def publish_event(self, event_type, data):
    event = {
        'timestamp': datetime.now().isoformat(),
        'type': event_type,
        'service': self.service_name,
        'data': data
    }
    await self.redis.xadd(stream_name, event)
```

## Zarządzanie Sekretami - PRZYKŁADY

### ✅ DOBRZE - Używanie zmiennych środowiskowych

```python
import os
from pathlib import Path

# Ładowanie z .env w development
if Path('.env').exists():
    from dotenv import load_dotenv
    load_dotenv()

# Pobieranie sekretów
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY not set in environment")

db_url = os.getenv('DATABASE_URL')
if not db_url:
    raise ValueError("DATABASE_URL not set in environment")
```

### ❌ ŹLE - Hardkodowane wartości

```python
# NIGDY TAK NIE RÓB!
api_key = "sk-1234567890abcdef"  # ❌
api_key = os.getenv('OPENAI_API_KEY', 'sk-default')  # ❌
db_url = "postgresql://user:pass@localhost/db"  # ❌
```

### Docker Compose z sekretami

```yaml
services:
  app:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
    env_file:
      - .env.decrypted  # Makefile automatycznie odszyfruje
```

### 🔐 SOPS - Szybkie komendy

```bash
# Pierwsza konfiguracja (tylko raz)
make secrets-init

# Edycja sekretów (otwiera edytor)
make secrets-edit
# lub
sops .env

# Uruchomienie z automatycznym odszyfrowaniem
make up  # Odszyfruje .env → uruchomi docker-compose → usunie .env.decrypted

# Ręczne odszyfrowanie (do debugowania)
make secrets-decrypt  # Tworzy .env.decrypted
# PAMIĘTAJ USUNĄĆ: rm .env.decrypted

# Dodanie nowego członka zespołu
# 1. Poproś o klucz publiczny (age1...)
# 2. Dodaj do .sops.yaml
# 3. sops updatekeys .env
```

### ⚠️ WAŻNE przy SOPS

- ✅ Commituj zaszyfrowany `.env` (wygląda jak JSON z encrypted values)
- ❌ NIGDY nie commituj `.env.decrypted` ani `keys.txt`
- ✅ Każdy developer ma własny klucz age
- ✅ Dokumentacja: `/docs/SECRETS_MANAGEMENT.md`

## 🚀 CI/CD i Deployment Strategy - OBOWIĄZKOWY STANDARD

<!--
LLM MANDATORY GUIDELINES:
Ta sekcja definiuje JEDYNĄ dozwoloną strategię deployment dla CAŁEGO PROJEKTU.
Każdy task, każda faza, każdy serwis MUSI używać tego podejścia.
NIE MA WYJĄTKÓW!
-->

### 🔄 Workflow CI/CD

**ZASADA**: Build w CI/CD, Deploy z Registry - NIGDY build na produkcji

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   git push  │───▶│ GitHub Actions   │───▶│ ghcr.io registry│
│   (main)    │    │ (.github/       │    │ (ready images)  │
└─────────────┘    │  workflows/     │    └─────────────────┘
                   │  deploy.yml)    │             │
                   └──────────────────┘             │
                                                    ▼
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│Nebula Server│◀───│ Deployment Script│◀───│ docker pull     │
│(production) │    │ (deploy-to-      │    │ (from registry) │
└─────────────┘    │  nebula.sh)     │    └─────────────────┘
```

### 📋 Deployment Commands - dla LLM

```bash
# 1. PEŁNY DEPLOYMENT FLOW (recommended)
git add . && git commit -m "feat: nowy serwis xyz" && git push origin main
# → Automatycznie: build → publish → deploy na Nebula

# 2. MANUAL DEPLOYMENT (z istniejących obrazów)
./scripts/deploy-to-nebula.sh

# 3. HEALTH CHECK
ssh nebula "/opt/detektor/scripts/health-check-all.sh"

# 4. LOGS i DEBUG
ssh nebula "cd /opt/detektor && docker-compose logs [service-name]"
ssh nebula "docker ps | grep detektor"

# 5. ROLLBACK (jeśli potrzebny)
ssh nebula "cd /opt/detektor && docker-compose down [service-name]"
ssh nebula "docker pull ghcr.io/hretheum/bezrobocie-detektor/[service]:previous-tag"
ssh nebula "cd /opt/detektor && docker-compose up -d [service-name]"
```

### 🎯 Image Naming Convention

```
ghcr.io/hretheum/bezrobocie-detektor/[SERVICE_NAME]:[TAG]

Przykłady:
- ghcr.io/hretheum/bezrobocie-detektor/example-otel:latest
- ghcr.io/hretheum/bezrobocie-detektor/frame-tracking:main-abc123def
- ghcr.io/hretheum/bezrobocie-detektor/gpu-demo:v1.2.3
```

### ⚠️ CO NIGDY NIE ROBIĆ

```bash
# ❌ ABSOLUTNIE ZAKAZANE:
ssh nebula "docker build ..."                    # Build na produkcji
ssh nebula "git clone ..."                       # Kod źródłowy na prod
docker build -f services/xyz/Dockerfile ...      # Local build
scp services/ nebula:/opt/detektor/              # Manual copy

# ❌ ZŁOWE PRACTICES:
docker-compose up --build                        # Build w compose
COPY . /app                                       # Całe repo w image
FROM ubuntu && apt install ...                   # Heavy base images
```

### ✅ CO ROBIĆ

```bash
# ✅ DOBRE PRACTICES:
git push origin main                              # Trigger CI/CD
./scripts/deploy-to-nebula.sh                    # Automated deploy
docker pull ghcr.io/...                         # Images z registry
FROM python:3.11-slim                           # Oficjalne base images
COPY requirements.txt /app/                      # Selective copy
```

### 🔧 Automated Deployment Process

1. **GitHub Actions** (`.github/workflows/deploy.yml`):
   - Build wszystkich service images
   - Run tests w containerach
   - Push do registry z proper tags
   - Optional: auto-deploy na Nebula

2. **Deployment Script** (`scripts/deploy-to-nebula.sh`):
   - Pull latest images z registry
   - Decrypt secrets z SOPS
   - Update docker-compose files
   - Rolling restart services
   - Health checks
   - Cleanup

3. **Service Discovery**:
   - Każdy serwis ma unikalny port 800X
   - Docker networks dla internal communication
   - Traefik/nginx dla external access (future)

### 📊 Monitoring & Observability

```bash
# Service-specific metrics:
curl http://nebula:800X/metrics        # Prometheus metrics
curl http://nebula:800X/health         # Health endpoint

# Stack monitoring:
http://nebula:9090                     # Prometheus UI
http://nebula:16686                    # Jaeger traces
http://nebula:3000                     # Grafana dashboards
```

### 🏗️ Service Development Workflow

1. **Nowy serwis**:
   ```bash
   cp -r services/base-template services/new-service
   # Edit Dockerfile, kod, testy
   git add . && git commit && git push
   # → Automatyczny build i deploy
   ```

2. **Update istniejącego**:
   ```bash
   # Edit kod w services/existing-service/
   git add . && git commit && git push
   # → Automatyczny rebuild i redeploy
   ```

3. **Testing**:
   ```bash
   # Local development:
   python -m pytest services/my-service/tests/

   # Integration test on Nebula:
   ssh nebula "/opt/detektor/scripts/health-check-all.sh"
   ```

### 💡 Pro Tips dla LLM

- **Zawsze** sprawdź czy image istnieje w registry przed deployem
- **Nigdy** nie edytuj plików bezpośrednio na Nebuli
- **Zawsze** używaj deployment script dla consistency
- **Monitor** logi po każdym deploy
- **Test** health endpoints po każdej zmianie

Ten workflow zapewnia:
- ✅ Reproducible deployments
- ✅ Version control wszystkiego
- ✅ Fast rollbacks
- ✅ Proper secrets management
- ✅ Full observability
