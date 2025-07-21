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

### Blok 2: Buffering i queue management ✅ COMPLETED (2025-01-20)

#### Zadania atomowe

1. **[x] TDD: Testy dla frame buffer**
   - **Metryka**: ✅ Tests dla overflow, underflow, threading
   - **Walidacja**: ✅ `pytest tests/test_frame_buffer.py --cov` - 85% coverage
   - **Czas**: 2h ✅ Completed
   - **Implementacja**: `tests/test_frame_buffer.py`

2. **[x] Implementacja circular frame buffer**
   - **Metryka**: ✅ Zero-copy operations, thread-safe implementation
   - **Walidacja**: ✅ Performance tests pokazują <1ms na operację
   - **Czas**: 3h ✅ Completed
   - **Implementacja**: `src/frame_buffer.py`

3. **[x] Integracja z Redis queue**
   - **Metryka**: ✅ Synchronous Redis z fallback implementation
   - **Walidacja**: ✅ Redis integration tests przechodzą
   - **Czas**: 2h ✅ Completed
   - **Implementacja**: `src/redis_queue.py` (synchronous version)
   - **Uwaga**: Zmieniono na synchronous Redis z powodu kompatybilności

### Blok 3: Observability i monitoring ✅ COMPLETED (2025-01-20)

#### Zadania atomowe

1. **[x] OpenTelemetry instrumentation**
   - **Metryka**: ✅ Trace per frame, span per operation
   - **Walidacja**: ✅ Tracing w `TracedFrameBuffer` i `TracedRedisQueue`
   - **Czas**: 2h ✅ Completed
   - **Implementacja**: `src/observability.py`

2. **[x] Prometheus metrics export**
   - **Metryka**: ✅ FPS, latency, drops, reconnects metrics
   - **Walidacja**: ✅ `curl localhost:8001/metrics | grep rtsp_`
   - **Czas**: 1h ✅ Completed
   - **Metrics**: frame_counter, frame_processing_time, buffer_size, errors_total

3. **[x] Health checks i readiness probes**
   - **Metryka**: ✅ Accurate health status (healthy/degraded/unhealthy)
   - **Walidacja**: ✅ `/health`, `/ready`, `/metrics`, `/ping` endpoints działają
   - **Czas**: 1h ✅ Completed
   - **Implementacja**: `src/health.py` z FastAPI router

### Blok 4: CI/CD Pipeline i Registry ✅ COMPLETED (2025-01-21)

#### Zadania atomowe

1. **[x] Multi-stage Dockerfile z optimization**
   - **Metryka**: ✅ Image size 204MB (cel <100MB nieosiągalny dla Python z deps)
   - **Walidacja**: ✅ Multi-stage build z wheel compilation
     ```bash
     docker build -f services/rtsp-capture/Dockerfile -t rtsp-capture:test .
     docker images | grep rtsp-capture
     # rtsp-capture:optimized - 204MB
     ```
   - **Quality Gate**: ✅ Build time <2min
   - **Guardrails**: ✅ Non-root user, no secrets
   - **Czas**: 2h ✅ Completed
   - **Commit**: b6a0f37

2. **[x] GitHub Actions workflow dla RTSP service**
   - **Metryka**: ✅ Automated build/test/push na każdy commit
   - **Walidacja**: ✅ `.github/workflows/rtsp-capture-deploy.yml` utworzony
     ```bash
     cat .github/workflows/rtsp-capture-deploy.yml
     # Complete CI/CD pipeline with test, build, scan, deploy stages
     ```
   - **Quality Gate**: ✅ Tests, linting, security scan w workflow
   - **Guardrails**: ✅ Only builds from main branch
   - **Czas**: 1.5h ✅ Completed

3. **[x] Push do GitHub Container Registry**
   - **Metryka**: ✅ Workflow skonfigurowany dla ghcr.io
   - **Walidacja**: ✅ docker-compose.yml używa registry images
     ```yaml
     rtsp-capture:
       image: ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest
     ```
   - **Quality Gate**: ✅ Proper image tagging strategy
   - **Guardrails**: ✅ GitHub Actions permissions configured
   - **Czas**: 1h ✅ Completed

### Blok 5: DEPLOYMENT NA SERWERZE NEBULA ⚠️ KRYTYCZNE

#### Zadania atomowe

1. **[x] Update docker-compose.yml z registry image
   - **Metryka**: Service uses ghcr.io image, not local build
   - **Walidacja**:
     ```yaml
     # docker-compose.yml should contain:
     services:
       rtsp-capture:
         image: ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest
         ports:
           - "8001:8001"
     ```
   - **Quality Gate**: No build directives in compose
   - **Guardrails**: Environment variables from .env
   - **Czas**: 1h

2. **[ ] Deploy via deployment script**
   - **Metryka**: Automated deployment to Nebula
   - **Walidacja NA SERWERZE**:
     ```bash
     ./scripts/deploy-to-nebula.sh --service rtsp-capture
     # Deployment successful

     ssh nebula "docker ps | grep rtsp-capture"
     # STATUS: Up X minutes (healthy)
     ```
   - **Quality Gate**: Zero downtime deployment
   - **Guardrails**: Rollback on failure
   - **Czas**: 1h

3. **[ ] Konfiguracja RTSP stream na Nebuli**
   - **Metryka**: Real camera stream connected
   - **Walidacja NA SERWERZE**:
     ```bash
     # Set RTSP URL in environment
     ssh nebula "cd /opt/detektor && echo 'RTSP_URL=rtsp://camera_ip:554/stream' >> .env"

     # Restart service
     ssh nebula "cd /opt/detektor && docker-compose restart rtsp-capture"

     # Check logs
     ssh nebula "docker logs rtsp-capture -f"
     # "Successfully connected to RTSP stream"
     ```
   - **Quality Gate**: Stable connection >5min
   - **Guardrails**: Auto-reconnect on disconnect
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

## CI/CD i Deployment Guidelines

### Image Registry Structure
```
ghcr.io/hretheum/bezrobocie-detektor/
├── rtsp-capture:latest        # Latest stable version
├── rtsp-capture:main-SHA      # Git commit tagged
└── rtsp-capture:v1.0.0        # Semantic version tags
```

### Deployment Checklist
- [ ] Image built and pushed to ghcr.io
- [ ] docker-compose.yml references registry image
- [ ] Environment variables configured (.env)
- [ ] RTSP URL validated and accessible
- [ ] Health endpoint responding
- [ ] Metrics exposed to Prometheus
- [ ] Traces visible in Jaeger
- [ ] Resource limits configured

### Monitoring Endpoints
- Health check: `http://nebula:8001/health`
- Metrics: `http://nebula:8001/metrics`
- API docs: `http://nebula:8001/docs`

### Key Metrics to Monitor
```promql
# Frame capture rate
rate(rtsp_frames_captured_total[5m])

# Connection stability
rtsp_connection_status{camera_id="main"}

# Processing latency
histogram_quantile(0.99, rtsp_frame_processing_duration_seconds)

# Error rate
rate(rtsp_errors_total[5m])
```

### Troubleshooting Commands
```bash
# Check service logs
ssh nebula "docker logs rtsp-capture --tail 100 -f"

# Verify RTSP connection
ssh nebula "docker exec rtsp-capture ffprobe -v quiet -print_format json -show_streams $RTSP_URL"

# Test frame capture
ssh nebula "docker exec rtsp-capture python -m rtsp_capture.test_connection"

# Check resource usage
ssh nebula "docker stats rtsp-capture --no-stream"
```

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-frame-buffer-redis.md](./02-frame-buffer-redis.md)
