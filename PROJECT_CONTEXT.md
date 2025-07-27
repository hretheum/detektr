# Kontekst Projektu Detektor - dla LLM

<!--
META LLM PROMPT:
Ten plik służy do szybkiego wprowadzenia LLM w kontekst projektu.
Wczytaj go na początku każdej nowej sesji/konwersacji.
-->

## O projekcie

**Nazwa**: System Detekcji i Automatyzacji Wizyjnej (Detektor)
**Repo**: github.com/hretheum/detektr
**Registry**: ghcr.io/hretheum/detektr/
**Typ**: Projekt hobbystyczny
**Cel**: Przechwytywanie obrazu z kamery IP + AI rozpoznawanie + automatyzacja Home Assistant

## Stack technologiczny

- **Serwer**: Ubuntu z GTX 4070 Super (16GB VRAM), i7, 64GB RAM (hostname: nebula)
- **Infrastruktura**: Docker, Docker Compose, container-first
- **CI/CD**: GitHub Actions + GitHub Container Registry (ghcr.io)
- **Języki**: Python 3.11+, FastAPI
- **AI/ML**: YOLO, MediaPipe, Whisper, OpenAI/Anthropic API
- **Observability**: Jaeger, Prometheus, Grafana (od początku!)
- **Architektura**: Clean Architecture, DDD, Event Sourcing, TDD
- **Message Bus**: Redis Streams (adoptowane z eofek/detektor)
- **Secrets**: SOPS z age encryption

## Influences - eofek/detektor Analysis

**Reference**: `docs/analysis/eofek-detektor-analysis.md`
**Source Repository**: <https://github.com/eofek/detektor> (własność autora - kod dostępny do wykorzystania)

**ADOPTUJEMY**:

- Metrics abstraction layer pattern
- Redis Streams event-driven architecture
- GPU monitoring patterns
- Docker organization (dev/prod configs)

**UNIKAMY**:

- Over-engineering (za dużo mikroservisów)
- Complex event flows
- External dependencies lock-in

## Struktura dokumentacji

```
/architektura_systemu.md     # Główny dokument, fazy projektu
/CLAUDE.md                   # Zasady i wzorce projektu
/docs/TASK_TEMPLATE.md       # Szablon dekompozycji zadań
/docs/faza-X-nazwa/*.md      # Dekompozycje zadań per faza
/PROJECT_CONTEXT.md          # Ten plik
```

## Workflow wykonywania zadań

### Development Flow
1. **Start**: Sprawdź aktualną fazę w `architektura_systemu.md`
2. **Wybierz zadanie**: Znajdź [ ] checkbox (nieukończone)
3. **Otwórz dekompozycję**: Kliknij link "Szczegóły →"
4. **Wykonaj**: Użyj `/nakurwiaj <numer_bloku>`
5. **Waliduj**: Po każdym bloku - testy, metryki, git commit

### CI/CD Flow (OBOWIĄZKOWY od Fazy 1)
1. **Build**: Obrazy Docker budowane w GitHub Actions
2. **Registry**: Publikacja do ghcr.io/hretheum/detektr/
3. **Deploy**: Pull z registry na serwer Nebula (NIGDY build na produkcji!)
4. **Verify**: Health checks wszystkich serwisów

```bash
# Pełny deployment
git push origin main  # → Automatyczny build i deploy

# Manual deployment
./scripts/deploy-to-nebula.sh
```

## Kluczowe zasady

- **TDD zawsze** - test first, code second
- **Observability first** - tracing/metrics od początku
- **Container first** - wszystko w Dockerze
- **CI/CD first** - build w GitHub Actions, deploy z registry
- **Clean Architecture** - separacja warstw
- **Zadania atomowe** - max 3h na zadanie
- **No hardcoded secrets** - wszystko przez SOPS

## Bounded Contexts

1. **Frame Processing** - Capture, buffering, storage
2. **AI Detection** - Face, gesture, object recognition
3. **Home Automation** - HA integration, action execution

## Fazy projektu

- **Faza 0**: Dokumentacja i planowanie ✅
- **Faza 1**: Fundament z observability ✅ (CI/CD + przykładowe serwisy)
- **Faza 2**: Akwizycja i storage 🚧 (5/8 zadań ukończonych)
- **Faza 3**: AI services podstawy
- **Faza 4**: Integracja z Home Assistant
- **Faza 5**: Zaawansowane AI i voice
- **Faza 6**: Optymalizacja i refinement

