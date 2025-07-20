# Faza 2 / Zadanie 3: Setup PostgreSQL/TimescaleDB z monitoringiem

## Cel zadania

Wdrożyć TimescaleDB jako time-series database dla metadanych klatek z automatyczną kompresją, continuous aggregates i pełnym monitoringiem.

## Blok 0: Prerequisites check NA SERWERZE NEBULA ⚠️

#### Zadania atomowe

1. **[ ] Weryfikacja wymagań PostgreSQL NA NEBULI**
   - **Metryka**: PostgreSQL 15+, TimescaleDB compatible
   - **Walidacja NA SERWERZE**:

     ```bash
     ssh nebula "docker run --rm timescale/timescaledb:latest-pg15 postgres --version"
     # PostgreSQL 15.x

     # Check available ports
     ssh nebula "sudo netstat -tuln | grep -E ':(5432|6432)'"
     # Ports should be free
     ```
   - **Quality Gate**: Compatible versions confirmed
   - **Guardrails**: No port conflicts
   - **Czas**: 0.5h

2. **[ ] Alokacja storage dla DB NA NEBULI**
   - **Metryka**: 50GB+ dedicated volume
   - **Walidacja NA SERWERZE**:

     ```bash
     ssh nebula "df -h /var/lib/docker/volumes"
     # >50GB available

     ssh nebula "docker volume create --driver local --opt type=none --opt device=/data/postgres --opt o=bind postgres_data"
     ssh nebula "docker volume inspect postgres_data | jq '.[0].Options'"
     ```
   - **Quality Gate**: Dedicated volume created
   - **Guardrails**: Alert if <20% free space
   - **Czas**: 0.5h

