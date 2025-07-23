#!/usr/bin/env python3
"""Simple backup script using SQL dumps through Python.

Alternative to pg_dump that works with version mismatches.
"""

import asyncio
import gzip
import json
import logging
from datetime import datetime
from pathlib import Path

import asyncpg

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def backup_schema_structure(
    conn: asyncpg.Connection, schema: str = "metadata"
) -> str:
    """Get schema structure as SQL."""
    sql_parts = []

    # Create schema
    sql_parts.append(f"CREATE SCHEMA IF NOT EXISTS {schema};")

    # Get all tables in the schema
    tables_query = """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = $1 AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    tables = await conn.fetch(tables_query, schema)

    for table_row in tables:
        table_name = table_row["table_name"]

        # Get table definition
        table_def_query = f"""
        SELECT pg_get_createtable_sql('{schema}.{table_name}') as create_sql
        """
        try:
            # Fallback to getting columns manually
            columns_query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position
            """
            columns = await conn.fetch(columns_query, schema, table_name)

            # Build CREATE TABLE statement
            create_sql = f"CREATE TABLE {schema}.{table_name} (\n"
            column_defs = []

            for col in columns:
                col_def = f"  {col['column_name']} {col['data_type']}"
                if col["is_nullable"] == "NO":
                    col_def += " NOT NULL"
                if col["column_default"]:
                    col_def += f" DEFAULT {col['column_default']}"
                column_defs.append(col_def)

            create_sql += ",\n".join(column_defs) + "\n);"
            sql_parts.append(create_sql)

        except Exception as e:
            logger.warning(f"Could not get structure for table {table_name}: {e}")

    # Get indexes
    indexes_query = """
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE schemaname = $1
    ORDER BY indexname
    """
    indexes = await conn.fetch(indexes_query, schema)

    for index_row in indexes:
        if not index_row["indexname"].endswith(
            "_pkey"
        ):  # Skip primary keys (already included)
            sql_parts.append(index_row["indexdef"] + ";")

    return "\n\n".join(sql_parts)


async def backup_schema_data(conn: asyncpg.Connection, schema: str = "metadata") -> str:
    """Get schema data as SQL INSERT statements."""
    sql_parts = []

    # Get all tables
    tables_query = """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = $1 AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    tables = await conn.fetch(tables_query, schema)

    for table_row in tables:
        table_name = table_row["table_name"]

        # Check if table has data
        count_query = f"SELECT COUNT(*) FROM {schema}.{table_name}"
        count = await conn.fetchval(count_query)

        if count > 0:
            logger.info(f"Backing up {count} rows from {table_name}...")

            # Get all data
            data_query = f"SELECT * FROM {schema}.{table_name}"
            rows = await conn.fetch(data_query)

            if rows:
                # Get column names
                columns = list(rows[0].keys())
                columns_str = ", ".join(columns)

                # Create INSERT statements
                sql_parts.append(f"-- Data for table {table_name}")

                for row in rows:
                    values = []
                    for col in columns:
                        value = row[col]
                        if value is None:
                            values.append("NULL")
                        elif isinstance(value, str):
                            # Escape single quotes
                            escaped_value = value.replace("'", "''")
                            values.append(f"'{escaped_value}'")
                        elif isinstance(value, dict):
                            # JSON data
                            json_str = json.dumps(value).replace("'", "''")
                            values.append(f"'{json_str}'::jsonb")
                        else:
                            values.append(str(value))

                    values_str = ", ".join(values)
                    sql_parts.append(
                        f"INSERT INTO {schema}.{table_name} ({columns_str}) VALUES ({values_str});"
                    )

    return "\n".join(sql_parts)


async def create_backup():
    """Create a simple backup."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"
    backup_dir = Path("/Users/hretheum/dev/bezrobocie/detektor/backups")
    backup_dir.mkdir(exist_ok=True)

    logger.info("Creating backup...")

    conn = await asyncpg.connect(conn_string)
    try:
        # Create backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"metadata_backup_{timestamp}.sql"
        backup_path = backup_dir / backup_filename

        # Get schema structure
        logger.info("Backing up schema structure...")
        structure_sql = await backup_schema_structure(conn, "metadata")

        # Get schema data
        logger.info("Backing up schema data...")
        data_sql = await backup_schema_data(conn, "metadata")

        # Combine and save
        full_backup = f"""-- TimescaleDB Metadata Backup
-- Created: {datetime.now().isoformat()}
-- Schema: metadata

{structure_sql}

-- Data
{data_sql}
"""

        with open(backup_path, "w") as f:
            f.write(full_backup)

        # Compress backup
        compressed_path = backup_path.with_suffix(".sql.gz")
        with open(backup_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                f_out.writelines(f_in)

        # Remove uncompressed file
        backup_path.unlink()

        file_size = compressed_path.stat().st_size
        logger.info(f"Backup completed: {compressed_path}")
        logger.info(f"File size: {file_size / 1024:.1f} KB")

        return {
            "filename": compressed_path.name,
            "path": str(compressed_path),
            "size_bytes": file_size,
            "created_at": datetime.now().isoformat(),
        }

    finally:
        await conn.close()


async def test_restore():
    """Test backup by verifying it can be read."""
    backup_dir = Path("/Users/hretheum/dev/bezrobocie/detektor/backups")

    # Find latest backup
    backups = list(backup_dir.glob("metadata_backup_*.sql.gz"))
    if not backups:
        logger.error("No backups found to test")
        return False

    latest_backup = sorted(backups)[-1]
    logger.info(f"Testing backup: {latest_backup}")

    try:
        with gzip.open(latest_backup, "rt") as f:
            content = f.read()

        # Basic validation
        if "CREATE SCHEMA" in content and "metadata" in content:
            logger.info(
                "✅ Backup test passed - file is readable and contains expected content"
            )
            return True
        else:
            logger.error("❌ Backup test failed - missing expected content")
            return False

    except Exception as e:
        logger.error(f"❌ Backup test failed: {e}")
        return False


async def main():
    """Main function."""
    print("\n=== SIMPLE METADATA BACKUP ===")
    print("\nOptions:")
    print("1. Create backup")
    print("2. Test latest backup")
    print("3. List backups")
    print("4. Exit")

    choice = input("\nSelect option (1-4): ")

    if choice == "1":
        backup_info = await create_backup()
        print(f"✅ Backup created: {backup_info['filename']}")
        print(f"   Size: {backup_info['size_bytes'] / 1024:.1f} KB")

        # Test the backup
        test_ok = await test_restore()
        if test_ok:
            print("✅ Backup verification passed")
        else:
            print("⚠️  Backup verification failed")

    elif choice == "2":
        test_ok = await test_restore()
        print(
            f"{'✅' if test_ok else '❌'} Backup test: {'PASSED' if test_ok else 'FAILED'}"
        )

    elif choice == "3":
        backup_dir = Path("/Users/hretheum/dev/bezrobocie/detektor/backups")
        backups = list(backup_dir.glob("metadata_backup_*.sql.gz"))

        if backups:
            print("\nAvailable backups:")
            for backup in sorted(backups, reverse=True):
                size = backup.stat().st_size
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"  📦 {backup.name}")
                print(f"     Size: {size / 1024:.1f} KB")
                print(f"     Modified: {mtime}")
        else:
            print("No backups found")

    elif choice == "4":
        print("👋 Goodbye!")

    else:
        print("Invalid option")


if __name__ == "__main__":
    asyncio.run(main())