## Porty serwisów

- 8000: base-template ✅
- 8001: frame-tracking ✅
- 8002: frame-buffer ✅
- 8003: object-detection
- 8004: ha-bridge
- 8005: metadata-storage ✅
- 8006: face-recognition
- 8007: echo-service
- 8008: gpu-demo
- 8009: example-otel
- 8080: rtsp-capture ✅
- 8099: sample-processor ✅
- 6379: Redis ✅
- 5432: PostgreSQL ✅
- 6432: PGBouncer ✅
- 9090: Prometheus ✅
- 16686: Jaeger ✅
- 3000: Grafana ✅

## Gdzie szukać czego

### Główna dokumentacja (NEW!)
- **Architektura**: `/docs/ARCHITECTURE.md` - jak działa system
- **Development**: `/docs/DEVELOPMENT.md` - jak rozwijać projekt
- **Troubleshooting**: `/docs/TROUBLESHOOTING.md` - rozwiązywanie problemów
- **Makefile Guide**: `/docs/MAKEFILE_GUIDE.md` - wszystkie komendy

### Deployment & Operations
- **Unified Deployment**: `/docs/deployment/unified-deployment.md` ⭐
- **Deployment Script**: `/scripts/deploy.sh` - jeden skrypt dla wszystkich środowisk
- **Runbooks**: `/docs/runbooks/` - procedury dla typowych operacji

### Konfiguracja
- **Environment configs**: `/docker/environments/` - konfiguracje per środowisko
- **CI/CD workflows**: `/.github/workflows/` - 5 zoptymalizowanych workflows
- **Secrets**: `.env.sops` - zaszyfrowane SOPS

### Legacy (do wygaszenia)
- **Stare deployment docs**: `/docs/deployment/README.md`
- **Jak coś zrobić**: `/CLAUDE.md`
- **Co zrobić**: `/architektura_systemu.md`

## Komendy projektu

### Quick Start (NEW!)
- `make setup` - inicjalizacja projektu dla nowego developera
- `make up` - start development environment
- `make deploy` - deploy to production
- `make help` - pokazuje wszystkie dostępne komendy

### Development
- `make dev-up` - start z hot reload
- `make dev-logs SERVICE=name` - logi konkretnego serwisu
- `make dev-shell SVC=name` - shell do kontenera
- `make test` - uruchom wszystkie testy
- `make lint` - sprawdź jakość kodu
- `make format` - formatuj kod

### Production
- `make prod-deploy` - deploy na produkcję
- `make prod-status` - sprawdź status
- `make prod-verify` - weryfikuj health checks
- `make prod-logs` - pokaż logi produkcyjne

### Deployment (NEW!)
- `./scripts/deploy.sh production deploy` - unified deployment
- `./scripts/deploy.sh production status` - check status
- `./scripts/deploy.sh production verify` - health checks
- `./scripts/deploy.sh production rollback` - rollback

### Utilities
- `make secrets-edit` - edycja sekretów SOPS
- `make db-shell` - PostgreSQL CLI
- `make redis-cli` - Redis CLI
- `make clean-all` - wyczyść wszystko

## Na co uważać

1. Blok 0 (Prerequisites) - ZAWSZE wykonaj pierwszy
2. Metryki sukcesu - każde zadanie ma kryteria
3. Rollback plan - każde zadanie można cofnąć
4. API keys - NIGDY nie commituj do repo (używaj SOPS!)
5. GPU memory - monitor użycie VRAM
6. CI/CD - NIGDY nie buduj obrazów na produkcji
7. Registry - wszystkie obrazy z ghcr.io/hretheum/detektr/

## Status Fazy 1 (COMPLETED ✅)

### Zrealizowane komponenty:
- ✅ Infrastruktura observability (Prometheus, Jaeger, Grafana)
- ✅ CI/CD pipeline (GitHub Actions + GHCR)
- ✅ Deployment automation (scripts/deploy-to-nebula.sh)
- ✅ Example service z pełnym observability (example-otel)

## Status transformacji projektu (2025-07-24)

