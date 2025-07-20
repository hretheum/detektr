# Faza 1 / Zadanie 99: Wdrożenie serwisów aplikacyjnych na serwerze Nebula

<!--
LLM CONTEXT PROMPT:
To zadanie naprawcze ma na celu wdrożenie WSZYSTKICH brakujących serwisów aplikacyjnych z Fazy 1 na serwerze Nebula.
Obecnie tylko infrastruktura observability działa - brak jakichkolwiek działających aplikacji Detektor.

STRATEGIA CI/CD:
- Obrazy Docker są budowane w GitHub Actions przy każdym push na main
- Obrazy publikowane do GitHub Container Registry (ghcr.io)
- Serwer Nebula TYLKO pobiera gotowe obrazy - NIGDY nie buduje lokalnie
- Deploy odbywa się przez ./scripts/deploy-to-nebula.sh lub automatycznie z GitHub Actions

STATUS na 2025-01-20:
- CI/CD pipeline: ✅ GOTOWY (wymaga tylko konfiguracji sekretów GitHub)
- Skrypty deployment: ✅ GOTOWE
- Serwis example-otel: ✅ ZAIMPLEMENTOWANY (lokalnie, wymaga dodania do docker-compose.yml)
- Pozostałe serwisy: ❌ DO IMPLEMENTACJI
- Deploy na Nebula: ❌ NIEWYKONANY
-->

## Cel zadania

Wdrożyć wszystkie brakujące serwisy aplikacyjne z Fazy 1 na serwerze Nebula, zapewniając działające przykłady wykorzystania infrastruktury observability, GPU oraz frame tracking, tworząc solidny fundament dla Fazy 2.

## 🚀 Strategia CI/CD - Obowiązujący Standard

<!--
LLM CONTEXT PROMPT:
TEN SECTION DEFINIUJE OBOWIĄZUJĄCY STANDARD dla WSZYSTKICH zadań w CAŁYM PROJEKCIE.
Każdy future task musi używać tej strategii CI/CD.
-->

### Workflow Deployment

1. **Build w GitHub Actions** (automatyczny):
   - Trigger: push na branch `main`
   - Buduje wszystkie obrazy Docker dla serwisów
   - Publikuje do `ghcr.io/hretheum/bezrobocie-detektor/[service]:latest`
   - Uruchamia się w `.github/workflows/deploy.yml`

2. **Deploy na Nebula** (automatyczny lub ręczny):
   - **Automatyczny**: GitHub Actions deployuje po udanym build
   - **Ręczny**: `./scripts/deploy-to-nebula.sh`
   - Pobiera obrazy z registry (NIGDY nie buduje lokalnie)
   - Aktualizuje docker-compose na serwerze
   - Restartuje serwisy

3. **Walidacja** (automatyczna):
   - Health checks wszystkich serwisów
   - Verification connectivity z observability stack
   - GPU tests (jeśli applicable)

### 🔧 Komendy dla LLM

```bash
# Build i deploy (pełny flow):
git add . && git commit -m "feat: deploy new service" && git push origin main

# Deploy z istniejących obrazów:
./scripts/deploy-to-nebula.sh

# Health check stack:
ssh nebula "/opt/detektor/scripts/health-check-all.sh"

# Logs:
ssh nebula "cd /opt/detektor && docker-compose logs [service-name]"
```

### ⚠️ WAŻNE: Co NIGDY nie robić

- ❌ `docker build` na serwerze produkcyjnym
- ❌ Kopiowanie kodu źródłowego na serwer
- ❌ Manual management docker-compose na serwerze
- ❌ Hardkodowanie image tags w compose files

### ✅ Co robić

- ✅ Commit kod → GitHub Actions buduje → deploy z registry
- ✅ Używaj `./scripts/deploy-to-nebula.sh` do deployment
- ✅ Pull images z `ghcr.io/hretheum/bezrobocie-detektor/`
- ✅ Wszystkie deployment commands przez automation

## Blok 0: Prerequisites check - KRYTYCZNE NA SERWERZE ⚠️

<!--
LLM PROMPT: Ten blok jest ABSOLUTNIE KRYTYCZNY.
Każda komenda MUSI być poprzedzona "ssh nebula".
Jeśli cokolwiek nie przejdzie, ZATRZYMAJ wykonanie i napraw problem.

STATUS: Skrypty weryfikacyjne przygotowane, ale NIE WYKONANE na serwerze.
-->

#### Zadania atomowe

