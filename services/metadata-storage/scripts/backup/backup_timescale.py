#!/usr/bin/env python3
"""Backup procedures for TimescaleDB.

Comprehensive backup solution with compression and verification.
"""

import asyncio
import gzip
import hashlib
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import asyncpg

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BackupManager:
    """Manage TimescaleDB backups."""

    def __init__(
        self,
        connection_string: str,
        backup_dir: str = "/Users/hretheum/dev/bezrobocie/detektor/backups",
    ):
        """Initialize backup manager."""
        self.connection_string = connection_string
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

        # Parse connection string for pg_dump
        import urllib.parse

        parsed = urllib.parse.urlparse(connection_string)
        self.db_config = {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "user": parsed.username,
            "password": parsed.password,
            "database": parsed.path.lstrip("/"),
        }

    async def get_database_size(self) -> Dict:
        """Get database size information."""
        conn = await asyncpg.connect(self.connection_string)
        try:
            query = """
            SELECT
                pg_database.datname,
                pg_size_pretty(pg_database_size(pg_database.datname)) as size,
                pg_database_size(pg_database.datname) as size_bytes
            FROM pg_database
            WHERE datname = $1
            """
            result = await conn.fetchrow(query, self.db_config["database"])

            # Get schema sizes
            schema_query = """
            SELECT
                schemaname,
                pg_size_pretty(sum(pg_relation_size(schemaname||'.'||tablename))) as size,
                sum(pg_relation_size(schemaname||'.'||tablename)) as size_bytes
            FROM pg_tables
            WHERE schemaname = 'metadata'
            GROUP BY schemaname
            """
            schema_result = await conn.fetchrow(schema_query)

            return {
                "database": dict(result) if result else {},
                "metadata_schema": dict(schema_result) if schema_result else {},
            }
        finally:
            await conn.close()

    def create_backup_filename(self, backup_type: str = "full") -> str:
        """Create backup filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"detektor_metadata_{backup_type}_{timestamp}.sql"

    async def create_full_backup(self, compress: bool = True) -> Dict:
        """Create full database backup."""
        logger.info("Starting full database backup...")

        backup_filename = self.create_backup_filename("full")
        backup_path = self.backup_dir / backup_filename

        # Get database size before backup
        size_info = await self.get_database_size()
        start_time = datetime.now()

        # Prepare pg_dump command
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_config["password"]

        cmd = [
            "pg_dump",
            f"--host={self.db_config['host']}",
            f"--port={self.db_config['port']}",
            f"--username={self.db_config['user']}",
            "--verbose",
            "--no-password",
            "--format=custom",
            "--compress=9",
            "--no-owner",
            "--no-privileges",
            self.db_config["database"],
        ]

        try:
            # Run pg_dump
            logger.info(f"Running: {' '.join(cmd)}")
            with open(backup_path, "wb") as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=300,  # 5 minutes timeout
                )

            if result.returncode != 0:
                error_msg = result.stderr.decode()
                logger.error(f"pg_dump failed: {error_msg}")
                raise Exception(f"Backup failed: {error_msg}")

            # Calculate backup size and duration
            backup_size = backup_path.stat().st_size
            duration = (datetime.now() - start_time).total_seconds()

            # Calculate checksum
            checksum = self.calculate_checksum(backup_path)

            # Compress if requested
            final_path = backup_path
            if compress and not backup_path.name.endswith(".gz"):
                final_path = self.compress_backup(backup_path)
                backup_size = final_path.stat().st_size

            backup_info = {
                "filename": final_path.name,
                "path": str(final_path),
                "size_bytes": backup_size,
                "size_pretty": self.format_bytes(backup_size),
                "duration_seconds": duration,
                "checksum": checksum,
                "created_at": start_time.isoformat(),
                "database_size": size_info,
                "backup_type": "full",
                "compressed": compress,
            }

            # Save backup metadata
            await self.save_backup_metadata(backup_info)

            logger.info(f"Backup completed: {final_path}")
            logger.info(f"Size: {self.format_bytes(backup_size)}")
            logger.info(f"Duration: {duration:.1f}s")

            return backup_info

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Clean up partial backup
            if backup_path.exists():
                backup_path.unlink()
            raise

    async def create_schema_backup(self, schema: str = "metadata") -> Dict:
        """Create backup of specific schema only."""
        logger.info(f"Starting schema backup for: {schema}")

        backup_filename = self.create_backup_filename(f"schema_{schema}")
        backup_path = self.backup_dir / backup_filename

        start_time = datetime.now()

        # Prepare pg_dump command for schema only
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_config["password"]

        cmd = [
            "pg_dump",
            f"--host={self.db_config['host']}",
            f"--port={self.db_config['port']}",
            f"--username={self.db_config['user']}",
            "--verbose",
            "--no-password",
            "--format=custom",
            "--compress=9",
            "--no-owner",
            "--no-privileges",
            f"--schema={schema}",
            self.db_config["database"],
        ]

        try:
            with open(backup_path, "wb") as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=180,  # 3 minutes timeout
                )

            if result.returncode != 0:
                error_msg = result.stderr.decode()
                logger.error(f"Schema backup failed: {error_msg}")
                raise Exception(f"Schema backup failed: {error_msg}")

            backup_size = backup_path.stat().st_size
            duration = (datetime.now() - start_time).total_seconds()
            checksum = self.calculate_checksum(backup_path)

            backup_info = {
                "filename": backup_path.name,
                "path": str(backup_path),
                "size_bytes": backup_size,
                "size_pretty": self.format_bytes(backup_size),
                "duration_seconds": duration,
                "checksum": checksum,
                "created_at": start_time.isoformat(),
                "backup_type": f"schema_{schema}",
                "schema": schema,
                "compressed": True,
            }

            await self.save_backup_metadata(backup_info)

            logger.info(f"Schema backup completed: {backup_path}")
            logger.info(f"Size: {self.format_bytes(backup_size)}")
            logger.info(f"Duration: {duration:.1f}s")

            return backup_info

        except Exception as e:
            logger.error(f"Schema backup failed: {e}")
            if backup_path.exists():
                backup_path.unlink()
            raise

    def compress_backup(self, backup_path: Path) -> Path:
        """Compress backup file using gzip."""
        logger.info(f"Compressing backup: {backup_path}")

        compressed_path = backup_path.with_suffix(backup_path.suffix + ".gz")

        with open(backup_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove original file
        backup_path.unlink()

        original_size = backup_path.stat().st_size if backup_path.exists() else 0
        compressed_size = compressed_path.stat().st_size
        compression_ratio = (
            1 - (compressed_size / original_size) if original_size > 0 else 0
        )

        logger.info(f"Compression completed: {compression_ratio:.1%} saved")
        return compressed_path

    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes as human readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f}PB"

    async def save_backup_metadata(self, backup_info: Dict):
        """Save backup metadata to JSON file."""
        metadata_path = self.backup_dir / "backup_metadata.json"

        # Load existing metadata
        metadata = []
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

        # Add new backup info
        metadata.append(backup_info)

        # Keep only last 50 backups in metadata
        metadata = metadata[-50:]

        # Save updated metadata
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

    async def list_backups(self) -> List[Dict]:
        """List all available backups."""
        metadata_path = self.backup_dir / "backup_metadata.json"

        if not metadata_path.exists():
            return []

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Sort by creation time (newest first)
        return sorted(metadata, key=lambda x: x["created_at"], reverse=True)

    async def verify_backup(self, backup_path: str) -> bool:
        """Verify backup integrity."""
        logger.info(f"Verifying backup: {backup_path}")

        backup_file = Path(backup_path)
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        # Check if it's a valid pg_dump file
        try:
            cmd = [
                "pg_restore",
                "--list",
                str(backup_file),
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
            )

            if result.returncode != 0:
                logger.error(f"Backup verification failed: {result.stderr.decode()}")
                return False

            # Count objects in backup
            output = result.stdout.decode()
            object_count = len([line for line in output.split("\n") if line.strip()])

            logger.info(f"Backup verified successfully: {object_count} objects")
            return True

        except Exception as e:
            logger.error(f"Backup verification error: {e}")
            return False

    async def cleanup_old_backups(self, keep_days: int = 7):
        """Clean up backups older than specified days."""
        logger.info(f"Cleaning up backups older than {keep_days} days...")

        cutoff_date = datetime.now() - timedelta(days=keep_days)
        removed_count = 0

        for backup_file in self.backup_dir.glob("detektor_metadata_*.sql*"):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                logger.info(f"Removing old backup: {backup_file.name}")
                backup_file.unlink()
                removed_count += 1

        logger.info(f"Removed {removed_count} old backup files")

        # Update metadata file
        backups = await self.list_backups()
        current_files = {
            f.name for f in self.backup_dir.glob("detektor_metadata_*.sql*")
        }

        # Filter metadata to only include existing files
        filtered_metadata = [
            backup
            for backup in backups
            if Path(backup["filename"]).name in current_files
        ]

        metadata_path = self.backup_dir / "backup_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(filtered_metadata, f, indent=2, default=str)


async def main():
    """Main backup operations."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    backup_manager = BackupManager(conn_string)

    print("\n" + "=" * 60)
    print("💾 TIMESCALEDB BACKUP MANAGER")
    print("=" * 60)

    # Show database size
    print("\n📊 Database Information:")
    size_info = await backup_manager.get_database_size()
    if size_info["database"]:
        print(f"  Database Size: {size_info['database']['size']}")
    if size_info["metadata_schema"]:
        print(f"  Metadata Schema: {size_info['metadata_schema']['size']}")

    # List existing backups
    print("\n📋 Existing Backups:")
    backups = await backup_manager.list_backups()
    if backups:
        for backup in backups[:5]:  # Show last 5
            print(f"  📦 {backup['filename']}")
            print(f"      Size: {backup['size_pretty']}")
            print(f"      Created: {backup['created_at']}")
            print(f"      Duration: {backup['duration_seconds']:.1f}s")
            print()
    else:
        print("  No backups found")

    # Ask user what to do
    print("\nOptions:")
    print("1. Create full backup")
    print("2. Create schema backup (metadata only)")
    print("3. Verify existing backup")
    print("4. Cleanup old backups")
    print("5. Exit")

    choice = input("\nSelect option (1-5): ")

    if choice == "1":
        print("\n🚀 Creating full backup...")
        backup_info = await backup_manager.create_full_backup(compress=True)
        print(f"✅ Full backup created: {backup_info['filename']}")

        # Verify the backup
        verify = input("\n🔍 Verify backup? (y/n): ")
        if verify.lower() == "y":
            is_valid = await backup_manager.verify_backup(backup_info["path"])
            print(
                f"{'✅' if is_valid else '❌'} Backup verification: {'PASSED' if is_valid else 'FAILED'}"
            )

    elif choice == "2":
        print("\n🚀 Creating schema backup...")
        backup_info = await backup_manager.create_schema_backup("metadata")
        print(f"✅ Schema backup created: {backup_info['filename']}")

        # Verify the backup
        verify = input("\n🔍 Verify backup? (y/n): ")
        if verify.lower() == "y":
            is_valid = await backup_manager.verify_backup(backup_info["path"])
            print(
                f"{'✅' if is_valid else '❌'} Backup verification: {'PASSED' if is_valid else 'FAILED'}"
            )

    elif choice == "3":
        if backups:
            print("\nSelect backup to verify:")
            for i, backup in enumerate(backups[:10]):
                print(f"{i+1}. {backup['filename']}")

            try:
                idx = int(input("Enter number: ")) - 1
                if 0 <= idx < len(backups):
                    backup_path = backups[idx]["path"]
                    is_valid = await backup_manager.verify_backup(backup_path)
                    print(
                        f"{'✅' if is_valid else '❌'} Backup verification: {'PASSED' if is_valid else 'FAILED'}"
                    )
                else:
                    print("Invalid selection")
            except ValueError:
                print("Invalid input")
        else:
            print("No backups available to verify")

    elif choice == "4":
        days = input("Keep backups for how many days? (default: 7): ")
        try:
            keep_days = int(days) if days else 7
            await backup_manager.cleanup_old_backups(keep_days)
            print(f"✅ Cleanup completed")
        except ValueError:
            print("Invalid number of days")

    elif choice == "5":
        print("👋 Goodbye!")

    else:
        print("Invalid option")


if __name__ == "__main__":
    asyncio.run(main())
