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

1. **[ ] Integration z ProcessorClient dla audio streams**
   - **Metryka**: Voice processor jako ProcessorClient konsumuje audio frames
   - **Walidacja**:

     ```python
     # services/voice-processing/src/main.py
     from services.frame_buffer_v2.src.processors.client import ProcessorClient

     class VoiceProcessor(ProcessorClient):
         def __init__(self):
             super().__init__(
                 processor_id="voice-processing-1",
                 capabilities=["speech_to_text", "whisper", "polish"],
                 orchestrator_url=os.getenv("ORCHESTRATOR_URL"),
                 capacity=3,  # Audio processing is intensive
                 result_stream="voice:transcribed"
             )
             self.whisper_model = None
             self.vad = VoiceActivityDetector()

         async def start(self):
             # Load Whisper model before starting
             model_size = os.getenv("WHISPER_MODEL_SIZE", "medium")
             self.whisper_model = whisper.load_model(model_size)
             await super().start()

         async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Dict:
             # Extract audio data
             if b"audio_data" not in frame_data:
                 return None

             audio_data = frame_data[b"audio_data"]

             # Voice activity detection
             if not self.vad.contains_speech(audio_data):
                 return None

             # Transcribe with Whisper
             result = self.whisper_model.transcribe(
                 audio_data,
                 language="pl",
                 task="transcribe"
             )

             return {
                 "frame_id": frame_data[b"frame_id"].decode(),
                 "transcript": result["text"],
                 "language": "pl",
                 "confidence": result.get("confidence", 0.0),
                 "processor_id": self.processor_id
             }
     ```

   - **Czas**: 2h

2. **[ ] Voice activity detection**
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
- Integrated with ProcessorClient pattern

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
  - GPU with 4GB+ VRAM (for medium/large models)
  - Audio input available
  - Frame-buffer-v2 z ProcessorClient pattern
  - Redis dla work queues
- **Blokuje**: Voice commands
- **Integracja**: Używa ProcessorClient dla audio frames - zobacz [Processor Client Migration Guide](../processor-client-migration-guide.md)

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

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **UNIFIED CI/CD DEPLOYMENT**

> **📚 Deployment dla tego serwisu jest zautomatyzowany przez zunifikowany workflow CI/CD.**

### Kroki deployment

1. **[ ] Przygotowanie serwisu do deployment**
   - **Metryka**: Voice processing dodany do workflow matrix
   - **Walidacja**:
     ```bash
     # Sprawdź czy serwis jest w .github/workflows/deploy-self-hosted.yml
     grep "voice-processing" .github/workflows/deploy-self-hosted.yml
     ```
   - **Dokumentacja**: [docs/deployment/guides/new-service.md](../../deployment/guides/new-service.md)

2. **[ ] Konfiguracja Whisper model**
   - **Metryka**: Model size selected (base/small/medium)
   - **Konfiguracja**: W `.env.sops` ustaw `WHISPER_MODEL_SIZE`
   - **GPU**: Opcjonalne GPU acceleration dla większych modeli

3. **[ ] Deploy przez GitHub Actions**
   - **Metryka**: Automated deployment via git push
   - **Komenda**:
     ```bash
     git add .
     git commit -m "feat: deploy voice-processing service with Whisper"
     git push origin main
     ```
   - **Monitorowanie**: https://github.com/hretheum/bezrobocie/actions

### **📋 Walidacja po deployment:**

```bash
# 1. Sprawdź health serwisu
curl http://nebula:8008/health

# 2. Sprawdź metryki
curl http://nebula:8008/metrics | grep voice_

# 3. Test transkrypcji
curl -X POST http://nebula:8008/transcribe \
  -F "audio=@test_audio/polish_command.wav" \
  | jq .transcript

# 4. Test streaming (jeśli włączone)
ws://nebula:8008/stream

# 5. Sprawdź traces w Jaeger
open http://nebula:16686/search?service=voice-processing
```

### **🔗 Dokumentacja:**
- **Unified Deployment Guide**: [docs/deployment/README.md](../../deployment/README.md)
- **New Service Guide**: [docs/deployment/guides/new-service.md](../../deployment/guides/new-service.md)
- **Whisper Docs**: https://github.com/openai/whisper

### **🔍 Metryki sukcesu bloku:**
- ✅ Serwis w workflow matrix `.github/workflows/deploy-self-hosted.yml`
- ✅ Whisper model loaded successfully
- ✅ <3s latency for 10s audio
- ✅ Polish language support working
- ✅ VAD reducing false triggers
- ✅ Metrics visible in Prometheus
- ✅ Zero-downtime deployment

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-llm-integration.md](./03-llm-integration.md) (already exists)