1. **[PREP] Weryfikacja dostępu SSH i uprawnień** ⚠️ **DO WYKONANIA NA SERWERZE**
   - **Metryka**: SSH działa, sudo access, git configured
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "whoami && sudo -n true && echo 'SSH + sudo OK' || echo 'FAIL'"
     ssh nebula "cd /opt/detektor && git remote -v | grep origin"
     ssh nebula "docker ps > /dev/null && echo 'Docker access OK' || echo 'FAIL'"
     ```
   - **Quality Gate**: All checks return OK
   - **Guardrails**: Abort if any check fails
   - **Czas**: 0.5h

2. **[PREP] Weryfikacja infrastruktury observability** ⚠️ **DO WYKONANIA NA SERWERZE**
   - **Metryka**: Prometheus, Grafana, Jaeger healthy
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "curl -s http://localhost:9090/-/healthy | grep 'Prometheus is Healthy'"
     ssh nebula "curl -s http://localhost:3000/api/health | jq '.database'"
     ssh nebula "curl -s http://localhost:16686/ | grep -q 'Jaeger UI' && echo 'Jaeger OK'"
     ```
   - **Quality Gate**: All services responding
   - **Guardrails**: Fix unhealthy services first
   - **Czas**: 0.5h

3. **[PREP] Weryfikacja GPU i przestrzeni dyskowej** ⚠️ **DO WYKONANIA NA SERWERZE**
   - **Metryka**: GPU accessible, >20GB free space
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "nvidia-smi --query-gpu=name,memory.free --format=csv"
     ssh nebula "df -h / | tail -1 | awk '{print \$4}' | grep -E '^[2-9][0-9]G|^[1-9][0-9]{2}G'"
     ssh nebula "docker system df"
     ```
   - **Quality Gate**: GPU detected, sufficient space
   - **Guardrails**: Clean up if <20GB free
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Fix telemetry service i deploy example OTEL service

<!--
LLM PROMPT: Najpierw napraw restartujący się kontener, potem deploy przykładu.
PAMIĘTAJ: ssh nebula przed każdą komendą!

STATUS:
- example-otel: ✅ ZAIMPLEMENTOWANY lokalnie
- Brakuje: konfiguracja w docker-compose.yml
- Brakuje: faktyczny deployment na Nebula
-->

#### Zadania atomowe

1. **[ ] Najpierw skonfiguruj sekrety GitHub** 🚨 **KRYTYCZNE**
   - **Metryka**: Wszystkie 4 sekrety skonfigurowane w GitHub
   - **Instrukcja**: Zobacz `/docs/GITHUB_SECRETS_SETUP.md`
   - **Wymagane sekrety**:
     - NEBULA_SSH_KEY
     - NEBULA_HOST
     - NEBULA_USER
     - SOPS_AGE_KEY
   - **Walidacja**:
     ```bash
     gh secret list
     ```
   - **Quality Gate**: Wszystkie 4 sekrety widoczne
   - **Guardrails**: Bez tego CI/CD nie zadziała!
   - **Czas**: 0.5h

2. **[ ] Debug i naprawa telemetry_service-jaeger-1** (jeśli istnieje)
   - **Metryka**: Container running stable, no restarts
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "docker logs telemetry_service-jaeger-1 --tail 100 | grep -i error"
     ssh nebula "docker compose -f docker-compose.observability.yml ps telemetry_service-jaeger-1"
     # Po naprawie:
     ssh nebula "docker ps | grep telemetry_service-jaeger-1 | grep -v Restarting"
     ```
   - **Quality Gate**: Zero restarts in 5 minutes
   - **Guardrails**: Remove if unfixable
   - **Czas**: 1h

3. **[ ] Dodaj example-otel do docker-compose.yml i zdeployuj**
   - **Metryka**: Example service running, exporting traces
   - **Prerequisites**:
     - Sekrety GitHub skonfigurowane
     - Serwis example-otel już zaimplementowany w `/services/example-otel/`
   - **Kroki**:
     ```bash
     # 1. Dodaj serwis do docker-compose.yml
     # 2. Dodaj do .env niezbędne zmienne
     # 3. Commit i push - CI/CD zbuduje obraz
     git add . && git commit -m "feat: add example-otel to docker-compose" && git push
     # 4. Po zbudowaniu obrazu, deploy:
     ./scripts/deploy-to-nebula.sh
     ```
   - **Walidacja NA SERWERZE**:
     ```bash
     # Pull latest image from registry
     ssh nebula "docker pull ghcr.io/hretheum/bezrobocie-detektor/example-otel:latest"
     # Deploy using deployment script
     ./scripts/deploy-to-nebula.sh
     # OR manual deploy:
     ssh nebula "cd /opt/detektor && docker-compose up -d example-otel"
     # Verify
     ssh nebula "curl -s http://localhost:8005/health | jq '.status'"
     ssh nebula "curl -s http://localhost:16686/api/services | jq '.data[]' | grep -q 'example-otel'"
     ```
   - **Quality Gate**: Health check passing, traces visible
   - **Guardrails**: CPU usage <50%
   - **Czas**: 2h

