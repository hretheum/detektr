# System Detekcji i Automatyzacji Wizyjnej

<!-- 
LLM CONTEXT PROMPT:
To jest główny dokument architektury systemu detekcji wizyjnej.
Projekt: Hobbystyczny system rozpoznawania obrazu z kamery IP + automatyzacja Home Assistant
Stack: Docker, Python, GPU (GTX 4070 Super), observability-first approach
Fazy: 0-6, każda z zadaniami zdekomponowanymi na bloki i zadania atomowe

INSPIRACJE: Bazujemy na proven patterns z eofek/detektor (docs/analysis/eofek-detektor-analysis.md):
- Source: https://github.com/eofek/detektor (repozytorium autorskie - kod dostępny)
- Metrics architecture pattern z abstraction layer
- Event-driven communication przez Redis Streams  
- GPU monitoring patterns
- Error handling (Circuit Breaker, Adaptive Backoff)
- Ale UNIKAMY: over-engineering, microservices complexity, external lock-in

Gdy rozpoczynasz pracę w dowolnym punkcie projektu:
1. Sprawdź w której fazie jesteśmy (zobacz sekcję 2)
2. Każde zadanie ma link do szczegółowej dekompozycji
3. Stosuj TDD, Clean Architecture, observability od początku
4. Używaj CLAUDE.md dla zasad projektu
5. Implementuj patterns z eofek/detektor analysis gdzie wskazane
-->

## 1. Architektura Rozwiązania

### 1.1 Przegląd Systemu

System składa się z następujących głównych komponentów:

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   Kamera IP    │────▶│   Serwer Ubuntu      │────▶│ Home Assistant  │
│   (PoE)        │     │   GTX 4070 Super     │     │   (Ubuntu)      │
└─────────────────┘     │   i7 + 64GB RAM      │     └─────────────────┘
                        └──────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │   Usługi Chmurowe    │
                        │   (LLM API)          │
                        └──────────────────────┘
```

### 1.2 Komponenty Systemu

#### 1.2.1 Warstwa Akwizycji Obrazu
- **RTSP Stream Capture Service**: Kontener odbierający strumień z kamery IP
- **Frame Buffer**: Redis/RabbitMQ do kolejkowania klatek do przetwarzania
- **Metadata Store**: PostgreSQL/TimescaleDB do przechowywania metadanych klatek

#### 1.2.2 Warstwa Przetwarzania AI
- **Face Recognition Service**: MediaPipe Face Detection + InsightFace embeddings (proven pattern z eofek/detektor)
- **Object Detection Service**: YOLO v8 (rozszerzenie względem eofek/detektor)
- **Gesture Detection Service**: MediaPipe Hands + custom gesture recognition
- **Voice Processing Service**: Whisper (STT) + TTS

#### 1.2.3 Warstwa Integracji
- **Event Bus**: Redis Streams z event acknowledgement (pattern z eofek/detektor)
- **Intent Recognition Service**: Połączenie z LLM (OpenAI/Anthropic)
- **Home Assistant Bridge**: MQTT/REST API (rozszerzenie - czego brakuje w eofek/detektor)
- **Metrics Adapter**: Abstraction layer dla Prometheus (adoptowane z eofek/detektor)

#### 1.2.4 Warstwa Observability
- **Distributed Tracing**: Jaeger
- **Metrics**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Frame Tracking**: Custom tracking ID dla każdej klatki

### 1.3 Architektura Kontenerowa

```yaml
# docker-compose.yml (uproszczony schemat)
version: '3.8'

services:
  # Akwizycja
  rtsp-capture:
    build: ./services/rtsp-capture
    environment:
      - CAMERA_IP=${CAMERA_IP}
      - FRAME_RATE=10
    volumes:
      - frame-storage:/data/frames
    
  # Kolejka
  redis:
    image: redis:alpine
    
  # Baza danych
  postgres:
    image: timescale/timescaledb:latest-pg15
    
  # AI Services
  face-recognition:
    build: ./services/face-recognition
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      
  gesture-detection:
    build: ./services/gesture-detection
    runtime: nvidia
    
  # Integracja
  mqtt-broker:
    image: eclipse-mosquitto
    
  # Observability
  jaeger:
    image: jaegertracing/all-in-one
    
  prometheus:
    image: prom/prometheus
    
  grafana:
    image: grafana/grafana
