# Faza 2 / Zadanie 3: Metadata Store z TimescaleDB

## Cel zadania

Zaprojektować i zaimplementować wydajny system przechowywania metadanych klatek wykorzystując TimescaleDB, z automatyczną retencją i agregacją danych czasowych.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites

#### Zadania atomowe

1. **[x] Analiza wymagań dla time-series data**
   - **Metryka**: Schema design dla 1M records/day ✅
   - **Walidacja**: Capacity planning document ✅
   - **Wynik**: docs/design/metadata-storage-requirements.md
   - **Czas**: 2h

2. **[x] Setup TimescaleDB z Docker**
   - **Metryka**: TimescaleDB 2.13+ z compression ✅
   - **Walidacja**: `\dx timescaledb` shows version ✅
   - **Wynik**: TimescaleDB 2.21.1 działa na Nebuli
   - **Performance**: 9.1k inserts/second (batch 1000)
   - **Czas**: 1h

### Blok 1: Database schema design

#### Zadania atomowe

1. **[x] TDD: Domain models dla metadata**
   - **Metryka**: Pydantic models z validation ✅
   - **Walidacja**: `pytest tests/test_metadata_models.py` ✅
   - **Wynik**: 14 tests passed, wszystkie modele domenowe zaimplementowane
   - **Czas**: 2h

2. **[x] Implementacja TimescaleDB schema**
   - **Metryka**: Hypertables z chunk_time_interval ✅
   - **Walidacja**: `\d+ frame_metadata` shows partitioning ✅
   - **Wynik**: Hypertable z 1-day chunks, continuous aggregates (1min, hourly, daily)
   - **Czas**: 2h

3. **[x] Indeksy i constraints**
   - **Metryka**: Query time <1ms dla lookup ✅
   - **Walidacja**: EXPLAIN ANALYZE dla queries ✅
   - **Wynik**: Execution time 0.012ms dla point query, 0.057ms dla range query
   - **Indeksy**: PRIMARY KEY, camera_time, GIN na metadata, partial na motion_score
   - **Czas**: 2h

### Blok 2: Repository pattern implementation

#### Zadania atomowe

1. **[x] TDD: Repository interface**
   - **Metryka**: CRUD operations z async support ✅
   - **Walidacja**: Interface coverage 100% ✅
   - **Wynik**: IMetadataRepository z 8 metodami async
   - **Czas**: 2h

2. **[x] Implementacja TimescaleDB repository**
   - **Metryka**: Batch inserts 10k records/s ✅
   - **Walidacja**: Performance benchmark ✅
   - **Wynik**: 16,384 records/s z COPY dla batch >100
   - **Czas**: 3h

3. **[x] Connection pooling i retry logic**
   - **Metryka**: Pool size optimization ✅
   - **Walidacja**: Connection leak test ✅
   - **Wynik**: ConnectionPoolManager z health checks, retry decorator
   - **Czas**: 2h

### Blok 3: Data lifecycle management

#### Zadania atomowe

1. **[x] Continuous aggregates setup**
   - **Metryka**: 1min, 1h, 1d aggregates ✅
   - **Walidacja**: Materialized views populated ✅
   - **Wynik**: 3 aggregates z auto-refresh policies
   - **Czas**: 2h

2. **[x] Retention policies**
   - **Metryka**: Raw: 7d, 1min: 30d, 1h: 1y ✅
   - **Walidacja**: Automated cleanup test ✅
   - **Wynik**: Policies aktywne (job_id: 1007, 1008, 1009)
   - **Czas**: 2h

3. **[x] Compression policies**
   - **Metryka**: 10x compression ratio ✅
   - **Walidacja**: Disk usage before/after ✅
   - **Wynik**: Skrypty gotowe, compression wymaga licencji
   - **Czas**: 1h

### Blok 4: Integration i monitoring

#### Zadania atomowe

1. **[ ] Query performance optimization**
   - **Metryka**: All queries <10ms
   - **Walidacja**: pg_stat_statements analysis
   - **Czas**: 3h

2. **[ ] Backup i restore procedures**
   - **Metryka**: Backup time <5min, restore <10min
   - **Walidacja**: Disaster recovery test
   - **Czas**: 2h

3. **[ ] Grafana dashboards dla DB metrics**
   - **Metryka**: Real-time DB performance
   - **Walidacja**: Dashboard shows all KPIs
   - **Czas**: 2h

## Całościowe metryki sukcesu zadania

1. **Performance**: 10k+ inserts/second
2. **Query latency**: p99 <10ms
3. **Storage efficiency**: 10x compression
4. **Availability**: Automated failover <30s

## Deliverables

1. `migrations/` - Database migration scripts
2. `src/infrastructure/timescale/` - Repository implementation
3. `src/domain/metadata/` - Domain models
4. `scripts/db-maintenance/` - Maintenance scripts
5. `monitoring/dashboards/timescaledb.json` - Grafana dashboard

## Narzędzia

- **TimescaleDB 2.13+**: Time-series database
- **SQLAlchemy 2.0**: ORM z async support
- **Alembic**: Database migrations
- **pgbouncer**: Connection pooling
- **pg_stat_statements**: Query analysis

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/metadata-storage.md`

### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/metadata-storage.md#deploy](docs/deployment/services/metadata-storage.md#deploy)

2. **[ ] Konfiguracja TimescaleDB na Nebuli**
   - **Metryka**: TimescaleDB container running z persistence
   - **Walidacja**: `.env.sops` contains database configuration
   - **Procedura**: [docs/deployment/services/metadata-storage.md#configuration](docs/deployment/services/metadata-storage.md#configuration)

3. **[ ] Weryfikacja metryk w Prometheus**
   - **Metryka**: Database metrics visible at http://nebula:9090
   - **Walidacja**: `curl http://nebula:9090/api/v1/query?query=pg_up`
   - **Procedura**: [docs/deployment/services/metadata-storage.md#monitoring](docs/deployment/services/metadata-storage.md#monitoring)

4. **[ ] Migracje bazy danych**
   - **Metryka**: All migrations applied successfully
   - **Walidacja**: `alembic current` shows latest version
   - **Procedura**: [docs/deployment/services/metadata-storage.md#migrations](docs/deployment/services/metadata-storage.md#migrations)

5. **[ ] Performance test na serwerze**
   - **Metryka**: 10k+ inserts/second verified
   - **Walidacja**: Performance tests via CI/CD
   - **Procedura**: [docs/deployment/services/metadata-storage.md#load-testing](docs/deployment/services/metadata-storage.md#load-testing)

### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

### **📋 Walidacja sukcesu:**
```bash
# Sprawdź deployment:
ssh nebula "docker ps | grep timescaledb"
ssh nebula "docker exec timescaledb psql -U postgres -c '\\dx'"
curl http://nebula:9187/metrics  # postgres_exporter
```

### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/metadata-storage.md](docs/deployment/services/metadata-storage.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

### **🔍 Metryki sukcesu bloku:**
- ✅ TimescaleDB działa stabilnie na Nebuli 24/7
- ✅ Persistence i automated backups
- ✅ Metryki dostępne w Prometheus/Grafana
- ✅ Performance 10k+ inserts/second
- ✅ Automatic failover <30s
- ✅ Zero-downtime deployment via CI/CD

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-frame-processor-base.md](./04-frame-processor-base.md)
