# Faza 2 / Zadanie 1: Implementacja RTSP capture service z OpenTelemetry

<!-- 
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Cel jest jasny i biznesowo uzasadniony
2. Dekompozycja pokrywa 100% zakresu zadania
3. Nie ma luk między blokami zadań
4. Całość można ukończyć w podanym czasie
-->

## Cel zadania
Zaimplementować wysokowydajny serwis przechwytywania strumienia wideo z kamer IP przez RTSP, z pełną obserwabilitą (distributed tracing, metryki) i gwarantowanym frame rate 10+ FPS.

## Blok 0: Prerequisites check
<!-- 
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe:
1. **[ ] Weryfikacja zależności systemowych**
   - **Metryka**: Docker, Python 3.11+, ffmpeg, poetry installed
   - **Walidacja**: 
     ```bash
     ./scripts/check-rtsp-prerequisites.sh
     # Sprawdza: docker --version && python --version && ffmpeg -version && poetry --version
     # Exit code: 0 = all OK
     ```
   - **Czas**: 0.5h

2. **[ ] Test połączenia z kamerą IP**
   - **Metryka**: RTSP stream dostępny i stabilny przez 60s
   - **Walidacja**: 
     ```bash
     ffplay -rtsp_transport tcp rtsp://${CAMERA_IP}/stream1 -t 60
     # Powinno pokazać obraz przez 60 sekund bez błędów
     ```
   - **Czas**: 0.5h

3. **[ ] Backup obecnej konfiguracji (jeśli istnieje)**
   - **Metryka**: Config files backed up z timestamp
   - **Walidacja**: `ls -la /backups/rtsp-capture/$(date +%Y%m%d)/` 
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Projekt struktury i dependencies
<!-- 
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. Każde zadanie atomowe musi być wykonalne w MAX 3h
2. Zadania w bloku powinny być logicznie powiązane
3. Kolejność zadań musi mieć sens (dependencies)
4. Blok powinien dostarczać konkretną wartość biznesową
-->

#### Zadania atomowe:
1. **[ ] Utworzenie struktury projektu zgodnej z Clean Architecture**
   <!-- 
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Mieć JEDEN konkretny deliverable
   - Być wykonalne przez jedną osobę bez przerw
   - Mieć jasne kryterium "done"
   - NIE wymagać czekania na zewnętrzne zależności
   -->
   - **Metryka**: Struktura katalogów utworzona, pyproject.toml skonfigurowany
   - **Walidacja**: 
     ```bash
     tree services/rtsp-capture -d -L 3
     # Output zawiera: domain/, infrastructure/, application/, tests/
     # ORAZ: poetry check zwraca "All set!"
     ```
   - **Czas**: 1h

2. **[ ] Konfiguracja dependencies i virtual environment**
   - **Metryka**: Wszystkie zależności zainstalowane, lock file utworzony
   - **Walidacja**: 
     ```bash
     cd services/rtsp-capture && poetry install && poetry run python -c "import cv2, av, opentelemetry"
     # Brak błędów importu = sukces
     ```
   - **Czas**: 1h

3. **[ ] Setup pre-commit hooks i linting**
   - **Metryka**: Black, flake8, mypy, pytest skonfigurowane
   - **Walidacja**: 
     ```bash
     pre-commit run --all-files
     # Exit code 0 = wszystkie checks przeszły
     ```
   - **Czas**: 1h

#### Metryki sukcesu bloku:
<!-- 
LLM PROMPT dla metryk bloku:
Metryki muszą potwierdzać że blok osiągnął swój cel.
Powinny być:
1. Mierzalne automatycznie gdzie możliwe
2. Agregować metryki zadań atomowych
3. Dawać pewność że można przejść do następnego bloku
-->
- Projekt structure kompletna i zgodna ze standardami
- Development environment w pełni funkcjonalny
- CI/CD ready (pre-commit hooks działają)

### Blok 2: Core RTSP capture implementation
<!-- 
LLM PROMPT: Ten blok implementuje główną funkcjonalność.
Pamiętaj o TDD - najpierw testy, potem implementacja.
-->

#### Zadania atomowe:
1. **[ ] TDD: Napisanie testów dla RTSP connection manager**
   - **Metryka**: 10+ test cases, mocking external dependencies
   - **Walidacja**: 
     ```bash
     poetry run pytest tests/unit/test_rtsp_connection.py -v
     # Wszystkie testy FAIL (bo nie ma jeszcze implementacji)
     ```
   - **Czas**: 2h

