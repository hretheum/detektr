# Faza 3 / Zadanie 1: Face recognition service z metrykami i tracingiem

<!--
LLM TASK CONTEXT:
To zadanie z Fazy 3 (AI Services).
Prerequisites: Docker, GPU support, observability stack, message queue
Tech stack: Python, PyTorch/TensorFlow, FastAPI, OpenTelemetry

EXECUTION WORKFLOW:
1. Start z Blok 0 (Prerequisites)
2. Research PRZED implementacją (Blok 1)
3. TDD approach (testy przed kodem)
4. Observability od początku (nie dodawać później)
5. Containerization na końcu

USE COMMAND: /nakurwiaj 1 (dla Bloku 1), etc.
-->

## Cel zadania

Zaimplementować wydajny serwis rozpoznawania twarzy wykorzystujący GPU, z pełnym observability (metryki, tracing) i accuracy >95% na test dataset.

## Dekompozycja na bloki zadań

### Blok 1: Research i wybór modelu AI

#### Zadania atomowe

1. **[ ] Benchmark 3 modeli face recognition**
   - **Metryka**: Porównanie FaceNet vs InsightFace vs DeepFace
   - **Walidacja**: Tabela z mAP, FPS, VRAM usage
   - **Czas**: 4h

2. **[ ] Przygotowanie test dataset**
   - **Metryka**: 1000+ twarzy, 20+ osób, różne warunki
   - **Walidacja**: `python validate_dataset.py --min-samples=50`
   - **Czas**: 3h

3. **[ ] Wybór finalnego modelu i wag**
   - **Metryka**: Model z best accuracy/performance ratio
   - **Walidacja**: Decyzja udokumentowana w ADR (Architecture Decision Record)
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Model wybrany na podstawie danych
- Test dataset reprezentatywny
- Trade-offs udokumentowane

### Blok 2: Implementacja serwisu z Clean Architecture

#### Zadania atomowe

1. **[ ] Setup project structure (domain/infra/app)**
   - **Metryka**: Struktura zgodna z hexagonal architecture
   - **Walidacja**:

     ```bash
     tree services/face-recognition -d -L 2
     # domain/, infrastructure/, application/ visible
     ```

   - **Czas**: 1h

2. **[ ] Implementacja domain layer (entities, use cases)**
   - **Metryka**: Pure Python, zero dependencies
   - **Walidacja**: `pytest tests/unit/domain --no-deps-check`
   - **Czas**: 4h

3. **[ ] Implementacja infrastructure (model loader, GPU)**
   - **Metryka**: Model ładuje się <5s, inference <100ms
   - **Walidacja**:

     ```python
     # Benchmark script
     times = benchmark_inference(n=100)
     assert np.percentile(times, 95) < 0.1  # 100ms
     ```

   - **Czas**: 6h

4. **[ ] Integracja z ProcessorClient pattern**
   - **Metryka**: Service dziedziczy z ProcessorClient, nie używa polling
   - **Walidacja**:
     ```python
     # services/face-recognition/src/main.py
     from services.frame_buffer_v2.src.processors.client import ProcessorClient

     class FaceRecognitionProcessor(ProcessorClient):
         def __init__(self):
             super().__init__(
                 processor_id="face-recognition-1",
                 capabilities=["face_detection", "face_recognition"],
                 orchestrator_url=os.getenv("ORCHESTRATOR_URL"),
                 capacity=10,
                 result_stream="faces:detected"
             )

         async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Dict:
             # Twoja logika przetwarzania
             pass
     ```
   - **Czas**: 3h

5. **[ ] Health endpoint i monitoring API**
   - **Metryka**: /health endpoint, metrics endpoint
   - **Walidacja**: `curl localhost:8003/health` zwraca status procesora
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Clean separation of concerns
- 100% unit test coverage dla domain
- API responds <200ms e2e

### Blok 3: Observability implementation

#### Zadania atomowe

