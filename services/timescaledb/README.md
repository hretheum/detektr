# TimescaleDB Service

This directory contains the TimescaleDB setup for the Detektor project.

## Structure

```
timescaledb/
├── Dockerfile              # Multi-stage build for TimescaleDB
├── scripts/               # Database initialization scripts
│   ├── 00-init-extensions.sql
│   ├── 01-create-schemas.sql
│   ├── 02-create-hypertables.sql
│   ├── 03-create-continuous-aggregates.sql
│   ├── 04-create-policies.sql
│   └── 05-create-indexes.sql
└── migrations/            # Database migrations
    └── 001_add_processing_stats.sql
```

## Features

- **TimescaleDB**: Time-series optimized PostgreSQL
- **Hypertables**: Automatic partitioning for time-series data
- **Continuous Aggregates**: Pre-computed aggregations
- **Compression**: Automatic data compression (Enterprise feature)
- **Retention Policies**: Automatic old data cleanup

## Deployment

The database is automatically built and deployed via GitHub Actions:

1. Push changes to `main` branch
2. GitHub Actions builds the image
3. Image is pushed to `ghcr.io/hretheum/detektr/timescaledb:latest`
4. Deployment script pulls and runs the new image

## Manual Operations

### Run migrations
```bash
docker-compose --profile migrate run db-migrate
```

### Connect to database
```bash
docker exec -it detektor-postgres-1 psql -U detektor -d detektor_db
```

### Check hypertables
```sql
SELECT * FROM timescaledb_information.hypertables;
```

### Check continuous aggregates
```sql
SELECT * FROM timescaledb_information.continuous_aggregates;
```

### Check compression status
```sql
SELECT * FROM timescaledb_information.compressed_chunk_stats;
```

## Performance Tuning

The following settings are optimized for production:
- `shared_buffers`: 25% of available RAM
- `effective_cache_size`: 75% of available RAM
- `work_mem`: 256MB
- `maintenance_work_mem`: 2GB
- TimescaleDB workers: 8

## Monitoring

Metrics are exported via postgres_exporter on port 9187.
Dashboard available in Grafana: "PostgreSQL / TimescaleDB Performance"
