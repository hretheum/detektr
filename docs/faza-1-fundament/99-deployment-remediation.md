# Faza 1 / Zadanie 99: Wdrożenie serwisów aplikacyjnych na serwerze Nebula

<!--
LLM CONTEXT PROMPT:
To zadanie naprawcze ma na celu wdrożenie WSZYSTKICH brakujących serwisów aplikacyjnych z Fazy 1 na serwerze Nebula.
Obecnie tylko infrastruktura observability działa - brak jakichkolwiek działających aplikacji Detektor.
CRITICAL: Wszystkie komendy MUSZĄ być wykonane przez SSH na serwerze Nebula, NIE lokalnie!
-->

## Cel zadania

Wdrożyć wszystkie brakujące serwisy aplikacyjne z Fazy 1 na serwerze Nebula, zapewniając działające przykłady wykorzystania infrastruktury observability, GPU oraz frame tracking, tworząc solidny fundament dla Fazy 2.

## Blok 0: Prerequisites check - KRYTYCZNE NA SERWERZE ⚠️

<!--
LLM PROMPT: Ten blok jest ABSOLUTNIE KRYTYCZNY.
Każda komenda MUSI być poprzedzona "ssh nebula".
Jeśli cokolwiek nie przejdzie, ZATRZYMAJ wykonanie i napraw problem.
-->

#### Zadania atomowe

1. **[ ] Weryfikacja dostępu SSH i uprawnień**
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

2. **[ ] Weryfikacja infrastruktury observability**
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

3. **[ ] Weryfikacja GPU i przestrzeni dyskowej**
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
-->

#### Zadania atomowe

1. **[ ] Debug i naprawa telemetry_service-jaeger-1**
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

2. **[ ] Build i deploy OpenTelemetry example service**
   - **Metryka**: Example service running, exporting traces
   - **Walidacja NA SERWERZE**:
     ```bash
     # Build
     ssh nebula "cd /opt/detektor && docker build -f services/example-otel/Dockerfile -t detektor/example-otel:latest ."
     # Deploy
     ssh nebula "cd /opt/detektor && docker compose -f docker-compose.yml up -d example-otel"
     # Verify
     ssh nebula "curl -s http://localhost:8005/health | jq '.status'"
     ssh nebula "curl -s http://localhost:16686/api/services | jq '.data[]' | grep -q 'example-otel'"
     ```
   - **Quality Gate**: Health check passing, traces visible
   - **Guardrails**: CPU usage <50%
   - **Czas**: 2h

3. **[ ] Verify GPU access in container**
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
-->

#### Zadania atomowe

1. **[ ] Deploy PostgreSQL z TimescaleDB**
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

2. **[ ] Build i deploy Frame Tracking Service**
   - **Metryka**: Frame tracking API running with event sourcing
   - **Walidacja NA SERWERZE**:
     ```bash
     # Build
     ssh nebula "cd /opt/detektor && docker build -f services/frame-tracking/Dockerfile -t detektor/frame-tracking:latest ."
     # Deploy
     ssh nebula "cd /opt/detektor && docker compose up -d frame-tracking"
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
-->

#### Zadania atomowe

1. **[ ] Przygotowanie service template z wszystkimi best practices**
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

2. **[ ] Deploy template service jako echo-service**
   - **Metryka**: Working service demonstrating all features
   - **Walidacja NA SERWERZE**:
     ```bash
     # Build z template
     ssh nebula "cd /opt/detektor && cp -r services/base-template services/echo-service"
     ssh nebula "cd /opt/detektor && docker build -f services/echo-service/Dockerfile -t detektor/echo-service:latest ."
     # Deploy
     ssh nebula "cd /opt/detektor && docker compose up -d echo-service"
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
-->

#### Zadania atomowe

1. **[ ] Deploy simple ML inference service**
   - **Metryka**: Service using GPU for inference
   - **Walidacja NA SERWERZE**:
     ```bash
     # Build GPU service
     ssh nebula "cd /opt/detektor && docker build -f services/gpu-demo/Dockerfile -t detektor/gpu-demo:latest ."
     # Run with GPU
     ssh nebula "cd /opt/detektor && docker compose -f docker-compose.gpu.yml up -d gpu-demo"
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

## Deliverables

1. `/opt/detektor/services/example-otel/` - Working OTEL example
2. `/opt/detektor/services/frame-tracking/` - Frame tracking z event sourcing
3. `/opt/detektor/services/echo-service/` - Base template demonstration
4. `/opt/detektor/services/gpu-demo/` - GPU utilization proof
5. `/opt/detektor/docker-compose.yml` - Updated with all services
6. `/opt/detektor/docker-compose.storage.yml` - PostgreSQL/TimescaleDB
7. `/opt/detektor/docker-compose.gpu.yml` - GPU services config
8. `/opt/detektor/docs/DEPLOYMENT_GUIDE_FAZA1.md` - Complete guide
9. `/opt/detektor/scripts/health-check-all.sh` - Stack validation
10. `/opt/detektor/dashboards/*.json` - Grafana dashboards

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

<!--
LLM FINAL REMINDER:
To zadanie jest KRYTYCZNE dla sukcesu projektu.
BEZ działających serwisów na serwerze cały projekt to tylko "localhost development".
KAŻDA komenda musi być wykonana przez SSH na Nebuli!
-->