4. **[ ] Verify GPU access in container**
   - **Metryka**: Container can access GPU
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi"
     ssh nebula "docker exec example-otel python -c 'import torch; print(f\"GPU available: {torch.cuda.is_available()}\")"
     ```
   - **Quality Gate**: GPU detected in container
   - **Guardrails**: Memory allocation works
   - **Czas**: 0.5h

#### Metryki sukcesu bloku

- No containers in restart loop
- Example service exporting traces to Jaeger
- GPU accessible from containers
- Metrics visible in Prometheus

### Blok 2: Deploy Frame Tracking Service z PostgreSQL

<!--
LLM PROMPT: Frame tracking to CORE functionality.
Deploy z TimescaleDB dla time-series data.

STATUS:
- PostgreSQL config: ❌ BRAK docker-compose.storage.yml
- frame-tracking service: ❌ DO IMPLEMENTACJI
-->

#### Zadania atomowe

1. **[ ] Stwórz docker-compose.storage.yml i deploy PostgreSQL**
   - **Metryka**: PostgreSQL running with TimescaleDB extension
   - **Walidacja NA SERWERZE**:
     ```bash
     # Deploy
     ssh nebula "cd /opt/detektor && docker compose -f docker-compose.storage.yml up -d postgres"
     # Verify TimescaleDB
     ssh nebula "docker exec postgres psql -U detektor -c 'CREATE EXTENSION IF NOT EXISTS timescaledb;'"
     ssh nebula "docker exec postgres psql -U detektor -c '\\dx' | grep timescaledb"
     ```
   - **Quality Gate**: Extension loaded, port 5432 accessible
   - **Guardrails**: Data persistence configured
   - **Czas**: 1.5h

2. **[ ] Implementuj i deploy Frame Tracking Service**
   - **Metryka**: Frame tracking API running with event sourcing
   - **Prerequisites**:
     - PostgreSQL z TimescaleDB running (poprzednie zadanie)
   - **Kroki implementacji**:
     ```bash
     # 1. Stwórz serwis w services/frame-tracking/
     # 2. Dodaj do GitHub Actions workflow matrix
     # 3. Dodaj do docker-compose.yml
     # 4. Commit, push i deploy
     ```
   - **Walidacja NA SERWERZE**:
     ```bash
     # Pull latest image from registry
     ssh nebula "docker pull ghcr.io/hretheum/bezrobocie-detektor/frame-tracking:latest"
     # Deploy using deployment script
     ./scripts/deploy-to-nebula.sh
     # OR manual deploy:
     ssh nebula "cd /opt/detektor && docker-compose up -d frame-tracking"
     # Verify API
     ssh nebula "curl -s http://localhost:8006/health | jq '.database'"
     ssh nebula "curl -s http://localhost:8006/api/v1/frames -X POST -H 'Content-Type: application/json' -d '{\"frame_id\":\"test-001\",\"timestamp\":\"2025-01-19T12:00:00Z\",\"camera_id\":\"cam-01\"}'"
     ```

   - **Quality Gate**: API responding, data persisted

   - **Guardrails**: Response time <100ms

   - **Czas**: 2h

3. **[ ] Integration test z observability**
   - **Metryka**: Traces, metrics, logs flowing correctly
   - **Walidacja NA SERWERZE**:
     ```bash
     # Generate test traffic
     ssh nebula "for i in {1..100}; do curl -s http://localhost:8006/api/v1/frames/test-\$i > /dev/null; done"
     # Check traces
     ssh nebula "curl -s 'http://localhost:16686/api/traces?service=frame-tracking&limit=10' | jq '.data | length'"
     # Check metrics
     ssh nebula "curl -s http://localhost:9090/api/v1/query?query=frame_tracking_requests_total | jq '.data.result | length'"
     ```
   - **Quality Gate**: >90% requests traced
   - **Guardrails**: No errors in logs
   - **Czas**: 1h

#### Metryki sukcesu bloku

- PostgreSQL z TimescaleDB operational
- Frame tracking API <100ms response time
- Event sourcing dla pełnej historii klatek
- Full observability integration

### Blok 3: Deploy Base Service Template jako działający przykład

<!--
LLM PROMPT: Template musi być DZIAŁAJĄCYM serwisem, nie tylko kodem.
To będzie wzorzec dla wszystkich przyszłych serwisów.

STATUS:
- base-template: ❌ DO STWORZENIA
- echo-service: ❌ DO IMPLEMENTACJI
- Grafana dashboards: ❌ BRAK
-->

#### Zadania atomowe

1. **[ ] Stwórz base-template jako wzorzec dla nowych serwisów**
   - **Metryka**: Template service implementing all patterns
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "cd /opt/detektor && ls -la services/base-template/"
     ssh nebula "cd /opt/detektor && grep -r '@traced' services/base-template/ | wc -l"
     ssh nebula "cd /opt/detektor && grep -r 'prometheus_client' services/base-template/ | wc -l"
     ```
   - **Quality Gate**: All patterns present
   - **Guardrails**: 100% test coverage
   - **Czas**: 2h

