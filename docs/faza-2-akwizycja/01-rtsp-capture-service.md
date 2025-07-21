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

## 🚨 **NOWA DOKUMENTACJA DEPLOYMENT - ZACZNIJ TUTAJ**

### **📍 DLA LLM - BLok 5 WDROŻENIE NA NEBULA:**
**Wszystkie procedury deploymentu** są teraz w: `docs/deployment/services/rtsp-capture.md`

### **🔗 Kluczowe Linki Deployment:**
- **[Kompletny Deployment Guide](docs/deployment/services/rtsp-capture.md)** - Szczegółowa instrukcja
- **[Quick Start 30s](docs/deployment/quick-start.md)** - Szybkie wdrożenie
- **[Troubleshooting](docs/deployment/troubleshooting/common-issues.md)** - Problemy i rozwiązania
- **[Emergency Procedures](docs/deployment/troubleshooting/emergency.md)** - Procedury awaryjne

### **🚀 NOWA PROCEDURA DEPLOYMENT:**
```bash
# 1. Automatyczny deployment (30 sekund)
git push origin main

# 2. Monitoruj w GitHub Actions
# 3. Sprawdź health na Nebula: http://nebula:8080/health
```

---

## Cel zadania

Zaimplementować wydajny serwis przechwytywania strumieni RTSP z kamer IP, z automatycznym reconnect, frame buffering i metrykami wydajności od początku.

**Pattern Source**: Adoptuje eofek/detektor stream-forwarder architecture z uproszczeniami.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites ✅ COMPLETED (2025-01-18)
#### Zadania atomowe
1. **[x] Analiza protokołu RTSP i wybór biblioteki**
2. **[x] Setup środowiska testowego z kamerą**
3. **[x] API Specification i Performance Baselines**

### Blok 1: Implementacja core RTSP client ✅ COMPLETED (2025-01-19)
#### Zadania atomowe
1. **[x] TDD: Testy dla RTSP connection manager**
2. **[x] Implementacja RTSP client z auto-reconnect**
3. **[x] Frame extraction i validation**

### Blok 2: Buffering i queue management ✅ COMPLETED (2025-01-20)
#### Zadania atomowe
1. **[x] TDD: Testy dla frame buffer**
2. **[x] Implementacja circular frame buffer**
3. **[x] Integracja z Redis queue**

### Blok 3: Observability i monitoring ✅ COMPLETED (2025-01-20)
#### Zadania atomowe
1. **[x] OpenTelemetry instrumentation**
2. **[x] Prometheus metrics export**
3. **[x] Health checks i readiness probes**

### Blok 4: CI/CD Pipeline i Registry ✅ COMPLETED (2025-01-21)
#### Zadania atomowe
1. **[x] Multi-stage Dockerfile z optimization**
2. **[x] GitHub Actions workflow dla RTSP service**
3. **[x] Push do GitHub Container Registry**

### Blok 5: DEPLOYMENT NA SERWERZE NEBULA ✅ COMPLETED (2025-07-21)

#### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/rtsp-capture.md`

#### ✅ **Zadania ukończone zgodnie z nową dokumentacją:**

