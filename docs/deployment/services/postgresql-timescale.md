# PostgreSQL/TimescaleDB Service Deployment

## Overview
TimescaleDB service providing time-series database for frame metadata and metrics.

## Service Details
- **Name**: postgresql-timescale
- **Port**: 5432 (PostgreSQL), 6432 (PgBouncer)
- **Image**: `ghcr.io/hretheum/bezrobocie-detektor/timescaledb:latest`
- **Dependencies**: None
- **Health Check**: `pg_isready`

## Configuration
### Environment Variables
```bash
POSTGRES_USER=detektor
POSTGRES_PASSWORD=<from-sops>
POSTGRES_DB=detektor
```

### Resource Requirements
- Memory: 2GB (limit), 512MB (reservation)
- CPU: 2 cores recommended
- Storage: 50GB+ for `/var/lib/postgresql/data`

## Deployment Steps
1. **Build and Push** (automated via GitHub Actions)
   ```bash
   git push origin main
   ```

2. **Deploy to Nebula**
   ```bash
   ./scripts/deploy-to-nebula.sh
   ```

3. **Run Migrations**
   ```bash
   docker-compose --profile migrate run db-migrate
   ```

## Monitoring
- **Metrics**: http://nebula:9187/metrics (postgres_exporter)
- **Grafana Dashboard**: "PostgreSQL / TimescaleDB Performance"
- **Key Metrics**:
  - `pg_up`: Database availability
  - `pg_database_size_bytes`: Database size
  - `pg_stat_database_xact_commit`: Transaction rate
  - `pg_stat_database_blks_hit`: Cache hit ratio

## Troubleshooting
### Connection Issues
```bash
# Check if service is running
docker ps | grep postgres

# Check logs
docker logs detektor-postgres-1 --tail 50

# Test connection
docker exec -it detektor-postgres-1 pg_isready
```

### Performance Issues
```sql
-- Check active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';

-- Check table sizes
SELECT * FROM pg_stat_user_tables ORDER BY n_tup_ins DESC;
```

## Backup & Recovery
```bash
# Backup
docker exec detektor-postgres-1 pg_dump -U detektor detektor_db > backup.sql

# Restore
docker exec -i detektor-postgres-1 psql -U detektor detektor_db < backup.sql
```