2. **[ ] Implementuj echo-service bazując na template i deploy**
   - **Metryka**: Working service demonstrating all features
   - **Prerequisites**: base-template gotowy
   - **Kroki**: Analogicznie jak frame-tracking
   - **Walidacja NA SERWERZE**:
     ```bash
     # Pull latest image from registry
     ssh nebula "docker pull ghcr.io/hretheum/bezrobocie-detektor/echo-service:latest"
     # Deploy using deployment script
     ./scripts/deploy-to-nebula.sh
     # OR manual deploy:
     ssh nebula "cd /opt/detektor && docker-compose up -d echo-service"
     # Test features
     ssh nebula "curl -s http://localhost:8007/health | jq '.features'"
     ssh nebula "curl -s http://localhost:8007/echo -X POST -d '{\"message\":\"test\"}' | jq '.correlation_id'"
     ```
   - **Quality Gate**: All endpoints working
   - **Guardrails**: Memory <500MB
   - **Czas**: 1.5h

3. **[ ] Create Grafana dashboard dla template**
   - **Metryka**: Dashboard showing all key metrics
   - **Walidacja NA SERWERZE**:
     ```bash
     # Import dashboard
     ssh nebula "curl -s -X POST http://admin:admin@localhost:3000/api/dashboards/db \
       -H 'Content-Type: application/json' \
       -d @/opt/detektor/dashboards/service-template.json"
     # Verify panels
     ssh nebula "curl -s http://localhost:3000/api/dashboards/uid/service-template | jq '.dashboard.panels | length'"
     ```
   - **Quality Gate**: Dashboard has >10 panels
   - **Guardrails**: All queries return data
   - **Czas**: 1h

#### Metryki sukcesu bloku

- Template service running with all features
- Developers can copy and modify for new services
- Full observability from day 1
- Documentation in code

### Blok 4: GPU utilization demo service

<!--
LLM PROMPT: Musimy pokazać że GPU faktycznie działa.
Simple ML inference service jako dowód koncepcji.

STATUS:
- gpu-demo: ❌ DO IMPLEMENTACJI
- GPU metrics: ❌ BRAK konfiguracji
-->

#### Zadania atomowe

1. **[ ] Implementuj GPU demo service z prostym modelem ML**
   - **Metryka**: Service using GPU for inference
   - **Prerequisites**: NVIDIA runtime w Docker
   - **Sugerowana implementacja**: YOLO lub prosty classifier
   - **Walidacja NA SERWERZE**:
     ```bash
     # Pull latest GPU image from registry
     ssh nebula "docker pull ghcr.io/hretheum/bezrobocie-detektor/gpu-demo:latest"
     # Deploy using deployment script (with GPU support)
     ./scripts/deploy-to-nebula.sh
     # OR manual deploy:
     ssh nebula "cd /opt/detektor && docker-compose up -d gpu-demo"
     # Test GPU usage
     ssh nebula "nvidia-smi | grep gpu-demo"
     ssh nebula "curl -s http://localhost:8008/inference -X POST -F 'image=@test-image.jpg' | jq '.gpu_used'"
     ```
   - **Quality Gate**: GPU memory allocated
   - **Guardrails**: GPU temp <80°C
   - **Czas**: 2h