1. **[ ] Integracja OpenTelemetry tracing**
   - **Metryka**: Every request ma trace z spans
   - **Walidacja**:

     ```python
     # Check trace
     trace = get_trace_by_id(request_id)
     assert len(trace.spans) >= 5  # intake->validate->inference->encode->response
     ```

   - **Czas**: 3h

2. **[ ] Implementacja Prometheus metrics**
   - **Metryka**: Request rate, latency, GPU util, accuracy
   - **Walidacja**:

     ```bash
     curl localhost:8002/metrics | grep -E "(face_recognition_requests_total|gpu_utilization)"
     ```

   - **Czas**: 2h

3. **[ ] Custom GPU metrics collector**
   - **Metryka**: VRAM usage, GPU temp, utilization %
   - **Walidacja**: `nvidia-ml-py` integration working
   - **Czas**: 2h

4. **[ ] Grafana dashboard dla serwisu**
   - **Metryka**: Real-time view wszystkich metryk
   - **Walidacja**: Import JSON, all panels show data
   - **Czas**: 2h

#### Metryki sukcesu bloku

- 100% requests traced
- Metrics scraping co 15s
- Dashboard shows real-time data

### Blok 4: Testing i optymalizacja

#### Zadania atomowe

1. **[ ] Unit tests z >80% coverage**
   - **Metryka**: Coverage report, all edge cases
   - **Walidacja**: `pytest --cov=face_recognition --cov-report=term-missing`
   - **Czas**: 4h

2. **[ ] Integration tests z test containers**
   - **Metryka**: Testy z prawdziwym modelem
   - **Walidacja**: `pytest tests/integration -v`
   - **Czas**: 3h

3. **[ ] Load testing i profiling**
   - **Metryka**: 50+ req/s, latency <100ms p95
   - **Walidacja**:

     ```bash
     locust -f tests/load/face_recognition.py --users 100 --spawn-rate 10
     ```

   - **Czas**: 3h

4. **[ ] GPU memory optimization**
   - **Metryka**: Batch processing, <4GB VRAM
   - **Walidacja**: Run 10 min pod load, check `nvidia-smi`
   - **Czas**: 4h

#### Metryki sukcesu bloku

- All tests green
- Performance targets met
- No memory leaks

### Blok 5: Containerization i deployment

#### Zadania atomowe

1. **[ ] Multi-stage Dockerfile z GPU support**
   - **Metryka**: Image <2GB, secure, optimized
   - **Walidacja**:

     ```bash
     docker build -t face-recognition:latest .
     dive face-recognition:latest  # check layers
     ```

   - **Czas**: 2h

2. **[ ] Docker Compose integration z ProcessorClient**
   - **Metryka**: Service starts with orchestrator configuration
   - **Walidacja**:
     ```yaml
     # docker-compose.yml
     face-recognition:
       environment:
         - ORCHESTRATOR_URL=http://frame-buffer-v2:8002
         - PROCESSOR_ID=face-recognition-1
         - REDIS_HOST=redis
       depends_on:
         frame-buffer-v2:
           condition: service_healthy
     ```
   - **Czas**: 1h

3. **[ ] Health checks i readiness probes**
   - **Metryka**: Proper startup/shutdown, graceful
   - **Walidacja**: Kill container, check no lost requests
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Container starts <30s
- Graceful shutdown
- Auto-restart on failure

## Całościowe metryki sukcesu zadania

1. **Accuracy**: >95% mAP na test set
2. **Performance**: <100ms inference p95
3. **Reliability**: 99.9% uptime pod load
4. **Observability**: 100% traced requests

## Deliverables

1. `/services/face-recognition/` - Kompletny serwis
2. `/services/face-recognition/Dockerfile` - GPU-enabled image
3. `/dashboards/face-recognition.json` - Grafana dashboard
4. `/tests/integration/test_face_recognition.py` - Test suite
5. `/docs/api/face-recognition-api.md` - API docs

## Narzędzia

