# Kontekst Projektu Detektor - dla LLM

<!--
META LLM PROMPT:
Ten plik służy do szybkiego wprowadzenia LLM w kontekst projektu.
Wczytaj go na początku każdej nowej sesji/konwersacji.

WAŻNE: Po wczytaniu tego pliku, NATYCHMIAST wczytaj również konfiguracje agentów:
- /Users/hretheum/dev/bezrobocie/detektor/.claude/agents/architecture-advisor.md
- /Users/hretheum/dev/bezrobocie/detektor/.claude/agents/code-reviewer.md
- /Users/hretheum/dev/bezrobocie/detektor/.claude/agents/debugger.md
- /Users/hretheum/dev/bezrobocie/detektor/.claude/agents/deployment-specialist.md
- /Users/hretheum/dev/bezrobocie/detektor/.claude/agents/pipeline-debugger.md
- /Users/hretheum/dev/bezrobocie/detektor/.claude/agents/detektor-coder.md
- /Users/hretheum/dev/bezrobocie/detektor/.claude/agents/documentation-keeper.md
- /Users/hretheum/dev/bezrobocie/detektor/.claude/agents/pisarz.md
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

## Workflow wykonywania zadań - Automatyczny łańcuch agentów

### Development Flow
1. **Start**: Sprawdź aktualną fazę w `architektura_systemu.md`
2. **Wybierz zadanie**: Znajdź [ ] checkbox (nieukończone)
3. **Otwórz dekompozycję**: Kliknij link "Szczegóły →"
4. **Wykonaj**: Użyj `/nakurwiaj <numer_bloku>`
5. **Code Review**: Po KAŻDYM zadaniu atomowym uruchom `/agent code-reviewer`
6. **Waliduj**: Po każdym bloku - testy, metryki, git commit

### Reguły generalne dla /nakurwiaj - Automatyczny łańcuch agentów

Gdy LLM otrzymuje komendę `/nakurwiaj`, automatycznie stosuje następujący łańcuch:

#### 1. Analiza kontekstu zadania
```
IF task contains "implement|create|add|napisz|stwórz|dodaj":
    → /agent detektor-coder
ELIF task contains "debug|fix|investigate|napraw|zbadaj":
    → /agent debugger lub pipeline-debugger
ELIF task contains "refactor|optimize|zoptymalizuj":
    → /agent architecture-advisor → detektor-coder
ELIF task contains "deploy|deployment|wdróż":
    → /agent deployment-specialist
```

#### 2. Quality Gate (ZAWSZE po każdym zadaniu)
```
AFTER each atomic task:
    → /agent code-reviewer
    IF critical_issues:
        → Loop back to previous agent with feedback
        → Maximum 3 iterations
        → Auto-fix issues without asking
```

#### 3. Deployment Flow (warunkowy)
```
IF block contains deployment tasks OR "CI/CD" OR "GitHub Actions":
    → git add -A && git commit -m "feat: [nazwa bloku]"
    → git push origin main (triggers CI/CD)
    → /agent deployment-specialist (monitor pipeline)
    → Verify health checks on Nebula
    → IF failed: automatic rollback + debug
```

#### 3.5. Documentation Sync (ZAWSZE przed przejściem do kolejnego bloku)
```
BEFORE moving to next block:
    → /agent documentation-keeper
    → Synchronize:
        - Task checkboxes [x] in decomposition files
        - Service ports in PROJECT_CONTEXT.md
        - Status in architektura_systemu.md
        - New problems in TROUBLESHOOTING.md
        - Service READMEs if new services added
    → Verify all docs are consistent
```

#### 4. Automatyzacja i autonomia
- ✅ Automatyczne commity z descriptive messages (format: "feat: [task name]" lub "fix: [issue]")
- ✅ Automatyczny push (chyba że user explicite mówi "bez push" lub "no push")
- ✅ Kontynuacja do następnego bloku (chyba że user mówi "tylko ten blok" lub "only this block")
- ✅ Brak pytań o potwierdzenie - pełne zaufanie do agentów i ich decyzji
- ✅ Automatyczne naprawianie błędów znalezionych przez code-reviewer
- ✅ Używanie wielu agentów równolegle gdy to możliwe