2. **[ ] GPU metrics integration**
   - **Metryka**: GPU metrics in Prometheus/Grafana
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "curl -s http://localhost:9400/metrics | grep -E 'nvidia_gpu_temperature|nvidia_gpu_memory_used'"
     ssh nebula "curl -s http://localhost:9090/api/v1/query?query=nvidia_gpu_memory_used_bytes | jq '.data.result | length'"
     ```
   - **Quality Gate**: GPU metrics collected
   - **Guardrails**: Alerts for high temp
   - **Czas**: 1h

#### Metryki sukcesu bloku

- At least one service actively using GPU
- GPU metrics visible in monitoring
- Inference working correctly

### Blok 5: Final integration test i dokumentacja

<!--
LLM PROMPT: Weryfikacja że WSZYSTKO działa razem.
To jest final checkpoint przed Fazą 2.

STATUS:
- Skrypty testowe: ❌ DO STWORZENIA
- Dokumentacja deployment: ❌ DO WYGENEROWANIA
-->

#### Zadania atomowe

1. **[ ] End-to-end integration test wszystkich serwisów**
   - **Metryka**: All services communicating correctly
   - **Walidacja NA SERWERZE**:
     ```bash
     # Full stack health check
     ssh nebula "cd /opt/detektor && ./scripts/health-check-all.sh"
     # E2E test flow
     ssh nebula "cd /opt/detektor && python tests/e2e/test_full_pipeline.py"
     # Verify no errors
     ssh nebula "docker compose logs --since 10m | grep -i error | wc -l"
     # Should be 0
     ```
   - **Quality Gate**: All tests passing
   - **Guardrails**: <5% error rate
   - **Czas**: 2h

2. **[ ] Generate deployment documentation**
   - **Metryka**: Complete deployment guide created
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "cd /opt/detektor && docker compose ps --format json > docs/deployment-status.json"
     ssh nebula "cd /opt/detektor && ./scripts/generate-deployment-docs.sh"
     ssh nebula "ls -la /opt/detektor/docs/DEPLOYMENT_GUIDE_FAZA1.md"
     ```
   - **Quality Gate**: Guide covers all services
   - **Guardrails**: Includes troubleshooting
   - **Czas**: 1h

3. **[ ] 24h stability verification**
   - **Metryka**: No crashes or memory leaks in 24h
   - **Walidacja NA SERWERZE**:
     ```bash
     # Start monitoring
     ssh nebula "cd /opt/detektor && ./scripts/start-stability-test.sh"
     # After 24h check
     ssh nebula "cd /opt/detektor && ./scripts/check-stability-results.sh"
     ```
   - **Quality Gate**: Zero service restarts
   - **Guardrails**: Memory growth <10%
   - **Czas**: 24h (passive)

#### Metryki sukcesu bloku

- Full stack operational on Nebula
- Zero errors in integration tests
- Documentation complete and accurate
- System stable for 24h

## Całościowe metryki sukcesu zadania

1. **Deployment completeness**: 100% serwisów z Fazy 1 działających na Nebuli
2. **Observability**: Każdy serwis ma traces, metrics, logs
3. **GPU utilization**: Przynajmniej 1 serwis aktywnie używa GPU
4. **Stability**: Zero restartów w ciągu 24h
5. **Performance**: Response times <100ms dla wszystkich API
6. **Documentation**: Deployment guide umożliwia odtworzenie w <30min

## Deliverables - Status wykonania

| Deliverable | Status | Opis |
|------------|--------|------|
| `/opt/detektor/services/example-otel/` | ✅ LOCAL | Zaimplementowany, wymaga deployment |
| `/opt/detektor/services/frame-tracking/` | ❌ | Do implementacji |
| `/opt/detektor/services/echo-service/` | ❌ | Do implementacji |
| `/opt/detektor/services/gpu-demo/` | ❌ | Do implementacji |
| `/opt/detektor/docker-compose.yml` | ⚠️ | Wymaga dodania serwisów |
| `/opt/detektor/docker-compose.storage.yml` | ❌ | Do stworzenia |
| `/opt/detektor/docker-compose.gpu.yml` | ❌ | Do stworzenia |
| `/opt/detektor/docs/DEPLOYMENT_GUIDE_FAZA1.md` | ✅ | Istnieje jako DEPLOYMENT_PHASE_1.md |
| `/opt/detektor/scripts/health-check-all.sh` | ✅ | Gotowy |
| `/opt/detektor/dashboards/*.json` | ❌ | Do stworzenia |

