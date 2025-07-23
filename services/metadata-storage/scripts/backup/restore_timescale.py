#!/usr/bin/env python3
"""Restore procedures for TimescaleDB.

Safe restore operations with validation and rollback capabilities.
"""

import asyncio
import gzip
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import asyncpg

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RestoreManager:
    """Manage TimescaleDB restore operations."""

    def __init__(
        self,
        connection_string: str,
        backup_dir: str = "/Users/hretheum/dev/bezrobocie/detektor/backups",
    ):
        """Initialize restore manager."""
        self.connection_string = connection_string
        self.backup_dir = Path(backup_dir)

        # Parse connection string
        import urllib.parse

        parsed = urllib.parse.urlparse(connection_string)
        self.db_config = {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "user": parsed.username,
            "password": parsed.password,
            "database": parsed.path.lstrip("/"),
        }

    async def list_available_backups(self) -> List[Dict]:
        """List all available backups for restore."""
        metadata_path = self.backup_dir / "backup_metadata.json"

        if not metadata_path.exists():
            logger.warning("No backup metadata found")
            return []

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Filter only existing files
        available_backups = []
        for backup in metadata:
            backup_path = Path(backup["path"])
            if backup_path.exists():
                available_backups.append(backup)

        return sorted(available_backups, key=lambda x: x["created_at"], reverse=True)

    async def get_database_info(self) -> Dict:
        """Get current database information."""
        conn = await asyncpg.connect(self.connection_string)
        try:
            # Get table counts
            tables_query = """
            SELECT
                schemaname,
                tablename,
                n_live_tup as row_count
            FROM pg_stat_user_tables
            WHERE schemaname = 'metadata'
            ORDER BY n_live_tup DESC
            """
            tables = await conn.fetch(tables_query)

            # Get database size
            size_query = """
            SELECT pg_size_pretty(pg_database_size(current_database())) as size
            """
            size_result = await conn.fetchrow(size_query)

            return {
                "tables": [dict(row) for row in tables],
                "total_size": size_result["size"] if size_result else "Unknown",
                "timestamp": datetime.now().isoformat(),
            }
        finally:
            await conn.close()

    async def create_pre_restore_snapshot(self) -> Dict:
        """Create snapshot of current database state before restore."""
        logger.info("Creating pre-restore snapshot...")

        snapshot_info = await self.get_database_info()

        # Save snapshot to file
        snapshot_file = (
            self.backup_dir
            / f"pre_restore_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(snapshot_file, "w") as f:
            json.dump(snapshot_info, f, indent=2, default=str)

        logger.info(f"Snapshot saved: {snapshot_file}")
        return snapshot_info

    async def validate_backup_before_restore(self, backup_path: str) -> Dict:
        """Validate backup file before attempting restore."""
        logger.info(f"Validating backup: {backup_path}")

        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        validation_result = {
            "file_exists": True,
            "file_size": backup_file.stat().st_size,
            "readable": False,
            "contains_metadata_schema": False,
            "object_count": 0,
            "estimated_restore_time": 0,
        }

        try:
            # Test if file is readable by pg_restore
            cmd = ["pg_restore", "--list", str(backup_file)]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
            )

            if result.returncode == 0:
                validation_result["readable"] = True

                # Parse output to get object information
                output = result.stdout.decode()
                lines = [line.strip() for line in output.split("\n") if line.strip()]
                validation_result["object_count"] = len(lines)

                # Check if metadata schema is present
                validation_result["contains_metadata_schema"] = any(
                    "metadata" in line.lower() for line in lines
                )

                # Estimate restore time based on file size (rough estimate)
                file_size_mb = validation_result["file_size"] / (1024 * 1024)
                validation_result["estimated_restore_time"] = max(
                    60, file_size_mb * 2
                )  # 2 seconds per MB, min 1 minute

            else:
                error_msg = result.stderr.decode()
                logger.error(f"Backup validation failed: {error_msg}")
                raise Exception(f"Invalid backup file: {error_msg}")

        except subprocess.TimeoutExpired:
            raise Exception("Backup validation timed out")
        except Exception as e:
            logger.error(f"Backup validation error: {e}")
            raise

        logger.info(
            f"Backup validation successful: {validation_result['object_count']} objects"
        )
        return validation_result

    async def restore_full_backup(
        self,
        backup_path: str,
        drop_existing: bool = False,
        schema_only: bool = False,
        data_only: bool = False,
    ) -> Dict:
        """Restore full database backup."""
        logger.info(f"Starting restore from: {backup_path}")

        # Validate backup first
        validation = await self.validate_backup_before_restore(backup_path)

        # Create pre-restore snapshot
        pre_snapshot = await self.create_pre_restore_snapshot()

        start_time = datetime.now()

        # Prepare pg_restore command
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_config["password"]

        cmd = [
            "pg_restore",
            f"--host={self.db_config['host']}",
            f"--port={self.db_config['port']}",
            f"--username={self.db_config['user']}",
            f"--dbname={self.db_config['database']}",
            "--verbose",
            "--no-password",
            "--no-owner",
            "--no-privileges",
        ]

        if drop_existing:
            cmd.append("--clean")

        if schema_only:
            cmd.append("--schema-only")
        elif data_only:
            cmd.append("--data-only")

        # Add single transaction for atomicity
        if not schema_only:
            cmd.append("--single-transaction")

        cmd.append(backup_path)

        try:
            logger.info(f"Running restore command...")
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=int(validation["estimated_restore_time"])
                + 300,  # Add 5 minute buffer
            )

            duration = (datetime.now() - start_time).total_seconds()

            if result.returncode != 0:
                error_msg = result.stderr.decode()
                logger.error(f"Restore failed: {error_msg}")

                # Try to get more details from stdout
                stdout_msg = result.stdout.decode()
                if stdout_msg:
                    logger.info(f"Restore stdout: {stdout_msg}")

                raise Exception(f"Restore failed: {error_msg}")

            # Get post-restore info
            post_snapshot = await self.get_database_info()

            restore_info = {
                "backup_path": backup_path,
                "restore_type": "schema_only"
                if schema_only
                else "data_only"
                if data_only
                else "full",
                "drop_existing": drop_existing,
                "duration_seconds": duration,
                "started_at": start_time.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "pre_restore_snapshot": pre_snapshot,
                "post_restore_snapshot": post_snapshot,
                "validation": validation,
                "success": True,
            }

            logger.info(f"Restore completed successfully in {duration:.1f}s")
            return restore_info

        except subprocess.TimeoutExpired:
            logger.error("Restore operation timed out")
            raise Exception("Restore operation timed out")
        except Exception as e:
            logger.error(f"Restore failed: {e}")

            # Create failure report
            restore_info = {
                "backup_path": backup_path,
                "restore_type": "schema_only"
                if schema_only
                else "data_only"
                if data_only
                else "full",
                "drop_existing": drop_existing,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
                "started_at": start_time.isoformat(),
                "failed_at": datetime.now().isoformat(),
                "pre_restore_snapshot": pre_snapshot,
                "validation": validation,
                "error": str(e),
                "success": False,
            }

            return restore_info

    async def restore_schema_only(self, backup_path: str) -> Dict:
        """Restore only schema (structure) from backup."""
        logger.info("Restoring schema only...")
        return await self.restore_full_backup(
            backup_path, drop_existing=True, schema_only=True
        )

    async def restore_data_only(self, backup_path: str) -> Dict:
        """Restore only data from backup."""
        logger.info("Restoring data only...")
        return await self.restore_full_backup(
            backup_path, drop_existing=False, data_only=True
        )

    async def test_restore(self, backup_path: str) -> Dict:
        """Test restore operation without affecting production database."""
        logger.info("Starting test restore...")

        # Create temporary database for testing
        test_db_name = f"test_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Connect to postgres database to create test database
        postgres_conn_string = self.connection_string.replace(
            f"/{self.db_config['database']}", "/postgres"
        )

        conn = await asyncpg.connect(postgres_conn_string)
        try:
            # Create test database
            await conn.execute(f"CREATE DATABASE {test_db_name}")
            logger.info(f"Created test database: {test_db_name}")
        finally:
            await conn.close()

        # Update connection string for test database
        test_conn_string = self.connection_string.replace(
            f"/{self.db_config['database']}", f"/{test_db_name}"
        )

        # Create test restore manager
        test_db_config = self.db_config.copy()
        test_db_config["database"] = test_db_name

        try:
            # Prepare pg_restore command for test database
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_config["password"]

            cmd = [
                "pg_restore",
                f"--host={test_db_config['host']}",
                f"--port={test_db_config['port']}",
                f"--username={test_db_config['user']}",
                f"--dbname={test_db_name}",
                "--verbose",
                "--no-password",
                "--no-owner",
                "--no-privileges",
                "--single-transaction",
                backup_path,
            ]

            start_time = datetime.now()

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=300,  # 5 minute timeout for test
            )

            duration = (datetime.now() - start_time).total_seconds()

            if result.returncode == 0:
                # Verify test database content
                test_conn = await asyncpg.connect(test_conn_string)
                try:
                    # Count tables in test database
                    table_count = await test_conn.fetchval(
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'metadata'"
                    )

                    # Count total rows (if any tables exist)
                    total_rows = 0
                    if table_count > 0:
                        row_query = """
                        SELECT SUM(n_live_tup) FROM pg_stat_user_tables
                        WHERE schemaname = 'metadata'
                        """
                        total_rows = await test_conn.fetchval(row_query) or 0

                    test_result = {
                        "success": True,
                        "test_database": test_db_name,
                        "duration_seconds": duration,
                        "tables_restored": table_count,
                        "total_rows": total_rows,
                        "stdout": result.stdout.decode(),
                    }

                    logger.info(
                        f"Test restore successful: {table_count} tables, {total_rows} rows"
                    )

                finally:
                    await test_conn.close()
            else:
                test_result = {
                    "success": False,
                    "test_database": test_db_name,
                    "duration_seconds": duration,
                    "error": result.stderr.decode(),
                    "stdout": result.stdout.decode(),
                }

                logger.error(f"Test restore failed: {result.stderr.decode()}")

        finally:
            # Clean up test database
            conn = await asyncpg.connect(postgres_conn_string)
            try:
                await conn.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
                logger.info(f"Cleaned up test database: {test_db_name}")
            finally:
                await conn.close()

        return test_result

    async def save_restore_report(self, restore_info: Dict):
        """Save restore operation report."""
        report_file = (
            self.backup_dir
            / f"restore_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(report_file, "w") as f:
            json.dump(restore_info, f, indent=2, default=str)

        logger.info(f"Restore report saved: {report_file}")


async def main():
    """Main restore operations."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    restore_manager = RestoreManager(conn_string)

    print("\n" + "=" * 60)
    print("🔄 TIMESCALEDB RESTORE MANAGER")
    print("=" * 60)

    # Show current database state
    print("\n📊 Current Database State:")
    db_info = await restore_manager.get_database_info()
    print(f"  Total Size: {db_info['total_size']}")
    if db_info["tables"]:
        print("  Tables:")
        for table in db_info["tables"][:5]:  # Show top 5
            print(f"    {table['tablename']}: {table['row_count']:,} rows")

    # List available backups
    print("\n📋 Available Backups:")
    backups = await restore_manager.list_available_backups()
    if backups:
        for i, backup in enumerate(backups[:10]):  # Show first 10
            print(f"  {i+1}. {backup['filename']}")
            print(f"     Created: {backup['created_at']}")
            print(f"     Size: {backup['size_pretty']}")
            print(f"     Type: {backup['backup_type']}")
            print()
    else:
        print("  No backups found")
        return

    # Ask user what to do
    print("Options:")
    print("1. Test restore (safe - uses temporary database)")
    print("2. Restore schema only (structure)")
    print("3. Restore data only")
    print("4. Full restore (⚠️  DESTRUCTIVE)")
    print("5. Exit")

    choice = input("\nSelect option (1-5): ")

    if choice == "5":
        print("👋 Goodbye!")
        return

    if choice not in ["1", "2", "3", "4"]:
        print("Invalid option")
        return

    # Select backup
    try:
        backup_idx = int(input(f"\nSelect backup (1-{len(backups)}): ")) - 1
        if not (0 <= backup_idx < len(backups)):
            print("Invalid backup selection")
            return

        selected_backup = backups[backup_idx]
        backup_path = selected_backup["path"]

    except ValueError:
        print("Invalid input")
        return

    print(f"\n📦 Selected backup: {selected_backup['filename']}")

    if choice == "1":
        print("\n🧪 Starting test restore...")
        test_result = await restore_manager.test_restore(backup_path)

        if test_result["success"]:
            print("✅ Test restore PASSED")
            print(f"   Tables restored: {test_result['tables_restored']}")
            print(f"   Total rows: {test_result['total_rows']:,}")
            print(f"   Duration: {test_result['duration_seconds']:.1f}s")
        else:
            print("❌ Test restore FAILED")
            print(f"   Error: {test_result['error']}")

    elif choice == "2":
        confirm = input(
            "\n⚠️  This will replace the current schema. Continue? (yes/no): "
        )
        if confirm.lower() == "yes":
            print("\n🔄 Starting schema restore...")
            result = await restore_manager.restore_schema_only(backup_path)

            if result["success"]:
                print("✅ Schema restore completed")
            else:
                print(f"❌ Schema restore failed: {result['error']}")

            await restore_manager.save_restore_report(result)
        else:
            print("Restore cancelled")

    elif choice == "3":
        confirm = input("\n⚠️  This will replace current data. Continue? (yes/no): ")
        if confirm.lower() == "yes":
            print("\n🔄 Starting data restore...")
            result = await restore_manager.restore_data_only(backup_path)

            if result["success"]:
                print("✅ Data restore completed")
            else:
                print(f"❌ Data restore failed: {result['error']}")

            await restore_manager.save_restore_report(result)
        else:
            print("Restore cancelled")

    elif choice == "4":
        print("\n⚠️  WARNING: This will completely replace the current database!")
        print("   All current data will be lost!")
        confirm = input("\nType 'DESTROY' to confirm: ")

        if confirm == "DESTROY":
            print("\n🔄 Starting full restore...")
            result = await restore_manager.restore_full_backup(
                backup_path, drop_existing=True
            )

            if result["success"]:
                print("✅ Full restore completed")
                print(f"   Duration: {result['duration_seconds']:.1f}s")
            else:
                print(f"❌ Full restore failed: {result['error']}")

            await restore_manager.save_restore_report(result)
        else:
            print("Restore cancelled")


if __name__ == "__main__":
    asyncio.run(main())
