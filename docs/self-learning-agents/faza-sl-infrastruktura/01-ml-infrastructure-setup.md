# Faza SL-1 / Zadanie 1: ML Infrastructure Setup

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. MLflow + MinIO są w pełni zintegrowane z istniejącą infrastrukturą Detektor
2. Wszystkie komponenty ML działają w Docker i są deployowane przez CI/CD
3. Brak konfliktu portów z istniejącymi serwisami
4. Backup/recovery jest częścią setup od początku
5. Zero wpływu na istniejące serwisy produkcyjne
-->

## Cel zadania

Przygotowanie pełnej infrastruktury Machine Learning (MLflow + MinIO + Feature Store) w środowisku Docker z pełną integracją z CI/CD i observability. Infrastruktura musi być gotowa do shadow mode learning bez wpływu na produkcję.

## Blok 0: Prerequisites check

<!--
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe:
1. **[ ] Weryfikacja dostępnych zasobów systemowych**
   - **Metryka**: 20GB wolnej przestrzeni dyskowej, 4GB RAM dostępne
   - **Walidacja**: `df -h | grep "/opt"` pokazuje >20GB, `free -h` pokazuje >4GB available
   - **Czas**: 0.5h

2. **[ ] Backup obecnej konfiguracji Docker**
   - **Metryka**: Kompletny backup docker/ folder z timestamp
   - **Walidacja**: `ls -la /opt/detektor/backups/$(date +%Y%m%d)/docker/` pokazuje pliki
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: MLflow Registry Setup

<!--
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. MLflow musi być w pełni zintegrowany z Docker Compose
2. Wszystkie dane muszą być persistent (volumes)
3. Setup musi być reproducible w CI/CD
4. Monitoring musi być włączony od początku
-->

#### Zadania atomowe:
1. **[ ] Implementacja MLflow Docker Compose**
   <!--
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Stworzyć docker/features/mlflow.yml
   - Używać port 5000 (sprawdź konflikty w PROJECT_CONTEXT.md)
   - Integrować z istniejącą siecią detektor-network
   - Po ukończeniu ZAWSZE wymagać code review przez `/agent code-reviewer`
   -->
   - **Metryka**: MLflow UI dostępne na http://nebula:5000, health check 200 OK
   - **Walidacja**:
     ```bash
     curl -s http://nebula:5000/health | grep -q "OK"
     docker ps | grep mlflow | grep "healthy"
     ```
   - **Code Review**: `/agent code-reviewer` (OBOWIĄZKOWE po implementacji)
   - **Czas**: 2h

2. **[ ] MinIO S3-compatible storage setup**
   - **Metryka**: MinIO console dostępne na http://nebula:9001, 10GB bucket created
   - **Walidacja**:
     ```bash
     curl -s http://nebula:9001/minio/health/live
     mc ls minio/mlflow-artifacts | grep -q "artifacts"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] MLflow-MinIO integration z secrets**
   - **Metryka**: MLflow może zapisywać artifacts do MinIO bucket
   - **Walidacja**:
     ```bash
     python -c "import mlflow; mlflow.set_tracking_uri('http://nebula:5000'); mlflow.log_artifact('/tmp/test.txt')"
     mc ls minio/mlflow-artifacts/0/ | wc -l | grep -q "1"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- MLflow UI fully functional na porcie 5000
- MinIO storage z 10GB capacity skonfigurowany
- End-to-end artifact storage test passed
- Wszystkie credentials w SOPS (nie hardcoded)
- Zero conflicts z istniejącymi portami

### Blok 2: PostgreSQL ML Extensions

<!--
LLM PROMPT dla bloku:
Rozszerzenie istniejącej bazy PostgreSQL o ML-specific extensions i tabele.
Musi być backward compatible z istniejącymi serwisami.
-->

#### Zadania atomowe:
1. **[ ] Instalacja pgvector extension dla embeddings**
   - **Metryka**: pgvector extension zainstalowane i dostępne
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "CREATE EXTENSION IF NOT EXISTS vector;"
     docker exec detektor-postgres psql -U detektor -c "SELECT extname FROM pg_extension WHERE extname='vector';"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1h

2. **[ ] Utworzenie ML schema i base tables**
   - **Metryka**: Schema 'ml_learning' z 5 base tables utworzone
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "\dn" | grep -q "ml_learning"
     docker exec detektor-postgres psql -U detektor -c "\dt ml_learning.*" | grep -c "agent_decisions\|agent_feedback\|learned_patterns\|model_metadata\|feature_store"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] TimescaleDB hypertables dla ML metrics**
   - **Metryka**: Hypertables dla time-series ML data skonfigurowane
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_name LIKE 'ml_%';" | wc -l | grep -q "2"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- pgvector extension operational dla embeddings
- ML schema z complete data model
- TimescaleDB hypertables dla metrics time-series
- Backward compatibility z existing services maintained
- Performance impact <5% na existing queries

### Blok 3: Redis ML Configuration

<!--
LLM PROMPT dla bloku:
Rozszerzenie Redis configuration o ML-specific namespaces i queues.
Używa istniejącej Redis infrastruktury.
-->

