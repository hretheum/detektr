#!/usr/bin/env python3
"""
Retention policies management for TimescaleDB.

Manages data retention and automated cleanup.
"""

import asyncio
import logging
from typing import Dict, List, Optional

import asyncpg
from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RetentionPolicyManager:
    """Manage TimescaleDB retention policies."""

    def __init__(self, connection_string: str):
        """Initialize with database connection string."""
        self.connection_string = connection_string
        self.conn: Optional[asyncpg.Connection] = None

    async def __aenter__(self):
        """Enter async context."""
        self.conn = await asyncpg.connect(self.connection_string)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self.conn:
            await self.conn.close()

    async def get_retention_policies(self) -> List[Dict]:
        """Get all active retention policies."""
        query = """
        SELECT
            hypertable_schema,
            hypertable_name,
            job_id,
            schedule_interval,
            config->>'drop_after' as retention_interval,
            next_start,
            total_runs,
            total_successes,
            total_failures,
            last_run_status,
            last_run_started_at,
            last_successful_finish
        FROM timescaledb_information.jobs
        WHERE application_name = 'Retention Policy'
        ORDER BY hypertable_schema, hypertable_name;
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def get_data_distribution(self) -> List[Dict]:
        """Get data distribution by age for each hypertable."""
        tables = [
            ("metadata", "frame_metadata", "timestamp"),
            ("metadata", "frame_stats_1min", "minute"),
            ("metadata", "frame_stats_hourly", "hour"),
            ("metadata", "frame_stats_daily", "day"),
        ]

        distribution = []
        for schema, table, time_col in tables:
            query = f"""
            WITH age_buckets AS (
                SELECT
                    CASE
                        WHEN {time_col} >= NOW() - INTERVAL '1 day' THEN '< 1 day'
                        WHEN {time_col} >= NOW() - INTERVAL '7 days' THEN '1-7 days'
                        WHEN {time_col} >= NOW() - INTERVAL '30 days' THEN '7-30 days'
                        WHEN {time_col} >= NOW() - INTERVAL '90 days' THEN '30-90 days'
                        WHEN {time_col} >= NOW() - INTERVAL '365 days' THEN '90-365 days'  # noqa: E501
                        ELSE '> 1 year'
                    END as age_bucket,
                    COUNT(*) as row_count
                FROM {schema}.{table}
                GROUP BY age_bucket
            )
            SELECT
                '{table}' as table_name,
                age_bucket,
                row_count,
                pg_size_pretty(row_count * 100) as estimated_size
            FROM age_buckets
            ORDER BY
                CASE age_bucket
                    WHEN '< 1 day' THEN 1
                    WHEN '1-7 days' THEN 2
                    WHEN '7-30 days' THEN 3
                    WHEN '30-90 days' THEN 4
                    WHEN '90-365 days' THEN 5
                    ELSE 6
                END;
            """

            rows = await self.conn.fetch(query)
            distribution.extend([dict(row) for row in rows])

        return distribution

    async def estimate_cleanup_impact(self) -> Dict:
        """Estimate the impact of running retention policies."""
        impact = {}

        # Raw data (7 days retention)
        raw_query = """
        SELECT
            COUNT(*) as rows_to_delete,
            pg_size_pretty(COUNT(*) * 100) as size_to_free
        FROM metadata.frame_metadata
        WHERE timestamp < NOW() - INTERVAL '7 days';
        """
        raw_result = await self.conn.fetchrow(raw_query)
        impact["frame_metadata"] = dict(raw_result) if raw_result else {}

        # 1-minute aggregates (30 days retention)
        min_query = """
        SELECT
            COUNT(*) as rows_to_delete,
            pg_size_pretty(COUNT(*) * 50) as size_to_free
        FROM metadata.frame_stats_1min
        WHERE minute < NOW() - INTERVAL '30 days';
        """
        min_result = await self.conn.fetchrow(min_query)
        impact["frame_stats_1min"] = dict(min_result) if min_result else {}

        # Hourly aggregates (365 days retention)
        hour_query = """
        SELECT
            COUNT(*) as rows_to_delete,
            pg_size_pretty(COUNT(*) * 50) as size_to_free
        FROM metadata.frame_stats_hourly
        WHERE hour < NOW() - INTERVAL '365 days';
        """
        hour_result = await self.conn.fetchrow(hour_query)
        impact["frame_stats_hourly"] = dict(hour_result) if hour_result else {}

        return impact

    async def verify_retention_effectiveness(self) -> Dict:
        """Verify that retention policies are working effectively."""
        effectiveness = {}

        # Check oldest data in each table
        tables = [
            ("metadata", "frame_metadata", "timestamp", 7),
            ("metadata", "frame_stats_1min", "minute", 30),
            ("metadata", "frame_stats_hourly", "hour", 365),
        ]

        for schema, table, time_col, expected_days in tables:
            query = f"""
            SELECT
                MIN({time_col}) as oldest_data,
                MAX({time_col}) as newest_data,
                NOW() - MIN({time_col}) as actual_retention,
                INTERVAL '{expected_days} days' as expected_retention,
                CASE
                    WHEN NOW() - MIN({time_col}) > INTERVAL '{expected_days + 1} days'
                    THEN 'POLICY NOT WORKING'
                    ELSE 'OK'
                END as status
            FROM {schema}.{table};
            """

            result = await self.conn.fetchrow(query)
            effectiveness[table] = dict(result) if result else {}

        return effectiveness

    async def run_manual_cleanup(self, table_name: str, older_than_days: int):
        """Manually run cleanup for a specific table."""
        logger.info(
            "Running manual cleanup for %s (data older than %s days)",
            table_name,
            older_than_days,
        )

        # Get count before cleanup
        count_query = f"""
        SELECT COUNT(*) as count_before
        FROM metadata.{table_name}
        WHERE timestamp < NOW() - INTERVAL '{older_than_days} days';
        """
        before = await self.conn.fetchrow(count_query)
        count_before = before["count_before"] if before else 0

        # Run cleanup
        if count_before > 0:
            delete_query = f"""
            DELETE FROM metadata.{table_name}
            WHERE timestamp < NOW() - INTERVAL '{older_than_days} days';
            """
            await self.conn.execute(delete_query)
            logger.info(f"Deleted {count_before} rows from {table_name}")
        else:
            logger.info(f"No rows to delete from {table_name}")

        return count_before

    async def get_chunk_statistics(self) -> List[Dict]:
        """Get statistics about TimescaleDB chunks."""
        query = """
        SELECT
            hypertable_schema,
            hypertable_name,
            chunk_schema,
            chunk_name,
            range_start,
            range_end,
            is_compressed,
            before_compression_total_bytes,
            after_compression_total_bytes,
            CASE
                WHEN before_compression_total_bytes > 0
                THEN round((1 - after_compression_total_bytes::numeric /
                           before_compression_total_bytes) * 100, 2)
                ELSE 0
            END as compression_ratio_pct
        FROM timescaledb_information.chunks
        WHERE hypertable_schema = 'metadata'
        ORDER BY hypertable_name, range_start DESC
        LIMIT 50;
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]


