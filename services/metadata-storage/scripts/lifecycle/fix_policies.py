#!/usr/bin/env python3
"""Fix retention and compression policies for TimescaleDB."""

import asyncio
import logging

import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_policies():
    """Fix retention policies with correct intervals."""
    conn = await asyncpg.connect(
        "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"
    )

    try:
        # First, check and remove incorrect policies
        logger.info("Checking existing retention policies...")

        existing = await conn.fetch(
            """
            SELECT
                job_id,
                hypertable_schema,
                hypertable_name,
                config->>'drop_after' as drop_after
            FROM timescaledb_information.jobs
            WHERE application_name = 'Retention Policy'
                AND hypertable_schema = 'metadata'
        """
        )

        # Remove incorrect policies
        for policy in existing:
            logger.info(
                "Removing incorrect policy for %s (job_id=%s)",
                policy["hypertable_name"],
                policy["job_id"],
            )
            try:
                await conn.execute(
                    f"SELECT remove_retention_policy('metadata.{policy['hypertable_name']}', "  # noqa: E501
                    "if_exists => true);"
                )
            except Exception as e:
                logger.warning(f"Could not remove policy: {e}")

        # Add correct retention policies
        policies = [
            ("frame_metadata", "7 days"),
            ("frame_stats_1min", "30 days"),
            ("frame_stats_hourly", "365 days"),
        ]

        for table, interval in policies:
            logger.info(f"Adding retention policy for {table}: {interval}")
            try:
                result = await conn.fetchval(
                    f"""
                    SELECT add_retention_policy('metadata.{table}',
                        INTERVAL '{interval}', if_not_exists => true);
                """
                )
                logger.info(f"Created policy job_id={result}")
            except Exception as e:
                logger.error(f"Failed to add policy for {table}: {e}")

        # Verify policies
        logger.info("\nVerifying policies...")
        final_policies = await conn.fetch(
            """
            SELECT
                hypertable_name,
                config->>'drop_after' as retention_interval
            FROM timescaledb_information.jobs
            WHERE application_name = 'Retention Policy'
                AND hypertable_schema = 'metadata'
            ORDER BY hypertable_name
        """
        )

        for policy in final_policies:
            logger.info(f"{policy['hypertable_name']}: {policy['retention_interval']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(fix_policies())