#### 5. Przykład pełnego flow
```
User: /nakurwiaj blok-1

LLM:
[Blok 1/N] Frame Processor Implementation
=========================================

[Zadanie 1/3] "Implement RTSP capture service"
→ Wywołuję: /agent detektor-coder
  ✓ Created: services/rtsp-capture/
  ✓ Tests: 15/15 passing
→ Wywołuję: /agent code-reviewer
  ! Found 2 issues - auto-fixing...
→ Wywołuję: /agent detektor-coder --fix
  ✓ Issues resolved
→ Wywołuję: /agent code-reviewer
  ✓ Code approved

[Zadanie 2/3] "Add distributed tracing"
→ Wywołuję: /agent detektor-coder --feature=tracing
  ✓ OpenTelemetry integrated
  ✓ Trace context propagation added
→ Wywołuję: /agent code-reviewer
  ✓ No issues found

[Zadanie 3/3] "Deploy to production"
→ Executing: git add -A && git commit -m "feat: rtsp-capture service with distributed tracing"
→ Executing: git push origin main
→ Wywołuję: /agent deployment-specialist
  ✓ CI/CD pipeline passed
  ✓ Health check: http://nebula:8080/health - OK
  ✓ Metrics endpoint verified

→ Wywołuję: /agent documentation-keeper
  ✓ Updated PROJECT_CONTEXT.md - service ports
  ✓ Updated architektura_systemu.md - task checkboxes
  ✓ Synced README.md - service list
  ✓ All documentation consistent

Blok 1 completed successfully. Proceeding to Blok 2...
```

#### 6. Specjalne przypadki
- **Błąd w pipeline**: Automatyczny rollback, następnie `/agent debugger` → napraw → ponów deployment
- **Test failures**: `/agent detektor-coder --fix-tests` → re-run tests → proceed
- **Performance issues**: `/agent architecture-advisor` → recommendations → `/agent detektor-coder` → implement
- **Brak dostępu/credentials**: Pause → inform user → wait for fix → resume

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
- **Code Review OBOWIĄZKOWY** - po każdym zadaniu atomowym `/agent code-reviewer`
- **No hardcoded secrets** - wszystko przez SOPS

## Bounded Contexts

1. **Frame Processing** - Capture, buffering, storage
2. **AI Detection** - Face, gesture, object recognition
3. **Home Automation** - HA integration, action execution

## Fazy projektu

- **Faza 0**: Dokumentacja i planowanie ✅
- **Faza 1**: Fundament z observability ✅ (CI/CD + przykładowe serwisy)
- **Faza 2**: Akwizycja i storage 🚧 (7/8 zadań ukończonych)
- **Faza 3**: AI services podstawy
- **Faza 4**: Integracja z Home Assistant
- **Faza 5**: Zaawansowane AI i voice
- **Faza 6**: Optymalizacja i refinement

## Dostępne Sub-Agenty (AI Assistants)

Projekt posiada 8 wyspecjalizowanych agentów pomocniczych:

1. **`/agent architecture-advisor`** - Ekspert od Clean Architecture, DDD, wzorców projektowych
2. **`/agent code-reviewer`** - Code review, refaktoring, best practices (OBOWIĄZKOWY po każdym zadaniu atomowym!)
3. **`/agent debugger`** - Troubleshooting, analiza logów, debugging runtime
4. **`/agent deployment-specialist`** - CI/CD, Docker, GitHub Actions, deployment na Nebula
5. **`/agent pipeline-debugger`** - Dedykowany dla problemów w pipeline przetwarzania klatek
6. **`/agent detektor-coder`** - Implementacja zadań atomowych, TDD, observability-first
7. **`/agent documentation-keeper`** - Synchronizacja dokumentacji, aktualizacja statusów (URUCHAMIANY przed przejściem do kolejnego bloku)
8. **`/agent pisarz`** - Zbiera materiały do tech deep dives na social media (zapisuje w /socmedia/)

Konfiguracje agentów znajdują się w: `/Users/hretheum/dev/bezrobocie/detektor/.claude/agents/`

## Porty serwisów

