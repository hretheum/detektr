#!/usr/bin/env python3
"""
Compression policies management for TimescaleDB.

Manages data compression for storage optimization.
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


class CompressionPolicyManager:
    """Manage TimescaleDB compression policies."""

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

    async def check_compression_support(self) -> bool:
        """Check if compression is available (requires license)."""
        query = """
        SELECT EXISTS (
            SELECT 1
            FROM pg_proc
            WHERE proname = 'compress_chunk'
        ) as compression_available;
        """
        result = await self.conn.fetchrow(query)
        return result["compression_available"] if result else False

    async def get_compression_settings(self) -> List[Dict]:
        """Get compression settings for all hypertables."""
        query = """
        SELECT
            ht.schema_name,
            ht.table_name,
            hc.segmentby,
            hc.orderby,
            hc.orderby_desc,
            hc.orderby_nullsfirst
        FROM _timescaledb_catalog.hypertable ht
        LEFT JOIN _timescaledb_catalog.compression_settings hc
            ON ht.id = hc.hypertable_id
        WHERE ht.schema_name = 'metadata'
        ORDER BY ht.table_name;
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def get_compression_status(self) -> List[Dict]:
        """Get compression status for all chunks."""
        query = """
        SELECT
            hypertable_schema,
            hypertable_name,
            COUNT(*) as total_chunks,
            COUNT(CASE WHEN is_compressed THEN 1 END) as compressed_chunks,
            ROUND(
                COUNT(CASE WHEN is_compressed THEN 1 END)::numeric /
                COUNT(*)::numeric * 100, 2
            ) as compression_pct,
            pg_size_pretty(SUM(before_compression_total_bytes)) as uncompressed_size,
            pg_size_pretty(SUM(after_compression_total_bytes)) as compressed_size,
            CASE
                WHEN SUM(before_compression_total_bytes) > 0
                THEN ROUND(
                    (1 - SUM(after_compression_total_bytes)::numeric /
                    SUM(before_compression_total_bytes)::numeric) * 100, 2
                )
                ELSE 0
            END as overall_compression_ratio
        FROM timescaledb_information.chunks
        WHERE hypertable_schema = 'metadata'
        GROUP BY hypertable_schema, hypertable_name
        ORDER BY hypertable_name;
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def analyze_compression_candidates(self) -> List[Dict]:
        """Find chunks that are good candidates for compression."""
        query = """
        SELECT
            chunk_schema,
            chunk_name,
            hypertable_name,
            range_start,
            range_end,
            pg_size_pretty(before_compression_total_bytes) as size,
            EXTRACT(EPOCH FROM (NOW() - range_end)) / 86400 as days_old
        FROM timescaledb_information.chunks
        WHERE hypertable_schema = 'metadata'
            AND NOT is_compressed
            AND before_compression_total_bytes > 1024 * 1024  -- > 1MB
            AND range_end < NOW() - INTERVAL '1 day'  -- Older than 1 day
        ORDER BY before_compression_total_bytes DESC
        LIMIT 20;
        """

        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def estimate_compression_savings(self) -> Dict:
        """Estimate potential compression savings."""
        # Sample compression ratios based on typical data
        compression_ratios = {
            "frame_metadata": 0.85,  # JSON data compresses well
            "frame_stats_1min": 0.70,  # Aggregated numeric data
            "frame_stats_hourly": 0.65,  # Less repetition
            "frame_stats_daily": 0.60,  # Least repetition
        }

        savings = {}
        for table, ratio in compression_ratios.items():
            query = f"""
            SELECT
                pg_size_pretty(pg_relation_size('metadata.{table}')) as current_size,
                pg_relation_size('metadata.{table}') as size_bytes,
                pg_size_pretty(
                    pg_relation_size('metadata.{table}') * {ratio}
                ) as estimated_compressed_size,
                pg_size_pretty(
                    pg_relation_size('metadata.{table}') * {1 - ratio}
                ) as estimated_savings
            """

            result = await self.conn.fetchrow(query)
            if result:
                savings[table] = dict(result)
                savings[table]["compression_ratio"] = f"{ratio * 100:.0f}%"

        return savings

    async def setup_compression_policy(self, table_name: str, compress_after_days: int):
        """Set up compression policy for a hypertable."""
        logger.info(f"Setting up compression for {table_name}")

        # First, ensure compression is enabled on the hypertable
        try:
            # Enable compression with appropriate settings
            if table_name == "frame_metadata":
                # For raw data, segment by camera_id for better query performance
                query = f"""
                ALTER TABLE metadata.{table_name}
                SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'camera_id',
                    timescaledb.compress_orderby = 'timestamp DESC'
                );
                """
            else:
                # For aggregates, segment by camera_id if available
                query = f"""
                ALTER TABLE metadata.{table_name}
                SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'camera_id'
                );
                """

            await self.conn.execute(query)
            logger.info(f"Compression enabled for {table_name}")

            # Add compression policy
            policy_query = f"""
            SELECT add_compression_policy(
                'metadata.{table_name}',
                INTERVAL '{compress_after_days} days',
                if_not_exists => true
            );
            """

            result = await self.conn.fetchval(policy_query)
            logger.info(f"Compression policy added for {table_name}: job_id={result}")

        except asyncpg.exceptions.PostgresError as e:
            logger.error(f"Failed to set up compression for {table_name}: {e}")
            return False

        return True

    async def compress_chunk_manually(self, chunk_name: str):
        """Manually compress a specific chunk."""
        logger.info(f"Manually compressing chunk: {chunk_name}")

        try:
            query = f"SELECT compress_chunk('{chunk_name}');"
            result = await self.conn.fetchrow(query)
            logger.info(f"Compression result: {dict(result)}")
            return True
        except asyncpg.exceptions.PostgresError as e:
            logger.error(f"Failed to compress chunk {chunk_name}: {e}")
            return False

    async def decompress_chunk(self, chunk_name: str):
        """Decompress a specific chunk."""
        logger.info(f"Decompressing chunk: {chunk_name}")

        try:
            query = f"SELECT decompress_chunk('{chunk_name}');"
            await self.conn.execute(query)
            logger.info(f"Chunk {chunk_name} decompressed successfully")
            return True
        except asyncpg.exceptions.PostgresError as e:
            logger.error(f"Failed to decompress chunk {chunk_name}: {e}")
            return False

    async def benchmark_compression(self, table_name: str, sample_size: int = 1000):
        """Benchmark query performance on compressed vs uncompressed data."""
        logger.info(f"Benchmarking compression for {table_name}")

        # Find a compressed and uncompressed chunk
        chunk_query = """
        SELECT
            chunk_name,
            is_compressed,
            before_compression_total_bytes,
            after_compression_total_bytes
        FROM timescaledb_information.chunks
        WHERE hypertable_name = %s
            AND hypertable_schema = 'metadata'
        ORDER BY range_end DESC
        LIMIT 10;
        """

        chunks = await self.conn.fetch(chunk_query, table_name)

        compressed_chunk = None
        uncompressed_chunk = None

        for chunk in chunks:
            if chunk["is_compressed"] and not compressed_chunk:
                compressed_chunk = chunk["chunk_name"]
            elif not chunk["is_compressed"] and not uncompressed_chunk:
                uncompressed_chunk = chunk["chunk_name"]

        if not compressed_chunk or not uncompressed_chunk:
            logger.warning(
                "Could not find both compressed and uncompressed "
                "chunks for benchmarking"
            )
            return {}

        # Benchmark queries
        results = {}

        # Test on uncompressed chunk
        start = datetime.now()
        await self.conn.fetch(f"SELECT * FROM {uncompressed_chunk} LIMIT {sample_size}")
        uncompressed_time = (datetime.now() - start).total_seconds() * 1000

        # Test on compressed chunk
        start = datetime.now()
        await self.conn.fetch(f"SELECT * FROM {compressed_chunk} LIMIT {sample_size}")
        compressed_time = (datetime.now() - start).total_seconds() * 1000

        results["uncompressed_query_ms"] = uncompressed_time
        results["compressed_query_ms"] = compressed_time
        results[
            "performance_impact"
        ] = f"{(compressed_time / uncompressed_time - 1) * 100:.1f}%"

        return results


async def simulate_compression():
    """Simulate compression on test data."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    async with CompressionPolicyManager(conn_string) as manager:
        # Check if compression is available
        compression_available = await manager.check_compression_support()

        if not compression_available:
            logger.warning(
                "Compression is not available (requires TimescaleDB license)"
            )
            logger.info("Showing estimated compression savings based on typical ratios")

            savings = await manager.estimate_compression_savings()
            print("\n=== Estimated Compression Savings ===")
            for table, stats in savings.items():
                print(f"\n{table}:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
        else:
            logger.info("Compression is available, setting up policies...")

            # Set up compression policies
            tables = [
                ("frame_metadata", 1),  # Compress after 1 day
                ("frame_stats_1min", 7),  # Compress after 7 days
                ("frame_stats_hourly", 30),  # Compress after 30 days
            ]

            for table, days in tables:
                await manager.setup_compression_policy(table, days)


async def main():
    """Run compression management."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    async with CompressionPolicyManager(conn_string) as manager:
        # Check compression support
        compression_available = await manager.check_compression_support()
        print("\n=== Compression Support ===")
        print(f"Compression available: {compression_available}")

        if not compression_available:
            print("\nNOTE: Compression requires TimescaleDB license.")
            print("Showing analysis based on uncompressed data.\n")

        print("\n=== Compression Settings ===")
        settings = await manager.get_compression_settings()
        if settings:
            print(tabulate(settings, headers="keys", tablefmt="grid"))
        else:
            print("No compression settings found")

        print("\n=== Compression Status ===")
        status = await manager.get_compression_status()
        if status:
            print(tabulate(status, headers="keys", tablefmt="grid"))
        else:
            print("No compression status available")

        print("\n=== Compression Candidates ===")
        candidates = await manager.analyze_compression_candidates()
        if candidates:
            print(tabulate(candidates, headers="keys", tablefmt="grid"))
        else:
            print("No compression candidates found")

        print("\n=== Estimated Compression Savings ===")
        savings = await manager.estimate_compression_savings()
        for table, stats in savings.items():
            print(f"\n{table}:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        # Ask if user wants to simulate compression
        if compression_available:
            simulate = input("\nSet up compression policies? (y/n): ")
            if simulate.lower() == "y":
                await simulate_compression()
        else:
            simulate = input("\nShow compression simulation? (y/n): ")
            if simulate.lower() == "y":
                await simulate_compression()


if __name__ == "__main__":
    asyncio.run(main())