## Narzędzia

- **Docker Compose**: Orchestration wszystkich serwisów
- **PostgreSQL + TimescaleDB**: Frame tracking storage
- **Python 3.11+**: Service implementation
- **NVIDIA Container Toolkit**: GPU access
- **curl/jq**: Validation and testing

## Zależności

- **Wymaga**:
  - Działająca infrastruktura observability (już jest)
  - Docker z GPU support (już jest)
  - SSH access do Nebula (verified w Blok 0)
- **Blokuje**:
  - Całą Fazę 2 - bez działających przykładów nie ma sensu iść dalej

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Brak miejsca na dysku podczas budowania | Średnie | Wysoki | Docker prune przed budowaniem | df -h shows <10GB |
| Konflikty portów między serwisami | Średnie | Średni | Każdy serwis ma unikalny port 800X | Bind address already in use |
| GPU nie działa w kontenerach | Niskie | Wysoki | Test GPU przed każdym deploymentem | nvidia-smi fails in container |
| PostgreSQL data loss | Niskie | Wysoki | Volume mounting, regular backups | Connection refused |
| Serwisy nie komunikują się | Średnie | Wysoki | Wszystkie w tej samej Docker network | No traces between services |

## Rollback Plan

1. **Detekcja problemu**:
   - Services crashują lub restartują się
   - Integration tests failing
   - GPU niedostępne
   - Performance degradation >50%

2. **Kroki rollback**:
   - [ ] Stop wszystkie nowe serwisy: `ssh nebula "cd /opt/detektor && docker compose down"`
   - [ ] Zachowaj logi: `ssh nebula "cd /opt/detektor && docker compose logs > rollback-logs-$(date +%s).txt"`
   - [ ] Przywróć poprzedni stan: `ssh nebula "cd /opt/detektor && git checkout HEAD~1"`
   - [ ] Restart tylko core services: `ssh nebula "cd /opt/detektor && docker compose up -d prometheus grafana jaeger"`

3. **Czas rollback**: <15 minut

## Następne kroki

Po ukończeniu tego zadania:
1. Wszystkie serwisy Fazy 1 będą działać na Nebuli
2. Możemy rozpocząć Fazę 2 z solidnym fundamentem
3. Każdy nowy serwis będzie miał działający przykład do skopiowania

→ Przejdź do [Faza 2 - Akwizycja danych](../../faza-2-akwizycja/README.md)

## 🎯 Podsumowanie - Co konkretnie zostało do zrobienia

### Krok 1: Przygotowanie (30 min)
1. [ ] Skonfiguruj 4 sekrety GitHub zgodnie z `/docs/GITHUB_SECRETS_SETUP.md`
2. [ ] Zweryfikuj dostęp SSH do Nebula i działanie observability stack

### Krok 2: Deploy example-otel (1h)
1. [ ] Dodaj example-otel do docker-compose.yml
2. [ ] Commit, push i poczekaj na build w GitHub Actions
3. [ ] Deploy na Nebula używając `./scripts/deploy-to-nebula.sh`
4. [ ] Zweryfikuj traces w Jaeger

### Krok 3: Implementacja brakujących serwisów (6-8h)
1. [ ] Stwórz docker-compose.storage.yml z PostgreSQL/TimescaleDB
2. [ ] Implementuj frame-tracking service
3. [ ] Stwórz base-template i echo-service
4. [ ] Implementuj gpu-demo z prostym modelem ML
5. [ ] Dodaj wszystkie serwisy do GitHub Actions workflow

### Krok 4: Finalizacja (2h)
1. [ ] Uruchom pełny stack na Nebula
2. [ ] Wykonaj testy integracyjne
3. [ ] Stwórz dashboardy Grafana
4. [ ] 24h test stabilności

**Całkowity czas**: ~12h aktywnej pracy + 24h test stabilności

<!--
LLM FINAL REMINDER:
To zadanie jest KRYTYCZNE dla sukcesu projektu.
BEZ działających serwisów na serwerze cały projekt to tylko "localhost development".
KAŻDA komenda musi być wykonana przez SSH na Nebuli!

PRIORYTET #1: Skonfiguruj sekrety GitHub!
PRIORYTET #2: Deploy example-otel jako proof of concept!
PRIORYTET #3: Reszta serwisów może być implementowana iteracyjnie.
-->