```

### 1.4 Flow Danych

1. **Capture**: Kamera IP → RTSP Service → Frame Buffer
2. **Process**: Frame Buffer → AI Services → Event Bus
3. **Analyze**: Event Bus → Intent Recognition → Action Queue
4. **Execute**: Action Queue → HA Bridge → Home Assistant
5. **Monitor**: Każdy krok → Jaeger/Prometheus → Dashboards

#### Observability First Approach

Każdy nowy serwis implementowany jest według wzorca:

```python
# base_service.py - szablon dla każdego serwisu
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.logging import LoggingInstrumentor

class BaseService:
    def __init__(self, service_name: str):
        self.tracer = trace.get_tracer(service_name)
        self.meter = metrics.get_meter(service_name)
        self.logger = self._setup_logging(service_name)
        
        # Automatyczne metryki
        self.request_counter = self.meter.create_counter(
            f"{service_name}_requests_total"
        )
        self.latency_histogram = self.meter.create_histogram(
            f"{service_name}_latency_seconds"
        )
        
    @traced  # Decorator automatycznie dodający span
    async def process_frame(self, frame_id: str):
        # Logika przetwarzania z automatycznym tracingiem
        pass
```

### 1.5 Tracking Klatek

Każda klatka otrzymuje unikalny UUID przy wejściu do systemu:
```
frame_id: {timestamp}_{camera_id}_{sequence_number}
```

Metadane klatki:
- Timestamp akwizycji
- Status przetwarzania
- Wykryte obiekty/twarze/gesty
- Podjęte akcje
- Czas przetwarzania na każdym etapie

## 2. Etapy Realizacji Projektu

<!-- 
LLM NAVIGATION PROMPT:
Każda faza ma zadania z linkami do dekompozycji.
Status projektu sprawdź w:
- [ ] checkbox = zadanie do zrobienia
- [x] checkbox = zadanie ukończone

Workflow dla nowego zadania:
1. Otwórz link "Szczegóły →" przy zadaniu
2. Użyj komendy /nakurwiaj <numer_bloku> do automatycznego wykonania
3. Po każdym bloku zadań: walidacja, code review, git commit

WAŻNE: Zawsze zaczynaj od Bloku 0 (Prerequisites) w każdym zadaniu!
-->

### Faza 0: Dokumentacja i Planowanie (1-2 tygodnie)

#### Zadania i Metryki

1. **[x] Analiza i dokumentacja wymagań**
   - **Metryki**:
     - 100% wymagań funkcjonalnych z ID i priorytetem
     - 100% wymagań niefunkcjonalnych zmapowanych
     - Macierz śledzenia wymagań utworzona
   - **Walidacja**:
     ```bash
     # Sprawdzenie kompletności
     grep -c "^- \*\*RF[0-9]\{3\}" docs/requirements/functional-requirements.md
     # Powinno zwrócić ≥20
     ```
   - **Sukces**: Wszystkie stakeholders zaakceptowali wymagania
   - **[Szczegóły →](docs/faza-0-dokumentacja/01-analiza-wymagan.md)**

2. **[x] Utworzenie struktury projektu i repozytorium**
   - **Metryki**:
     - Struktura katalogów zgodna z Clean Architecture
     - CI/CD pipeline skonfigurowany
     - Pre-commit hooks działają
   - **Walidacja**:
     ```bash
     pre-commit run --all-files
     gh workflow list
     ```
   - **Sukces**: Pierwszy commit przechodzi przez CI
   - **[Szczegóły →](docs/faza-0-dokumentacja/02-struktura-projektu.md)**

3. **[x] Dekompozycja wszystkich zadań projektowych**
   - **Metryki**:
     - 100% zadań z faz 1-6 zdekomponowanych
     - Każde zadanie ma 3-7 zadań atomowych
     - Wszystkie mają metryki i walidację
   - **Walidacja**:
     ```bash
     find docs/faza-* -name "*.md" | wc -l
     # Powinno zwrócić ≥40 plików
     ```
   - **Sukces**: Każde zadanie ma dokument z dekompozycją
   - **[Szczegóły →](docs/faza-0-dokumentacja/03-dekompozycja-zadan.md)**

4. **[x] Przygotowanie środowiska developerskiego**
   - **Metryki**:
     - Dev containers działają na Mac OS
     - Remote development przez SSH działa
     - GPU forwarding skonfigurowany
   - **Walidacja**:
     ```bash
     docker run --rm hello-world
     ssh ubuntu-server "nvidia-smi"
     ```
   - **Sukces**: Można developować z Mac'a na Ubuntu
   - **[Szczegóły →](docs/faza-0-dokumentacja/04-srodowisko-dev.md)**

5. **[x] Szablon dokumentacji technicznej**
   - **Metryki**:
     - Templates dla: API, Architecture, Runbook
     - Style guide utworzony
     - Automated docs generation działa
   - **Walidacja**:
     ```bash
     mkdocs build
     vale docs/ # linter dokumentacji
     ```
   - **Sukces**: Dokumentacja generuje się automatycznie
   - **[Szczegóły →](docs/faza-0-dokumentacja/05-szablon-dokumentacji.md)**

### Faza 1: Fundament z Observability (2-3 tygodnie)

#### Zadania i Metryki

1. **[x] Konfiguracja środowiska Docker na serwerze Ubuntu**
   - **Metryka**: Docker daemon działa, docker-compose v2.20+
   - **Walidacja**: `docker run hello-world && docker compose version`
   - **Sukces**: Zwraca wersję ≥ 2.20, hello-world działa
   - **[Szczegóły →](docs/faza-1-fundament/01-konfiguracja-docker.md)**

2. **Instalacja NVIDIA Container Toolkit**
   - **Metryka**: GPU dostępne w kontenerach
   - **Walidacja**: `docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi`
   - **Sukces**: Pokazuje GTX 4070 Super, CUDA 12.0+
   - **[Szczegóły →](docs/faza-1-fundament/02-nvidia-toolkit.md)**

3. **Setup repozytorium Git z podstawową strukturą**
   - **Metryka**: Struktura katalogów zgodna z Clean Architecture
   - **Walidacja**: `tree -d -L 3` pokazuje wymaganą strukturę
   - **Sukces**: Istnieją: services/, docs/, tests/, .github/
   - **[Szczegóły →](docs/faza-1-fundament/03-git-repository-setup.md)**

4. **Deploy stack observability: Jaeger, Prometheus, Grafana, Loki**
   - **Metryki**: 
     - Jaeger UI: http://localhost:16686
     - Prometheus: http://localhost:9090
     - Grafana: http://localhost:3000
     - Loki query: `{job="detektor"}`
   - **Walidacja**: `curl -s http://localhost:9090/-/healthy | grep "Prometheus Server is Healthy"`
   - **Sukces**: Wszystkie 4 UI dostępne, health check OK
   - **[Szczegóły →](docs/faza-1-fundament/04-observability-stack.md)**