- **PyTorch/TensorFlow**: Deep learning framework
- **FastAPI**: REST API framework
- **OpenTelemetry**: Tracing
- **Prometheus client**: Metrics
- **pytest**: Testing
- **locust**: Load testing

## Zależności

- **Wymaga**:
  - Docker z GPU support (Faza 1)
  - Observability stack (Faza 1)
  - Frame-buffer-v2 z ProcessorClient (Faza 2)
  - Redis dla queue management
- **Blokuje**: Gesture detection, full pipeline testing
- **Nowy pattern**: Używa ProcessorClient zamiast polling - zobacz [Processor Client Migration Guide](../processor-client-migration-guide.md)

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja |
|--------|-------------------|-------|-----------|
| Model accuracy <95% | Średnie | Wysoki | Multiple models, ensemble option |
| GPU OOM | Średnie | Wysoki | Batch size tuning, memory monitoring |
| Latency spikes | Niskie | Średni | Request queuing, timeout handling |

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DEPLOYMENT**

**WAŻNE**: Ten serwis musi być dodany do workflow matrix w `.github/workflows/deploy-self-hosted.yml`

**Procedury deploymentu**: Zobacz [docs/deployment/README.md](../../deployment/README.md) dla pełnego przewodnika.
**Quick reference**: [docs/deployment/guides/new-service.md](../../deployment/guides/new-service.md)

### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/face-recognition.md#deploy](docs/deployment/services/face-recognition.md#deploy)

2. **[ ] Konfiguracja GPU na Nebuli**
   - **Metryka**: Service has GPU access in container
   - **Walidacja**: `docker exec face-recognition nvidia-smi`
   - **Procedura**: [docs/deployment/services/face-recognition.md#gpu-configuration](docs/deployment/services/face-recognition.md#gpu-configuration)

3. **[ ] Weryfikacja metryk w Prometheus**
   - **Metryka**: Face detection metrics visible at http://nebula:9090
   - **Walidacja**: `curl http://nebula:9090/api/v1/query?query=face_detections_total`
   - **Procedura**: [docs/deployment/services/face-recognition.md#monitoring](docs/deployment/services/face-recognition.md#monitoring)

4. **[ ] Integracja z Jaeger tracing**
   - **Metryka**: Traces visible at http://nebula:16686
   - **Walidacja**: `curl http://nebula:16686/api/traces?service=face-recognition`
   - **Procedura**: [docs/deployment/services/face-recognition.md#tracing](docs/deployment/services/face-recognition.md#tracing)

5. **[ ] Performance test na produkcji**
   - **Metryka**: <100ms inference p95 on Nebula GPU
   - **Walidacja**: Load test via CI/CD pipeline
   - **Procedura**: [docs/deployment/services/face-recognition.md#performance-testing](docs/deployment/services/face-recognition.md#performance-testing)

### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

### **📋 Walidacja sukcesu:**
```bash
# Sprawdź deployment:
curl http://nebula:8002/health
curl http://nebula:8002/metrics

# Test GPU:
ssh nebula "docker exec face-recognition nvidia-smi"

# Test inference:
curl -X POST http://nebula:8002/detect -F "image=@test_face.jpg"
```

### **🔗 Linki do procedur:**
- **Główny przewodnik**: [docs/deployment/README.md](../../deployment/README.md)
- **Dodawanie serwisu**: [docs/deployment/guides/new-service.md](../../deployment/guides/new-service.md)
- **Troubleshooting**: [docs/deployment/guides/troubleshooting.md](../../deployment/guides/troubleshooting.md)
- **Workflow config**: [.github/workflows/deploy-self-hosted.yml](../../.github/workflows/deploy-self-hosted.yml)

### **🔍 Metryki sukcesu bloku:**
- ✅ Service running on Nebula with GPU access
- ✅ >95% accuracy on test dataset
- ✅ <100ms inference p95
- ✅ Metrics and traces in monitoring stack
- ✅ Grafana dashboard operational
- ✅ Zero-downtime deployment via CI/CD

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-object-detection.md](./02-object-detection.md)
