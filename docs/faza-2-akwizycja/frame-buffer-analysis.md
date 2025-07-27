# Analiza Problemu Frame Buffer Dead-End

## Problem
Frame Buffer działa jako "ślepa uliczka" - konsumuje klatki z Redis Stream ale procesory nie pobierają danych z jego API.

## Objawy
1. **Buffer API pokazuje size=0** mimo że consumer działa i odbiera klatki
2. **Logi pokazują "Buffer full"** - setki dropped frames
3. **Sample-processor nie wykonuje requestów** do `/frames/dequeue` (0 requestów)
4. **100% frame loss** po zapełnieniu bufora (1000 klatek)

## Analiza Kodu

### Problem 1: Brak współdzielenia stanu
- `consumer.py` tworzy własną instancję `FrameBuffer()` (linia 37)
- `main.py` nie ma dostępu do tego samego bufora
- API endpoint `/frames/dequeue` czyta z Redis, nie z bufora w pamięci

### Problem 2: Architektura Dead-End
```
RTSP → Redis Stream → Consumer → FrameBuffer (w pamięci)
                                       ↓
                                    STOP (nikt nie czyta)

Sample-Processor → ??? (brak konfiguracji do pobierania z frame-buffer)
```

### Problem 3: API Endpoints działają na Redis, nie na buforze
- `/frames/dequeue` - czyta bezpośrednio z Redis Stream
- `/frames/status` - pokazuje stan Redis, nie bufora w pamięci
- Brak synchronizacji między consumer a API

## Skutki
- Frame buffer wypełnia się do 1000 klatek i zaczyna odrzucać wszystkie nowe
- Procesory nie mają skąd pobierać klatek
- Distributed tracing jest przerwany - brak end-to-end flow
- System nie przetwarza żadnych klatek mimo że RTSP capture działa

## Rozwiązanie
Implementacja SharedFrameBuffer pattern aby consumer i API używały tego samego bufora w pamięci.