5. **Konfiguracja OpenTelemetry SDK**
   - **Metryka**: Traces widoczne w Jaeger z example service
   - **Walidacja**: Run example service, sprawdź trace w Jaeger UI
   - **Sukces**: Trace zawiera: service name, span duration, attributes
   - **[Szczegóły →](docs/faza-1-fundament/05-opentelemetry-config.md)**

6. **Podstawowe dashboardy i alerty**
   - **Metryka**: 3 dashboardy (System, Docker, Custom)
   - **Walidacja**: Import dashboards, test alert firing
   - **Sukces**: Dashboardy pokazują dane, test alert dociera na Slack/email
   - **[Szczegóły →](docs/faza-1-fundament/06-dashboards-alerts.md)**

7. **Szablon bazowy dla nowych serwisów z wbudowanym tracingiem**
   - **Metryka**: BaseService z auto-instrumentation
   - **Walidacja**: `pytest tests/test_base_service.py -v`
   - **Sukces**: 100% testów przechodzi, trace span automatycznie tworzony
   - **[Szczegóły →](docs/faza-1-fundament/07-base-service-template.md)**

### Faza 2: Akwizycja i Storage z pełnym monitoringiem (2-3 tygodnie)

#### Zadania i Metryki

1. **Implementacja RTSP capture service z OpenTelemetry**
   - **Metryki**: 
     - FPS capture rate: 10-30 fps
     - Frame loss: <0.1%
     - Latency: <50ms
   - **Walidacja**: 
     ```bash
     curl http://localhost:8001/metrics | grep rtsp_frames_captured_total
     # Trace w Jaeger: service="rtsp-capture" operation="capture_frame"
     ```
   - **Sukces**: Stable 10+ FPS, traces pokazują każdą klatkę
   - **[Szczegóły →](docs/faza-2-akwizycja/01-rtsp-capture-service.md)**

2. **Konfiguracja Redis/RabbitMQ z metrykami Prometheus**
   - **Metryki**:
     - Queue depth: <1000 frames
     - Message throughput: >100 msg/s
     - Redis memory: <2GB
   - **Walidacja**:
     ```bash
     redis-cli INFO stats | grep instantaneous_ops_per_sec
     curl http://localhost:15692/metrics | grep rabbitmq_queue_messages
     ```
   - **Sukces**: Prometheus scrape działa, metryki widoczne
   - **[Szczegóły →](docs/faza-2-akwizycja/02-redis-rabbitmq-config.md)**