2. **[ ] Implementacja RTSP connection z retry logic**
   - **Metryka**: Auto-reconnect w <5s, exponential backoff
   - **Walidacja**: 
     ```bash
     poetry run pytest tests/unit/test_rtsp_connection.py -v
     # Wszystkie testy PASS
     # ORAZ: poetry run python -m rtsp_capture.test_connection
     ```
   - **Czas**: 3h

3. **[ ] TDD: Testy dla frame extraction i buffering**
   - **Metryka**: Tests for 10+ FPS, frame dropping, buffering
   - **Walidacja**: 
     ```bash
     poetry run pytest tests/unit/test_frame_extractor.py -v --benchmark
     # Testy zdefiniowane, FAIL
     ```
   - **Czas**: 2h

4. **[ ] Implementacja frame extraction z PyAV**
   - **Metryka**: Stable 10+ FPS, <50ms latency per frame
   - **Walidacja**: 
     ```bash
     poetry run pytest tests/unit/test_frame_extractor.py -v --benchmark
     # PASS + benchmark pokazuje >10 FPS capability
     ```
   - **Czas**: 3h

#### Metryki sukcesu bloku:
- 100% test coverage dla core functionality
- Benchmark potwierdzający 10+ FPS
- Reconnection działa w każdym scenariuszu

### Blok 3: OpenTelemetry integration
<!-- 
LLM PROMPT: Observability musi być wbudowana od początku.
Każda operacja musi mieć trace span i metryki.
-->

#### Zadania atomowe:
1. **[ ] Implementacja OpenTelemetry TracerProvider**
   - **Metryka**: Traces eksportowane do Jaeger, service name visible
   - **Walidacja**: 
     ```bash
     # Run test capture for 30s
     poetry run python -m rtsp_capture.capture --test-mode --duration 30
     # Check Jaeger UI
     curl "http://localhost:16686/api/traces?service=rtsp-capture" | jq '.data[0].spans | length'
     # Should return >0
     ```
   - **Czas**: 2h

2. **[ ] Dodanie span dla każdej captured frame**
   - **Metryka**: Każda klatka ma trace z timestamp, size, processing time
   - **Walidacja**: 
     ```python
     # Test script
     trace = get_latest_trace("rtsp-capture")
     frame_spans = [s for s in trace.spans if s.name == "capture_frame"]
     assert len(frame_spans) > 100  # dla 10s capture
     assert all(s.attributes.get("frame.size") > 0 for s in frame_spans)
     ```
   - **Czas**: 2h

3. **[ ] Prometheus metrics dla capture performance**
   - **Metryka**: FPS, dropped frames, latency jako Prometheus metrics
   - **Walidacja**: 
     ```bash
     # Po 1 min działania
     curl localhost:8001/metrics | grep -E "rtsp_capture_fps|rtsp_frames_dropped_total|rtsp_capture_latency"
     # Wszystkie 3 metryki obecne z wartościami >0
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- 100% operacji ma trace spans
- Metryki dostępne na /metrics endpoint
- Jaeger pokazuje pełny flow przetwarzania

### Blok 4: Queue integration i frame metadata
<!-- 
LLM PROMPT: Integracja z message queue dla downstream processing.
Frame metadata musi zawierać wszystko potrzebne do trackingu.
-->

#### Zadania atomowe:
1. **[ ] Implementacja frame metadata model**
   - **Metryka**: Dataclass z validation, JSON serializable
   - **Walidacja**: 
     ```python
     from rtsp_capture.domain.models import FrameMetadata
     meta = FrameMetadata.create_test_instance()
     assert meta.to_json() and FrameMetadata.from_json(meta.to_json()) == meta
     ```
   - **Czas**: 1h

2. **[ ] Redis queue publisher z retries**
   - **Metryka**: 99.9% delivery rate, <10ms publish time
   - **Walidacja**: 
     ```bash
     # Publish 1000 test frames
     poetry run python -m rtsp_capture.test_publisher --count 1000
     # Check Redis
     redis-cli LLEN frame_queue  # Should be 1000
     ```
   - **Czas**: 2h

3. **[ ] Integration test: capture → queue**
   - **Metryka**: End-to-end test passing, no frame loss
   - **Walidacja**: 
     ```bash
     poetry run pytest tests/integration/test_capture_to_queue.py -v
     # Captures 100 frames, all arrive in queue with correct metadata
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Zero frame loss w normalnych warunkach
- Metadata kompletna i trackable
- Queue integration przetestowana e2e

### Blok 5: Containerization i health checks
<!-- 
LLM PROMPT: Production-ready container z proper health checking.
Multi-stage build dla małego image size.
-->

