#!/usr/bin/env python3
"""Query performance analyzer for TimescaleDB.

Analyze query performance and identify optimization opportunities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import asyncpg
from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """Analyze query performance in TimescaleDB."""

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

    async def enable_pg_stat_statements(self):
        """Enable pg_stat_statements extension if not already enabled."""
        try:
            await self.conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
            logger.info("pg_stat_statements extension enabled")
        except asyncpg.exceptions.InsufficientPrivilegeError:
            logger.warning(
                "Cannot create pg_stat_statements extension (requires superuser)"
            )
            # Check if it's already enabled
            result = await self.conn.fetchval(
                "SELECT COUNT(*) FROM pg_extension WHERE extname = 'pg_stat_statements'"
            )
            if result > 0:
                logger.info("pg_stat_statements is already enabled")
            else:
                raise

    async def get_slow_queries(self, threshold_ms: float = 10.0) -> List[Dict]:
        """Get queries slower than threshold."""
        query = """
        SELECT
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            stddev_exec_time,
            min_exec_time,
            max_exec_time,
            rows
        FROM pg_stat_statements
        WHERE query NOT LIKE '%pg_stat_statements%'
            AND query LIKE '%metadata%'
            AND mean_exec_time > $1
        ORDER BY mean_exec_time DESC
        LIMIT 20
        """

        try:
            rows = await self.conn.fetch(query, threshold_ms)
            return [dict(row) for row in rows]
        except (
            asyncpg.exceptions.UndefinedTableError,
            asyncpg.exceptions.ObjectNotInPrerequisiteStateError,
        ) as e:
            logger.warning(f"pg_stat_statements not available: {e}")
            return []

    async def analyze_common_queries(self) -> Dict[str, List[Dict]]:
        """Analyze performance of common query patterns."""
        results = {}

        # Define common query patterns to test
        query_patterns = {
            "point_lookup": {
                "name": "Point Lookup by frame_id",
                "query": """
                    SELECT * FROM metadata.frame_metadata
                    WHERE frame_id = $1
                """,
                "params": ["test_frame_001"],
            },
            "range_scan": {
                "name": "Range Scan by timestamp",
                "query": """
                    SELECT * FROM metadata.frame_metadata
                    WHERE timestamp >= $1 AND timestamp < $2
                    ORDER BY timestamp DESC
                    LIMIT 100
                """,
                "params": [
                    datetime.now() - timedelta(hours=1),
                    datetime.now(),
                ],
            },
            "camera_history": {
                "name": "Camera History Query",
                "query": """
                    SELECT * FROM metadata.frame_metadata
                    WHERE camera_id = $1
                        AND timestamp >= $2
                    ORDER BY timestamp DESC
                    LIMIT 100
                """,
                "params": ["camera_001", datetime.now() - timedelta(hours=24)],
            },
            "metadata_search": {
                "name": "JSONB Metadata Search",
                "query": """
                    SELECT * FROM metadata.frame_metadata
                    WHERE metadata @> $1::jsonb
                        AND timestamp >= $2
                    LIMIT 100
                """,
                "params": [
                    '{"motion_detected": true}',
                    datetime.now() - timedelta(hours=1),
                ],
            },
            "aggregate_1min": {
                "name": "1-Minute Aggregate Query",
                "query": """
                    SELECT * FROM metadata.frame_stats_1min
                    WHERE minute >= $1 AND minute < $2
                        AND camera_id = $3
                    ORDER BY minute DESC
                """,
                "params": [
                    datetime.now() - timedelta(hours=1),
                    datetime.now(),
                    "camera_001",
                ],
            },
        }

        for key, pattern in query_patterns.items():
            logger.info(f"Analyzing: {pattern['name']}")

            # Run EXPLAIN ANALYZE
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {pattern['query']}"

            try:
                # Execute multiple times to get average
                timings = []
                for i in range(5):
                    start = datetime.now()
                    explain_result = await self.conn.fetch(
                        explain_query, *pattern["params"]
                    )
                    execution_time = (datetime.now() - start).total_seconds() * 1000
                    timings.append(execution_time)

                # Parse execution plan
                plan_text = "\n".join([row["QUERY PLAN"] for row in explain_result])

                # Extract actual time from plan
                import re

                time_match = re.search(
                    r"Execution Time: ([\d.]+) ms", plan_text, re.IGNORECASE
                )
                actual_time = float(time_match.group(1)) if time_match else None

                results[key] = {
                    "name": pattern["name"],
                    "avg_time_ms": sum(timings) / len(timings),
                    "min_time_ms": min(timings),
                    "max_time_ms": max(timings),
                    "actual_time_ms": actual_time,
                    "plan": plan_text,
                    "status": "PASS" if actual_time and actual_time < 10 else "SLOW",
                }

            except Exception as e:
                logger.error(f"Failed to analyze {pattern['name']}: {e}")
                results[key] = {
                    "name": pattern["name"],
                    "error": str(e),
                    "status": "ERROR",
                }

        return results

    async def check_missing_indexes(self) -> List[Dict]:
        """Check for missing indexes based on query patterns."""
        query = """
        SELECT
            schemaname,
            relname as tablename,
            seq_scan,
            seq_tup_read,
            idx_scan,
            idx_tup_fetch,
            CASE
                WHEN seq_scan > 0 AND idx_scan > 0
                THEN ROUND((seq_scan::numeric / (seq_scan + idx_scan)) * 100, 2)
                WHEN seq_scan > 0 AND idx_scan = 0
                THEN 100.0
                ELSE 0
            END as seq_scan_pct,
            CASE
                WHEN seq_scan > 1000 AND (idx_scan = 0 OR seq_scan > idx_scan * 2)
                THEN 'Missing index likely'
                WHEN seq_scan > 100 AND (idx_scan = 0 OR seq_scan > idx_scan)
                THEN 'Consider index'
                ELSE 'OK'
            END as recommendation
        FROM pg_stat_user_tables
        WHERE schemaname = 'metadata'
        ORDER BY seq_scan DESC
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def analyze_index_bloat(self) -> List[Dict]:
        """Check for index bloat."""
        query = """
        WITH btree_index_atts AS (
            SELECT
                nspname,
                indexclass.relname as index_name,
                indexclass.reltuples,
                indexclass.relpages,
                tableclass.relname as tablename,
                regexp_split_to_table(indkey::text, ' ')::smallint AS attnum,
                indexrelid as index_oid
            FROM pg_index
            JOIN pg_class AS indexclass ON pg_index.indexrelid = indexclass.oid
            JOIN pg_class AS tableclass ON pg_index.indrelid = tableclass.oid
            JOIN pg_namespace ON pg_namespace.oid = indexclass.relnamespace
            WHERE nspname = 'metadata'
                AND indexclass.relkind = 'i'
                AND indexclass.relpages > 0
        ),
        index_item_sizes AS (
            SELECT
                ind_atts.nspname,
                ind_atts.index_name,
                ind_atts.reltuples,
                ind_atts.relpages,
                ind_atts.tablename,
                SUM(CASE WHEN a.atttypid = 'name'::regtype THEN 64 ELSE a.attlen END) as index_size
            FROM btree_index_atts AS ind_atts
            JOIN pg_attribute AS a ON ind_atts.attnum = a.attnum
                AND a.attrelid = ind_atts.index_oid
            GROUP BY 1, 2, 3, 4, 5
        ),
        index_aligned_est AS (
            SELECT
                index_name,
                tablename,
                reltuples::bigint AS index_entries,
                relpages::bigint AS index_pages,
                COALESCE(
                    CEIL(reltuples * (90 + index_size)::numeric / 8192),
                    0
                ) AS expected_pages
            FROM index_item_sizes
        )
        SELECT
            index_name,
            tablename,
            index_entries,
            index_pages,
            expected_pages,
            CASE
                WHEN expected_pages > 0
                THEN ROUND(((index_pages - expected_pages)::numeric / index_pages) * 100, 2)
                ELSE 0
            END AS bloat_pct,
            CASE
                WHEN index_pages > expected_pages * 1.5
                THEN 'BLOATED'
                WHEN index_pages > expected_pages * 1.2
                THEN 'MODERATE'
                ELSE 'OK'
            END AS status
        FROM index_aligned_est
        WHERE index_pages > 10
        ORDER BY bloat_pct DESC
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def get_table_statistics(self) -> List[Dict]:
        """Get table statistics for optimization."""
        query = """
        SELECT
            schemaname,
            relname as tablename,
            n_live_tup as live_rows,
            n_dead_tup as dead_rows,
            CASE
                WHEN n_live_tup > 0
                THEN ROUND((n_dead_tup::numeric / n_live_tup) * 100, 2)
                ELSE 0
            END as dead_rows_pct,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze,
            vacuum_count,
            autovacuum_count
        FROM pg_stat_user_tables
        WHERE schemaname = 'metadata'
        ORDER BY n_live_tup DESC
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def suggest_optimizations(self) -> Dict[str, List[str]]:
        """Suggest query optimizations based on analysis."""
        suggestions = {
            "indexes": [],
            "maintenance": [],
            "query_rewrites": [],
            "configuration": [],
        }

        # Check for missing indexes
        missing_indexes = await self.check_missing_indexes()
        for table in missing_indexes:
            if table["recommendation"] != "OK":
                suggestions["indexes"].append(
                    f"Table '{table['tablename']}' has "
                    f"{table['seq_scan_pct']:.1f}% "
                    f"sequential scans. Consider adding indexes."
                )

        # Check for bloated indexes
        bloated = await self.analyze_index_bloat()
        for index in bloated:
            if index["status"] == "BLOATED":
                suggestions["maintenance"].append(
                    f"Index '{index['index_name']}' is "
                    f"{index['bloat_pct']:.1f}% bloated. "
                    f"Consider REINDEX."
                )

        # Check table statistics
        stats = await self.get_table_statistics()
        for table in stats:
            if table["dead_rows_pct"] and table["dead_rows_pct"] > 20:
                suggestions["maintenance"].append(
                    f"Table '{table['tablename']}' has "
                    f"{table['dead_rows_pct']:.1f}% "
                    f"dead rows. Consider VACUUM."
                )

        # General recommendations
        suggestions["query_rewrites"].extend(
            [
                "Use prepared statements for frequently executed queries",
                "Consider partial indexes for queries with WHERE conditions",
                "Use LIMIT for exploratory queries",
                "Prefer time-based queries over full table scans",
            ]
        )

        suggestions["configuration"].extend(
            [
                "Ensure shared_buffers is at least 25% of RAM",
                "Set effective_cache_size to 50-75% of RAM",
                "Enable parallel query execution for large scans",
                "Configure work_mem based on concurrent connections",
            ]
        )

        return suggestions