async def test_retention_policies():
    """Test retention policy functionality."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    async with RetentionPolicyManager(conn_string) as manager:
        # Insert test data with old timestamps
        logger.info("Inserting test data with old timestamps...")

        # Insert data that should be cleaned up
        old_data_query = """
        INSERT INTO metadata.frame_metadata (frame_id, timestamp, camera_id, sequence_number, metadata)
        VALUES
            ('test_old_1', NOW() - INTERVAL '8 days', 'test_cam', 1, '{"test": true}'::jsonb),  # noqa: E501
            ('test_old_2', NOW() - INTERVAL '10 days', 'test_cam', 2, '{"test": true}'::jsonb),  # noqa: E501
            ('test_old_3', NOW() - INTERVAL '15 days', 'test_cam', 3, '{"test": true}'::jsonb);  # noqa: E501
        """
        await manager.conn.execute(old_data_query)

        # Verify data exists
        count_before = await manager.conn.fetchval(
            "SELECT COUNT(*) FROM metadata.frame_metadata WHERE camera_id = 'test_cam'"
        )
        logger.info(f"Test data inserted: {count_before} rows")

        # Run manual cleanup (simulating retention policy)
        deleted = await manager.run_manual_cleanup("frame_metadata", 7)

        # Verify cleanup worked
        count_after = await manager.conn.fetchval(
            "SELECT COUNT(*) FROM metadata.frame_metadata WHERE camera_id = 'test_cam'"
        )
        logger.info(f"After cleanup: {count_after} rows (deleted {deleted})")

        # Clean up test data
        await manager.conn.execute(
            "DELETE FROM metadata.frame_metadata WHERE camera_id = 'test_cam'"
        )


async def main():
    """Run retention policy management."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    async with RetentionPolicyManager(conn_string) as manager:
        print("\n=== Active Retention Policies ===")
        policies = await manager.get_retention_policies()
        if policies:
            print(tabulate(policies, headers="keys", tablefmt="grid"))
        else:
            print("No retention policies found")

        print("\n=== Data Distribution by Age ===")
        distribution = await manager.get_data_distribution()
        if distribution:
            print(tabulate(distribution, headers="keys", tablefmt="grid"))

        print("\n=== Estimated Cleanup Impact ===")
        impact = await manager.estimate_cleanup_impact()
        for table, stats in impact.items():
            print(f"\n{table}:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        print("\n=== Retention Policy Effectiveness ===")
        effectiveness = await manager.verify_retention_effectiveness()
        for table, stats in effectiveness.items():
            print(f"\n{table}:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        print("\n=== Chunk Statistics ===")
        chunks = await manager.get_chunk_statistics()
        if chunks:
            print(tabulate(chunks[:10], headers="keys", tablefmt="grid"))

        # Run test if requested
        test = input("\nRun retention policy test? (y/n): ")
        if test.lower() == "y":
            await test_retention_policies()


if __name__ == "__main__":
    asyncio.run(main())