3. **Setup PostgreSQL/TimescaleDB z monitoringiem**
   - **Metryki**:
     - Connection pool: <80% utilized
     - Query latency p99: <100ms
     - Hypertable compression: >10:1
   - **Walidacja**:
     ```sql
     SELECT * FROM timescaledb_information.hypertables;
     SELECT * FROM pg_stat_activity WHERE state = 'active';
     ```
   - **Sukces**: Hypertable utworzona, continuous aggregates działają
   - **[Szczegóły →](docs/faza-2-akwizycja/03-postgresql-timescale.md)**

4. **Frame tracking z distributed tracing od wejścia**
   - **Metryka**: Każda klatka ma trace_id i span przez cały pipeline
   - **Walidacja**:
     ```python
     # Test script sprawdzający frame metadata
     assert frame.trace_id is not None
     assert len(frame.processing_spans) > 0
     ```
   - **Sukces**: 100% klatek ma kompletny trace
   - **[Szczegóły →](docs/faza-2-akwizycja/04-frame-tracking.md)**

5. **Dashboard: Frame Pipeline Overview**
   - **Metryki na dashboardzie**:
     - Frames per second (live)
     - Processing latency histogram
     - Queue depths
     - Error rate
   - **Walidacja**: Import dashboard JSON do Grafana
   - **Sukces**: Wszystkie panele pokazują dane real-time
   - **[Szczegóły →](docs/faza-2-akwizycja/05-dashboard-frame-pipeline.md)**

6. **Alerty: frame drop, latency, queue size**
   - **Alerty**:
     - Frame drop rate > 1%
     - Processing latency p95 > 200ms
     - Queue size > 5000
   - **Walidacja**: Trigger test conditions, check alert manager
   - **Sukces**: Alerty firing w <1 min od warunku
   - **[Szczegóły →](docs/faza-2-akwizycja/06-alerts-configuration.md)**

### Faza 3: AI Services - Podstawy (3-4 tygodnie)

#### Zadania i Metryki

1. **Face recognition service z metrykami i tracingiem**
   - **Metryki**:
     - Accuracy: >95% na test dataset
     - Inference time: <100ms/frame
     - GPU utilization: 40-80%
   - **Walidacja**:
     ```bash
     pytest tests/test_face_recognition.py --benchmark
     nvidia-smi dmon -s um -i 0 # GPU monitoring
     ```
   - **Sukces**: mAP >0.95, p99 latency <100ms
   - **[Szczegóły →](docs/faza-3-ai-services/01-face-recognition-service.md)**

2. **Object detection z metrykami GPU i tracingiem**
   - **Metryki**:
     - YOLO v8 mAP: >0.85
     - FPS: >10 na 1080p
     - Memory usage: <4GB VRAM
   - **Walidacja**:
     ```python
     # Benchmark script
     results = model.val(data='test_dataset.yaml')
     print(f"mAP: {results.box.map}")
     ```
   - **Sukces**: Detects persons, animals, vehicles reliably
   - **[Szczegóły →](docs/faza-3-ai-services/02-object-detection.md)**

3. **Event bus (Kafka/NATS) z pełnym monitoringiem**
   - **Metryki**:
     - Message throughput: >1000 msg/s
     - Latency p99: <10ms
     - Partition lag: <100
   - **Walidacja**:
     ```bash
     kafka-run-class kafka.tools.ConsumerOffsetChecker
     nats-top -s localhost:8222
     ```
   - **Sukces**: Zero message loss pod load testem
   - **[Szczegóły →](docs/faza-3-ai-services/03-event-bus-setup.md)**

4. **Dashboard: AI Processing Performance**
   - **Panele**:
     - GPU utilization over time
     - Model inference latency
     - Detection confidence distribution
     - Errors by type
   - **Walidacja**: Grafana dashboard z przykładowymi danymi
   - **Sukces**: Real-time GPU metrics, heatmap latency
   - **[Szczegóły →](docs/faza-3-ai-services/04-dashboard-ai-performance.md)**

5. **Trace: pełny flow od klatki do wyniku AI**
   - **Metryka**: End-to-end trace pokazuje wszystkie kroki
   - **Walidacja**:
     ```
     Jaeger: frame_capture → queue → ai_inference → result_publish
     Each span has: duration, GPU metrics, result count
     ```
   - **Sukces**: <5% traces z missing spans
   - **[Szczegóły →](docs/faza-3-ai-services/05-end-to-end-tracing.md)**

6. **Testy wydajnościowe z analizą w Grafanie**
   - **Metryki**:
     - Throughput: >10 FPS sustained
     - Resource usage stable over 1h
     - No memory leaks
   - **Walidacja**: Run locust/k6 load test for 1 hour
   - **Sukces**: Performance report w Grafana, no degradation
   - **[Szczegóły →](docs/faza-3-ai-services/06-performance-testing.md)**

