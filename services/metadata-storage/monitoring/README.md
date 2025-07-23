# TimescaleDB Monitoring Setup

## Overview
This monitoring setup provides comprehensive observability for the TimescaleDB metadata storage system.

## Components

### Dashboards
1. **TimescaleDB Metadata Storage** (`timescaledb-dashboard.json`)
   - Database status and health
   - Query performance metrics
   - Cache hit ratios
   - Connection monitoring
   - I/O performance

2. **TimescaleDB Hypertables & Chunks** (`timescaledb-hypertables.json`)
   - Hypertable-specific metrics
   - Chunk statistics
   - Compression ratios
   - Table operations

### Alerts (`timescaledb-alerts.yml`)
- **Critical**: Database down, replication lag
- **Warning**: High connections, low cache hit ratio, disk usage
- **Info**: Low compression ratio

### Key Metrics

#### Database Health
- `pg_up`: Database availability
- `pg_stat_database_numbackends`: Active connections
- `pg_database_size_bytes`: Database size

#### Performance
- Cache hit ratio calculation
- Query execution times
- I/O operations (reads/writes)

#### TimescaleDB Specific
- `timescaledb_hypertable_chunks_total`: Number of chunks
- `timescaledb_hypertable_compression_ratio`: Compression efficiency

## Setup Instructions

1. Ensure postgres_exporter is running:
   ```bash
   docker run -d \
     --name postgres_exporter \
     -p 9187:9187 \
     -e DATA_SOURCE_NAME="postgresql://exporter:password@timescaledb:5432/detektor_db?sslmode=disable" \
     prometheuscommunity/postgres-exporter
   ```

2. Configure Prometheus to scrape postgres_exporter:
   ```yaml
   scrape_configs:
     - job_name: 'postgres'
       static_configs:
         - targets: ['postgres_exporter:9187']
   ```

3. Import dashboards and configure alerts using this script:
   ```bash
   python setup-monitoring.py
   ```

## Dashboard URLs
- Main Dashboard: http://nebula:3000/d/timescaledb-metadata
- Hypertables Dashboard: http://nebula:3000/d/timescaledb-hypertables

## Alert Manager
Configure Alertmanager to handle notifications:
- Slack/Discord for critical alerts
- Email for warnings
- PagerDuty for production incidents

## Maintenance
- Review alert thresholds monthly
- Update dashboards based on usage patterns
- Monitor dashboard performance and optimize queries