- 8000: base-template ✅
- 8001: frame-tracking ✅ (frame-events)
- 8002: frame-buffer-v2 ✅ (z Block 3 features)
- 8003: face-recognition
- 8004: object-detection
- 8005: metadata-storage ✅
- 8006: (reserved)
- 8007: echo-service
- 8008: gpu-demo
- 8099: sample-processor ✅ (aktywnie przetwarza klatki)
- 8009: example-otel
- 8080: rtsp-capture ✅
- 8081: frame-events ✅
- 8082: cadvisor ✅
- 8083: adminer
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

## Status Fazy 2: Akwizycja i Storage (2025-01-31) ✅ **PRAWIE UKOŃCZONA**

### ✅ Ukończone zadania (7/8):
1. **RTSP Capture Service** - Działający na Nebula:8080, publikuje do Redis Stream "frames:metadata" z detection_type
2. **Frame Buffer z Redis** - ✅ NAPRAWIONY! Consumer pobiera z frames:metadata i dystrybuuje do procesorów
3. **Redis Configuration** - 4GB limit, persistence, monitoring, Telegram alerts
4. **PostgreSQL/TimescaleDB** - 100GB volume, PGBouncer, hypertables ready
5. **Frame Processor Base Service** - Framework w services/shared/base-processor/, sample-processor na Nebula:8099
6. **Frame tracking z distributed tracing** - Biblioteka frame-tracking zintegrowana, pełny flow działa
7. **Pipeline integration** - ✅ Pełny flow: RTSP → Redis → Frame Buffer → Processors → Results

### 📋 Do zrobienia (1/8):
8. Dashboard: Frame Pipeline Overview + Alerty (frame drop, latency, queue size)

### ✅ ROZWIĄZANE problemy architekturalne (2025-01-31):
1. **Frame Buffer Dead-End** → **NAPRAWIONY**:
   - Frame-buffer-v2 konsumuje z "frames:metadata" (nie frame_queue)
   - Procesory rejestrują się w frame-buffer i otrzymują klatki
   - Sample-processor przetwarza klatki i zapisuje wyniki do "sample:results"
   - Pełny pipeline działa end-to-end!

2. **Niekompletny pipeline** → **NAPRAWIONY**:
   - Pipeline: RTSP → Redis (frames:metadata) → Frame Buffer → Processors → Storage ✅
   - Sample-processor jest zarejestrowany i przetwarza klatki
   - Wyniki są zapisywane w Redis stream "sample:results"

3. **Trace propagation** → **NAPRAWIONA**:
   - rtsp-capture: ✅ generuje trace_context z trace_id i span_id
   - frame-buffer: ✅ parsuje trace_context i propaguje do procesorów
   - sample-processor: ✅ przetwarza z trace context
   - Pełna widoczność w Jaeger UI

### 🔧 Działające usługi produkcyjne:
- **Infrastruktura**: postgres, pgbouncer, redis, prometheus, grafana, jaeger (wszystkie healthy)
- **Aplikacyjne**:
  - rtsp-capture (czeka na kamerę, ale kod gotowy z detection_type)
  - frame-buffer-v2 (z /metrics endpoint, obsługą None priority, Block 3 features)
  - frame-events (event sourcing)
  - metadata-storage (gotowy do użycia)
  - base-template (przykładowy serwis)
  - sample-processor (aktywnie przetwarza klatki!)
- **Sieć**: Wszystkie serwisy na jednej sieci `detektor-network`
- **Pipeline**: Pełny flow działa z testowymi klatkami

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

## ✅ ROZWIĄZANY PROBLEM: Pipeline zatrzymywał wszystkie serwisy podczas deploy (2025-07-28)

### Problem:
- Funkcja `cleanup_ports()` w `scripts/deploy.sh` zatrzymywała WSZYSTKIE kontenery używające portów ze zdefiniowanej listy
- To powodowało zatrzymanie wszystkich serwisów podczas deploymentu pojedynczego serwisu

### Rozwiązanie:
- Zmodyfikowano `cleanup_ports()` aby sprawdzała tylko porty serwisów w `DEPLOY_SERVICES`
- Dodano przekazywanie `DEPLOY_SERVICES` przez SSH do zdalnych deploymentów
- Zaktualizowano wszystkie referencje z `frame-buffer` na `frame-buffer-v2`

