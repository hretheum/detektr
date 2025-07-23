#!/usr/bin/env python3
"""Performance benchmark for optimized queries.

Verify all queries meet <10ms requirement.
"""

import asyncio
import json
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import asyncpg

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """Benchmark query performance."""

    def __init__(self, connection_string: str):
        """Initialize with database connection string."""
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None

    async def __aenter__(self):
        """Enter async context."""
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self.pool:
            await self.pool.close()

    def generate_frame_id(self) -> str:
        """Generate random frame ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = "".join(random.choices(string.ascii_lowercase, k=6))
        return f"{timestamp}_camera_{random.randint(1, 10):03d}_{random_suffix}"

    async def insert_test_data(self, count: int = 10000):
        """Insert test data for benchmarking."""
        logger.info(f"Inserting {count} test records...")

        # Generate test data
        records = []
        base_time = datetime.now() - timedelta(days=7)

        for i in range(count):
            timestamp = base_time + timedelta(seconds=i * 0.1)
            camera_id = f"camera_{random.randint(1, 10):03d}"
            frame_id = self.generate_frame_id()

            metadata = {
                "motion_detected": random.random() > 0.7,
                "objects_detected": random.randint(0, 5),
                "motion_score": random.random(),
                "processing_time_ms": random.uniform(10, 50),
                "resolution": "1920x1080",
            }

            records.append(
                (
                    frame_id,
                    timestamp,
                    camera_id,
                    i,
                    json.dumps(metadata),
                )
            )

        # Batch insert
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO metadata.frame_metadata
                (frame_id, timestamp, camera_id, sequence_number, metadata)
                VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
                records,
            )

        logger.info(f"Inserted {count} test records")

    async def benchmark_query(
        self, name: str, query: str, params: List = None, iterations: int = 100
    ) -> Dict:
        """Benchmark a single query."""
        if params is None:
            params = []

        timings = []
        errors = 0

        for i in range(iterations):
            try:
                async with self.pool.acquire() as conn:
                    start = datetime.now()
                    await conn.fetch(query, *params)
                    elapsed = (datetime.now() - start).total_seconds() * 1000
                    timings.append(elapsed)
            except Exception as e:
                logger.error(f"Query failed: {e}")
                errors += 1

        if timings:
            return {
                "name": name,
                "iterations": iterations,
                "errors": errors,
                "min_ms": min(timings),
                "max_ms": max(timings),
                "avg_ms": sum(timings) / len(timings),
                "p50_ms": sorted(timings)[len(timings) // 2],
                "p95_ms": sorted(timings)[int(len(timings) * 0.95)],
                "p99_ms": sorted(timings)[int(len(timings) * 0.99)],
                "meets_sla": sorted(timings)[int(len(timings) * 0.99)] < 10,
            }
        else:
            return {
                "name": name,
                "iterations": iterations,
                "errors": errors,
                "meets_sla": False,
            }

    async def run_benchmarks(self) -> Dict[str, Dict]:
        """Run all performance benchmarks."""
        results = {}

        # Get sample data for queries
        async with self.pool.acquire() as conn:
            sample_frame = await conn.fetchrow(
                "SELECT frame_id FROM metadata.frame_metadata LIMIT 1"
            )
            sample_camera = await conn.fetchrow(
                "SELECT DISTINCT camera_id FROM metadata.frame_metadata LIMIT 1"
            )

        if not sample_frame or not sample_camera:
            logger.error("No sample data found. Inserting test data...")
            await self.insert_test_data(10000)
            # Retry getting samples
            async with self.pool.acquire() as conn:
                sample_frame = await conn.fetchrow(
                    "SELECT frame_id FROM metadata.frame_metadata LIMIT 1"
                )
                sample_camera = await conn.fetchrow(
                    "SELECT DISTINCT camera_id FROM metadata.frame_metadata LIMIT 1"
                )

        benchmarks = [
            {
                "name": "Point Lookup",
                "query": "SELECT * FROM metadata.frame_metadata WHERE frame_id = $1",
                "params": [sample_frame["frame_id"] if sample_frame else "test_001"],
            },
            {
                "name": "Time Range Query",
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
            {
                "name": "Camera History",
                "query": """
                    SELECT * FROM metadata.frame_metadata
                    WHERE camera_id = $1 AND timestamp >= $2
                    ORDER BY timestamp DESC
                    LIMIT 100
                """,
                "params": [
                    sample_camera["camera_id"] if sample_camera else "camera_001",
                    datetime.now() - timedelta(hours=24),
                ],
            },
            {
                "name": "Motion Detection Query",
                "query": """
                    SELECT * FROM metadata.frame_metadata
                    WHERE (metadata->>'motion_detected')::boolean = true
                        AND timestamp >= $1
                    LIMIT 100
                """,
                "params": [datetime.now() - timedelta(hours=1)],
            },
            {
                "name": "JSONB Search",
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
            {
                "name": "1-Min Aggregate",
                "query": """
                    SELECT * FROM metadata.frame_stats_1min
                    WHERE minute >= $1 AND minute < $2
                    ORDER BY minute DESC
                    LIMIT 100
                """,
                "params": [
                    datetime.now() - timedelta(hours=1),
                    datetime.now(),
                ],
            },
            {
                "name": "Hourly Aggregate",
                "query": """
                    SELECT * FROM metadata.frame_stats_hourly
                    WHERE hour >= $1 AND hour < $2
                    ORDER BY hour DESC
                    LIMIT 100
                """,
                "params": [
                    datetime.now() - timedelta(days=1),
                    datetime.now(),
                ],
            },
            {
                "name": "Daily Aggregate",
                "query": """
                    SELECT * FROM metadata.frame_stats_daily
                    WHERE day >= $1 AND day < $2
                    ORDER BY day DESC
                """,
                "params": [
                    datetime.now() - timedelta(days=30),
                    datetime.now(),
                ],
            },
        ]

        logger.info("Running performance benchmarks...")
        for benchmark in benchmarks:
            logger.info(f"Benchmarking: {benchmark['name']}")
            results[benchmark["name"]] = await self.benchmark_query(
                benchmark["name"],
                benchmark["query"],
                benchmark["params"],
                iterations=100,
            )

        return results

    async def stress_test(self, duration_seconds: int = 60) -> Dict:
        """Run stress test with concurrent queries."""
        logger.info(f"Running {duration_seconds}s stress test...")

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)
        query_counts = {}
        error_counts = {}
        latencies = {}

        queries = [
            {
                "name": "point_lookup",
                "query": "SELECT * FROM metadata.frame_metadata WHERE frame_id = $1",
                "params_gen": lambda: [self.generate_frame_id()],
            },
            {
                "name": "time_range",
                "query": """
                    SELECT * FROM metadata.frame_metadata
                    WHERE timestamp >= $1 AND timestamp < $2
                    LIMIT 100
                """,
                "params_gen": lambda: [
                    datetime.now() - timedelta(minutes=random.randint(1, 60)),
                    datetime.now(),
                ],
            },
            {
                "name": "camera_scan",
                "query": """
                    SELECT * FROM metadata.frame_metadata
                    WHERE camera_id = $1 AND timestamp >= $2
                    LIMIT 100
                """,
                "params_gen": lambda: [
                    f"camera_{random.randint(1, 10):03d}",
                    datetime.now() - timedelta(hours=1),
                ],
            },
        ]

        async def run_query(query_def):
            name = query_def["name"]
            while datetime.now() < end_time:
                try:
                    params = query_def["params_gen"]()
                    async with self.pool.acquire() as conn:
                        start = datetime.now()
                        await conn.fetch(query_def["query"], *params)
                        elapsed = (datetime.now() - start).total_seconds() * 1000

                        if name not in query_counts:
                            query_counts[name] = 0
                            error_counts[name] = 0
                            latencies[name] = []

                        query_counts[name] += 1
                        latencies[name].append(elapsed)

                except Exception as e:
                    logger.error(f"Query {name} failed: {e}")
                    error_counts[name] = error_counts.get(name, 0) + 1

                await asyncio.sleep(0.01)  # Small delay between queries

        # Run queries concurrently
        tasks = []
        for i in range(10):  # 10 concurrent workers per query type
            for query_def in queries:
                tasks.append(asyncio.create_task(run_query(query_def)))

        await asyncio.gather(*tasks)

        # Calculate results
        duration = (datetime.now() - start_time).total_seconds()
        results = {
            "duration_seconds": duration,
            "total_queries": sum(query_counts.values()),
            "qps": sum(query_counts.values()) / duration,
            "queries": {},
        }

        for name in query_counts:
            if latencies[name]:
                sorted_latencies = sorted(latencies[name])
                results["queries"][name] = {
                    "count": query_counts[name],
                    "errors": error_counts.get(name, 0),
                    "qps": query_counts[name] / duration,
                    "min_ms": min(latencies[name]),
                    "avg_ms": sum(latencies[name]) / len(latencies[name]),
                    "p50_ms": sorted_latencies[len(sorted_latencies) // 2],
                    "p95_ms": sorted_latencies[int(len(sorted_latencies) * 0.95)],
                    "p99_ms": sorted_latencies[int(len(sorted_latencies) * 0.99)],
                    "max_ms": max(latencies[name]),
                }

        return results


async def main():
    """Run performance benchmarks."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    async with PerformanceBenchmark(conn_string) as benchmark:
        print("\n" + "=" * 60)
        print("🚀 PERFORMANCE BENCHMARK")
        print("=" * 60)

        # Run individual benchmarks
        print("\n📊 Individual Query Benchmarks (100 iterations each):")
        results = await benchmark.run_benchmarks()

        # Display results
        all_meet_sla = True
        for name, result in results.items():
            status = "✅" if result["meets_sla"] else "❌"
            print(f"\n{status} {name}:")
            print(f"   Avg: {result.get('avg_ms', 0):.2f}ms")
            print(f"   P50: {result.get('p50_ms', 0):.2f}ms")
            print(f"   P95: {result.get('p95_ms', 0):.2f}ms")
            print(f"   P99: {result.get('p99_ms', 0):.2f}ms")
            print(f"   Min: {result.get('min_ms', 0):.2f}ms")
            print(f"   Max: {result.get('max_ms', 0):.2f}ms")
            if result.get("errors", 0) > 0:
                print(f"   ⚠️  Errors: {result['errors']}")

            if not result["meets_sla"]:
                all_meet_sla = False

        # Run stress test
        print("\n" + "=" * 60)
        print("🔥 STRESS TEST (60s concurrent load)")
        print("=" * 60)

        stress_results = await benchmark.stress_test(duration_seconds=60)

        print("\n📈 Overall Performance:")
        print(f"   Duration: {stress_results['duration_seconds']:.1f}s")
        print(f"   Total Queries: {stress_results['total_queries']:,}")
        print(f"   Overall QPS: {stress_results['qps']:.1f}")

        print("\n📊 Per Query Type:")
        for name, stats in stress_results["queries"].items():
            print(f"\n   {name}:")
            print(f"      Count: {stats['count']:,}")
            print(f"      QPS: {stats['qps']:.1f}")
            print(f"      Avg: {stats['avg_ms']:.2f}ms")
            print(f"      P99: {stats['p99_ms']:.2f}ms")
            if stats["errors"] > 0:
                print(f"      ⚠️  Errors: {stats['errors']}")

        # Final verdict
        print("\n" + "=" * 60)
        print("📋 FINAL VERDICT")
        print("=" * 60)

        if all_meet_sla:
            print("✅ ALL QUERIES MEET <10ms SLA AT P99!")
            print("✅ System is optimized and ready for production.")
        else:
            print("❌ Some queries exceed 10ms SLA.")
            print("⚠️  Further optimization needed.")

        # Save detailed report
        report_path = (
            "/Users/hretheum/dev/bezrobocie/detektor/services/"
            "metadata-storage/performance_report.json"
        )
        with open(report_path, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "individual_benchmarks": results,
                    "stress_test": stress_results,
                    "all_meet_sla": all_meet_sla,
                },
                f,
                indent=2,
                default=str,
            )
        print(f"\n📄 Detailed report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