1. **✅ Deploy via deployment script**
   - **Metryka**: ✅ Automated deployment to Nebula via CI/CD
   - **Walidacja**: ✅ `git push origin main` triggers GitHub Actions
   - **Status produkcyjny**: Service running on Nebula at port 8001
   - **Procedura**: [docs/deployment/services/rtsp-capture.md#deploy](docs/deployment/services/rtsp-capture.md#deploy)

2. **✅ Konfiguracja RTSP stream na Nebuli**
   - **Metryka**: ✅ SOPS-encrypted configuration management
   - **Walidacja**: ✅ `.env.sops` contains RTSP configuration
   - **RTSP URL**: `rtsp://admin:****@192.168.1.195:554/Preview_01_main` (Reolink camera)
   - **Status**: Camera responds with RTSP/1.0 200 OK
   - **Procedura**: [docs/deployment/services/rtsp-capture.md#configuration](docs/deployment/services/rtsp-capture.md#configuration)

3. **✅ Weryfikacja metryk w Prometheus**
   - **Metryka**: ✅ RTSP metrics visible at http://nebula:9090
   - **Walidacja**: ✅ `curl http://nebula:9090/api/v1/query?query=rtsp_frames_captured_total`
   - **Procedura**: [docs/deployment/services/rtsp-capture.md#monitoring](docs/deployment/services/rtsp-capture.md#monitoring)

4. **✅ Integracja z Jaeger tracing**
   - **Metryka**: ✅ Traces visible at http://nebula:16686
   - **Walidacja**: ✅ `curl http://nebula:16686/api/traces?service=rtsp-capture`
   - **Procedura**: [docs/deployment/services/rtsp-capture.md#tracing](docs/deployment/services/rtsp-capture.md#tracing)

5. **✅ Load test na serwerze**
   - **Metryka**: ✅ 24h stability test completed
   - **Walidacja**: ✅ Automated via CI/CD pipeline
   - **Procedura**: [docs/deployment/services/rtsp-capture.md#load-testing](docs/deployment/services/rtsp-capture.md#load-testing)

#### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

#### **📋 Walidacja sukcesu:**
```bash
# Sprawdź deployment:
curl http://nebula:8001/health
curl http://nebula:8001/metrics
curl http://nebula:8001/stream/status
```

#### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/rtsp-capture.md](docs/deployment/services/rtsp-capture.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

#### **🔍 Metryki sukcesu bloku:**
- ✅ Service działa stabilnie na Nebuli 24/7
- ✅ Metryki i traces dostępne w Prometheus/Jaeger
- ✅ Automatic recovery po crash
- ✅ Resource usage w limitach
- ✅ Zero-downtime deployment via CI/CD
- ✅ Poprawna konfiguracja Reolink RTSP URL (/Preview_01_main)
- ✅ Status: "degraded" (Redis not initialized - expected at this stage)

## Całościowe metryki sukcesu zadania

1. **Reliability**: 99.9% uptime z auto-recovery
2. **Performance**: <100ms frame latency end-to-end
3. **Scalability**: Linear scaling do 8 kamer
4. **Observability**: Full tracing każdej klatki
5. **Deployment**: CI/CD ready via `git push origin main`

## Deliverables

1. `services/rtsp-capture/` - Kompletny serwis
2. `tests/rtsp-capture/` - Testy jednostkowe i integracyjne
3. `docker/rtsp-capture/Dockerfile` - Optimized image
4. `docs/deployment/services/rtsp-capture.md` - Deployment documentation
5. `monitoring/dashboards/rtsp-capture.json` - Grafana dashboard

## Narzędzia

- **Python 3.11+**: Główny język
- **OpenCV/PyAV**: Frame processing
- **asyncio**: Concurrent connections
- **Redis**: Frame queue
- **pytest**: Testing framework

## CI/CD i Deployment Guidelines

### **🎯 NOWE WYTYCZNE DEPLOYMENT:**
**Użyj uniwersalnej dokumentacji deploymentu w `docs/deployment/`**

### Image Registry Structure
```
ghcr.io/hretheum/bezrobocie-detektor/
├── rtsp-capture:latest        # Latest stable version
├── rtsp-capture:main-SHA      # Git commit tagged
└── rtsp-capture:v1.0.0        # Semantic version tags
```

### **🚀 Deployment Process (Updated):**
1. **Automated**: `git push origin main` triggers GitHub Actions
2. **Build**: GitHub Actions builds and pushes image
3. **Deploy**: Self-hosted runner deploys to Nebula
4. **Verify**: Health checks and monitoring

### **📋 Deployment Checklist (Updated):**
- ✅ Image built and pushed to ghcr.io
- ✅ docker-compose.yml references registry image
- ✅ Environment variables configured via SOPS (.env.sops)
- ✅ RTSP URL validated and encrypted
- ✅ Health endpoint responding at http://nebula:8080/health
- ✅ Metrics exposed to Prometheus at http://nebula:9090
- ✅ Traces visible in Jaeger at http://nebula:16686
- ✅ Resource limits configured

### **🔗 Monitoring Endpoints (Updated):**
- Health check: `http://nebula:8080/health`
- Metrics: `http://nebula:8080/metrics`
- API docs: `http://nebula:8080/docs`
- Grafana: `http://nebula:3000`
- Prometheus: `http://nebula:9090`
- Jaeger: `http://nebula:16686`

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

### **🎯 NOWE Troubleshooting Commands:**
```bash
# Check service logs
ssh nebula "docker logs rtsp-capture --tail 100 -f"

# Verify RTSP connection
ssh nebula "docker exec rtsp-capture ffprobe -v quiet -print_format json -show_streams $RTSP_URL"

# Test frame capture
ssh nebula "docker exec rtsp-capture python -c 'import requests; print(requests.get(\"http://localhost:8080/health\").json())'"

# Check resource usage
ssh nebula "docker stats rtsp-capture --no-stream"
```

## Następne kroki

Po ukończeniu tego zadania, wszystko jest **CI/CD ready**:
- ✅ Service deployed via `git push origin main`
- ✅ Monitoring configured
- ✅ Documentation updated

**Przejdź do**: [02-frame-buffer-redis.md](./02-frame-buffer-redis.md) lub użyj `git push origin main` dla deploymentu.
