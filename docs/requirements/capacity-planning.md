# Capacity Planning - System Detektor

## Założenia Bazowe

### Parametry Wejściowe
- Liczba kamer: 1-8
- FPS per kamera: 10
- Rozdzielczość: 1920x1080 (Full HD)
- Kompresja: H.264
- Średni bitrate: 2 Mbps per kamera

## Obliczenia Zasobów

### 1. Przepustowość Sieci

| Kamery | Bandwidth IN | Processing | Bandwidth OUT |
|--------|--------------|------------|---------------|
| 1      | 2 Mbps       | 0.5 Mbps   | 0.2 Mbps     |
| 2      | 4 Mbps       | 1 Mbps     | 0.4 Mbps     |
| 4      | 8 Mbps       | 2 Mbps     | 0.8 Mbps     |
| 8      | 16 Mbps      | 4 Mbps     | 1.6 Mbps     |

**Total Network**: 20 Mbps dla 8 kamer (z overhead)

### 2. Wykorzystanie CPU/GPU

| Komponent | 1 kamera | 4 kamery | 8 kamer |
|-----------|----------|----------|---------|
| CPU (cores) | 2 | 4 | 8 |
| RAM (GB) | 4 | 8 | 16 |
| GPU (%) | 20% | 60% | 90% |
| GPU VRAM (GB) | 2 | 6 | 10 |

### 3. Storage (Metadata + Events)

| Typ danych | Rozmiar/event | Events/day | Storage/day |
|------------|---------------|------------|-------------|
| Detection metadata | 1 KB | 10,000 | 10 MB |
| Face embeddings | 2 KB | 1,000 | 2 MB |
| Event logs | 0.5 KB | 50,000 | 25 MB |
| Thumbnails | 50 KB | 1,000 | 50 MB |

**Total**: ~100 MB/day per kamera
**7 dni**: 700 MB per kamera
**8 kamer x 7 dni**: ~6 GB

### 4. Database Sizing

| Tabela | Rekordów/dzień | Rozmiar/rekord | Total/dzień |
|--------|----------------|----------------|-------------|
| frame_metadata | 864,000 | 200 bytes | 173 MB |
| detections | 10,000 | 500 bytes | 5 MB |
| events | 1,000 | 1 KB | 1 MB |
| metrics | 86,400 | 100 bytes | 8.6 MB |

**Total DB growth**: ~200 MB/day
**Retention 30 dni**: 6 GB

### 5. Message Queue Sizing

| Queue | Messages/sec | Size/msg | Throughput |
|-------|--------------|----------|------------|
| frame_queue | 40 | 100 bytes | 4 KB/s |
| detection_queue | 10 | 1 KB | 10 KB/s |
| event_queue | 1 | 2 KB | 2 KB/s |

**Total Queue Memory**: 100 MB (z bufferem)

## Rekomendacje Sprzętowe

### Minimalne (1-2 kamery)
- CPU: i5 lub Ryzen 5 (4 cores)
- RAM: 8 GB
- GPU: GTX 1660 (6GB VRAM)
- Storage: 256 GB SSD

### Rekomendowane (4 kamery)
- CPU: i7 lub Ryzen 7 (8 cores)
- RAM: 16 GB
- GPU: RTX 3060 (12GB VRAM)
- Storage: 512 GB SSD

### Maksymalne (8 kamer)
- CPU: i7/i9 lub Ryzen 9 (16 cores)
- RAM: 32-64 GB
- GPU: RTX 4070 Super (12-16GB VRAM)
- Storage: 1 TB NVMe SSD

## Limity Systemowe

1. **Max concurrent cameras**: 8 (GPU bottleneck)
2. **Max FPS total**: 80 (8 cameras × 10 FPS)
3. **Max events/second**: 100 (queue limit)
4. **Max storage days**: 30 (przed archiwizacją)
5. **Max concurrent users**: 10 (API limit)

## Monitorowanie Wykorzystania

```bash
# CPU/Memory
docker stats

# GPU
nvidia-smi dmon -s mu

# Disk I/O
iostat -x 1

# Network
iftop -i eth0
```

## Skalowanie Horyzontalne

Przy przekroczeniu limitów:
1. Detection services: scale to 2-3 instances
2. Database: read replicas
3. Message queue: cluster mode
4. Storage: distributed (MinIO, Ceph)