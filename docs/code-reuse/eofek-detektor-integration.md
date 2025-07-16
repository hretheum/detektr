# Integracja z eofek/detektor - Plan Wykorzystania Kodu

## Przegląd

**Repozytorium źródłowe**: <https://github.com/eofek/detektor>
**Status prawny**: Własność autora projektu Detektor - kod dostępny do swobodnego wykorzystania
**Strategia**: Selective adoption - proven patterns bez over-engineering

## Komponenty do Bezpośredniego Wykorzystania

### 1. 📊 Metrics System (WYSOKIE PRIORITET)

**Źródło**: `src/infrastructure/metrics/`
**Destination**: `src/shared/metrics/`

```python
# KOPIUJ: Metrics adapter pattern
class MetricsAdapter:
    def __init__(self, service_name):
        self.service_name = service_name

    def increment(self, metric_name):
        # Implementation from eofek/detektor
```

**Files to copy**:

- `metrics_adapter.py` → `src/shared/metrics/adapter.py`
- `prometheus_exporter.py` → `src/shared/metrics/prometheus.py`
- `gpu_metrics.py` → `src/shared/metrics/gpu.py`

### 2. 🔄 Redis Streams Event System

**Źródło**: `src/infrastructure/messaging/`
**Destination**: `src/shared/events/`

```python
# KOPIUJ: Event publishing pattern
async def publish_event(self, event_type, data):
    event = {
        'timestamp': datetime.now().isoformat(),
        'type': event_type,
        'service': self.service_name,
        'data': data
    }
    await self.redis.xadd(stream_name, event)
```

**Files to copy**:

- `redis_publisher.py` → `src/shared/events/publisher.py`
- `event_consumer.py` → `src/shared/events/consumer.py`

### 3. 🎥 Stream Forwarder Base

**Źródło**: `services/stream-forwarder/`
**Destination**: `services/rtsp-capture/`

**Key components**:

- RTSP connection management
- Frame extraction logic
- Auto-reconnect mechanism
- Health check implementation

### 4. 🐳 Docker Organization

**Źródło**: `docker/`
**Destination**: `docker/`

```yaml
# KOPIUJ: Environment-specific Docker patterns
version: '3.8'
services:
  service-name:
    environment:
      - ENV=${ENVIRONMENT:-development}
    volumes:
      - ./config/${ENVIRONMENT}:/config
```

**Files to copy**:

- `docker/development/` patterns
- `docker/production/` patterns
- Multi-stage Dockerfile approaches

## Modyfikacje i Adaptacje

### 1. Uproszczenia Architektury

```diff
# eofek/detektor (complex)
- microservices for each detection type
- multiple Redis dependencies
- complex event routing

# Nasz projekt (simplified)
+ monolithic detection service
+ single Redis instance
+ direct event publishing
```

### 2. Rozszerzenia AI Models

```python
# EXTEND: eofek/detektor MediaPipe + DODAJ YOLO
class DetectionService:
    def __init__(self):
        self.face_detector = MediaPipeDetector()  # FROM eofek/detektor
        self.object_detector = YOLODetector()     # NASZ ADDITION
        self.gesture_detector = GestureDetector() # NASZ ADDITION
```

### 3. Home Assistant Integration

```python
# NEW: Czego brakuje w eofek/detektor
class HomeAssistantBridge:
    async def send_automation_trigger(self, event):
        # MQTT/REST API integration
        # Completely new component
```

## Plan Implementacji

### Faza 1: Core Infrastructure

1. **[✅ GOTOWE]** Skopiuj metrics system pattern
2. **[⏳ TODO]** Adaptuj Redis Streams event architecture
3. **[⏳ TODO]** Zintegruj Docker organization patterns

### Faza 2: AI Services Base

1. **[⏳ TODO]** Wykorzystaj MediaPipe face detection base
2. **[⏳ TODO]** Rozszerz o YOLO object detection
3. **[⏳ TODO]** Dodaj gesture recognition (nowy komponent)

### Faza 3: Stream Processing

1. **[⏳ TODO]** Adaptuj stream-forwarder dla RTSP capture
2. **[⏳ TODO]** Zintegruj z naszym frame tracking system
3. **[⏳ TODO]** Dodaj GPU optimization patterns

## Konkretne Code Snippets do Wykorzystania

### GPU Detection Logic

```python
# FROM: eofek/detektor/src/infrastructure/gpu.py
import tensorflow as tf

def setup_gpu():
    physical_devices = tf.config.list_physical_devices('GPU')
    if len(physical_devices) > 0:
        tf.config.experimental.set_memory_growth(physical_devices[0], True)
        return True
    return False
```

### Health Check Pattern

```python
# FROM: eofek/detektor/src/infrastructure/health.py
class HealthChecker:
    async def check_redis(self):
        try:
            await self.redis.ping()
            return True
        except:
            return False
```

### Metrics Export

```python
# FROM: eofek/detektor/src/infrastructure/metrics.py
METRICS = {
    'frames_processed': Counter('frames_processed_total'),
    'frames_dropped': Counter('frames_dropped_total'),
    'processing_delay': Histogram('processing_delay_seconds'),
    'gpu_usage': Gauge('gpu_usage_percent')
}
```

## Files Mapping - Exact Copy Plan

```
eofek/detektor → Nasz projekt

# Infrastructure
src/infrastructure/metrics/ → src/shared/metrics/
src/infrastructure/messaging/ → src/shared/events/
src/infrastructure/health/ → src/shared/health/

# Docker
docker/development/ → docker/dev/
docker/production/ → docker/prod/

# Services (selective)
services/stream-forwarder/ → services/rtsp-capture/ (adapted)
```

## Validation Strategy

Dla każdego skopiowanego komponentu:

1. **Copy → Test → Adapt**
2. **Integracja z naszą architekturą**
3. **Removal of unnecessary complexity**
4. **Extension with missing features**

## Legal/Attribution Notes

- ✅ Kod dostępny - własność autora projektu Detektor
- ✅ Swobodne wykorzystanie i modyfikacja
- ✅ Attribution w komentarzach: `# Adapted from eofek/detektor`
- ✅ Link do source repository w dokumentacji

## Next Steps

1. **Import core metrics system** (pierwsza implementacja)
2. **Setup Redis Streams** z ich event patterns
3. **Docker organization** adoption
4. **Stream forwarder** adaptation dla RTSP
5. **Iterative integration** pozostałych komponentów

---

**Status**: Plan Ready
**Priorytet**: Wysoki - znacznie przyspieszy development
**Odpowiedzialny**: Team Lead (using /nakurwiaj automation)
