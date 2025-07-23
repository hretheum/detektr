#!/usr/bin/env python3
"""Cache optimization for TimescaleDB.

Monitor and optimize buffer cache performance.
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


class CacheOptimizer:
    """Optimize cache performance for TimescaleDB."""

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

    async def get_cache_hit_ratio(self) -> Dict:
        """Get buffer cache hit ratio."""
        query = """
        SELECT
            sum(heap_blks_read) as heap_read,
            sum(heap_blks_hit) as heap_hit,
            sum(idx_blks_read) as idx_read,
            sum(idx_blks_hit) as idx_hit,
            CASE
                WHEN sum(heap_blks_hit) + sum(heap_blks_read) > 0
                THEN round(
                    sum(heap_blks_hit)::numeric /
                    (sum(heap_blks_hit) + sum(heap_blks_read)) * 100, 2
                )
                ELSE 0
            END as heap_hit_ratio,
            CASE
                WHEN sum(idx_blks_hit) + sum(idx_blks_read) > 0
                THEN round(
                    sum(idx_blks_hit)::numeric /
                    (sum(idx_blks_hit) + sum(idx_blks_read)) * 100, 2
                )
                ELSE 0
            END as idx_hit_ratio
        FROM pg_statio_user_tables
        WHERE schemaname = 'metadata'
        """

        result = await self.conn.fetchrow(query)
        return dict(result) if result else {}

    async def get_table_cache_stats(self) -> List[Dict]:
        """Get cache statistics per table."""
        query = """
        SELECT
            schemaname,
            relname as tablename,
            heap_blks_read,
            heap_blks_hit,
            idx_blks_read,
            idx_blks_hit,
            CASE
                WHEN heap_blks_hit + heap_blks_read > 0
                THEN round(
                    heap_blks_hit::numeric /
                    (heap_blks_hit + heap_blks_read) * 100, 2
                )
                ELSE 0
            END as heap_hit_ratio,
            CASE
                WHEN idx_blks_hit + idx_blks_read > 0
                THEN round(
                    idx_blks_hit::numeric /
                    (idx_blks_hit + idx_blks_read) * 100, 2
                )
                ELSE 0
            END as idx_hit_ratio
        FROM pg_statio_user_tables
        WHERE schemaname = 'metadata'
        ORDER BY heap_blks_read + idx_blks_read DESC
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def get_buffer_usage(self) -> List[Dict]:
        """Get buffer usage by relation."""
        query = """
        SELECT
            c.relname,
            pg_size_pretty(pg_relation_size(c.oid)) AS size,
            count(*) AS buffers,
            round(
                count(*)::numeric * 8192 / pg_relation_size(c.oid) * 100, 2
            ) AS percent_cached
        FROM pg_buffercache b
        INNER JOIN pg_class c ON b.relfilenode = pg_relation_filenode(c.oid)
        WHERE c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'metadata')
            AND c.relkind IN ('r', 'i')
        GROUP BY c.oid, c.relname
        HAVING count(*) > 0
        ORDER BY count(*) DESC
        """

        try:
            rows = await self.conn.fetch(query)
            return [dict(row) for row in rows]
        except asyncpg.exceptions.UndefinedTableError:
            logger.warning("pg_buffercache extension not available")
            return []

    async def get_memory_settings(self) -> Dict:
        """Get memory-related configuration settings."""
        settings = {}

        queries = {
            "shared_buffers": "SHOW shared_buffers",
            "effective_cache_size": "SHOW effective_cache_size",
            "work_mem": "SHOW work_mem",
            "maintenance_work_mem": "SHOW maintenance_work_mem",
            "max_connections": "SHOW max_connections",
        }

        for name, query in queries.items():
            result = await self.conn.fetchval(query)
            settings[name] = result

        # Get system memory info
        try:
            mem_query = """
            SELECT
                pg_size_pretty(
                    pg_size_bytes(current_setting('shared_buffers'))
                ) as shared_buffers_pretty,
                round(
                    pg_size_bytes(current_setting('shared_buffers'))::numeric /
                    (SELECT setting::bigint * 8192
                     FROM pg_settings
                     WHERE name = 'block_size') * 100, 2
                ) as shared_buffers_pct
            """
            mem_info = await self.conn.fetchrow(mem_query)
            settings.update(dict(mem_info))
        except Exception as e:
            logger.warning(f"Could not get memory info: {e}")

        return settings

    async def warm_cache(self, table_name: str):
        """Warm the cache for a specific table."""
        logger.info(f"Warming cache for {table_name}...")

        # Use pg_prewarm if available
        try:
            await self.conn.execute("CREATE EXTENSION IF NOT EXISTS pg_prewarm")
            await self.conn.execute(f"SELECT pg_prewarm('metadata.{table_name}')")
            logger.info(f"Cache warmed using pg_prewarm for {table_name}")
        except Exception:
            # Fallback to manual warming
            logger.info("pg_prewarm not available, using manual warming...")
            await self.conn.execute(f"SELECT COUNT(*) FROM metadata.{table_name}")
            logger.info(f"Manual cache warming completed for {table_name}")

    async def analyze_cache_efficiency(self) -> Dict[str, List[str]]:
        """Analyze cache efficiency and provide recommendations."""
        recommendations = {
            "critical": [],
            "warning": [],
            "info": [],
        }

        # Check overall hit ratio
        hit_ratio = await self.get_cache_hit_ratio()
        heap_ratio = hit_ratio.get("heap_hit_ratio", 0)
        idx_ratio = hit_ratio.get("idx_hit_ratio", 0)

        if heap_ratio < 90:
            recommendations["critical"].append(
                f"Heap cache hit ratio is {heap_ratio}% (should be >90%). "
                "Consider increasing shared_buffers."
            )
        elif heap_ratio < 95:
            recommendations["warning"].append(
                f"Heap cache hit ratio is {heap_ratio}% (optimal is >95%)."
            )

        if idx_ratio < 95:
            recommendations["warning"].append(
                f"Index cache hit ratio is {idx_ratio}% (should be >95%). "
                "Indexes may not fit in memory."
            )

        # Check table-specific stats
        table_stats = await self.get_table_cache_stats()
        for table in table_stats:
            if table["heap_hit_ratio"] < 85:
                recommendations["warning"].append(
                    f"Table '{table['tablename']}' has low cache hit ratio: "
                    f"{table['heap_hit_ratio']}%"
                )

        # Check memory settings
        settings = await self.get_memory_settings()

        # Parse shared_buffers
        shared_buffers_str = settings.get("shared_buffers", "128MB")
        if "MB" in shared_buffers_str:
            shared_mb = int(shared_buffers_str.replace("MB", ""))
        elif "GB" in shared_buffers_str:
            shared_mb = int(shared_buffers_str.replace("GB", "")) * 1024
        else:
            shared_mb = 128  # Default

        if shared_mb < 1024:  # Less than 1GB
            recommendations["critical"].append(
                f"shared_buffers is only {shared_buffers_str}. "
                "Recommend at least 1GB for production."
            )

        # General recommendations
        recommendations["info"].extend(
            [
                "Monitor cache hit ratios during peak load",
                "Use pg_prewarm to warm critical tables after restart",
                "Consider using huge pages for large shared_buffers",
                "Enable track_io_timing for detailed I/O statistics",
            ]
        )

        return recommendations


