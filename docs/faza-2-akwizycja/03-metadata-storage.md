# Faza 2 / Zadanie 3: Metadata Store z TimescaleDB

## Cel zadania

Zaprojektować i zaimplementować wydajny system przechowywania metadanych klatek wykorzystując TimescaleDB, z automatyczną retencją i agregacją danych czasowych.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites

#### Zadania atomowe

1. **[ ] Analiza wymagań dla time-series data**
   - **Metryka**: Schema design dla 1M records/day
   - **Walidacja**: Capacity planning document
   - **Czas**: 2h

2. **[ ] Setup TimescaleDB z Docker**
   - **Metryka**: TimescaleDB 2.13+ z compression
   - **Walidacja**: `\dx timescaledb` shows version
   - **Czas**: 1h

### Blok 1: Database schema design

#### Zadania atomowe

1. **[ ] TDD: Domain models dla metadata**
   - **Metryka**: Pydantic models z validation
   - **Walidacja**: `pytest tests/test_metadata_models.py`
   - **Czas**: 2h

2. **[ ] Implementacja TimescaleDB schema**
   - **Metryka**: Hypertables z chunk_time_interval
   - **Walidacja**: `\d+ frame_metadata` shows partitioning
   - **Czas**: 2h

3. **[ ] Indeksy i constraints**
   - **Metryka**: Query time <1ms dla lookup
   - **Walidacja**: EXPLAIN ANALYZE dla queries
   - **Czas**: 2h

### Blok 2: Repository pattern implementation

#### Zadania atomowe

1. **[ ] TDD: Repository interface**
   - **Metryka**: CRUD operations z async support
   - **Walidacja**: Interface coverage 100%
   - **Czas**: 2h

2. **[ ] Implementacja TimescaleDB repository**
   - **Metryka**: Batch inserts 10k records/s
   - **Walidacja**: Performance benchmark
   - **Czas**: 3h

3. **[ ] Connection pooling i retry logic**
   - **Metryka**: Pool size optimization
   - **Walidacja**: Connection leak test
   - **Czas**: 2h

### Blok 3: Data lifecycle management

#### Zadania atomowe

1. **[ ] Continuous aggregates setup**
   - **Metryka**: 1min, 1h, 1d aggregates
   - **Walidacja**: Materialized views populated
   - **Czas**: 2h

2. **[ ] Retention policies**
   - **Metryka**: Raw: 7d, 1min: 30d, 1h: 1y
   - **Walidacja**: Automated cleanup test
   - **Czas**: 2h

3. **[ ] Compression policies**
   - **Metryka**: 10x compression ratio
   - **Walidacja**: Disk usage before/after
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

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-frame-processor-base.md](./04-frame-processor-base.md)
