"""Example database operations with OpenTelemetry instrumentation."""

import asyncio
import os
import sys
import time

import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.shared.telemetry import (  # noqa: E402
    setup_auto_instrumentation,
    setup_telemetry,
)

# Setup telemetry first
tracer, meter, _ = setup_telemetry("database-example", "0.1.0")

# Enable auto-instrumentation
setup_auto_instrumentation()

# Database URLs (these would fail without actual DB, but show instrumentation)
POSTGRES_URL = "postgresql://user:pass@localhost:5432/detektor"
ASYNC_POSTGRES_URL = "postgresql://user:pass@localhost:5432/detektor"


def test_sqlalchemy() -> None:
    """Test SQLAlchemy instrumentation."""
    print("\n=== Testing SQLAlchemy instrumentation ===")

    with tracer.start_as_current_span("sqlalchemy_test") as span:
        span.set_attribute("db.system", "postgresql")

        try:
            # Create engine - this will be auto-instrumented
            engine = create_engine(POSTGRES_URL, echo=True)
            Session = sessionmaker(bind=engine)

            # Test query
            with Session() as session:
                # This query will be traced automatically
                result = session.execute(text("SELECT 1"))
                print(f"Query result: {result}")

        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            print(f"Expected error (no DB): {e}")


async def test_asyncpg() -> None:
    """Test AsyncPG instrumentation."""
    print("\n=== Testing AsyncPG instrumentation ===")

    with tracer.start_as_current_span("asyncpg_test") as span:
        span.set_attribute("db.system", "postgresql")

        try:
            # Connect - this will be auto-instrumented
            conn = await asyncpg.connect(ASYNC_POSTGRES_URL)

            # Test query
            result = await conn.fetch("SELECT 1")
            print(f"Async query result: {result}")

            await conn.close()

        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            print(f"Expected error (no DB): {e}")


def test_database_metrics() -> None:
    """Test database metrics collection."""
    print("\n=== Testing database metrics ===")

    # Create metrics
    query_counter = meter.create_counter(
        name="db_queries_total",
        description="Total number of database queries",
        unit="query",
    )

    query_duration = meter.create_histogram(
        name="db_query_duration_seconds",
        description="Database query duration",
        unit="s",
    )

    # Simulate queries
    for i in range(5):
        start_time = time.time()

        with tracer.start_as_current_span(f"query_{i}") as span:
            span.set_attribute("db.operation", "SELECT")
            span.set_attribute("db.statement", f"SELECT * FROM table_{i}")  # nosec B608

            # Simulate query time
            time.sleep(0.01 * (i + 1))  # Increasing latency

            duration = time.time() - start_time

            # Record metrics
            query_counter.add(1, {"operation": "SELECT", "table": f"table_{i}"})
            query_duration.record(duration, {"operation": "SELECT"})

            print(f"Query {i} completed in {duration:.3f}s")


async def main() -> None:
    """Run all database tests."""
    print("Starting database telemetry examples...")
    print("Note: These will fail without actual database, but show instrumentation")

    # Test SQLAlchemy
    test_sqlalchemy()

    # Test AsyncPG
    await test_asyncpg()

    # Test metrics
    test_database_metrics()

    print("\nDatabase tests completed!")
    print("Check traces in Jaeger (if exporter configured)")


if __name__ == "__main__":
    asyncio.run(main())
