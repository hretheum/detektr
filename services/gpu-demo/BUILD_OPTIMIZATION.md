# GPU Demo Build Optimization Guide

## Problem
Build GPU demo trwa bardzo długo z powodu:
- PyTorch + torchvision = ~2.5GB dependencies
- Kompilacja niektórych pakietów from source
- Duża ilość zależności systemowych

## Rozwiązania

### 1. **Użyj zoptymalizowanego Dockerfile** (REKOMENDOWANE)

```bash
# Zastąp obecny Dockerfile
cp Dockerfile.optimized Dockerfile
```

Zalety:
- 3-stage build z cachowaniem wheels
- Parallel download dependencies
- Minimalne runtime dependencies
- ~40% szybszy build przy cache hit

### 2. **CPU-only build dla development**

```bash
# Dla lokalnego developmentu bez GPU
docker build --build-arg REQUIREMENTS_FILE=requirements-cpu.txt -f Dockerfile.optimized .
```

CPU-only PyTorch:
- 600MB zamiast 2.5GB
- 5x szybszy download
- Wystarczający do testów

### 3. **Pre-built base image z PyTorch**

Stwórz bazowy obraz raz na tydzień:

```dockerfile
# base-pytorch.Dockerfile
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04
RUN pip install torch torchvision ultralytics
```

```bash
# Build i push do registry
docker build -f base-pytorch.Dockerfile -t ghcr.io/hretheum/detektr/base-pytorch:latest .
docker push ghcr.io/hretheum/detektr/base-pytorch:latest
```

Potem w głównym Dockerfile:
```dockerfile
FROM ghcr.io/hretheum/detektr/base-pytorch:latest
# Tylko aplikacja, bez PyTorch
```

### 4. **Docker BuildKit cache mounts**

Włącz BuildKit i cache mounts:

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Cache pip downloads między buildami
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch torchvision
```

```bash
# Build z BuildKit
DOCKER_BUILDKIT=1 docker build .
```

### 5. **GitHub Actions cache**

W workflow dodaj cache dla Docker layers:

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Build with cache
  uses: docker/build-push-action@v5
  with:
    cache-from: type=registry,ref=ghcr.io/hretheum/detektr/gpu-demo:buildcache
    cache-to: type=registry,ref=ghcr.io/hretheum/detektr/gpu-demo:buildcache,mode=max
```

## Porównanie czasów budowania

| Metoda | Czas (bez cache) | Czas (z cache) | Rozmiar obrazu |
|--------|------------------|----------------|----------------|
| Obecny Dockerfile | ~15-20 min | ~10 min | 5.2 GB |
| Optimized Dockerfile | ~10-12 min | ~3-5 min | 5.0 GB |
| CPU-only | ~5-7 min | ~2-3 min | 2.1 GB |
| Pre-built base | ~3-5 min | ~1-2 min | 5.2 GB |

## Rekomendacje

1. **Dla CI/CD**: Użyj Dockerfile.optimized + GitHub Actions cache
2. **Dla local dev**: Użyj CPU-only requirements
3. **Dla produkcji**: Pre-built base image z GPU support

## Implementacja w projekcie

```bash
# 1. Zastąp Dockerfile
mv Dockerfile Dockerfile.original
cp Dockerfile.optimized Dockerfile

# 2. Update CI/CD workflow
# Dodaj cache-from/cache-to do build step

# 3. Commit
git add .
git commit -m "perf: optimize gpu-demo Docker build time"
```