async def optimize_specific_queries():
    """Run specific query optimizations."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    async with QueryAnalyzer(conn_string) as analyzer:
        logger.info("Creating optimized indexes...")

        # Create partial index for motion detection queries
        try:
            await analyzer.conn.execute(
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_motion_detected
                ON metadata.frame_metadata (camera_id, timestamp)
                WHERE (metadata->>'motion_detected')::boolean = true
            """
            )
            logger.info("Created partial index for motion detection")
        except Exception as e:
            logger.error(f"Failed to create motion index: {e}")

        # Create index for aggregate queries
        try:
            await analyzer.conn.execute(
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stats_camera_time
                ON metadata.frame_stats_1min (camera_id, minute DESC)
            """
            )
            logger.info("Created index for 1-minute stats")
        except Exception as e:
            logger.error(f"Failed to create stats index: {e}")

        # Analyze tables to update statistics
        logger.info("Updating table statistics...")
        await analyzer.conn.execute("ANALYZE metadata.frame_metadata")
        await analyzer.conn.execute("ANALYZE metadata.frame_stats_1min")
        await analyzer.conn.execute("ANALYZE metadata.frame_stats_hourly")
        await analyzer.conn.execute("ANALYZE metadata.frame_stats_daily")


async def main():
    """Run query performance analysis."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    async with QueryAnalyzer(conn_string) as analyzer:
        # Enable pg_stat_statements
        await analyzer.enable_pg_stat_statements()

        print("\n=== Query Performance Analysis ===")

        # Analyze common queries
        print("\n📊 Common Query Patterns:")
        query_results = await analyzer.analyze_common_queries()

        for key, result in query_results.items():
            print(f"\n{result['name']}:")
            if "error" in result:
                print(f"  ❌ Error: {result['error']}")
            else:
                status_icon = "✅" if result["status"] == "PASS" else "⚠️"
                print(f"  {status_icon} Status: {result['status']}")
                print(f"  ⏱️  Average: {result['avg_time_ms']:.2f}ms")
                if result["actual_time_ms"]:
                    print(f"  ⏱️  Actual: {result['actual_time_ms']:.2f}ms")

        # Check for slow queries
        print("\n🐌 Slow Queries (>10ms):")
        slow_queries = await analyzer.get_slow_queries()
        if slow_queries:
            headers = [
                "Query",
                "Calls",
                "Mean Time (ms)",
                "Total Time (ms)",
                "Rows",
            ]
            data = [
                [
                    q["query"][:50] + "..." if len(q["query"]) > 50 else q["query"],
                    q["calls"],
                    f"{q['mean_exec_time']:.2f}",
                    f"{q['total_exec_time']:.2f}",
                    q["rows"],
                ]
                for q in slow_queries
            ]
            print(tabulate(data, headers=headers, tablefmt="grid"))
        else:
            print("  ✅ No slow queries found")

        # Check missing indexes
        print("\n🔍 Index Usage Analysis:")
        missing = await analyzer.check_missing_indexes()
        if missing:
            print(tabulate(missing, headers="keys", tablefmt="grid", floatfmt=".2f"))

        # Check index bloat
        print("\n💨 Index Bloat Analysis:")
        bloat = await analyzer.analyze_index_bloat()
        if bloat:
            print(tabulate(bloat, headers="keys", tablefmt="grid", floatfmt=".2f"))

        # Table statistics
        print("\n📈 Table Statistics:")
        stats = await analyzer.get_table_statistics()
        if stats:
            # Only show relevant columns
            display_stats = [
                {
                    "table": s["tablename"],
                    "live_rows": s["live_rows"],
                    "dead_rows_pct": f"{s['dead_rows_pct']:.1f}%",
                    "last_vacuum": s["last_vacuum"],
                    "last_analyze": s["last_analyze"],
                }
                for s in stats
            ]
            print(tabulate(display_stats, headers="keys", tablefmt="grid"))

        # Get optimization suggestions
        print("\n💡 Optimization Suggestions:")
        suggestions = await analyzer.suggest_optimizations()

        for category, items in suggestions.items():
            if items:
                print(f"\n{category.upper()}:")
                for suggestion in items:
                    print(f"  • {suggestion}")

        # Ask if user wants to apply optimizations
        optimize = input("\n🚀 Apply recommended optimizations? (y/n): ")
        if optimize.lower() == "y":
            await optimize_specific_queries()
            print("\n✅ Optimizations applied!")


if __name__ == "__main__":
    asyncio.run(main())
