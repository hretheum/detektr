# Frame Tracking Library

## 📚 O bibliotece

Frame-tracking to **biblioteka** (nie serwis!) do distributed tracing klatek wideo w systemie Detektor. Zapewnia spójne śledzenie każdej klatki przez cały pipeline przetwarzania.

## 🎯 Główne komponenty

### 1. **FrameID** - Unikalny identyfikator klatki
```python
from frame_tracking import FrameID

# Generowanie ID z kontekstem
frame_id = FrameID.generate(
    camera_id="cam01",
    source="rtsp-capture"
)
# Przykład: "1737123456789_rtsp-capture_cam01_0001_a3f2"
```

### 2. **FrameMetadata** - Metadane klatki
```python
from frame_tracking import FrameMetadata

metadata = FrameMetadata(
    frame_id=frame_id,
    timestamp=datetime.now(),
    camera_id="cam01",
    resolution=(1920, 1080),
    format="bgr24"
)

# Śledzenie etapów przetwarzania
metadata.add_processing_stage(
    name="capture",
    service="rtsp-capture",
    status="completed"
)
```

### 3. **TraceContext** - Kontekst distributed tracing
```python
from frame_tracking import TraceContext

# Automatyczna propagacja trace
with TraceContext.inject(frame_id, metadata) as ctx:
    # Wszystkie operacje wewnątrz są śledzone
    ctx.add_event("frame_captured")
    process_frame(frame)
```

## 🔧 Instalacja w serwisach

### W Dockerfile
```dockerfile
# Kopiuj bibliotekę
COPY services/shared/frame-tracking /app/services/shared/frame-tracking

# Instaluj w trybie edytowalnym
RUN pip install -e /app/services/shared/frame-tracking
```

### W requirements.txt
```txt
# Dla lokalnego developmentu
frame-tracking @ file:///Users/hretheum/dev/bezrobocie/detektor/services/shared/frame-tracking

# Dla Dockera
frame-tracking @ file:///app/services/shared/frame-tracking
```

## 🌊 Przepływ przez system

```
RTSP Capture (używa biblioteki)
    ↓
    → Generuje FrameID
    → Tworzy FrameMetadata
    → Inicjuje TraceContext
    → Publikuje do Redis z trace context

Frame Processor (używa biblioteki)
    ↓
    → Odbiera z Redis
    → Ekstraktuje trace context
    → Kontynuuje ten sam trace
    → Dodaje swoje spany

Storage Service (używa biblioteki)
    ↓
    → Odbiera przetworzoną klatkę
    → Kontynuuje trace
    → Zapisuje z pełną historią
```

## 📊 Przykład użycia w serwisie

```python
# services/rtsp-capture/src/main.py
from frame_tracking import FrameID, FrameMetadata, TraceContext

async def capture_frame(camera_id: str):
    # Generuj ID
    frame_id = FrameID.generate(camera_id=camera_id, source="rtsp-capture")

    # Utwórz metadane
    metadata = FrameMetadata(
        frame_id=frame_id,
        timestamp=datetime.now(),
        camera_id=camera_id
    )

    # Śledź operację
    with TraceContext.inject(frame_id, metadata) as ctx:
        # Przechwyć klatkę
        frame = await camera.read()

        # Dodaj informacje
        ctx.set_attributes({
            "frame.size": frame.nbytes,
            "frame.width": frame.shape[1],
            "frame.height": frame.shape[0]
        })

        # Publikuj do kolejki z kontekstem
        await redis_queue.publish({
            "frame_id": frame_id,
            "metadata": metadata.model_dump(),
            "traceparent": ctx.get_traceparent()  # W3C Trace Context
        })

    return frame_id
```

## 🔍 Wyszukiwanie śladów

```python
from frame_tracking import quick_search

# Szybkie wyszukanie śladów klatki
result = await quick_search("20240315_cam01_000123")
print(result)
```

## ⚙️ Konfiguracja

Biblioteka używa zmiennych środowiskowych:
- `OTEL_SERVICE_NAME` - nazwa serwisu
- `OTEL_EXPORTER_OTLP_ENDPOINT` - endpoint Jaeger/OTEL collector
- `OTEL_TRACES_EXPORTER` - typ eksportera (domyślnie: otlp)

## 📈 Metryki sukcesu

- **Pokrycie**: 100% klatek ma kompletne trace
- **Wydajność**: <1ms narzutu na klatkę
- **Wyszukiwanie**: Dowolna klatka znajdowana po ID w <1s

## 🚀 Rozwój

### Uruchomienie testów
```bash
cd services/shared/frame-tracking
pytest tests/ -v --cov=frame_tracking
```

### Budowanie pakietu
```bash
python -m build
# Tworzy wheel w dist/
```

## ❓ FAQ

**Q: Dlaczego biblioteka, a nie serwis?**
A: Frame tracking to przekrojowa funkcjonalność. Jako biblioteka:
- Zero opóźnień sieciowych
- Bezpośrednia integracja z OpenTelemetry
- Prostsze wdrożenie i utrzymanie
- Każdy serwis śledzi swoje klatki lokalnie

**Q: Jak zaktualizować bibliotekę we wszystkich serwisach?**
A: Przy kolejnym buildzie obrazów Docker, nowa wersja biblioteki zostanie automatycznie wgrana.

**Q: Czy mogę używać biblioteki poza Dockerem?**
A: Tak, zainstaluj lokalnie: `pip install -e services/shared/frame-tracking`
