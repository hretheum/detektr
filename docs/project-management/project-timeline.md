# Timeline Projektu Detektor

## Podsumowanie
- **Start**: 1 stycznia 2025
- **Koniec**: 30 kwietnia 2025
- **Czas trwania**: 4 miesiące (17 tygodni)
- **Effort**: ~680 godzin

## Harmonogram Faz

### Faza 0: Dokumentacja i Planowanie
**Czas**: 1-2 tygodnie (1-14 stycznia)
- Tydzień 1: Analiza wymagań, struktura projektu
- Tydzień 2: Dekompozycja zadań, środowisko dev

### Faza 1: Fundament z Observability  
**Czas**: 2-3 tygodnie (15 stycznia - 4 lutego)
- Tydzień 3: Docker, GPU, Git setup
- Tydzień 4: Observability stack (Jaeger, Prometheus, Grafana)
- Tydzień 5: Frame tracking, TDD, dashboards

### Faza 2: Akwizycja Obrazu
**Czas**: 2 tygodnie (5-18 lutego)
- Tydzień 6: RTSP capture, frame buffer
- Tydzień 7: Metadata store, base processor, health checks

### Faza 3: Detekcja AI
**Czas**: 3-4 tygodnie (19 lutego - 18 marca)
- Tydzień 8-9: YOLO, Face recognition, Gesture detection
- Tydzień 10: Event aggregation, GPU optimization
- Tydzień 11: Detection zones, integration testing

### Faza 4: Integracja  
**Czas**: 2-3 tygodnie (19 marca - 8 kwietnia)
- Tydzień 12: MQTT/HA bridge, Event bus
- Tydzień 13: Automation engine, API gateway
- Tydzień 14: E2E integration tests

### Faza 5: LLM i Voice
**Czas**: 2 tygodnie (9-22 kwietnia)
- Tydzień 15: LLM integration, Intent recognition
- Tydzień 16: Voice processing, Conversation memory

### Faza 6: Optymalizacja
**Czas**: 1 tydzień (23-30 kwietnia)
- Tydzień 17: Performance profiling, bottlenecks, production hardening

## Kamienie Milowe

1. **M1 (14 stycznia)**: Dokumentacja kompletna, projekt zaplanowany
2. **M2 (4 lutego)**: Infrastruktura gotowa, observability działa
3. **M3 (18 lutego)**: Akwizycja obrazu działa dla 4 kamer
4. **M4 (18 marca)**: Wszystkie AI detektory zintegrowane
5. **M5 (8 kwietnia)**: Home Assistant integration kompletna
6. **M6 (22 kwietnia)**: Voice control i LLM działają
7. **M7 (30 kwietnia)**: System production-ready

## Buffer i Ryzyka

- **Buffer**: 10% (17 dni) wbudowany w estymacje
- **Ryzyka**:
  - Problemy z GPU/CUDA setup (+1 tydzień)
  - Integracja z Home Assistant (+3 dni)
  - Performance issues w Fazie 6 (+1 tydzień)

## Ścieżka Krytyczna

1. Faza 0 → Faza 1 (Docker) → Faza 1 (Frame tracking)
2. → Faza 2 (Base processor) → Faza 3 (Event aggregation)
3. → Faza 4 (Automation engine) → Faza 5 (Intent recognition)

Opóźnienie na ścieżce krytycznej = opóźnienie całego projektu