#### Zadania atomowe:
1. **[ ] ML-specific Redis namespaces setup**
   - **Metryka**: 3 Redis namespaces dla ML data skonfigurowane
   - **Walidacja**:
     ```bash
     redis-cli --scan --pattern "ml:decisions:*" | wc -l
     redis-cli --scan --pattern "ml:features:*" | wc -l
     redis-cli --scan --pattern "ml:models:*" | wc -l
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1h

2. **[ ] Redis Streams dla async learning events**
   - **Metryka**: Redis Stream 'ml-learning-events' z consumer groups
   - **Walidacja**:
     ```bash
     redis-cli XINFO STREAM ml-learning-events | grep -q "length"
     redis-cli XINFO GROUPS ml-learning-events | grep -q "ml-processors"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] Memory allocation i TTL policies dla ML data**
   - **Metryka**: 2GB Redis memory allocated for ML, TTL policies configured
   - **Walidacja**:
     ```bash
     redis-cli INFO memory | grep used_memory_human
     redis-cli TTL ml:features:sample | grep -E "^[0-9]+$"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Redis ML namespaces operational
- Async event streaming working
- Memory allocation appropriate (2GB for ML)
- TTL policies prevent memory leaks
- Integration with existing Redis maintained

### Blok 4: Monitoring Integration

<!--
LLM PROMPT dla bloku:
Integracja ML infrastructure z istniejącym Prometheus + Grafana.
Wszystkie ML komponenty muszą być monitorowane.
-->

#### Zadania atomowe:
1. **[ ] Prometheus metrics dla MLflow**
   - **Metryka**: MLflow eksportuje 10+ metrics do Prometheus
   - **Walidacja**:
     ```bash
     curl -s http://nebula:9090/api/v1/query?query=mlflow_up | jq '.data.result | length'
     curl -s http://nebula:9090/api/v1/query?query=mlflow_experiments_total | jq '.data.result[0].value[1]'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

2. **[ ] Grafana dashboard dla ML infrastructure**
   - **Metryka**: Complete dashboard z 8 panels dla ML monitoring
   - **Walidacja**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/ml-infrastructure | jq '.dashboard.panels | length' | grep -q "8"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Alerting rules dla ML system health**
   - **Metryka**: 5 alert rules dla critical ML infrastructure
   - **Walidacja**:
     ```bash
     curl -s http://nebula:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.alert | contains("ML")) | .alert' | wc -l | grep -q "5"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- Complete observability dla ML infrastructure
- Real-time monitoring w Grafana
- Proactive alerting skonfigurowane
- Integration z existing observability stack
- Performance metrics baseline established

## Całościowe metryki sukcesu zadania

<!--
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **Infrastructure Completeness**: MLflow, MinIO, PostgreSQL extensions wszystkie healthy i operational
2. **Integration Quality**: Zero conflicts z existing services, <5% performance impact
3. **Monitoring Coverage**: 100% ML infrastructure components monitorowane w Grafana
4. **Security Compliance**: Wszystkie credentials w SOPS, no hardcoded secrets
5. **Backup Readiness**: Backup/restore procedures tested i operational

## Deliverables

<!--
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi mieć konkretną ścieżkę i być wymieniony w zadaniu atomowym.
-->

1. `/docker/features/mlflow.yml` - MLflow Docker Compose configuration
2. `/docker/features/minio.yml` - MinIO S3-compatible storage
3. `/scripts/sql/ml-schema.sql` - PostgreSQL ML database schema
4. `/monitoring/grafana/dashboards/ml-infrastructure.json` - ML monitoring dashboard
5. `/monitoring/prometheus/rules/ml-alerts.yml` - ML alerting rules
6. `/docs/self-learning-agents/infrastructure-guide.md` - Operations guide
7. `.env.sops` updates - ML infrastructure secrets

## Narzędzia

<!--
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
-->

- **MLflow 2.9.2**: Model registry i experiment tracking
- **MinIO latest**: S3-compatible object storage dla ML artifacts
- **PostgreSQL 15 + pgvector**: Vector database dla embeddings
- **TimescaleDB**: Time-series dla ML metrics
- **Redis 7**: Caching i async event streaming
- **Prometheus**: Metrics collection i alerting
- **Grafana**: Visualization i dashboards

## Zależności

- **Wymaga**: Faza 2 ukończona (PostgreSQL, Redis, observability stack)
- **Blokuje**: Faza SL-2 (Shadow Learning Implementation)

## Ryzyka i mitigacje

<!--
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Port conflicts z existing services | Średnie | Średni | Sprawdź PORT_ALLOCATION.md, use next available | docker ps shows port already in use |
| Insufficient disk space | Niskie | Wysoki | Pre-check disk space, setup monitoring | df -h shows <10GB available |
| MinIO-MLflow connectivity issues | Średnie | Średni | Test connection w każdym step | MLflow nie może save artifacts |
| PostgreSQL extension conflicts | Niskie | Średni | Test na staging first | Extension install fails |

## Rollback Plan

<!--
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
-->

1. **Detekcja problemu**: Monitorowanie health checks fail lub existing services affected
2. **Kroki rollback**:
   - [ ] Stop ML containers: `docker compose -f docker/features/mlflow.yml down`
   - [ ] Remove ML schemas: `psql -f scripts/sql/rollback-ml-schema.sql`
   - [ ] Restore backup: `cp -r /backups/$(date +%Y%m%d)/docker/ .`
   - [ ] Restart existing services: `make prod-deploy`
3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-security-privacy-layer.md](./02-security-privacy-layer.md)