async def optimize_cache_settings():
    """Apply cache optimization settings."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    async with CacheOptimizer(conn_string) as optimizer:
        logger.info("Applying cache optimizations...")

        # Warm critical tables
        tables = ["frame_metadata", "frame_stats_1min", "frame_stats_hourly"]

        for table in tables:
            try:
                await optimizer.warm_cache(table)
            except Exception as e:
                logger.error(f"Failed to warm cache for {table}: {e}")

        logger.info("Cache optimization completed")


async def main():
    """Run cache optimization analysis."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    async with CacheOptimizer(conn_string) as optimizer:
        print("\n" + "=" * 60)
        print("🧠 CACHE OPTIMIZATION ANALYSIS")
        print("=" * 60)

        # Get overall cache hit ratio
        print("\n📊 Overall Cache Hit Ratios:")
        hit_ratio = await optimizer.get_cache_hit_ratio()
        if hit_ratio:
            heap_ratio = hit_ratio["heap_hit_ratio"]
            idx_ratio = hit_ratio["idx_hit_ratio"]

            heap_status = "✅" if heap_ratio >= 95 else "⚠️" if heap_ratio >= 90 else "❌"
            idx_status = "✅" if idx_ratio >= 95 else "⚠️" if idx_ratio >= 90 else "❌"

            print(f"  {heap_status} Heap Hit Ratio: {heap_ratio}%")
            print(f"  {idx_status} Index Hit Ratio: {idx_ratio}%")
            print(f"  📖 Heap Reads: {hit_ratio['heap_read']:,}")
            print(f"  ✨ Heap Hits: {hit_ratio['heap_hit']:,}")

        # Get per-table cache stats
        print("\n📋 Per-Table Cache Statistics:")
        table_stats = await optimizer.get_table_cache_stats()
        if table_stats:
            print(
                tabulate(table_stats, headers="keys", tablefmt="grid", floatfmt=".2f")
            )

        # Get buffer usage
        print("\n💾 Buffer Usage by Relation:")
        buffer_usage = await optimizer.get_buffer_usage()
        if buffer_usage:
            print(
                tabulate(
                    buffer_usage[:10],  # Top 10
                    headers="keys",
                    tablefmt="grid",
                    floatfmt=".2f",
                )
            )
        else:
            print("  ℹ️  pg_buffercache extension not available")

        # Get memory settings
        print("\n⚙️  Memory Configuration:")
        settings = await optimizer.get_memory_settings()
        for key, value in settings.items():
            if not key.endswith("_pretty") and not key.endswith("_pct"):
                print(f"  {key}: {value}")

        # Get recommendations
        print("\n💡 Cache Optimization Recommendations:")
        recommendations = await optimizer.analyze_cache_efficiency()

        if recommendations["critical"]:
            print("\n❌ CRITICAL:")
            for rec in recommendations["critical"]:
                print(f"  • {rec}")

        if recommendations["warning"]:
            print("\n⚠️  WARNING:")
            for rec in recommendations["warning"]:
                print(f"  • {rec}")

        if recommendations["info"]:
            print("\nℹ️  INFO:")
            for rec in recommendations["info"]:
                print(f"  • {rec}")

        # Ask if user wants to warm caches
        warm = input("\n🔥 Warm critical table caches? (y/n): ")
        if warm.lower() == "y":
            await optimize_cache_settings()
            print("\n✅ Cache warming completed!")


if __name__ == "__main__":
    asyncio.run(main())