3. **[ ] Weryfikacja network connectivity na Nebuli**
   - **Metryka**: detektor-network accessible for DB
   - **Walidacja NA SERWERZE**:
     ```bash
     ssh nebula "docker network inspect detektor-network | jq '.IPAM.Config'"
     # Network configuration correct
     ```
   - **Quality Gate**: Network ready for DB containers
   - **Guardrails**: Subnet not conflicting
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

     # Check version and config
     docker exec postgres psql -U postgres -c "SELECT default_version, installed_version FROM pg_available_extensions WHERE name = 'timescaledb'"
     ```
   - **Quality Gate**: TimescaleDB 2.x installed
   - **Guardrails**: Memory limits set, restart policy configured
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

### Blok 4: CI/CD Pipeline dla TimescaleDB

#### Zadania atomowe

1. **[ ] Dockerfile dla TimescaleDB z migrations**
   - **Metryka**: Image includes schema and seed data
   - **Walidacja**:
     ```bash
     # Build test
     docker build -f services/timescaledb/Dockerfile -t timescaledb-detektor:test .
     docker run --rm timescaledb-detektor:test psql --version
     # PostgreSQL 15.x with TimescaleDB
     ```
   - **Quality Gate**: Image size <500MB
   - **Guardrails**: Init scripts validated
   - **Czas**: 1.5h

2. **[ ] GitHub Actions workflow dla DB images**
   - **Metryka**: Automated DB image builds
   - **Walidacja**:
     ```bash
     # Workflow file
     cat .github/workflows/db-deploy.yml | grep "timescaledb"
     # Push to trigger
     git push origin main
     ```
   - **Quality Gate**: Build completes <10min
   - **Guardrails**: Schema migrations tested
   - **Czas**: 1.5h

3. **[ ] docker-compose.db.yml dla Nebula**
   - **Metryka**: Compose file uses registry images
   - **Walidacja**:
     ```yaml
     # docker-compose.db.yml
     services:
       postgres:
         image: ghcr.io/hretheum/bezrobocie-detektor/timescaledb:latest
       pgbouncer:
         image: ghcr.io/hretheum/bezrobocie-detektor/pgbouncer:latest
       postgres-exporter:
         image: prom/postgres-exporter:latest
     ```
   - **Quality Gate**: No build directives
   - **Guardrails**: Volumes properly mapped
   - **Czas**: 1h

### Blok 5: DEPLOYMENT NA NEBULA I WALIDACJA ⚠️

#### Zadania atomowe

1. **[ ] Database deployment na Nebuli**
   - **Metryka**: TimescaleDB running on production
   - **Walidacja NA SERWERZE**:
     ```bash
     # Deploy database stack
     ssh nebula "cd /opt/detektor && docker-compose -f docker-compose.yml -f docker-compose.db.yml pull"
     ssh nebula "cd /opt/detektor && docker-compose -f docker-compose.yml -f docker-compose.db.yml up -d"

     # Verify health
     ssh nebula "docker exec postgres pg_isready -U postgres"
     # accepting connections
     ```
   - **Quality Gate**: Database healthy
   - **Guardrails**: Backup configured
   - **Czas**: 1h

2. **[ ] Schema migration na produkcji**
   - **Metryka**: All tables and hypertables created
   - **Walidacja NA SERWERZE**:
     ```bash
     # Run migrations
     ssh nebula "docker exec postgres psql -U postgres -d detektor -f /docker-entrypoint-initdb.d/schema.sql"

     # Verify schema
     ssh nebula "docker exec postgres psql -U postgres -d detektor -c '\dt'"
     ssh nebula "docker exec postgres psql -U postgres -d detektor -c 'SELECT * FROM timescaledb_information.hypertables'"
     ```
   - **Quality Gate**: All migrations successful
   - **Guardrails**: Rollback script ready
   - **Czas**: 1h

3. **[ ] Performance testing na Nebuli**
   - **Metryka**: Handles 1000 inserts/sec
   - **Walidacja NA SERWERZE**:
     ```bash
     # Run benchmark
     ssh nebula "docker run --rm --network detektor-network \
       ghcr.io/hretheum/bezrobocie-detektor/db-benchmark:latest \
       --host postgres --duration 300 --rate 1000"

     # Check metrics
     curl -s http://nebula:9187/metrics | grep pg_stat_database_tup_inserted
     ```
   - **Quality Gate**: p99 latency <50ms
   - **Guardrails**: CPU <70% during test
   - **Czas**: 2h

4. **[ ] Monitoring integration na produkcji**
   - **Metryka**: Grafana shows DB metrics
   - **Walidacja NA SERWERZE**:
     ```bash
     # Import dashboard
     ssh nebula "curl -X POST http://localhost:3000/api/dashboards/db \
       -H 'Content-Type: application/json' \
       -d @/opt/detektor/dashboards/timescaledb.json"

     # Check data
     open http://nebula:3000/d/timescale/postgresql-timescaledb
     ```
   - **Quality Gate**: All panels show data
   - **Guardrails**: Alerts configured
   - **Czas**: 1h

5. **[ ] 48h stability test**
   - **Metryka**: No connection drops or performance degradation
   - **Walidacja NA SERWERZE**:
     ```bash
     # Start monitoring
     ssh nebula "/opt/detektor/scripts/db-monitor.sh start"

     # After 48h
     ssh nebula "/opt/detektor/scripts/db-monitor.sh report"
     # Uptime 100%, no slow queries
     ```
   - **Quality Gate**: Zero downtime
   - **Guardrails**: Automated backup verified
   - **Czas**: 48h

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

## CI/CD i Deployment Guidelines

### Image Registry Structure
```
ghcr.io/hretheum/bezrobocie-detektor/
├── timescaledb:latest         # TimescaleDB z migrations
├── timescaledb:main-SHA       # Tagged versions
├── pgbouncer:latest          # Connection pooler
└── db-benchmark:latest       # Performance test tool
```

### Deployment Checklist
- [ ] Database images built in GitHub Actions
- [ ] Schema migrations included in image
- [ ] docker-compose.db.yml references registry images
- [ ] Volumes properly configured on Nebula
- [ ] Backup strategy implemented
- [ ] Monitoring endpoints active
- [ ] Performance baselines established

### Monitoring Endpoints
- PostgreSQL metrics: `http://nebula:9187/metrics`
- PgBouncer stats: `http://nebula:6432/stats`
- Grafana dashboard: `http://nebula:3000/d/timescale`

### Critical Configurations
```yaml
# Memory settings for production
shared_buffers: 16GB
effective_cache_size: 48GB
work_mem: 256MB
maintenance_work_mem: 2GB

# TimescaleDB specific
timescaledb.max_background_workers: 8
max_parallel_workers: 8
```

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-frame-tracking.md](./04-frame-tracking.md)
