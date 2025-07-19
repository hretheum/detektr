# Faza 2 / Zadanie 1: Serwis RTSP Stream Capture

<!--
LLM CONTEXT PROMPT:
RTSP capture service bazuje na eofek/detektor stream-forwarder patterns (docs/analysis/eofek-detektor-analysis.md):
- Docker organization pattern z metrics export
- GPU detection logic dla optimization
- Health checks z comprehensive monitoring
- Redis integration dla frame buffering
- ADOPTUJEMY: ich Docker patterns, metrics abstraction
- UNIKAMY: microservices complexity, external dependencies lock-in
-->

## Cel zadania

Zaimplementować wydajny serwis przechwytywania strumieni RTSP z kamer IP, z automatycznym reconnect, frame buffering i metrykami wydajności od początku.

**Pattern Source**: Adoptuje eofek/detektor stream-forwarder architecture z uproszczeniami.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites ✅ COMPLETED (2025-01-18)

#### Zadania atomowe

1. **[x] Analiza protokołu RTSP i wybór biblioteki**
   - **Metryka**: ✅ PyAV wybrane - obsługuje H.264/H.265, reconnect
   - **Walidacja**: ✅ Proof of concept z test stream: `proof_of_concept.py`
   - **Czas**: 2h ✅ Completed
   - **ADR**: `docs/adr/ADR-2025-01-18-rtsp-library-selection.md`

2. **[x] Setup środowiska testowego z kamerą**
   - **Metryka**: ✅ Symulator RTSP + instrukcje fizycznej kamery

   - **Walidacja**: ✅ `rtsp_simulator.py` + `test_environment.py`
   - **Czas**: 1h ✅ Completed
   - **Kamera na nebula**: **Potrzebna w Bloku 1 - Zadanie 2**

3. **[x] API Specification i Performance Baselines**
   - **Metryka**: ✅ Complete OpenAPI spec w `api_spec.py`
   - **Walidacja**: ✅ Performance tests w `test_rtsp_baseline.py`
   - **Czas**: 3h ✅ Completed
   - **Deliverables**:
     - Complete API spec (OpenAPI 3.0)
     - Performance baseline framework
     - Prerequisites tests (PyAV, FFmpeg, etc.)

### Blok 1: Implementacja core RTSP client

#### Zadania atomowe

1. **[ ] TDD: Testy dla RTSP connection manager**
   - **Metryka**: 100% coverage dla connection logic
   - **Walidacja**: `pytest tests/test_rtsp_connection.py -v`
   - **Czas**: 2h

2. **[ ] Implementacja RTSP client z auto-reconnect**
   - **Metryka**: Reconnect w <5s po utracie połączenia
   - **Walidacja**: Chaos test z network disruption
   - **Czas**: 3h

3. **[ ] Frame extraction i validation**
   - **Metryka**: 0% corrupted frames
   - **Walidacja**: OpenCV frame validation w pipeline
   - **Czas**: 2h

### Blok 2: Buffering i queue management

#### Zadania atomowe

1. **[ ] TDD: Testy dla frame buffer**
   - **Metryka**: Tests dla overflow, underflow, threading
   - **Walidacja**: `pytest tests/test_frame_buffer.py --cov`
   - **Czas**: 2h

2. **[ ] Implementacja circular frame buffer**
   - **Metryka**: Zero-copy operations, 1000 FPS throughput
   - **Walidacja**: Benchmark z memory profiler
   - **Czas**: 3h

3. **[ ] Integracja z Redis queue**
   - **Metryka**: <1ms latency na frame publish
   - **Walidacja**: Redis MONITOR pokazuje frame IDs
   - **Czas**: 2h

### Blok 3: Observability i monitoring

#### Zadania atomowe

1. **[ ] OpenTelemetry instrumentation**
   - **Metryka**: Trace per frame, span per operation
   - **Walidacja**: Jaeger pokazuje full trace
   - **Czas**: 2h

2. **[ ] Prometheus metrics export**
   - **Metryka**: FPS, latency, drops, reconnects metrics
   - **Walidacja**: `curl localhost:8000/metrics | grep rtsp_`
   - **Czas**: 1h

3. **[ ] Health checks i readiness probes**
   - **Metryka**: Accurate health status
   - **Walidacja**: K8s-style probes responding correctly
   - **Czas**: 1h

### Blok 4: Containerization i deployment

#### Zadania atomowe

1. **[ ] Multi-stage Dockerfile z optimization**
   - **Metryka**: Image size <100MB
   - **Walidacja**: `docker images | grep rtsp-capture`
   - **Czas**: 2h

2. **[ ] Docker Compose integration**
   - **Metryka**: Service starts in <10s
   - **Walidacja**: `docker-compose ps` shows healthy
   - **Czas**: 1h

3. **[ ] Performance testing i tuning**
   - **Metryka**: 4 cameras @ 10 FPS, CPU <50%
   - **Walidacja**: Stress test for 24h
   - **Czas**: 3h

## Całościowe metryki sukcesu zadania

1. **Reliability**: 99.9% uptime z auto-recovery
2. **Performance**: <100ms frame latency end-to-end
3. **Scalability**: Linear scaling do 8 kamer
4. **Observability**: Full tracing każdej klatki

## Deliverables

1. `services/rtsp-capture/` - Kompletny serwis
2. `tests/rtsp-capture/` - Testy jednostkowe i integracyjne
3. `docker/rtsp-capture/Dockerfile` - Optimized image
4. `docs/rtsp-capture-api.md` - API documentation
5. `monitoring/dashboards/rtsp-capture.json` - Grafana dashboard

## Narzędzia

- **Python 3.11+**: Główny język
- **OpenCV/PyAV**: Frame processing
- **asyncio**: Concurrent connections
- **Redis**: Frame queue
- **pytest**: Testing framework

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-frame-buffer-redis.md](./02-frame-buffer-redis.md)
