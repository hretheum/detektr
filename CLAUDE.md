# Projekt Detektor - Zasady i Wzorce

<!-- 
LLM PROJECT CONTEXT:
Ten plik jest "pamięcią projektu" - zawiera kluczowe decyzje i wzorce.
Używaj go gdy:
1. Implementujesz nowy serwis/komponent
2. Nie wiesz jak coś zrobić "the project way"
3. Potrzebujesz quick reference dla komend/standardów

WORKFLOW STARTOWY:
1. Przeczytaj ten plik w całości
2. Sprawdź aktualną fazę w architektura_systemu.md
3. Znajdź zadanie do wykonania ([ ] checkbox)
4. Otwórz jego dekompozycję (link "Szczegóły →")
5. Użyj /nakurwiaj <blok> do automatycznego wykonania
-->

## Główne Zasady Projektu

### 🚨 ZASADA ZERO - NAJWYŻSZY PRIORYTET 🚨
**NO HARDCODED SECRETS - ABSOLUTNY ZAKAZ**
- NIGDY nie hardkoduj kluczy API, haseł, tokenów, connection strings
- NIGDY nie używaj sekretów jako fallback/default values
- WSZYSTKIE sekrety TYLKO w plikach .env lub Docker secrets
- Przykład DOBRY: `api_key = os.getenv('OPENAI_API_KEY')`
- Przykład ZŁY: `api_key = os.getenv('OPENAI_API_KEY', 'sk-12345...')` ❌

### Pozostałe zasady (w kolejności ważności):
1. **Test-Driven Development (TDD)** - ZAWSZE pisz test przed implementacją
2. **Observability First** - Każdy serwis ma wbudowany tracing i metryki od początku
3. **Clean Architecture** - Separacja warstw: domain, infrastructure, application
4. **Domain-Driven Design** - Bounded contexts, aggregates, domain events
5. **SOLID Principles** - Każda klasa/moduł zgodny z SOLID
6. **Container First** - Wszystko w kontenerach Docker

## Wzorce do Stosowania

<!-- 
LLM IMPLEMENTATION GUIDE:
Poniższe wzorce są OBOWIĄZKOWE dla każdego nowego komponentu.
Copy-paste i dostosuj do swojego serwisu.
-->

### Architektura Serwisu
```
service-name/
├── domain/           # Pure business logic
├── infrastructure/   # External dependencies
├── application/      # Use case orchestration
└── tests/           # TDD tests
```

### Bazowa Klasa Serwisu
Każdy serwis dziedziczy po `BaseService` z automatycznym observability.

### Testowanie
- Unit: 80% coverage, <100ms/test
- Integration: Granice serwisów
- E2E: Scenariusze biznesowe
- Performance: Baseline metrics

### Tracking Klatek
Format ID: `{timestamp}_{camera_id}_{sequence_number}`
Każda klatka ma pełną historię (Event Sourcing).

### Wzorce Projektowe
- Repository Pattern dla dostępu do danych
- Circuit Breaker dla external services
- Event Sourcing dla frame tracking
- Dependency Injection

### Standards
- Type hints everywhere
- Docstrings w formacie Google
- Pre-commit hooks (black, flake8, mypy)
- CI/CD z GitHub Actions

## Komendy do Pamiętania

<!-- 
LLM QUICK REFERENCE:
Te komendy używaj podczas development i debugging.
Każdy serwis ma te same porty względne:
- 8001: rtsp-capture
- 8002: face-recognition
- 8003: object-detection
- 8004: ha-bridge
- 8005: llm-intent
-->

```bash
# Uruchom testy
docker-compose -f docker-compose.test.yml up

# Sprawdź metryki
curl http://localhost:9090/metrics

# Zobacz trace
open http://localhost:16686

# Logi
docker-compose logs -f service-name

# Health check serwisu
curl http://localhost:800X/health

# Benchmark serwisu
python -m service_name.benchmark --duration 60

# Sprawdź GPU
docker exec -it service-name nvidia-smi
```

## Bounded Contexts
1. **Frame Processing** - Capture, buffering, storage
2. **AI Detection** - Face, gesture, object recognition  
3. **Home Automation** - HA integration, action execution

## Ważne Decyzje
- GPU tylko dla AI services
- LLM w chmurze (OpenAI/Anthropic)
- Lokalne modele: YOLO, MediaPipe, Whisper
- Message bus: Kafka/NATS
- Observability: Jaeger + Prometheus + Grafana

## Zarządzanie Sekretami - PRZYKŁADY

### ✅ DOBRZE - Używanie zmiennych środowiskowych:
```python
import os
from pathlib import Path

# Ładowanie z .env w development
if Path('.env').exists():
    from dotenv import load_dotenv
    load_dotenv()

# Pobieranie sekretów
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY not set in environment")

db_url = os.getenv('DATABASE_URL')
if not db_url:
    raise ValueError("DATABASE_URL not set in environment")
```

### ❌ ŹLE - Hardkodowane wartości:
```python
# NIGDY TAK NIE RÓB!
api_key = "sk-1234567890abcdef"  # ❌
api_key = os.getenv('OPENAI_API_KEY', 'sk-default')  # ❌
db_url = "postgresql://user:pass@localhost/db"  # ❌
```

### Docker Compose z sekretami:
```yaml
services:
  app:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
    env_file:
      - .env  # Tylko w development!
```