### Faza 4: Integracja z Home Assistant (2 tygodnie)

#### Zadania i Metryki

1. **MQTT bridge z metrykami publikacji/subskrypcji**
   - **Metryki**:
     - Message delivery rate: >99.9%
     - Publish latency: <50ms
     - Active subscriptions: correct count
   - **Walidacja**:
     ```bash
     mosquitto_sub -h localhost -t "detektor/#" -v
     curl http://localhost:9090/metrics | grep mqtt_messages_published_total
     ```
   - **Sukces**: Wszystkie eventy docierają do HA
   - **[Szczegóły →](docs/faza-4-integracja/01-mqtt-bridge.md)**

2. **HA Bridge service z tracingiem akcji**
   - **Metryki**:
     - API call success rate: >99%
     - Action execution time: <500ms
     - Retry rate: <5%
   - **Walidacja**:
     ```python
     # Test HA integration
     response = ha_client.call_service('light.turn_on', entity_id='light.living_room')
     assert response.status == 'success'
     ```
   - **Sukces**: Trace pokazuje: detection → decision → HA call → result
   - **[Szczegóły →](docs/faza-4-integracja/02-ha-bridge-service.md)**

3. **Dashboard: Automation Execution**
   - **Panele**:
     - Automations triggered/hour
     - Success/failure rate
     - Latency distribution
     - Most common triggers
   - **Walidacja**: Test dashboard z symulowanymi automatyzacjami
   - **Sukces**: Live view działających automatyzacji
   - **[Szczegóły →](docs/faza-4-integracja/03-dashboard-automation.md)**

4. **Trace: od detekcji do wykonania automatyzacji**
   - **Metryka**: Complete trace z wszystkimi krokami
   - **Walidacja**:
     ```
     Trace path: object_detected → intent_recognized → 
                 automation_triggered → ha_service_called → 
                 action_completed
     ```
   - **Sukces**: E2E latency <2s w 95% przypadków
   - **[Szczegóły →](docs/faza-4-integracja/04-automation-tracing.md)**

5. **Testowanie scenariuszy z pełną widocznością**
   - **Scenariusze**:
     - Person at door → notification
     - Gesture stop → turn off music  
     - Pet in kitchen → alert
   - **Walidacja**: Automated test suite z assertions
   - **Sukces**: 10/10 scenariuszy działa poprawnie
   - **[Szczegóły →](docs/faza-4-integracja/05-scenario-testing.md)**

### Faza 5: Zaawansowane AI i Voice (3-4 tygodnie)

#### Zadania i Metryki

1. **Gesture detection z metrykami i tracingiem**
   - **Metryki**:
     - Recognition accuracy: >90% (5 basic gestures)
     - Processing latency: <150ms
     - False positive rate: <5%
   - **Walidacja**:
     ```python
     # Test gesture recognition
     gestures = ['stop', 'thumbs_up', 'wave', 'point', 'peace']
     accuracy = test_gesture_model(test_dataset, gestures)
     assert accuracy > 0.9
     ```
   - **Sukces**: MediaPipe tracks 21 hand landmarks reliably
   - **[Szczegóły →](docs/faza-5-advanced-ai/01-gesture-detection.md)**

2. **Voice processing (Whisper) z metrykami STT**
   - **Metryki**:
     - WER (Word Error Rate): <10% for Polish
     - Processing time: <2s for 10s audio
     - Memory usage: <2GB
   - **Walidacja**:
     ```bash
     # Benchmark Whisper
     python benchmark_whisper.py --language pl --model medium
     ```
   - **Sukces**: Real-time factor <0.2 (5x faster than real-time)
   - **[Szczegóły →](docs/faza-5-advanced-ai/02-voice-processing.md)**

3. **LLM integration z metrykami API calls i kosztów**
   - **Metryki**:
     - Intent recognition accuracy: >95%
     - API latency p99: <3s
     - Cost per request: <$0.02
   - **Walidacja**:
     ```python
     # Track API usage
     metrics = llm_client.get_usage_stats()
     assert metrics['cost_today'] < daily_budget
     assert metrics['success_rate'] > 0.95
     ```
   - **Sukces**: Circuit breaker działa, costs tracked in Grafana
   - **[Szczegóły →](docs/faza-5-advanced-ai/03-llm-integration.md)**

