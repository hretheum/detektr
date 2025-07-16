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

## Następne kroki
- Blok 3: Monitoring GPU