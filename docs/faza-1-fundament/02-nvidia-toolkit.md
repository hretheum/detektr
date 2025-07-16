# Faza 1 / Zadanie 2: Instalacja NVIDIA Container Toolkit

## Cel zadania
Zainstalować i skonfigurować NVIDIA Container Toolkit, umożliwiając kontenerom Docker dostęp do GPU GTX 4070 Super dla operacji AI/ML.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites
#### Zadania atomowe:
1. **[x] Weryfikacja sterowników NVIDIA**
   - **Metryka**: NVIDIA Driver 525+ zainstalowany
   - **Walidacja**: `nvidia-smi | grep "Driver Version" | grep -E "5[2-9][0-9]|[6-9][0-9][0-9]"`
   - **Czas**: 0.5h

2. **[x] Sprawdzenie CUDA compatibility**
   - **Metryka**: CUDA 12.0+ support
   - **Walidacja**: `nvidia-smi | grep "CUDA Version" | grep -E "12\.[0-9]|1[3-9]\.[0-9]"`
   - **Czas**: 0.5h

### Blok 1: Instalacja NVIDIA Container Toolkit

#### Zadania atomowe:
1. **[x] Dodanie NVIDIA package repositories**
   - **Metryka**: nvidia-container-toolkit repo aktywne
   - **Walidacja**: `apt-cache policy nvidia-container-toolkit`
   - **Czas**: 0.5h

2. **[x] Instalacja nvidia-container-toolkit**
   - **Metryka**: Pakiety zainstalowane bez błędów
   - **Walidacja**: `dpkg -l | grep nvidia-container-toolkit`
   - **Czas**: 1h

3. **[x] Konfiguracja Docker runtime**
   - **Metryka**: nvidia runtime zarejestrowany
   - **Walidacja**: `docker info | grep nvidia`
   - **Czas**: 1h

### Blok 2: Weryfikacja i testy GPU

#### Zadania atomowe:
1. **[x] Test podstawowy CUDA container**
   - **Metryka**: GPU widoczne w kontenerze
   - **Walidacja**: `docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi`
   - **Czas**: 0.5h

2. **[x] Test ML framework (PyTorch)**
   - **Metryka**: PyTorch widzi GPU
   - **Walidacja**: `docker run --rm --gpus all pytorch/pytorch python -c "import torch; print(torch.cuda.is_available())"`
   - **Czas**: 1h

3. **[x] Benchmark GPU performance**
   - **Metryka**: Performance zgodny ze specyfikacją
   - **Walidacja**: cuda-samples nbody benchmark
   - **Czas**: 1h

### Blok 3: Monitoring GPU

#### Zadania atomowe:
1. **[x] Setup nvidia_gpu_exporter dla Prometheus**
   - **Metryka**: Metryki GPU dostępne na :9400
   - **Walidacja**: `curl localhost:9400/metrics | grep DCGM_FI_DEV_GPU_TEMP`
   - **Czas**: 1h

2. **[x] Konfiguracja alertów GPU**
   - **Metryka**: Alerty na temp >80°C, util >90%
   - **Walidacja**: Test alert w Prometheus
   - **Czas**: 1h

## Całościowe metryki sukcesu zadania

1. **Funkcjonalność**: GPU dostępne we wszystkich kontenerach AI/ML
2. **Performance**: CUDA operations latency <10ms
3. **Monitoring**: GPU metrics w Prometheus/Grafana
4. **Stabilność**: Brak błędów GPU po 24h stress test

## Deliverables

1. `/etc/docker/daemon.json` z nvidia runtime
2. `/opt/detektor/docker-compose.gpu.yml` z GPU services
3. `/opt/detektor/monitoring/gpu-dashboard.json` dla Grafana
4. `/opt/detektor/tests/gpu-validation.sh`

## Narzędzia

- **nvidia-container-toolkit**: GPU access dla Docker
- **nvidia-smi**: GPU monitoring
- **cuda-samples**: Performance testing
- **nvidia_gpu_exporter**: Prometheus metrics

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-git-repository-setup.md](./03-git-repository-setup.md)