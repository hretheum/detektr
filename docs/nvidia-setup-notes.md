# NVIDIA Setup - Notatki z instalacji

## Blok 0: Prerequisites - COMPLETED ✅

### Zainstalowane komponenty

- **NVIDIA Driver**: 575.64.03 (open kernel)
- **CUDA Version**: 12.9
- **GPU**: NVIDIA GeForce RTX 4070 Ti SUPER
- **VRAM**: 16376 MiB (16GB)

### Wykonane kroki

1. Wykrycie GPU: `lspci | grep -i nvidia`
2. Sprawdzenie rekomendowanych sterowników: `ubuntu-drivers devices`
3. Instalacja: `sudo ubuntu-drivers autoinstall`
4. **Restart systemu** (wymagany)
5. Weryfikacja: `nvidia-smi`

### Walidacja

```bash
# Driver version check
nvidia-smi | grep "Driver Version" | grep -E "5[2-9][0-9]|[6-9][0-9][0-9]"
# ✅ 575.64.03 > 525

# CUDA version check
nvidia-smi | grep "CUDA Version" | grep -E "12\.[0-9]|1[3-9]\.[0-9]"
# ✅ 12.9 > 12.0
```

## Blok 1: Instalacja NVIDIA Container Toolkit - COMPLETED ✅

### Zainstalowane pakiety

- nvidia-container-toolkit: 1.17.8-1
- nvidia-container-toolkit-base: 1.17.8-1
- libnvidia-container-tools: 1.17.8-1
- libnvidia-container1: 1.17.8-1

### Wykonane kroki

1. Dodanie NVIDIA GPG key i repository
2. `sudo apt install nvidia-container-toolkit`
3. `sudo nvidia-ctk runtime configure --runtime=docker`
4. `sudo systemctl restart docker`

### Konfiguracja

Docker daemon.json zaktualizowany z:

```json
"runtimes": {
  "nvidia": {
    "args": [],
    "path": "nvidia-container-runtime"
  }
}
```

## Blok 2: Weryfikacja i testy GPU - COMPLETED ✅

### Testy wykonane

1. **CUDA container test**

   ```bash
   docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
   ```

   - ✅ GPU widoczne w kontenerze
   - ✅ CUDA 12.9 dostępne

2. **PyTorch GPU test**

   ```bash
   docker run --rm --gpus all pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime python -c "..."
   ```

   - ✅ PyTorch 2.1.0 widzi GPU
   - ✅ Matrix multiplication działa
   - ✅ GPU memory allocation OK

3. **Performance benchmark**
   - GPU: RTX 4070 Ti SUPER
   - Compute capability: 8.9
   - Performance: 28.83 TFLOPS (FP32)

## Blok 3: Monitoring GPU - COMPLETED ✅

### Zainstalowane komponenty

- **DCGM Exporter**: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.0-ubuntu22.04
- **Prometheus**: prom/prometheus:v2.45.0
- **Network mode**: host (dla lepszej kompatybilności)

### Wykonane kroki

1. Utworzono `/opt/detektor/docker-compose.gpu.yml` z DCGM exporter
2. Skonfigurowano DCGM na porcie 9400
3. Utworzono `/opt/detektor/prometheus/prometheus.yml`
4. Skonfigurowano 5 alertów GPU w `/opt/detektor/prometheus/rules/gpu-alerts.yml`
5. Uruchomiono Prometheus na porcie 9090

### Dostępne metryki

- `DCGM_FI_DEV_GPU_TEMP` - temperatura GPU
- `DCGM_FI_DEV_GPU_UTIL` - wykorzystanie GPU
- `DCGM_FI_DEV_POWER_USAGE` - zużycie energii
- `DCGM_FI_DEV_FB_USED/FREE` - pamięć GPU
- `DCGM_FI_DEV_XID_ERRORS` - błędy GPU

### Skonfigurowane alerty

1. GPUHighTemperature - temp > 80°C (warning)
2. GPUCriticalTemperature - temp > 85°C (critical)
3. GPUHighUtilization - util > 90% przez 5 min
4. GPUHighMemoryUsage - mem > 90% przez 5 min
5. GPUXIDErrors - jakiekolwiek błędy XID

### Walidacja

```bash
/opt/detektor/tests/test-gpu-alerts.sh
# ✅ Wszystkie testy przeszły pomyślnie
```

### Endpointy

- Metryki GPU: <http://localhost:9400/metrics>
- Prometheus: <http://localhost:9090>
- Alerty: <http://localhost:9090/api/v1/rules>