4. **Dashboard: Voice & Intent Processing**
   - **Panele**:
     - Voice commands/hour
     - Intent recognition success rate
     - Language distribution
     - API costs over time
   - **Walidacja**: Live data z voice commands
   - **Sukces**: Cost alerts, WER tracking, latency heatmap
   - **[Szczegóły →](docs/faza-5-advanced-ai/04-dashboard-voice-intent.md)**

5. **End-to-end trace: głos → intent → akcja**
   - **Metryka**: Complete voice command execution trace
   - **Walidacja**:
     ```
     Trace: audio_capture → whisper_stt → text_normalization →
            llm_intent → action_mapping → ha_execution
     ```
   - **Sukces**: Voice to action <5s w 90% przypadków
   - **[Szczegóły →](docs/faza-5-advanced-ai/05-voice-to-action-trace.md)**

### Faza 6: Optymalizacja i Refinement (2-3 tygodnie)

#### Zadania i Metryki

1. **Analiza bottlenecków na podstawie metryk**
   - **Metryki**:
     - Zidentyfikowane top 3 bottlenecks
     - Baseline performance metrics
     - Resource utilization patterns
   - **Walidacja**:
     ```sql
     -- Jaeger slow queries
     SELECT operation_name, percentile_cont(0.95) 
     WITHIN GROUP (ORDER BY duration) as p95_latency
     FROM spans GROUP BY operation_name
     ORDER BY p95_latency DESC LIMIT 10;
     ```
   - **Sukces**: Bottleneck analysis report z rekomendacjami
   - **[Szczegóły →](docs/faza-6-optymalizacja/01-bottleneck-analysis.md)**

2. **Optymalizacja pipeline'u używając danych z Jaeger**
   - **Metryki**:
     - E2E latency reduction: >30%
     - Throughput increase: >50%
     - Resource usage: -20%
   - **Walidacja**: Before/after performance tests
   - **Sukces**: p95 latency <1.5s (from 2s+)
   - **[Szczegóły →](docs/faza-6-optymalizacja/02-pipeline-optimization.md)**

3. **Rozbudowa automatyzacji z monitoringiem**
   - **Metryki**:
     - 20+ automation rules
     - <1% false positive rate
     - Automation coverage: 90%
   - **Walidacja**: Test każdej automatyzacji z metrykami
   - **Sukces**: Wszystkie automatyzacje mają traces i alerts
   - **[Szczegóły →](docs/faza-6-optymalizacja/03-automation-expansion.md)**

4. **UI/Dashboard do zarządzania systemem**
   - **Features**:
     - Live camera view z bounding boxes
     - System health overview
     - Automation rule editor
     - Alert configuration
   - **Walidacja**: UI responsive <200ms
   - **Sukces**: Web UI działa na mobile i desktop
   - **[Szczegóły →](docs/faza-6-optymalizacja/04-management-ui.md)**

5. **Consolidated monitoring dashboard**
   - **Metryki na jednym dashboardzie**:
     - System health score (0-100)
     - All service statuses
     - Resource usage trends
     - Cost tracking
   - **Walidacja**: Single pane of glass dla całego systemu
   - **Sukces**: 1-click drill-down do problemów
   - **[Szczegóły →](docs/faza-6-optymalizacja/05-consolidated-dashboard.md)**

6. **Dokumentacja z przykładami trace'ów**
   - **Dokumenty**:
     - Troubleshooting guide z traces
     - Performance tuning guide
     - Automation cookbook
     - API reference
   - **Walidacja**: Peer review dokumentacji
   - **Sukces**: New developer onboarding <1 day
   - **[Szczegóły →](docs/faza-6-optymalizacja/06-documentation-traces.md)**

## 3. Struktura Dokumentacji

### 3.1 Dokumentacja Techniczna
```
docs/
├── requirements/
│   ├── functional-requirements.md
│   ├── non-functional-requirements.md
│   ├── hardware-requirements.md
│   └── use-cases.md
├── architecture/
│   ├── system-overview.md
│   ├── component-design.md
│   ├── data-flow.md
│   └── security-considerations.md
├── api/
│   ├── rest-api.md
│   ├── mqtt-topics.md
│   └── event-schemas.md
├── deployment/
│   ├── installation-guide.md
│   ├── configuration.md
│   └── troubleshooting.md
└── development/
    ├── setup-dev-environment.md
    ├── coding-standards.md
    └── testing-strategy.md
```

### 3.2 Wymagania - Szablon

#### Wymagania Funkcjonalne
- **RF001**: System musi przechwytywać obraz z kamery IP w rozdzielczości min. 1080p
- **RF002**: System musi wykrywać twarze z dokładnością >95%
- **RF003**: System musi rozpoznawać podstawowe gesty (min. 5 typów)
- **RF004**: System musi integrować się z Home Assistant przez MQTT
- **RF005**: System musi umożliwiać sterowanie głosowe w języku polskim