### ✅ Faza 1: Unifikacja nazewnictwa (COMPLETED)
- Zmiana nazwy projektu: bezrobocie-detektor → detektr
- Aktualizacja 42 plików (workflows, docker-compose, dokumentacja)
- Nowy registry path: ghcr.io/hretheum/detektr/
- Backup branch: naming-unification-backup-20250723-220210

### ✅ Faza 2: Konsolidacja workflows (COMPLETED)
- Redukcja z 14 do 5 workflows (-64%)
- Nowe workflows:
  - main-pipeline.yml (główny CI/CD)
  - pr-checks.yml (walidacja PR + testy)
  - manual-operations.yml (operacje manualne)
  - scheduled-tasks.yml (zadania cykliczne)
  - release.yml (bez zmian)
- Skrypt migracji: scripts/migrate-workflows.sh
- Dokumentacja: docs/WORKFLOW_CONSOLIDATION_PLAN.md

### ✅ Faza 3: Reorganizacja Docker Compose (COMPLETED)
- Reorganizacja 16+ plików → 8 plików w hierarchicznej strukturze
- Nowa struktura: docker/base, docker/environments, docker/features
- Convenience scripts: docker/dev.sh, docker/prod.sh, docker/test.sh
- Skrypt migracji: scripts/migrate-docker-compose.sh
- Pełna dokumentacja: docker/README.md

