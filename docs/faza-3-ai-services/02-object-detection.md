# Faza 3 / Zadanie 2: Object detection z metrykami GPU i tracingiem

## Cel zadania

Wdrożyć wysokowydajny serwis detekcji obiektów oparty na YOLO v8 z pełnym monitoringiem GPU i distributed tracing.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja GPU i CUDA**
   - **Metryka**: CUDA 12.0+, GPU memory >4GB free
   - **Walidacja**:

     ```bash
     nvidia-smi --query-gpu=name,memory.free,driver_version --format=csv
     docker run --gpus all nvidia/cuda:12.0-base nvidia-smi
     ```

   - **Czas**: 0.5h

2. **[ ] Test YOLO installation**
   - **Metryka**: YOLOv8 imports bez błędów
   - **Walidacja**:

     ```python
     from ultralytics import YOLO
     model = YOLO('yolov8n.pt')
     print(model.model.cuda)  # Should show model on GPU
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: YOLO service implementation

#### Zadania atomowe

1. **[ ] TDD: Object detection API tests**
   - **Metryka**: 15+ test cases covering all endpoints
   - **Walidacja**:

     ```bash
     pytest tests/unit/test_object_detection_api.py -v
     # All tests FAIL (no implementation yet)
     ```

   - **Czas**: 2h

2. **[ ] YOLO v8 service wrapper**
   - **Metryka**: Batch processing, GPU optimization
   - **Walidacja**:

     ```python
     # Benchmark single vs batch
     single_fps = benchmark_single_inference()
     batch_fps = benchmark_batch_inference(batch_size=8)
     assert batch_fps > single_fps * 5  # Batch much faster
     ```

   - **Czas**: 3h

3. **[ ] Multi-model support**
   - **Metryka**: Switch between yolov8n/s/m/l/x
   - **Walidacja**:

     ```bash
     curl -X POST localhost:8003/models/load -d '{"model": "yolov8m"}'
     curl localhost:8003/info | jq .current_model
     # "yolov8m"
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- API tests passing
- GPU utilization >40%
- Model switching works

### Blok 2: GPU monitoring integration

#### Zadania atomowe

1. **[ ] nvidia-smi exporter setup**
   - **Metryka**: GPU metrics in Prometheus
   - **Walidacja**:

     ```bash
     curl localhost:9835/metrics | grep nvidia_gpu_
     # Shows utilization, memory, temperature
     ```

   - **Czas**: 1.5h

2. **[ ] Custom inference metrics**
   - **Metryka**: FPS, objects/frame, confidence scores
   - **Walidacja**:

     ```promql
     rate(yolo_inferences_total[1m])  # >10
     histogram_quantile(0.95, yolo_inference_duration_bucket)  # <100ms
     ```

   - **Czas**: 2h

3. **[ ] GPU memory management**
   - **Metryka**: No memory leaks, <4GB usage
   - **Walidacja**:

     ```python
     # Run for 1 hour
     memory_start = get_gpu_memory()
     run_inference_loop(duration=3600)
     memory_end = get_gpu_memory()
     assert memory_end - memory_start < 100  # MB
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Complete GPU visibility
- Memory stable
- Performance tracked

### Blok 3: Integration i optimization

#### Zadania atomowe

1. **[ ] Queue consumer z batching**
   - **Metryka**: Process frames in batches of 8
   - **Walidacja**:

     ```bash
     # Monitor batch sizes
     redis-cli XINFO STREAM detection_queue
     # Batches of 8 being processed
     ```

   - **Czas**: 2h

2. **[ ] Result publisher z filtering**
   - **Metryka**: Only high-confidence detections published
   - **Walidacja**:

     ```python
     results = consume_detection_results(n=100)
     assert all(r.confidence > 0.5 for r in results)
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- End-to-end pipeline working
- Optimized for throughput
- Results quality controlled

## Całościowe metryki sukcesu zadania

