#!/bin/bash
# Database monitoring script for stability validation

set -e

MONITORING_DURATION=${1:-3600}  # Default 1 hour
INTERVAL=60  # Check every minute

echo "Starting database stability monitoring for $MONITORING_DURATION seconds..."
echo "Checking every $INTERVAL seconds"

START_TIME=$(date +%s)
END_TIME=$((START_TIME + MONITORING_DURATION))
CHECK_COUNT=0
ERROR_COUNT=0

# Log file
LOG_FILE="/tmp/db-monitor-$(date +%Y%m%d-%H%M%S).log"

while [ "$(date +%s)" -lt "$END_TIME" ]; do
    CHECK_COUNT=$((CHECK_COUNT + 1))
    CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$CURRENT_TIME] Check #$CHECK_COUNT" | tee -a "$LOG_FILE"

    # 1. Check PostgreSQL health
    if docker exec detektor-postgres-1 pg_isready -U detektor -d detektor_db >/dev/null 2>&1; then
        echo "  ✓ PostgreSQL: Healthy" | tee -a "$LOG_FILE"
    else
        echo "  ✗ PostgreSQL: Not responding!" | tee -a "$LOG_FILE"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi

    # 2. Check PgBouncer health
    if docker exec detektor-pgbouncer-1 pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo "  ✓ PgBouncer: Healthy" | tee -a "$LOG_FILE"
    else
        echo "  ✗ PgBouncer: Not responding!" | tee -a "$LOG_FILE"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi

    # 3. Check connection count
    CONN_COUNT=$(docker exec detektor-postgres-1 psql -U detektor -d detektor_db -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='detektor_db';" 2>/dev/null | xargs)
    echo "  → Active connections: $CONN_COUNT" | tee -a "$LOG_FILE"

    # 4. Check database size
    DB_SIZE=$(docker exec detektor-postgres-1 psql -U detektor -d detektor_db -t -c "SELECT pg_size_pretty(pg_database_size('detektor_db'));" 2>/dev/null | xargs)
    echo "  → Database size: $DB_SIZE" | tee -a "$LOG_FILE"

    # 5. Check for long-running queries
    LONG_QUERIES=$(docker exec detektor-postgres-1 psql -U detektor -d detektor_db -t -c "SELECT count(*) FROM pg_stat_activity WHERE state != 'idle' AND query_start < now() - interval '5 minutes';" 2>/dev/null | xargs)
    if [ "$LONG_QUERIES" -gt 0 ]; then
        echo "  ⚠ Long-running queries: $LONG_QUERIES" | tee -a "$LOG_FILE"
    fi

    # 6. Check TimescaleDB jobs
    FAILED_JOBS=$(docker exec detektor-postgres-1 psql -U detektor -d detektor_db -t -c "SELECT count(*) FROM timescaledb_information.job_stats WHERE last_run_status = 'failed' AND last_finish > NOW() - INTERVAL '1 hour';" 2>/dev/null | xargs)
    if [ "$FAILED_JOBS" -gt 0 ]; then
        echo "  ⚠ Failed TimescaleDB jobs: $FAILED_JOBS" | tee -a "$LOG_FILE"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi

    # 7. Check resource usage
    CONTAINER_STATS=$(docker stats detektor-postgres-1 --no-stream --format "CPU: {{.CPUPerc}} | MEM: {{.MemUsage}}")
    echo "  → Resources: $CONTAINER_STATS" | tee -a "$LOG_FILE"

    echo "" | tee -a "$LOG_FILE"

    # Sleep until next check
    sleep $INTERVAL
done

# Final report
DURATION=$(($(date +%s) - START_TIME))
echo "===== STABILITY MONITORING REPORT =====" | tee -a "$LOG_FILE"
echo "Duration: $DURATION seconds" | tee -a "$LOG_FILE"
echo "Total checks: $CHECK_COUNT" | tee -a "$LOG_FILE"
echo "Errors detected: $ERROR_COUNT" | tee -a "$LOG_FILE"
echo "Error rate: $(awk "BEGIN {printf \"%.2f\", $ERROR_COUNT/$CHECK_COUNT*100}")%" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"

if [ $ERROR_COUNT -eq 0 ]; then
    echo "✅ STABILITY TEST: PASSED" | tee -a "$LOG_FILE"
    exit 0
else
    echo "❌ STABILITY TEST: FAILED" | tee -a "$LOG_FILE"
    exit 1
fi