### ✅ Faza 4: GHCR Cleanup (COMPLETED)
- Migracja 5 brakujących obrazów do ghcr.io/hretheum/detektr/*
- Usunięcie przestarzałych obrazów consensus/*
- Automatyczny cleanup workflow (co niedzielę 4:00 UTC)
- Retention policy: 30 dni / 5 ostatnich wersji
- Workflow: .github/workflows/ghcr-cleanup.yml
- Raport: docs/PHASE4_GHCR_CLEANUP_REPORT.md

### ✅ Faza 5: Deployment Automation (COMPLETED)
- Unified deployment script: scripts/deploy.sh
- Wsparcie dla 3 środowisk: production, staging, local
- 7 akcji: deploy, status, logs, restart, stop, verify, cleanup
- Environment-specific configs w docker/environments/
- Integracja z GitHub Actions (main-pipeline.yml)
- Dokumentacja: docs/deployment/unified-deployment.md

### ✅ Faza 6: Documentation (COMPLETED)
- Nowy README.md z 3 kluczowymi linkami
- docs/ARCHITECTURE.md - pełna architektura systemu
- docs/DEVELOPMENT.md - przewodnik developera
- docs/TROUBLESHOOTING.md - rozwiązywanie problemów
- Runbooks w docs/runbooks/ dla typowych operacji
- docs/MAKEFILE_GUIDE.md - dokumentacja Makefile

### ✅ Faza 7: Makefile Unification (COMPLETED)
- Unified Makefile z 50+ komendami
- Kategorie: Quick Start, Development, Production, Testing, etc.
- Inteligentna selekcja środowisk (ENV variable)
- User-friendly help z opisami
- Aliasy dla popularnych komend (make up, make deploy)
- Pełna integracja z CI/CD

### Dokumentacja zaktualizowana:
- ✅ CLAUDE.md - zawiera pełne CI/CD guidelines
- ✅ docs/CI_CD_SETUP.md - instrukcje konfiguracji
- ✅ docs/faza-1-fundament/99-deployment-remediation.md - strategia deployment

### Ready for Faza 2:
- Solidny fundament CI/CD
- Działające przykłady do kopiowania
- Pełna observability od początku
- Zautomatyzowany deployment

## Krytyczne problemy i rozwiązania

### Docker Compose - problem z wczytywaniem zmiennych środowiskowych (2025-07-25)

**Problem**: Usługi (frame-tracking, base-template, metadata-storage) nie mogły połączyć się z PostgreSQL z błędem "password authentication failed for user 'detektor'".

**Przyczyna**: Docker Compose nie wczytuje automatycznie pliku `.env` gdy używane są pełne ścieżki do plików compose (np. `-f /opt/detektor/docker/base/docker-compose.yml`). W rezultacie zmienna `POSTGRES_PASSWORD` była pusta.

**Rozwiązanie**: Dodanie `--env-file .env` do WSZYSTKICH wywołań `docker compose` w skrypcie `deploy.sh`:

```bash
# Niepoprawnie (nie działa z pełnymi ścieżkami):
docker compose "${COMPOSE_FILES[@]}" up -d

# Poprawnie (wymusza wczytanie .env):
docker compose --env-file .env "${COMPOSE_FILES[@]}" up -d
```

**Zakres zmian**:
- scripts/deploy.sh - 8 miejsc gdzie dodano `--env-file .env`
- .github/workflows/main-pipeline.yml - usunięto domyślne eksporty haseł, dodano kopiowanie istniejącego .env

**Lekcja**: Zawsze używaj `--env-file .env` w skryptach deployment gdy używasz pełnych ścieżek do plików docker-compose.

### 6. Frame Tracking - Dwa komponenty (2025-07-26)

**Problem**: Początkowo niejasne czy frame-tracking to serwis czy biblioteka.

**Rozwiązanie**: Frame tracking składa się z DWÓCH komponentów:
1. **Frame-tracking SERVICE** (port 8081) - Event Sourcing dla audytu cyklu życia klatek
2. **Frame-tracking LIBRARY** (services/shared/frame-tracking) - Distributed tracing z OpenTelemetry

**Implementacja biblioteki**:
- Zintegrowana w 4 serwisach: frame-buffer, base-processor, metadata-storage, sample-processor
- Automatyczna propagacja trace context przez Redis Streams i HTTP headers
- Graceful fallback gdy biblioteka niedostępna
- Pełna widoczność w Jaeger UI

**Lekcja**: Rozróżniaj między serwisami infrastrukturalnymi (event sourcing) a bibliotekami współdzielonymi (tracing).

## Status Fazy 2: Akwizycja i Storage (2025-07-26)

### ✅ Ukończone zadania (6/8):
1. **RTSP Capture Service** - Działający na Nebula:8080, konfiguracja Reolink, status "degraded" (czeka na Redis)
2. **Frame Buffer z Redis** - Throughput 80k frames/s, latency 0.01ms, DLQ skonfigurowane
3. **Redis Configuration** - 4GB limit, persistence, monitoring, Telegram alerts
4. **PostgreSQL/TimescaleDB** - 100GB volume, PGBouncer, hypertables ready
5. **Frame Processor Base Service** - Framework w services/shared/base-processor/, sample-processor na Nebula:8099
6. **Frame tracking z distributed tracing** - Biblioteka w services/shared/frame-tracking, zintegrowana w 4 serwisach, trace propagation działa

### ⏳ W trakcie realizacji (0/8):
- Brak aktywnych zadań

### 📋 Do zrobienia (2/8):
7. Dashboard: Frame Pipeline Overview
8. Alerty: frame drop, latency, queue size

### 🔧 Działające usługi produkcyjne:
- **Infrastruktura**: postgres, pgbouncer, redis, prometheus, grafana, jaeger (wszystkie healthy)
- **Aplikacyjne**: rtsp-capture, frame-buffer, frame-tracking (jako serwis event sourcing), metadata-storage, base-template, sample-processor (wszystkie healthy)
- **Biblioteki**: frame-tracking (shared library) zintegrowana w: frame-buffer, base-processor, metadata-storage, sample-processor
- **Łącznie**: 11 usług działających na Nebula z pełnym monitoringiem i distributed tracing

## ✅ ROZWIĄZANY PROBLEM: rtsp-capture nie odpowiada na HTTP (2025-07-26 23:20)

### Problem:
- **`cv2.VideoCapture.read()`** to synchroniczna funkcja która blokowała event loop FastAPI
- Wszystkie HTTP requesty wisiały w nieskończoność mimo że capture działał

### Rozwiązanie:
```python
# Zamiast:
ret, frame = self.cap.read()

# Używamy:
loop = asyncio.get_event_loop()
ret, frame = await loop.run_in_executor(None, self.cap.read)
```

### Dodatkowe poprawki:
- Wykomentowano `RedisInstrumentor().instrument()` w observability.py (mogło powodować problemy)
- Przeniesiono `init_telemetry()` do startup event (zamiast na poziomie modułu)

### Status: ✅ DZIAŁA
- rtsp-capture działa na porcie 8080
- Łapie klatki z kamery Reolink (192.168.1.195)
- Publikuje metadata do Redis Streams
- Health endpoint `/health` odpowiada poprawnie
- Wszystkie metryki i monitoring działają