1. **Performance**: >10 FPS on 1080p, mAP >0.85
2. **Efficiency**: GPU utilization 40-80%, batch processing
3. **Observability**: Complete GPU and inference metrics

## Deliverables

1. `/services/object-detection/` - YOLO service code
2. `/services/object-detection/models/` - Model storage
3. `/config/yolo/` - Configuration files
4. `/dashboards/gpu-metrics.json` - GPU dashboard
5. `/benchmarks/yolo_performance.py` - Benchmark script

## Narzędzia

- **YOLOv8**: Object detection framework
- **Ultralytics**: YOLO Python package
- **TorchServe**: Model serving (alternative)
- **nvidia-smi**: GPU monitoring

## Zależności

- **Wymaga**:
  - NVIDIA GPU access
  - Frame queue running
- **Blokuje**: Automation decisions

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| GPU OOM | Średnie | Wysoki | Batch size limits, model size selection | Memory >90% |
| Model accuracy issues | Niskie | Średni | Multiple model options, fine-tuning | mAP <0.8 |

## Rollback Plan

1. **Detekcja problemu**:
   - GPU crashes/OOM
   - Detection accuracy <80%
   - FPS <5

2. **Kroki rollback**:
   - [ ] Switch to smaller model: `yolov8n`
   - [ ] Reduce batch size to 1
   - [ ] Clear GPU memory: `nvidia-smi --gpu-reset`
   - [ ] Restart with conservative settings

3. **Czas rollback**: <10 min

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/object-detection.md`

### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/object-detection.md#deploy](docs/deployment/services/object-detection.md#deploy)

2. **[ ] Konfiguracja YOLO z GPU na Nebuli**
   - **Metryka**: YOLOv8 running on GTX 4070
   - **Walidacja**: `docker exec object-detection nvidia-smi`
   - **Procedura**: [docs/deployment/services/object-detection.md#gpu-configuration](docs/deployment/services/object-detection.md#gpu-configuration)

3. **[ ] Weryfikacja metryk w Prometheus**
   - **Metryka**: Object detection metrics visible at http://nebula:9090
   - **Walidacja**: `curl http://nebula:9090/api/v1/query?query=object_detections_total`
   - **Procedura**: [docs/deployment/services/object-detection.md#monitoring](docs/deployment/services/object-detection.md#monitoring)

4. **[ ] Integracja z Jaeger tracing**
   - **Metryka**: Traces visible at http://nebula:16686
   - **Walidacja**: `curl http://nebula:16686/api/traces?service=object-detection`
   - **Procedura**: [docs/deployment/services/object-detection.md#tracing](docs/deployment/services/object-detection.md#tracing)

5. **[ ] Performance test YOLO na GTX 4070**
   - **Metryka**: >10 FPS z YOLOv8m na 1080p
   - **Walidacja**: Load test via CI/CD pipeline
   - **Procedura**: [docs/deployment/services/object-detection.md#performance-testing](docs/deployment/services/object-detection.md#performance-testing)

### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

### **📋 Walidacja sukcesu:**
```bash
# Sprawdź deployment:
curl http://nebula:8003/health
curl http://nebula:8003/metrics

# Test GPU i YOLO:
ssh nebula "docker exec object-detection python -c 'from ultralytics import YOLO; print(YOLO(\"yolov8m.pt\").model.device)'"

# Test detekcji:
curl -X POST http://nebula:8003/detect -F "image=@test_scene.jpg"
```

### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/object-detection.md](docs/deployment/services/object-detection.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

### **🔍 Metryki sukcesu bloku:**
- ✅ YOLOv8 running on GTX 4070 Super
- ✅ >10 FPS on 1080p video streams
- ✅ GPU memory usage <8GB
- ✅ Metrics and traces in monitoring stack
- ✅ Grafana GPU dashboard operational
- ✅ Zero-downtime deployment via CI/CD

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-event-bus-setup.md](./03-event-bus-setup.md)
