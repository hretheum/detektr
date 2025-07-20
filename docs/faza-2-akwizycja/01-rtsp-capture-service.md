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

### Blok 4: CI/CD Pipeline i Registry

#### Zadania atomowe

1. **[ ] Multi-stage Dockerfile z optimization**
   - **Metryka**: Image size <100MB, secure base image
   - **Walidacja**:
     ```bash
     docker build -f services/rtsp-capture/Dockerfile -t rtsp-capture:test .
     docker images | grep rtsp-capture
     # Size <100MB
     trivy image rtsp-capture:test
     # No HIGH/CRITICAL vulnerabilities
     ```
   - **Quality Gate**: Build time <3min
   - **Guardrails**: No build secrets exposed
   - **Czas**: 2h

2. **[ ] GitHub Actions workflow dla RTSP service**
   - **Metryka**: Automated build/test/push na każdy commit
   - **Walidacja**:
     ```bash
     cat .github/workflows/rtsp-capture-deploy.yml
     git push origin main
     # Check: https://github.com/hretheum/bezrobocie/actions
     ```
   - **Quality Gate**: All tests pass in CI
   - **Guardrails**: Only builds from main branch
   - **Czas**: 1.5h

3. **[ ] Push do GitHub Container Registry**
   - **Metryka**: Image available at ghcr.io
   - **Walidacja**:
     ```bash
     docker pull ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest
     # Successfully pulled
     ```
   - **Quality Gate**: Image tagged properly
   - **Guardrails**: Registry credentials secure
   - **Czas**: 1h

### Blok 5: DEPLOYMENT NA SERWERZE NEBULA ⚠️ KRYTYCZNE

#### Zadania atomowe

1. **[ ] Update docker-compose.yml z registry image**
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