### Status: ✅ DZIAŁA
- Pipeline teraz zatrzymuje tylko serwisy które są deployowane
- Pozostałe serwisy działają bez przerwy
- Deployment pojedynczego serwisu nie wpływa na resztę systemu

## ✅ ROZWIĄZANY PROBLEM: frame-buffer-v2 models directory nie był kopiowany do Docker (2025-07-28)

### Problem:
- Katalog `services/frame-buffer-v2/src/models/` nie był śledzony przez Git
- Docker build nie mógł znaleźć pliku `__init__.py` podczas kopiowania
- Kontener ciągle restartował z błędem `ModuleNotFoundError: No module named 'src.models'`

### Rozwiązanie:
- Dodano `services/frame-buffer-v2/src/models/__init__.py` do Git (`git add -f`)
- Dodano `.gitkeep` do katalogu models dla pewności
- Zaktualizowano Dockerfile z explicit copy instrukcjami

### Status: ✅ DZIAŁA
- frame-buffer-v2 działa poprawnie na porcie 8002
- Wszystkie moduły są prawidłowo importowane
- Block 3 features (backpressure control, smart routing, circuit breaker, priority queue) są dostępne

## ✅ ROZWIĄZANY PROBLEM: Frame Buffer v2 - błąd NoneType przy priority (2025-01-31)

### Problem:
- Frame Buffer v2 rzucał błąd `DataError: Invalid input of type: 'NoneType'` przy próbie zapisu do Redis
- Pole `priority` mogło być None, a Redis nie akceptuje None jako wartości

### Rozwiązanie:
- Dodano obsługę None w 4 miejscach:
  - `models/__init__.py` - konwersja None → 0 w `__post_init__` i `to_json()`
  - `distributor.py` - użycie `.get("priority", 0)` zamiast bezpośredniego dostępu
  - `queue_manager.py` i `client.py` - konwersja None → pusty string dla Redis
- Dodano test jednostkowy weryfikujący obsługę None

### Status: ✅ DZIAŁA
- Frame Buffer v2 poprawnie obsługuje klatki z priority=None
- Wszystkie wartości są konwertowane na stringi przed zapisem do Redis

## ✅ ROZWIĄZANY PROBLEM: Brak /metrics endpoint w Frame Buffer v2 (2025-01-31)

### Problem:
- Prometheus health check oznaczał frame-buffer-v2 jako "unhealthy" z powodu braku endpoint /metrics

### Rozwiązanie:
- Dodano endpoint `/metrics` w `src/api/app.py`
- Endpoint zwraca:
  - Status serwisu
  - Liczbę zarejestrowanych procesorów
  - Metryki Redis (connected clients, memory usage)
  - Informacje o input stream
- Poprawiono błąd `list_processors()` → `list_all()`

### Status: ✅ DZIAŁA
- /metrics endpoint dostępny i zwraca pełne metryki
- Serwis oznaczony jako "healthy" w Prometheus

## ✅ ROZWIĄZANY PROBLEM: Pipeline nie działał end-to-end (2025-01-31)

### Problem:
- RTSP capture publikował do `frame_queue`, ale Frame Buffer v2 konsumował z `frames:metadata`
- Frame Buffer v2 wymagał `detection_type` w metadata, którego brakowało
- Nieprawidłowy format `trace_context` powodował błędy

### Rozwiązanie:
1. **Ustalono prawidłowy przepływ**:
   - RTSP → `frames:metadata` (nie frame_queue)
   - Frame Buffer v2 konsumuje z `frames:metadata`

2. **Dodano detection_type**:
   - RTSP capture dodaje `detection_type` do metadata (domyślnie "object_detection")
   - Konfigurowalne przez zmienną środowiskową `DETECTION_TYPE`

3. **Poprawiono format trace_context**:
   - Wymagane pola: trace_id, span_id, trace_flags, trace_state, attributes, baggage
   - Nie tylko "traceparent" jak wcześniej

### Status: ✅ DZIAŁA
- Pipeline działa end-to-end z testowymi klatkami
- Klatki są dystrybuowane do procesorów i przetwarzane
- Wyniki zapisywane w "sample:results"
