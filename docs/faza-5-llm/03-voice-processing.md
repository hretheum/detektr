# Faza 5 / Zadanie 3: Voice Processing z Whisper

## Cel zadania

Zaimplementować przetwarzanie komend głosowych wykorzystując Whisper ASR, z obsługą języka polskiego, wake word detection i noise suppression.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites

#### Zadania atomowe

1. **[ ] Analiza Whisper models (base, small, medium)**
   - **Metryka**: Speed vs accuracy tradeoff
   - **Walidacja**: Benchmark results
   - **Czas**: 2h

2. **[ ] Audio hardware setup**
   - **Metryka**: Microphone array configured
   - **Walidacja**: Audio quality test
   - **Czas**: 1h

### Blok 1: Audio capture pipeline

#### Zadania atomowe

1. **[ ] TDD: Audio stream interface**
   - **Metryka**: Continuous audio capture
   - **Walidacja**: `pytest tests/test_audio_stream.py`
   - **Czas**: 2h

2. **[ ] Real-time audio buffering**
   - **Metryka**: Circular buffer, no drops
   - **Walidacja**: Buffer integrity test
   - **Czas**: 3h

3. **[ ] Noise suppression (RNNoise)**
   - **Metryka**: 20dB+ noise reduction
   - **Walidacja**: SNR improvement test
   - **Czas**: 2h

### Blok 2: Wake word detection

#### Zadania atomowe

1. **[ ] Wake word engine (Porcupine/custom)**
   - **Metryka**: "Detektor" detection >95%
   - **Walidacja**: Wake word accuracy test
   - **Czas**: 3h

2. **[ ] Low-latency activation**
   - **Metryka**: <100ms wake response
   - **Walidacja**: Latency measurement
   - **Czas**: 2h

3. **[ ] False positive reduction**
   - **Metryka**: <1 false wake per hour
   - **Walidacja**: Long-term stability test
   - **Czas**: 2h

### Blok 3: Speech-to-text processing

#### Zadania atomowe

1. **[ ] Whisper integration**
   - **Metryka**: Polish language support
   - **Walidacja**: WER <10% for Polish
   - **Czas**: 3h

2. **[ ] Streaming transcription**
   - **Metryka**: Real-time partial results
   - **Walidacja**: Streaming accuracy test
   - **Czas**: 3h

3. **[ ] Speaker diarization (optional)**
   - **Metryka**: Multi-speaker support
   - **Walidacja**: Speaker separation test
   - **Czas**: 3h

### Blok 4: Command processing

#### Zadania atomowe

1. **[ ] Command grammar definition**
   - **Metryka**: Natural language commands
   - **Walidacja**: Grammar coverage test
   - **Czas**: 2h

2. **[ ] Fuzzy command matching**
   - **Metryka**: Typo/variation tolerance
   - **Walidacja**: Fuzzy match accuracy
   - **Czas**: 2h

3. **[ ] Voice feedback system**
   - **Metryka**: TTS confirmation
   - **Walidacja**: User feedback test
   - **Czas**: 2h

## Całościowe metryki sukcesu zadania

1. **Accuracy**: WER <10% for commands
2. **Latency**: <500ms wake to action
3. **Reliability**: 99%+ wake word detection
4. **Usability**: Natural conversation flow

## Deliverables

1. `services/voice-processing/` - Voice service
2. `models/whisper/` - Fine-tuned models
3. `audio/wake-words/` - Wake word models
4. `config/voice-commands.yml` - Command grammar
5. `docs/voice-commands-guide.md` - User guide

## Narzędzia

- **Whisper**: Speech recognition
- **PyAudio/sounddevice**: Audio capture
- **RNNoise**: Noise suppression
- **Porcupine**: Wake word detection
- **gTTS/pyttsx3**: Text-to-speech

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-conversation-memory.md](./04-conversation-memory.md)
