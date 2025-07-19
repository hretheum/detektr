# Kontekst Projektu Detektor - dla LLM

<!--
META LLM PROMPT:
Ten plik służy do szybkiego wprowadzenia LLM w kontekst projektu.
Wczytaj go na początku każdej nowej sesji/konwersacji.
-->

## O projekcie

**Nazwa**: System Detekcji i Automatyzacji Wizyjnej
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
2. **Registry**: Publikacja do ghcr.io/hretheum/bezrobocie-detektor/
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
- **Faza 2**: Akwizycja i storage 🚧
- **Faza 3**: AI services podstawy
- **Faza 4**: Integracja z Home Assistant
- **Faza 5**: Zaawansowane AI i voice
- **Faza 6**: Optymalizacja i refinement

## Porty serwisów

- 8001: rtsp-capture
- 8002: face-recognition
- 8003: object-detection
- 8004: ha-bridge
- 8005: example-otel ✅ (działający przykład z Fazy 1)
- 8006: frame-tracking
- 8007: echo-service
- 8008: gpu-demo
- 9090: Prometheus ✅
- 16686: Jaeger ✅
- 3000: Grafana ✅

## Gdzie szukać czego

- **Jak coś zrobić**: `/CLAUDE.md` (zawiera CI/CD guidelines!)
- **Co zrobić**: `/architektura_systemu.md`
- **Szczegóły zadania**: `/docs/faza-*/`
- **Szablon nowego zadania**: `/docs/TASK_TEMPLATE.md`
- **CI/CD setup**: `/docs/CI_CD_SETUP.md`
- **Deployment scripts**: `/scripts/deploy-to-nebula.sh`

## Komendy projektu

### Development
- `/nakurwiaj <blok>` - automatyczne wykonanie bloku zadań
- `docker-compose up -d` - start lokalnego stacku
- `docker-compose logs -f service-name` - logi serwisu
- `curl http://localhost:800X/health` - health check

### CI/CD & Deployment
- `git push origin main` - trigger CI/CD pipeline
- `./scripts/deploy-to-nebula.sh` - manual deployment
- `ssh nebula "/opt/detektor/scripts/health-check-all.sh"` - verify deployment
- `make secrets-edit` - edycja sekretów SOPS

## Na co uważać

1. Blok 0 (Prerequisites) - ZAWSZE wykonaj pierwszy
2. Metryki sukcesu - każde zadanie ma kryteria
3. Rollback plan - każde zadanie można cofnąć
4. API keys - NIGDY nie commituj do repo (używaj SOPS!)
5. GPU memory - monitor użycie VRAM
6. CI/CD - NIGDY nie buduj obrazów na produkcji
7. Registry - wszystkie obrazy z ghcr.io/hretheum/bezrobocie-detektor/

## Status Fazy 1 (COMPLETED ✅)

### Zrealizowane komponenty:
- ✅ Infrastruktura observability (Prometheus, Jaeger, Grafana)
- ✅ CI/CD pipeline (GitHub Actions + GHCR)
- ✅ Deployment automation (scripts/deploy-to-nebula.sh)
- ✅ Example service z pełnym observability (example-otel)
- ✅ Secrets management (SOPS z age)
- ✅ Health monitoring (scripts/health-check-all.sh)

### Dokumentacja zaktualizowana:
- ✅ CLAUDE.md - zawiera pełne CI/CD guidelines
- ✅ docs/CI_CD_SETUP.md - instrukcje konfiguracji
- ✅ docs/faza-1-fundament/99-deployment-remediation.md - strategia deployment

### Ready for Faza 2:
- Solidny fundament CI/CD
- Działające przykłady do kopiowania
- Pełna observability od początku
- Zautomatyzowany deployment
