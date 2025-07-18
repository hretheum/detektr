# RTSP Camera Setup Guide

## 🎯 Cel

Przygotowanie środowiska testowego z kamerą RTSP - zarówno symulator jak i prawdziwa kamera.

## 🔧 Opcja 1: Symulator (Natychmiastowe testowanie)

### Wymagania
- FFmpeg zainstalowany
- Python 3.11+
- Port 8554 wolny

### Uruchomienie
```bash
cd services/rtsp-capture
python rtsp_simulator.py
```

**Stream URL**: `rtsp://localhost:8554/stream`

## 📷 Opcja 2: Prawdziwa kamera IP

### Popularkie kamery IP z RTSP:
1. **Hikvision**: `rtsp://admin:admin@192.168.1.100:554/stream1`
2. **Dahua**: `rtsp://admin:admin@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0`
3. **TP-Link**: `rtsp://admin:admin@192.168.1.100:554/stream1`
4. **Reolink**: `rtsp://admin:admin@192.168.1.100:554/h264Preview_01_main`

### Konfiguracja kamery
1. Podłącz kamerę do sieci
2. Znajdź IP kamery (router admin lub IP scanner)
3. Zaloguj się przez przeglądarkę
4. Włącz RTSP stream w ustawieniach
5. Ustaw credentials (domyślnie admin/admin)

## 🖥️ Podłączenie kamery do serwera nebula

**⚠️ KIEDY PODŁĄCZYĆ KAMERĘ:**

Będziesz musiał podłączyć kamerę do serwera nebula w **Bloku 1** (Implementacja core RTSP client),
konkretnie przed **Zadaniem 2**: "Implementacja RTSP client z auto-reconnect".

**Co będzie potrzebne:**
- Kamera IP z RTSP support
- Kabel ethernet
- Dostęp do routera/switcha na serwerze nebula
- Statyczne IP lub DHCP reservation

**Procedura:**
1. Podłącz kamerę do sieci nebula
2. Skonfiguruj IP (statyczne lub DHCP)
3. Włącz RTSP stream
4. Przetestuj dostęp: `ffprobe rtsp://IP_KAMERY/stream`

## 🧪 Testowanie połączenia

### Test 1: Sprawdzenie dostępności
```bash
# Test z ffprobe
ffprobe -v quiet -print_format json -show_streams rtsp://camera_ip/stream

# Test z curl (dla HTTP management)
curl -u admin:admin http://camera_ip/
```

### Test 2: Proof of Concept
```bash
cd services/rtsp-capture
python proof_of_concept.py
```

### Test 3: Benchmark wydajności
```bash
# Będzie dostępne po implementacji
python -m pytest tests/performance/test_rtsp_baseline.py
```

## 📊 Metryki walidacji

**Blok 0 - Complete gdy:**
- ✅ Wybrana biblioteka (PyAV) obsługuje H.264/H.265
- ✅ Proof of concept łączy się z test stream
- ✅ `ffprobe rtsp://camera_ip/stream` zwraca metadane
- ✅ Kamera gotowa do podłączenia na nebula

## 🚨 Troubleshooting

### Problem: FFmpeg not found
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Weryfikacja
ffmpeg -version
```

### Problem: RTSP connection failed
1. Sprawdź IP kamery
2. Sprawdź credentials
3. Sprawdź czy RTSP jest włączony na kamerze
4. Sprawdź firewall
5. Sprawdź format URL (różne dla różnych marek)

### Problem: Stream timeouts
1. Użyj TCP transport: `rtsp_transport=tcp`
2. Zwiększ timeout
3. Sprawdź bandwidth
4. Sprawdź czy kamera nie jest przeciążona

## 🔄 Następne kroki

Po ukończeniu setup (Blok 0):
1. **Blok 1**: Implementacja RTSP client z TDD
2. **Blok 2**: Frame buffering i Redis integration
3. **Blok 3**: Monitoring i observability
4. **Blok 4**: Containerization
