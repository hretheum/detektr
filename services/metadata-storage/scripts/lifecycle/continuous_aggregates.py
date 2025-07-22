#!/usr/bin/env python3
"""
Continuous aggregates management for TimescaleDB.

Manages and monitors continuous aggregates for frame metadata.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import asyncpg
from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ContinuousAggregatesManager:
    """Manage TimescaleDB continuous aggregates."""

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

    async def check_aggregates_status(self) -> List[Dict]:
        """Check status of all continuous aggregates."""
        query = """
        SELECT
            view_name,
            format_bytes(materialization_hypertable_size) as mat_size,
            format_bytes(compression_chunk_size) as compressed_size,
            completed_threshold,
            invalidation_threshold,
            last_run_started_at,
            last_successful_finish,
            last_run_duration,
            job_status
        FROM timescaledb_information.continuous_aggregates
        LEFT JOIN timescaledb_information.job_stats
            ON continuous_aggregates.materialization_hypertable_name = job_stats.hypertable_name  # noqa: E501
        WHERE view_schema = 'metadata'
        ORDER BY view_name;
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def get_aggregate_lag(self) -> List[Dict]:
        """Get lag information for each continuous aggregate."""
        aggregates = ["frame_stats_1min", "frame_stats_hourly", "frame_stats_daily"]
        lag_info = []

        for agg in aggregates:
            # Get latest data in raw table
            raw_query = """
            SELECT MAX(timestamp) as latest_raw
            FROM metadata.frame_metadata
            """
            raw_result = await self.conn.fetchrow(raw_query)
            latest_raw = raw_result["latest_raw"] if raw_result else None

            # Get latest data in aggregate
            if agg == "frame_stats_1min":
                time_col = "minute"
            elif agg == "frame_stats_hourly":
                time_col = "hour"
            else:
                time_col = "day"

            agg_query = f"""
            SELECT MAX({time_col}) as latest_agg
            FROM metadata.{agg}
            """
            agg_result = await self.conn.fetchrow(agg_query)
            latest_agg = agg_result["latest_agg"] if agg_result else None

            lag = None
            if latest_raw and latest_agg:
                lag = latest_raw - latest_agg

            lag_info.append(
                {
                    "aggregate": agg,
                    "latest_raw": latest_raw,
                    "latest_aggregate": latest_agg,
                    "lag": str(lag) if lag else "N/A",
                }
            )

        return lag_info

    async def refresh_aggregate(
        self,
        aggregate_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        """Manually refresh a continuous aggregate."""
        if not start_time:
            from datetime import timedelta

            start_time = datetime.now() - timedelta(days=1)
        if not end_time:
            end_time = datetime.now()

        query = f"""
        CALL refresh_continuous_aggregate(
            'metadata.{aggregate_name}',
            '{start_time.isoformat()}',
            '{end_time.isoformat()}'
        );
        """

        logger.info(f"Refreshing {aggregate_name} from {start_time} to {end_time}")
        await self.conn.execute(query)
        logger.info(f"Refresh completed for {aggregate_name}")

    async def get_aggregate_stats(self, aggregate_name: str) -> Dict:
        """Get statistics for a specific aggregate."""
        if aggregate_name == "frame_stats_1min":
            time_col = "minute"
        elif aggregate_name == "frame_stats_hourly":
            time_col = "hour"
        else:
            time_col = "day"

        query = f"""
        SELECT
            COUNT(*) as row_count,
            MIN({time_col}) as oldest_data,
            MAX({time_col}) as newest_data,
            COUNT(DISTINCT camera_id) as cameras,
            AVG(frame_count) as avg_frames_per_bucket,
            AVG(avg_latency) as overall_avg_latency,
            MAX(max_latency) as overall_max_latency
        FROM metadata.{aggregate_name}
        """

        result = await self.conn.fetchrow(query)
        return dict(result) if result else {}

    async def verify_refresh_policies(self) -> List[Dict]:
        """Verify continuous aggregate refresh policies."""
        query = """
        SELECT
            application_name,
            job_id,
            schedule_interval,
            max_runtime,
            max_retries,
            retry_period,
            config->>'start_offset' as start_offset,
            config->>'end_offset' as end_offset,
            next_start,
            total_runs,
            total_successes,
            total_failures
        FROM timescaledb_information.jobs
        WHERE application_name LIKE 'Refresh Continuous Aggregate%'
        ORDER BY job_id;
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def monitor_performance(self) -> Dict:
        """Monitor aggregate query performance."""
        performance = {}

        # Test 1-minute aggregate query
        start = datetime.now()
        await self.conn.fetch(
            """
            SELECT * FROM metadata.frame_stats_1min
            WHERE minute >= NOW() - INTERVAL '1 hour'
            LIMIT 1000
        """
        )
        performance["1min_query_ms"] = (datetime.now() - start).total_seconds() * 1000

        # Test hourly aggregate query
        start = datetime.now()
        await self.conn.fetch(
            """
            SELECT * FROM metadata.frame_stats_hourly
            WHERE hour >= NOW() - INTERVAL '24 hours'
            LIMIT 1000
        """
        )
        performance["hourly_query_ms"] = (datetime.now() - start).total_seconds() * 1000

        # Test daily aggregate query
        start = datetime.now()
        await self.conn.fetch(
            """
            SELECT * FROM metadata.frame_stats_daily
            WHERE day >= NOW() - INTERVAL '30 days'
            LIMIT 1000
        """
        )
        performance["daily_query_ms"] = (datetime.now() - start).total_seconds() * 1000

        return performance


async def main():
    """Run continuous aggregates management."""
    # Connection string - adjust as needed
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    async with ContinuousAggregatesManager(conn_string) as manager:
        print("\n=== Continuous Aggregates Status ===")
        status = await manager.check_aggregates_status()
        if status:
            print(tabulate(status, headers="keys", tablefmt="grid"))
        else:
            print("No continuous aggregates found")

        print("\n=== Aggregate Lag Information ===")
        lag_info = await manager.get_aggregate_lag()
        print(tabulate(lag_info, headers="keys", tablefmt="grid"))

        print("\n=== Refresh Policies ===")
        policies = await manager.verify_refresh_policies()
        if policies:
            print(tabulate(policies, headers="keys", tablefmt="grid"))

        print("\n=== Aggregate Statistics ===")
        for agg in ["frame_stats_1min", "frame_stats_hourly", "frame_stats_daily"]:
            stats = await manager.get_aggregate_stats(agg)
            if stats:
                print(f"\n{agg}:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")

        print("\n=== Query Performance ===")
        perf = await manager.monitor_performance()
        for key, value in perf.items():
            print(f"{key}: {value:.2f}ms")


if __name__ == "__main__":
    asyncio.run(main())