#### Zadania atomowe:
1. **[ ] Multi-stage Dockerfile z minimal runtime**
   - **Metryka**: Image <500MB, tylko runtime dependencies
   - **Walidacja**: 
     ```bash
     docker build -t rtsp-capture:test .
     docker images rtsp-capture:test --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
     # Size <500MB
     dive rtsp-capture:test  # Check for wasted space
     ```
   - **Czas**: 2h

2. **[ ] Health check endpoint z diagnostics**
   - **Metryka**: /health zwraca camera status, FPS, queue status
   - **Walidacja**: 
     ```bash
     docker run -d --name rtsp-test rtsp-capture:test
     sleep 10
     curl localhost:8001/health | jq '.status'  # "healthy"
     curl localhost:8001/health | jq '.fps'     # >0
     ```
   - **Czas**: 1.5h

3. **[ ] Docker Compose integration z dependencies**
   - **Metryka**: Service startuje z Redis, exports metrics
   - **Walidacja**: 
     ```bash
     docker-compose up -d rtsp-capture redis
     sleep 20
     docker-compose ps  # Both healthy
     curl localhost:8001/metrics | grep rtsp_  # Metrics visible
     ```
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Container production-ready
- Health checks comprehensive
- Graceful shutdown bez frame loss

## Całościowe metryki sukcesu zadania
<!-- 
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera (self w tym przypadku)
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **Performance**: Stable 10+ FPS capture z <0.1% frame loss
2. **Observability**: 100% frames traced, metrics dostępne real-time
3. **Reliability**: Auto-reconnect <5s, 99.9% uptime pod normalnym load
4. **Integration**: Frames w queue z full metadata do trackingu

## Deliverables
<!-- 
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi:
1. Mieć konkretną ścieżkę w filesystem
2. Być wymieniony w jakimś zadaniu atomowym
3. Mieć jasny format i przeznaczenie
-->

1. `/services/rtsp-capture/` - Kompletny serwis Python
2. `/services/rtsp-capture/Dockerfile` - Production-ready image
3. `/services/rtsp-capture/tests/` - Unit + integration tests  
4. `/docker-compose.yml` - Updated z rtsp-capture service
5. `/docs/api/rtsp-capture-api.md` - API documentation
6. `/dashboards/rtsp-capture.json` - Grafana dashboard
7. `/scripts/check-rtsp-prerequisites.sh` - Dependency checker

## Narzędzia
<!-- 
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
Dla każdego podaj:
1. Dokładną nazwę i wersję (jeśli istotna)
2. Konkretne zastosowanie w tym zadaniu
3. Alternatywy jeśli główne narzędzie zawiedzie
-->

- **PyAV**: RTSP stream decoding (alternatywa: OpenCV)
- **Poetry**: Dependency management (alternatywa: pip-tools)
- **OpenTelemetry**: Distributed tracing
- **Prometheus Client**: Metrics export
- **Redis**: Frame queue (alternatywa: RabbitMQ)
- **pytest**: Testing framework z pytest-benchmark

## Zależności

- **Wymaga**: 
  - Observability stack deployed (Faza 1)
  - Network access do kamery IP
  - Redis/RabbitMQ running
- **Blokuje**: 
  - Wszystkie AI services (potrzebują frames)
  - Pipeline testing

## Ryzyka i mitigacje
<!-- 
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
Dla każdego ryzyka:
1. Opisz konkretny scenariusz
2. Oceń realistycznie prawdopodobieństwo
3. Zaproponuj WYKONALNĄ mitigację
4. Dodaj trigger/early warning sign
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Niestabilne połączenie RTSP | Wysokie | Wysoki | Aggressive retry, local buffering | Dropped frames >1% |
| Memory leak przy długim runtime | Średnie | Wysoki | Memory profiling, restart policy | RSS memory growing |
| Camera firmware incompatibility | Niskie | Średni | Multiple RTSP libraries ready | Connection errors |

## Rollback Plan
<!-- 
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
Opisz:
1. Jak wykryć że coś poszło źle
2. Kroki do przywrócenia poprzedniego stanu
3. Maksymalny czas rollbacku
-->

1. **Detekcja problemu**: 
   - FPS <5 przez >1 minutę
   - Frame loss >5%
   - Memory usage >2GB
   - Health check failing

2. **Kroki rollback**:
   - [ ] Stop container: `docker-compose stop rtsp-capture`
   - [ ] Restore previous image: `docker tag rtsp-capture:backup rtsp-capture:latest`
   - [ ] Clear corrupted queue: `redis-cli DEL frame_queue`
   - [ ] Restart z poprzednią wersją: `docker-compose up -d rtsp-capture`

3. **Czas rollback**: <5 minut

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-redis-rabbitmq-config.md](./02-redis-rabbitmq-config.md)