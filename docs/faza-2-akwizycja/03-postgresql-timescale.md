# Faza 2 / Zadanie 3: Setup PostgreSQL/TimescaleDB z monitoringiem

## Cel zadania

Wdrożyć TimescaleDB jako time-series database dla metadanych klatek z automatyczną kompresją, continuous aggregates i pełnym monitoringiem.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja wymagań PostgreSQL**
   - **Metryka**: PostgreSQL 15+, TimescaleDB compatible
   - **Walidacja**:

     ```bash
     docker run --rm timescale/timescaledb:latest-pg15 postgres --version
     # PostgreSQL 15.x
     ```

   - **Czas**: 0.5h

2. **[ ] Alokacja storage dla DB**
   - **Metryka**: 50GB+ dedicated volume
   - **Walidacja**:

     ```bash
     df -h /var/lib/docker/volumes | grep postgres
     docker volume inspect postgres_data | jq '.[0].Options'
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Database deployment i schema

#### Zadania atomowe

1. **[ ] Deploy TimescaleDB container**
   - **Metryka**: DB accepting connections, extensions loaded
   - **Walidacja**:

     ```bash
     docker exec postgres psql -U postgres -c "SELECT extname FROM pg_extension WHERE extname='timescaledb'"
     # timescaledb
     ```

   - **Czas**: 1h

2. **[ ] Utworzenie schema dla frame metadata**
   - **Metryka**: Hypertables created, indexes optimized
   - **Walidacja**:

     ```sql
     SELECT hypertable_name FROM timescaledb_information.hypertables;
     -- frame_metadata, detection_events
     ```

   - **Czas**: 2h

3. **[ ] Konfiguracja connection pooling (PgBouncer)**
   - **Metryka**: <100 direct connections, pool working
   - **Walidacja**:

     ```bash
     psql -h localhost -p 6432 -U postgres -c "SHOW POOLS"
     # active connections through pool
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Database schema complete
- Hypertables configured
- Connection pooling active

### Blok 2: Automated data management

#### Zadania atomowe

1. **[ ] Setup compression policies**
   - **Metryka**: >10:1 compression ratio after 7 days
   - **Walidacja**:

     ```sql
     SELECT * FROM timescaledb_information.compressed_chunk_stats;
     -- compression_ratio > 10
     ```

   - **Czas**: 1.5h

2. **[ ] Continuous aggregates dla stats**
   - **Metryka**: Hourly/daily aggregates auto-refresh
   - **Walidacja**:

     ```sql
     SELECT view_name, refresh_lag FROM timescaledb_information.continuous_aggregates;
     -- All aggregates current
     ```

   - **Czas**: 2h

3. **[ ] Data retention policies**
   - **Metryka**: Auto-drop data >30 days
   - **Walidacja**:

     ```sql
     SELECT * FROM timescaledb_information.drop_chunks_policies;
     -- Policy configured and active
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Automated maintenance working
- Storage growth controlled
- Query performance stable

### Blok 3: Monitoring integration

#### Zadania atomowe

1. **[ ] postgres_exporter setup**
   - **Metryka**: DB metrics available in Prometheus
   - **Walidacja**:

     ```bash
     curl -s localhost:9187/metrics | grep pg_up
     # pg_up 1
     ```

   - **Czas**: 1h

2. **[ ] Custom metrics queries**
   - **Metryka**: Frame count, detection stats exported
   - **Walidacja**:

     ```bash
     curl -s localhost:9187/metrics | grep frame_count_total
     # custom metrics present
     ```

   - **Czas**: 1.5h

3. **[ ] Grafana dashboard import**
   - **Metryka**: PostgreSQL performance visible
   - **Walidacja**:

     ```bash
     curl -s http://localhost:3000/api/dashboards/uid/postgres-timescale | jq .dashboard.title
     # "TimescaleDB Performance"
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- All metrics exported
- Dashboard functional
- Alerts configured

## Całościowe metryki sukcesu zadania

1. **Performance**: Query latency p99 <100ms, compression >10:1
2. **Scalability**: Handles 1M+ frames/day, auto-maintenance
3. **Observability**: Complete metrics in Prometheus

## Deliverables

1. `/docker-compose.yml` - Updated z TimescaleDB
2. `/sql/schema.sql` - Database schema
3. `/sql/migrations/` - Migration scripts
4. `/config/postgres/` - Tuned configuration
5. `/dashboards/timescaledb.json` - Grafana dashboard

## Narzędzia

- **TimescaleDB 2.x**: Time-series PostgreSQL extension
- **PgBouncer**: Connection pooling
- **postgres_exporter**: Prometheus metrics
- **pgAdmin**: Database management UI

## Zależności

- **Wymaga**: Docker stack (Faza 1)
- **Blokuje**: Frame tracking (następne zadanie)

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Disk space exhaustion | Średnie | Wysoki | Compression + retention policies | >80% disk usage |
| Query performance degradation | Średnie | Średni | Continuous aggregates, indexing | p99 >200ms |

## Rollback Plan

1. **Detekcja problemu**:
   - Queries timing out
   - Disk usage critical
   - Connection pool exhausted

2. **Kroki rollback**:
   - [ ] Stop writes: `UPDATE pg_stat_activity SET state='idle'`
   - [ ] Backup current data: `pg_dump -Fc detektor > backup.dump`
   - [ ] Restore previous version
   - [ ] Replay missing data from queue

3. **Czas rollback**: <30 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-frame-tracking.md](./04-frame-tracking.md)
