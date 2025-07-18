# ADR-2025-01-18: RTSP Library Selection

## Status
Accepted

## Context
Potrzebujemy biblioteki do obsługi strumieni RTSP z kamer IP. Kluczowe wymagania:
- Obsługa H.264/H.265 kodowania
- Automatyczne reconnect po utracie połączenia
- Asynchroniczne przetwarzanie z asyncio
- Dobra wydajność (>30 FPS z 4 kamer)
- Kompatybilność z OpenCV do dalszego przetwarzania

## Opcje rozważane

### 1. OpenCV (cv2.VideoCapture)
- ✅ Szeroko znany, stabilny
- ✅ Bezpośrednia integracja z OpenCV pipeline
- ✅ Obsługa wielu kodeków (H.264, H.265, MJPEG)
- ❌ Brak natywnego wsparcia async
- ❌ Ograniczone opcje reconnect
- ❌ Trudności z resource management

### 2. PyAV (Python FFmpeg binding)
- ✅ Pełna kontrola nad dekodowaniem
- ✅ Async support poprzez threading
- ✅ Excellentna wydajność
- ✅ Wsparcie dla wszystkich kodeków FFmpeg
- ❌ Większa złożoność API
- ❌ Wymaga znajomości FFmpeg

### 3. aiortc (WebRTC/RTSP)
- ✅ Natywne asyncio support
- ✅ Nowoczesne API
- ❌ Głównie WebRTC focus
- ❌ Ograniczone RTSP features
- ❌ Mniejsza community

### 4. GStreamer Python
- ✅ Profesjonalny media framework
- ✅ Excellentna wydajność
- ✅ Zaawansowane pipeline features
- ❌ Bardzo złożony API
- ❌ Trudna konfiguracja
- ❌ Duże dependencies

## Decision
**Wybieramy PyAV** z asyncio wrapper dla obsługi RTSP streams.

## Rationale
1. **Performance**: PyAV oferuje najlepszą wydajność dzięki bezpośredniemu FFmpeg backend
2. **Flexibility**: Pełna kontrola nad dekodowaniem i frame processing
3. **Codec Support**: Obsługa wszystkich nowoczesnych kodeków
4. **Async Integration**: Możliwość owinięcia w asyncio dla proper concurrency
5. **Future-proofing**: FFmpeg jest standard industrialny

## Implementation Strategy
```python
# Wrapper pattern dla asyncio compatibility
class AsyncRTSPCapture:
    def __init__(self, url: str):
        self.url = url
        self.container = None
        self.stream = None

    async def connect(self):
        # Run in thread pool to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None, self._connect_sync
        )

    def _connect_sync(self):
        import av
        self.container = av.open(self.url)
        self.stream = self.container.streams.video[0]

    async def capture_frame(self):
        return await asyncio.get_event_loop().run_in_executor(
            None, self._capture_frame_sync
        )
```

## Consequences
- ✅ Excellentna wydajność video processing
- ✅ Wsparcie dla wszystkich kodeków
- ✅ Możliwość optymalizacji low-level
- ❌ Wymaga learning curve dla team
- ❌ Więcej kodu dla async handling
- ❌ Dependency na FFmpeg libraries

## Monitoring
- FPS measurement per camera
- Decode latency per frame
- Connection stability metrics
- Memory usage tracking

## Next Steps
1. Implement PyAV wrapper z asyncio
2. Add comprehensive error handling
3. Implement connection pooling
4. Add performance benchmarks
