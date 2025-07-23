-- Health check script for TimescaleDB
-- Returns 1 if healthy, 0 if not

DO $$
DECLARE
    db_healthy BOOLEAN := TRUE;
    hypertable_count INTEGER;
    aggregate_count INTEGER;
    job_failures INTEGER;
BEGIN
    -- Check if TimescaleDB is loaded
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        RAISE NOTICE 'TimescaleDB extension not found';
        db_healthy := FALSE;
    END IF;

    -- Check hypertables exist
    SELECT COUNT(*) INTO hypertable_count
    FROM timescaledb_information.hypertables
    WHERE hypertable_schema IN ('tracking', 'metadata');

    IF hypertable_count < 4 THEN
        RAISE NOTICE 'Expected at least 4 hypertables, found %', hypertable_count;
        db_healthy := FALSE;
    END IF;

    -- Check continuous aggregates
    SELECT COUNT(*) INTO aggregate_count
    FROM timescaledb_information.continuous_aggregates;

    IF aggregate_count < 4 THEN
        RAISE NOTICE 'Expected at least 4 continuous aggregates, found %', aggregate_count;
        db_healthy := FALSE;
    END IF;

    -- Check for failed jobs
    SELECT COUNT(*) INTO job_failures
    FROM timescaledb_information.job_stats
    WHERE last_run_status = 'failed'
    AND last_finish > NOW() - INTERVAL '1 hour';

    IF job_failures > 0 THEN
        RAISE NOTICE 'Found % failed jobs in last hour', job_failures;
        db_healthy := FALSE;
    END IF;

    -- Final result
    IF db_healthy THEN
        RAISE NOTICE 'Database health check: PASSED';
        SELECT 1;
    ELSE
        RAISE EXCEPTION 'Database health check: FAILED';
    END IF;
END $$;
