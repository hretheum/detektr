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

### Blok 1: Implementacja core RTSP client ✅ COMPLETED (2025-01-19)

#### Zadania atomowe

1. **[x] TDD: Testy dla RTSP connection manager**
   - **Metryka**: ✅ 80% coverage dla connection logic
   - **Walidacja**: ✅ `pytest tests/test_rtsp_connection.py -v` - 12 testów przechodzi
   - **Czas**: 2h ✅ Completed
   - **Commit**: e88f610

2. **[x] Implementacja RTSP client z auto-reconnect**
   - **Metryka**: ✅ Reconnect w 5s (domyślnie)
   - **Walidacja**: ✅ Test auto-reconnect przechodzi
   - **Czas**: 3h ✅ Completed
   - **Implementacja**: `src/rtsp_connection.py`

3. **[x] Frame extraction i validation**
   - **Metryka**: ✅ 0% corrupted frames - walidacja black frames
   - **Walidacja**: ✅ Frame validation w `src/frame_extractor.py`
   - **Czas**: 2h ✅ Completed
   - **Coverage**: 73% dla frame extractor

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

### Blok 5: DEPLOYMENT NA SERWERZE NEBULA ⚠️ KRYTYCZNE

#### Zadania atomowe

1. **[ ] Utworzenie production-ready Dockerfile**
   - **Metryka**: Multi-stage build, final image <150MB
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "docker images | grep rtsp-capture"
     # rtsp-capture:latest <150MB
     ```
   - **Quality Gate**: Image security scan pass (trivy)
   - **Guardrails**: No secrets in image, non-root user
   - **Czas**: 2h

2. **[ ] Integracja z głównym docker-compose.yml**
   - **Metryka**: Service zdefiniowany w docker-compose.yml
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "cd /path/to/detektor && docker-compose config | grep rtsp-capture"
     # Shows service definition
     ```
   - **Quality Gate**: Health check defined, restart policy
   - **Guardrails**: Resource limits set (CPU/memory)
   - **Czas**: 1h

3. **[ ] Uruchomienie kontenera na Nebuli**
   - **Metryka**: Container running i healthy
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "docker ps | grep rtsp-capture"
     # STATUS: Up X minutes (healthy)
     ```
   - **Quality Gate**: Health endpoint returns 200
   - **Guardrails**: Auto-restart on failure
   - **Czas**: 1h

4. **[ ] Weryfikacja metryk w Prometheus**
   - **Metryka**: RTSP metrics visible in Prometheus
   - **Walidacja NA SERWERZE**:
     ```bash
     curl http://nebula:9090/api/v1/query?query=rtsp_frames_captured_total
     # Returns data points
     ```
   - **Quality Gate**: All key metrics exported
   - **Guardrails**: No metric gaps >1min
   - **Czas**: 1h

5. **[ ] Integracja z Jaeger tracing**
   - **Metryka**: Traces visible for each frame
   - **Walidacja NA SERWERZE**:
     ```bash
     curl http://nebula:16686/api/traces?service=rtsp-capture
     # Returns trace data
     ```
   - **Quality Gate**: <1% traces dropped
   - **Guardrails**: Trace context propagated
   - **Czas**: 2h

6. **[ ] Load test na serwerze**
   - **Metryka**: Handle real RTSP stream 24h
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "docker stats rtsp-capture --no-stream"
     # CPU <50%, MEM <500MB after 24h
     ```
   - **Quality Gate**: 0% frame loss, stable memory
   - **Guardrails**: Alerts on high CPU/memory
   - **Czas**: 24h

#### Metryki sukcesu bloku
- Service działa stabilnie na Nebuli 24/7
- Metryki i traces dostępne w Prometheus/Jaeger
- Automatic recovery po crash
- Resource usage w limitach

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