#### Wymagania Niefunkcjonalne
- **RNF001**: Latencja end-to-end < 2 sekundy
- **RNF002**: System musi przetwarzać min. 10 FPS
- **RNF003**: Dostępność systemu > 99%
- **RNF004**: Wszystkie dane muszą być szyfrowane w tranzycie
- **RNF005**: System musi działać na podanej konfiguracji sprzętowej

#### Przypadki Użycia
- **UC001**: Wykrycie osoby przy drzwiach → powiadomienie + zapis
- **UC002**: Gest "stop" → wyłączenie muzyki
- **UC003**: Komenda głosowa → wykonanie automatyzacji
- **UC004**: Wykrycie zwierzęcia → alert jeśli w zakazanej strefie

## 4. Praktyki Development i Architektura

<!-- 
LLM DEVELOPMENT PROMPT:
Ta sekcja definiuje HOW we write code w projekcie.
Kluczowe zasady:
1. TDD ZAWSZE - test first, implementation second
2. Clean Architecture - separacja warstw (domain, infra, app)
3. SOLID principles w każdym komponencie
4. Event Sourcing dla frame tracking
5. Observability wbudowana od początku (nie jako afterthought)

Przy implementacji nowego serwisu:
- Użyj BaseService template (sekcja 1.4)
- Struktura katalogów jak w sekcji 4.2
- Testy na 3 poziomach (unit, integration, e2e)
-->

### 4.1 Test-Driven Development (TDD)

#### Cykl TDD
1. **RED**: Napisz test który nie przechodzi
2. **GREEN**: Napisz minimalny kod aby test przeszedł  
3. **REFACTOR**: Popraw kod zachowując zielone testy

#### Struktura Testów
```python
# tests/unit/test_frame_processor.py
import pytest
from unittest.mock import Mock, patch

class TestFrameProcessor:
    def test_should_assign_unique_id_to_frame(self):
        # Given
        processor = FrameProcessor()
        frame_data = Mock()
        
        # When
        result = processor.process(frame_data)
        
        # Then
        assert result.frame_id is not None
        assert isinstance(result.frame_id, str)
        
    def test_should_emit_telemetry_on_processing(self):
        # Given
        processor = FrameProcessor()
        with patch('opentelemetry.trace.get_tracer') as mock_tracer:
            # When
            processor.process(Mock())
            
            # Then
            mock_tracer.return_value.start_span.assert_called_once()
```

#### Poziomy Testów
- **Unit Tests**: 80% pokrycia, <100ms na test
- **Integration Tests**: Testowanie granic serwisów
- **E2E Tests**: Kluczowe scenariusze biznesowe
- **Performance Tests**: Baseline dla każdego serwisu

### 4.2 Wzorce Architektoniczne

#### Clean Architecture / Hexagonal Architecture
```
services/
├── face-recognition/
│   ├── domain/           # Logika biznesowa (bez zależności)
│   │   ├── entities/
│   │   ├── use_cases/
│   │   └── interfaces/
│   ├── infrastructure/   # Adaptery (DB, API, Queue)
│   │   ├── repositories/
│   │   ├── messaging/
│   │   └── api/
│   ├── application/      # Orchestracja
│   │   └── services/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
```

#### Domain-Driven Design (DDD)
- **Bounded Contexts**: Frame Processing, AI Detection, Home Automation
- **Aggregates**: Frame, DetectionResult, AutomationAction
- **Domain Events**: FrameCaptured, ObjectDetected, ActionTriggered

#### SOLID Principles
```python
# Single Responsibility
class FrameCapture:
    def capture_frame(self) -> Frame:
        pass

# Open/Closed + Dependency Inversion
class DetectionService(ABC):
    @abstractmethod
    def detect(self, frame: Frame) -> DetectionResult:
        pass

class FaceDetectionService(DetectionService):
    def detect(self, frame: Frame) -> DetectionResult:
        # Implementacja
        pass

# Interface Segregation
class Readable(Protocol):
    def read(self) -> bytes:
        pass

class Writable(Protocol):  
    def write(self, data: bytes) -> None:
        pass
```

### 4.3 Wzorce Projektowe

#### Repository Pattern
```python
class FrameRepository(ABC):
    @abstractmethod
    async def save(self, frame: Frame) -> None:
        pass
    
    @abstractmethod
    async def get_by_id(self, frame_id: str) -> Optional[Frame]:
        pass

class PostgresFrameRepository(FrameRepository):
    def __init__(self, connection_pool):
        self._pool = connection_pool
        
    async def save(self, frame: Frame) -> None:
        # Implementacja z tracingiem
        with self.tracer.start_as_current_span("save_frame"):
            # ...
```

