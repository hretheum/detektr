# Faza 5 / Zadanie 1: Gesture detection z metrykami i tracingiem

## Cel zadania

Implementować detekcję gestów przy użyciu MediaPipe z wysoką dokładnością rozpoznawania 5 podstawowych gestów i pełnym monitoringiem.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja MediaPipe i GPU**
   - **Metryka**: MediaPipe with GPU acceleration
   - **Walidacja**:

     ```python
     import mediapipe as mp
     hands = mp.solutions.hands.Hands(static_image_mode=False)
     # Process test image
     results = hands.process(test_image)
     assert results.multi_hand_landmarks is not None
     ```

   - **Czas**: 0.5h

2. **[ ] Test gesture dataset**
   - **Metryka**: 100+ samples per gesture
   - **Walidacja**:

     ```bash
     find /datasets/gestures -name "*.jpg" | \
       awk -F'/' '{print $(NF-1)}' | sort | uniq -c
     # Each gesture class >100 samples
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: MediaPipe integration

#### Zadania atomowe

1. **[ ] Hand tracking service**
   - **Metryka**: 21 landmarks detected reliably
   - **Walidacja**:

     ```python
     tracker = HandTracker()
     landmarks = tracker.process_frame(frame)
     assert len(landmarks) == 21
     assert all(0 <= lm.x <= 1 for lm in landmarks)
     ```

   - **Czas**: 2h

2. **[ ] Gesture classifier training**
   - **Metryka**: >90% accuracy on test set
   - **Walidacja**:

     ```python
     model = train_gesture_classifier(dataset)
     accuracy = evaluate_model(model, test_set)
     assert accuracy > 0.9
     # Confusion matrix shows clear separation
     ```

   - **Czas**: 3h

3. **[ ] Real-time gesture recognition**
   - **Metryka**: <150ms latency, 30+ FPS
   - **Walidacja**:

     ```bash
     python benchmark_gesture_detection.py
     # FPS: 32.5, Latency p95: 145ms
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Accurate hand tracking
- Trained classifier
- Real-time performance

### Blok 2: Gesture service implementation

#### Zadania atomowe

1. **[ ] API endpoints z validation**
   - **Metryka**: REST API for gesture detection
   - **Walidacja**:

     ```bash
     curl -X POST localhost:8005/detect \
       -F "image=@test_gesture.jpg"
     # {"gesture": "thumbs_up", "confidence": 0.92}
     ```

   - **Czas**: 1.5h

2. **[ ] Temporal gesture smoothing**
   - **Metryka**: Reduce false positives
   - **Walidacja**:

     ```python
     # Rapid hand movement shouldn't trigger
     results = detect_with_smoothing(noisy_sequence)
     assert results.false_positives < 0.05
     ```

   - **Czas**: 2h

3. **[ ] Multi-hand support**
   - **Metryka**: Detect gestures from both hands
   - **Walidacja**:

     ```python
     results = detector.process(two_hands_frame)
     assert len(results.gestures) == 2
     assert results.gestures[0].hand == "left"
     assert results.gestures[1].hand == "right"
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- API functional
- Robust detection
- Multi-hand capable

### Blok 3: Monitoring and optimization

#### Zadania atomowe

1. **[ ] Gesture metrics export**
   - **Metryka**: Prometheus metrics for all gestures
   - **Walidacja**:

     ```bash
     curl localhost:8005/metrics | grep gesture_
     # gesture_detected_total{type="stop"}
     # gesture_confidence_histogram
     # gesture_processing_duration_seconds
     ```

   - **Czas**: 1.5h

2. **[ ] Performance profiling**
   - **Metryka**: Identify bottlenecks
   - **Walidacja**:

     ```python
     profile = profile_gesture_pipeline()
     assert profile.mediapipe_time < 50  # ms
     assert profile.classifier_time < 20  # ms
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Full monitoring
- Performance optimized
- Bottlenecks identified

## Całościowe metryki sukcesu zadania

1. **Accuracy**: >90% for 5 basic gestures
2. **Performance**: <150ms latency, 30+ FPS
3. **Reliability**: <5% false positive rate

## Deliverables

1. `/services/gesture-detection/` - Gesture service
2. `/models/gesture_classifier.onnx` - Trained model
3. `/datasets/gestures/` - Training data
4. `/dashboards/gesture-metrics.json` - Monitoring
5. `/docs/supported-gestures.md` - Gesture guide

## Narzędzia

- **MediaPipe**: Hand tracking framework
- **scikit-learn**: Gesture classifier
- **ONNX**: Model deployment
- **OpenCV**: Image processing

## Zależności

- **Wymaga**:
  - GPU available
  - Training dataset
- **Blokuje**: Gesture-based automations

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Lighting variations | Wysokie | Średni | Data augmentation, normalization | Accuracy drops |
| Hand occlusion | Średnie | Średni | Partial landmark handling | Missing landmarks |

## Rollback Plan

1. **Detekcja problemu**:
   - Accuracy <80%
   - Latency >200ms
   - High false positives

2. **Kroki rollback**:
   - [ ] Reduce gesture set to 3 most reliable
   - [ ] Increase confidence threshold
   - [ ] Disable temporal smoothing
   - [ ] Fall back to simple detection

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-voice-processing.md](./02-voice-processing.md)
