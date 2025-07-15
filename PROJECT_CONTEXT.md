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
- **Serwer**: Ubuntu z GTX 4070 Super (16GB VRAM), i7, 64GB RAM
- **Infrastruktura**: Docker, Docker Compose, container-first
- **Języki**: Python 3.11+, FastAPI
- **AI/ML**: YOLO, MediaPipe, Whisper, OpenAI/Anthropic API
- **Observability**: Jaeger, Prometheus, Grafana (od początku!)
- **Architektura**: Clean Architecture, DDD, Event Sourcing, TDD

## Struktura dokumentacji
```
/architektura_systemu.md     # Główny dokument, fazy projektu
/CLAUDE.md                   # Zasady i wzorce projektu
/docs/TASK_TEMPLATE.md       # Szablon dekompozycji zadań
/docs/faza-X-nazwa/*.md      # Dekompozycje zadań per faza
/PROJECT_CONTEXT.md          # Ten plik
```

## Workflow wykonywania zadań
1. **Start**: Sprawdź aktualną fazę w `architektura_systemu.md`
2. **Wybierz zadanie**: Znajdź [ ] checkbox (nieukończone)
3. **Otwórz dekompozycję**: Kliknij link "Szczegóły →"
4. **Wykonaj**: Użyj `/nakurwiaj <numer_bloku>`
5. **Waliduj**: Po każdym bloku - testy, metryki, git commit

## Kluczowe zasady
- **TDD zawsze** - test first, code second
- **Observability first** - tracing/metrics od początku
- **Container first** - wszystko w Dockerze
- **Clean Architecture** - separacja warstw
- **Zadania atomowe** - max 3h na zadanie

## Bounded Contexts
1. **Frame Processing** - Capture, buffering, storage
2. **AI Detection** - Face, gesture, object recognition
3. **Home Automation** - HA integration, action execution

## Fazy projektu
- **Faza 0**: Dokumentacja i planowanie
- **Faza 1**: Fundament z observability
- **Faza 2**: Akwizycja i storage
- **Faza 3**: AI services podstawy
- **Faza 4**: Integracja z Home Assistant
- **Faza 5**: Zaawansowane AI i voice
- **Faza 6**: Optymalizacja i refinement

## Porty serwisów
- 8001: rtsp-capture
- 8002: face-recognition
- 8003: object-detection
- 8004: ha-bridge
- 8005: llm-intent
- 9090: Prometheus
- 16686: Jaeger
- 3000: Grafana

## Gdzie szukać czego
- **Jak coś zrobić**: `/CLAUDE.md`
- **Co zrobić**: `/architektura_systemu.md`
- **Szczegóły zadania**: `/docs/faza-*/`
- **Szablon nowego zadania**: `/docs/TASK_TEMPLATE.md`

## Komendy projektu
- `/nakurwiaj <blok>` - automatyczne wykonanie bloku zadań
- `docker-compose up -d` - start całego stacku
- `docker-compose logs -f service-name` - logi serwisu
- `curl http://localhost:800X/health` - health check

## Na co uważać
1. Blok 0 (Prerequisites) - ZAWSZE wykonaj pierwszy
2. Metryki sukcesu - każde zadanie ma kryteria
3. Rollback plan - każde zadanie można cofnąć
4. API keys - NIGDY nie commituj do repo
5. GPU memory - monitor użycie VRAM