#### Event Sourcing dla Frame Tracking
```python
@dataclass
class FrameEvent:
    frame_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    
class FrameEventStore:
    async def append(self, event: FrameEvent) -> None:
        # Zapisz event z metrykami
        pass
        
    async def get_frame_history(self, frame_id: str) -> List[FrameEvent]:
        # Odtwórz historię klatki
        pass
```

#### Circuit Breaker dla External Services
```python
class LLMServiceCircuitBreaker:
    def __init__(self, failure_threshold: int = 5):
        self._failure_count = 0
        self._threshold = failure_threshold
        self._is_open = False
        
    async def call_llm(self, prompt: str) -> str:
        if self._is_open:
            raise CircuitOpenError()
            
        try:
            result = await self._llm_client.complete(prompt)
            self._failure_count = 0
            return result
        except Exception as e:
            self._failure_count += 1
            if self._failure_count >= self._threshold:
                self._is_open = True
            raise
```

### 4.4 Praktyki CI/CD

#### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black
  - repo: https://github.com/PyCQA/flake8
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
```

#### GitHub Actions Pipeline
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests
        run: |
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
```

### 4.5 Code Quality Standards

#### Type Hints i Static Analysis
```python
from typing import Protocol, TypeVar, Generic

T = TypeVar('T')

class Processor(Protocol[T]):
    def process(self, item: T) -> T:
        ...

def create_pipeline(processors: list[Processor[Frame]]) -> Pipeline[Frame]:
    return Pipeline(processors)
```

#### Documentation Standards
```python
def detect_objects(frame: Frame, confidence: float = 0.8) -> list[Detection]:
    """
    Detect objects in a given frame.
    
    Args:
        frame: Input frame to process
        confidence: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        List of detected objects with bounding boxes
        
    Raises:
        InvalidFrameError: If frame is corrupted
        ModelNotLoadedError: If detection model not initialized
        
    Example:
        >>> frame = capture_frame()
        >>> detections = detect_objects(frame, confidence=0.9)
        >>> print(f"Found {len(detections)} objects")
    """
```

## 5. Technologie i Narzędzia

### Backend
- **Python 3.11+**: Główny język implementacji
- **FastAPI**: REST API
- **OpenCV**: Przetwarzanie obrazu
- **PyTorch/TensorFlow**: Modele AI
- **Celery**: Kolejkowanie zadań

### AI/ML
- **YOLO v8**: Detekcja obiektów
- **FaceNet/InsightFace**: Rozpoznawanie twarzy
- **MediaPipe**: Detekcja gestów
- **Whisper**: Speech-to-text
- **OpenAI/Anthropic API**: LLM dla intent recognition

### Infrastructure
- **Docker + Docker Compose**: Konteneryzacja
- **NVIDIA Container Toolkit**: GPU w kontenerach
- **Traefik**: Reverse proxy
- **MinIO**: Object storage dla klatek

### Observability
- **OpenTelemetry**: Standard dla telemetrii
- **Jaeger**: Distributed tracing
- **Prometheus**: Metryki
- **Grafana**: Wizualizacja
- **Loki**: Agregacja logów

## 5. Bezpieczeństwo

- **Sieć izolowana**: VLAN dla urządzeń IoT
- **TLS everywhere**: Szyfrowanie komunikacji
- **API Keys**: Dla dostępu do usług chmurowych
- **RBAC**: Role-based access control
- **Secrets management**: Docker secrets/Vault

## 6. Estymacja Kosztów

### Koszty jednorazowe
- Kamera IP PoE: 300-500 PLN
- Switch PoE: 200-300 PLN
- Kable, akcesoria: 100 PLN

### Koszty miesięczne
- LLM API (OpenAI/Anthropic): ~$20-50/miesiąc
- Backup storage (opcjonalnie): ~$5/miesiąc
- Domena + SSL (opcjonalnie): ~$10/rok

### Infrastruktura
- Serwer Ubuntu: już posiadany
- Home Assistant: już posiadany
- Wszystkie usługi self-hosted: $0

## 7. Następne Kroki

1. **Walidacja wymagań**: Przegląd i doprecyzowanie wymagań
2. **Proof of Concept**: Prosty pipeline kamera → detekcja → akcja
3. **Wybór technologii**: Finalna decyzja o stacku technologicznym
4. **Setup środowiska**: Przygotowanie dev environment na Mac OS
5. **Rozpoczęcie Fazy 1**: Implementacja fundamentów systemu