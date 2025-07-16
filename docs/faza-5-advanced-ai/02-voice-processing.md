# Faza 5 / Zadanie 2: Voice processing (Whisper) z metrykami STT

## Cel zadania

Wdrożyć Whisper do rozpoznawania mowy w języku polskim z niskim WER (<10%) i obsługą komend głosowych w czasie rzeczywistym.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja Whisper i modeli**
   - **Metryka**: Whisper medium/large model loaded
   - **Walidacja**:

     ```python
     import whisper
     model = whisper.load_model("medium")
     result = model.transcribe("test_polish.wav", language="pl")
     assert len(result["text"]) > 0
     ```

   - **Czas**: 0.5h

2. **[ ] Audio capture test**
   - **Metryka**: Microphone/stream capture working
   - **Walidacja**:

     ```bash
     python test_audio_capture.py --duration 5
     # Records 5s audio, plays back correctly
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Whisper service setup

#### Zadania atomowe

1. **[ ] Whisper API service**
   - **Metryka**: REST endpoint for transcription
   - **Walidacja**:

     ```bash
     curl -X POST localhost:8006/transcribe \
       -F "audio=@command.wav" \
       -F "language=pl"
     # {"text": "włącz światło w salonie", "confidence": 0.95}
     ```

   - **Czas**: 2h

2. **[ ] Streaming transcription**
   - **Metryka**: Real-time processing chunks
   - **Walidacja**:

     ```python
     stream = AudioStream()
     for chunk in stream:
         result = whisper_stream.process(chunk)
         if result.is_final:
             print(result.text)  # Partial results
     ```

   - **Czas**: 3h

3. **[ ] Model optimization**
   - **Metryka**: <2s for 10s audio
   - **Walidacja**:

     ```bash
     python benchmark_whisper.py --audio-length 10
     # Processing time: 1.8s (0.18x real-time)
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- API functional
- Streaming works
- Performance acceptable

### Blok 2: Polish language optimization

#### Zadania atomowe

1. **[ ] WER measurement setup**
   - **Metryka**: Automated WER calculation
   - **Walidacja**:

     ```python
     wer = calculate_wer(reference_text, whisper_output)
     assert wer < 0.10  # <10% WER
     ```

   - **Czas**: 1.5h

2. **[ ] Command vocabulary tuning**
   - **Metryka**: Home automation commands 99% accurate
   - **Walidacja**:

     ```python
     commands = ["włącz światło", "wyłącz telewizor", "zamknij rolety"]
     results = [transcribe(cmd) for cmd in test_commands]
     accuracy = sum(r.correct for r in results) / len(results)
     assert accuracy > 0.99
     ```

   - **Czas**: 2h

3. **[ ] Noise robustness**
   - **Metryka**: Works with background noise
   - **Walidacja**:

     ```python
     # Add various noise levels
     for snr in [20, 10, 5]:  # dB
         noisy = add_noise(clean_audio, snr)
         result = transcribe(noisy)
         assert wer(result) < 0.15
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Polish optimized
- Commands reliable
- Noise resistant

### Blok 3: Integration and monitoring

#### Zadania atomowe

1. **[ ] Voice activity detection**
   - **Metryka**: Detect speech segments
   - **Walidacja**:

     ```python
     vad = VoiceActivityDetector()
     segments = vad.process(audio_stream)
     # Only processes actual speech
     assert len(segments) < total_chunks * 0.3
     ```

   - **Czas**: 1.5h

2. **[ ] STT metrics dashboard**
   - **Metryka**: WER, latency, usage tracked
   - **Walidacja**:

     ```promql
     # Prometheus queries
     rate(stt_requests_total[5m])
     histogram_quantile(0.95, stt_latency_bucket)
     stt_wer_score
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- VAD working
- Metrics tracked
- Dashboard ready

## Całościowe metryki sukcesu zadania

1. **Accuracy**: WER <10% for Polish
2. **Performance**: <2s for 10s audio (5x real-time)
3. **Reliability**: 99% command recognition

## Deliverables

1. `/services/voice-processing/` - Whisper service
2. `/models/whisper-medium-pl/` - Optimized model
3. `/audio/test-commands/` - Test dataset
4. `/dashboards/stt-metrics.json` - STT dashboard
5. `/docs/voice-commands.md` - Supported commands

## Narzędzia

- **Whisper**: OpenAI STT model
- **librosa**: Audio processing
- **webrtcvad**: Voice activity detection
- **PyAudio**: Audio capture

## Zależności

- **Wymaga**:
  - GPU with 4GB+ VRAM
  - Audio input available
- **Blokuje**: Voice commands

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Model size/speed tradeoff | Wysokie | Średni | Multiple model options | Latency >3s |
| Polish accuracy issues | Średnie | Wysoki | Fine-tuning, custom vocab | WER >15% |

## Rollback Plan

1. **Detekcja problemu**:
   - WER >15%
   - Latency >5s
   - Memory issues

2. **Kroki rollback**:
   - [ ] Switch to smaller model (base/small)
   - [ ] Disable streaming mode
   - [ ] Increase VAD threshold
   - [ ] Limit to key commands only

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-llm-integration.md](./03-llm-integration.md) (already exists)
