#!/usr/bin/env python3
"""Disaster recovery procedures for TimescaleDB.

Automated disaster recovery testing and procedures.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import asyncpg
from backup_timescale import BackupManager
from restore_timescale import RestoreManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DisasterRecoveryManager:
    """Manage disaster recovery procedures."""

    def __init__(
        self,
        connection_string: str,
        backup_dir: str = "/Users/hretheum/dev/bezrobocie/detektor/backups",
    ):
        """Initialize disaster recovery manager."""
        self.connection_string = connection_string
        self.backup_dir = Path(backup_dir)
        self.backup_manager = BackupManager(connection_string, str(backup_dir))
        self.restore_manager = RestoreManager(connection_string, str(backup_dir))

    async def test_database_connectivity(self) -> Dict:
        """Test if database is accessible."""
        logger.info("Testing database connectivity...")

        try:
            conn = await asyncpg.connect(self.connection_string)
            start_time = time.time()

            # Simple query to test responsiveness
            await conn.fetchval("SELECT 1")
            response_time = (time.time() - start_time) * 1000  # ms

            # Check if TimescaleDB extension is available
            timescale_version = await conn.fetchval(
                "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
            )

            await conn.close()

            return {
                "accessible": True,
                "response_time_ms": response_time,
                "timescale_version": timescale_version,
                "test_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Database connectivity test failed: {e}")
            return {
                "accessible": False,
                "error": str(e),
                "test_time": datetime.now().isoformat(),
            }

    async def run_backup_verification_test(self) -> Dict:
        """Run comprehensive backup verification test."""
        logger.info("Starting backup verification test...")

        test_results = {
            "test_type": "backup_verification",
            "started_at": datetime.now().isoformat(),
            "steps": [],
        }

        try:
            # Step 1: Create a test backup
            logger.info("Step 1: Creating test backup...")
            step1_start = time.time()

            backup_info = await self.backup_manager.create_schema_backup("metadata")
            step1_duration = time.time() - step1_start

            test_results["steps"].append(
                {
                    "step": 1,
                    "description": "Create test backup",
                    "duration_seconds": step1_duration,
                    "success": True,
                    "backup_file": backup_info["filename"],
                    "backup_size": backup_info["size_pretty"],
                }
            )

            # Step 2: Verify backup integrity
            logger.info("Step 2: Verifying backup integrity...")
            step2_start = time.time()

            is_valid = await self.backup_manager.verify_backup(backup_info["path"])
            step2_duration = time.time() - step2_start

            test_results["steps"].append(
                {
                    "step": 2,
                    "description": "Verify backup integrity",
                    "duration_seconds": step2_duration,
                    "success": is_valid,
                }
            )

            if not is_valid:
                raise Exception("Backup integrity check failed")

            # Step 3: Test restore to temporary database
            logger.info("Step 3: Testing restore to temporary database...")
            step3_start = time.time()

            restore_test = await self.restore_manager.test_restore(backup_info["path"])
            step3_duration = time.time() - step3_start

            test_results["steps"].append(
                {
                    "step": 3,
                    "description": "Test restore to temporary database",
                    "duration_seconds": step3_duration,
                    "success": restore_test["success"],
                    "tables_restored": restore_test.get("tables_restored", 0),
                    "total_rows": restore_test.get("total_rows", 0),
                }
            )

            if not restore_test["success"]:
                raise Exception(
                    f"Restore test failed: {restore_test.get('error', 'Unknown error')}"
                )

            # Step 4: Cleanup test backup
            logger.info("Step 4: Cleaning up test backup...")
            backup_path = Path(backup_info["path"])
            if backup_path.exists():
                backup_path.unlink()

            test_results["steps"].append(
                {
                    "step": 4,
                    "description": "Cleanup test backup",
                    "success": True,
                }
            )

            test_results["overall_success"] = True
            test_results["completed_at"] = datetime.now().isoformat()

            logger.info("Backup verification test completed successfully")

        except Exception as e:
            logger.error(f"Backup verification test failed: {e}")
            test_results["overall_success"] = False
            test_results["error"] = str(e)
            test_results["failed_at"] = datetime.now().isoformat()

        return test_results

    async def run_rto_test(self) -> Dict:
        """Run Recovery Time Objective (RTO) test."""
        logger.info("Starting RTO test...")

        rto_test = {
            "test_type": "rto_measurement",
            "target_rto_minutes": 10,  # Target: restore within 10 minutes
            "started_at": datetime.now().isoformat(),
            "phases": [],
        }

        try:
            # Phase 1: Create backup (simulating latest backup)
            logger.info("Phase 1: Creating backup...")
            phase1_start = time.time()

            backup_info = await self.backup_manager.create_schema_backup("metadata")
            phase1_duration = time.time() - phase1_start

            rto_test["phases"].append(
                {
                    "phase": 1,
                    "description": "Backup creation",
                    "duration_seconds": phase1_duration,
                    "success": True,
                }
            )

            # Phase 2: Simulate database failure detection time
            logger.info("Phase 2: Simulating failure detection...")
            detection_time = 30  # 30 seconds to detect failure
            await asyncio.sleep(1)  # Simulate detection process

            rto_test["phases"].append(
                {
                    "phase": 2,
                    "description": "Failure detection",
                    "duration_seconds": detection_time,
                    "success": True,
                }
            )

            # Phase 3: Restore time measurement
            logger.info("Phase 3: Measuring restore time...")
            phase3_start = time.time()

            restore_test = await self.restore_manager.test_restore(backup_info["path"])
            phase3_duration = time.time() - phase3_start

            rto_test["phases"].append(
                {
                    "phase": 3,
                    "description": "Database restore",
                    "duration_seconds": phase3_duration,
                    "success": restore_test["success"],
                    "tables_restored": restore_test.get("tables_restored", 0),
                }
            )

            # Calculate total RTO
            total_rto_seconds = phase1_duration + detection_time + phase3_duration
            total_rto_minutes = total_rto_seconds / 60

            rto_test["total_rto_seconds"] = total_rto_seconds
            rto_test["total_rto_minutes"] = total_rto_minutes
            rto_test["meets_target"] = (
                total_rto_minutes <= rto_test["target_rto_minutes"]
            )

            # Cleanup
            backup_path = Path(backup_info["path"])
            if backup_path.exists():
                backup_path.unlink()

            rto_test["overall_success"] = restore_test["success"]
            rto_test["completed_at"] = datetime.now().isoformat()

            if rto_test["meets_target"]:
                logger.info(
                    f"RTO test PASSED: {total_rto_minutes:.1f} minutes (target: {rto_test['target_rto_minutes']} minutes)"
                )
            else:
                logger.warning(
                    f"RTO test FAILED: {total_rto_minutes:.1f} minutes exceeds target of {rto_test['target_rto_minutes']} minutes"
                )

        except Exception as e:
            logger.error(f"RTO test failed: {e}")
            rto_test["overall_success"] = False
            rto_test["error"] = str(e)
            rto_test["failed_at"] = datetime.now().isoformat()

        return rto_test

    async def run_rpo_test(self) -> Dict:
        """Run Recovery Point Objective (RPO) test."""
        logger.info("Starting RPO test...")

        rpo_test = {
            "test_type": "rpo_measurement",
            "target_rpo_minutes": 60,  # Target: max 1 hour data loss
            "started_at": datetime.now().isoformat(),
        }

        try:
            # Check backup frequency from metadata
            backups = await self.backup_manager.list_backups()

            if len(backups) >= 2:
                # Calculate time between last two backups
                latest_backup = datetime.fromisoformat(backups[0]["created_at"])
                previous_backup = datetime.fromisoformat(backups[1]["created_at"])

                backup_interval_minutes = (
                    latest_backup - previous_backup
                ).total_seconds() / 60

                rpo_test["backup_interval_minutes"] = backup_interval_minutes
                rpo_test["meets_target"] = (
                    backup_interval_minutes <= rpo_test["target_rpo_minutes"]
                )
                rpo_test["latest_backup_age_minutes"] = (
                    datetime.now() - latest_backup
                ).total_seconds() / 60

                if rpo_test["meets_target"]:
                    logger.info(
                        f"RPO test PASSED: backup interval {backup_interval_minutes:.1f} minutes (target: <={rpo_test['target_rpo_minutes']} minutes)"
                    )
                else:
                    logger.warning(
                        f"RPO test FAILED: backup interval {backup_interval_minutes:.1f} minutes exceeds target of {rpo_test['target_rpo_minutes']} minutes"
                    )
            else:
                rpo_test["meets_target"] = False
                rpo_test["error"] = "Insufficient backup history to measure RPO"
                logger.warning(
                    "RPO test failed: need at least 2 backups to measure interval"
                )

            rpo_test["overall_success"] = rpo_test.get("meets_target", False)
            rpo_test["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"RPO test failed: {e}")
            rpo_test["overall_success"] = False
            rpo_test["error"] = str(e)
            rpo_test["failed_at"] = datetime.now().isoformat()

        return rpo_test

    async def run_comprehensive_dr_test(self) -> Dict:
        """Run comprehensive disaster recovery test."""
        logger.info("Starting comprehensive disaster recovery test...")

        dr_test = {
            "test_suite": "comprehensive_disaster_recovery",
            "started_at": datetime.now().isoformat(),
            "tests": [],
        }

        # Test 1: Database connectivity
        connectivity_test = await self.test_database_connectivity()
        dr_test["tests"].append(
            {
                "test_name": "database_connectivity",
                "result": connectivity_test,
            }
        )

        # Test 2: Backup verification
        backup_test = await self.run_backup_verification_test()
        dr_test["tests"].append(
            {
                "test_name": "backup_verification",
                "result": backup_test,
            }
        )

        # Test 3: RTO measurement
        rto_test = await self.run_rto_test()
        dr_test["tests"].append(
            {
                "test_name": "rto_measurement",
                "result": rto_test,
            }
        )

        # Test 4: RPO measurement
        rpo_test = await self.run_rpo_test()
        dr_test["tests"].append(
            {
                "test_name": "rpo_measurement",
                "result": rpo_test,
            }
        )

        # Calculate overall results
        all_tests_passed = all(
            test["result"].get("overall_success", False)
            or test["result"].get("accessible", False)
            for test in dr_test["tests"]
        )

        dr_test["overall_success"] = all_tests_passed
        dr_test["completed_at"] = datetime.now().isoformat()

        # Save comprehensive report
        report_file = (
            self.backup_dir
            / f"dr_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w") as f:
            json.dump(dr_test, f, indent=2, default=str)

        logger.info(f"Comprehensive DR test completed. Report saved: {report_file}")

        return dr_test

    async def generate_dr_summary_report(self) -> Dict:
        """Generate disaster recovery summary report."""
        logger.info("Generating DR summary report...")

        summary = {
            "report_type": "disaster_recovery_summary",
            "generated_at": datetime.now().isoformat(),
            "database_status": {},
            "backup_status": {},
            "recovery_capabilities": {},
            "recommendations": [],
        }

        # Database status
        connectivity = await self.test_database_connectivity()
        summary["database_status"] = connectivity

        # Backup status
        backups = await self.backup_manager.list_backups()
        if backups:
            latest_backup = backups[0]
            backup_age_hours = (
                datetime.now() - datetime.fromisoformat(latest_backup["created_at"])
            ).total_seconds() / 3600

            summary["backup_status"] = {
                "total_backups": len(backups),
                "latest_backup": latest_backup["filename"],
                "latest_backup_age_hours": backup_age_hours,
                "latest_backup_size": latest_backup["size_pretty"],
                "backup_healthy": backup_age_hours
                < 24,  # Backup should be less than 24h old
            }
        else:
            summary["backup_status"] = {
                "total_backups": 0,
                "backup_healthy": False,
            }

        # Recovery capabilities (based on latest test results)
        try:
            # Look for latest DR test report
            dr_reports = list(self.backup_dir.glob("dr_test_report_*.json"))
            if dr_reports:
                latest_report = sorted(dr_reports)[-1]
                with open(latest_report, "r") as f:
                    latest_dr_test = json.load(f)

                # Extract RTO/RPO from latest test
                for test in latest_dr_test.get("tests", []):
                    if test["test_name"] == "rto_measurement":
                        summary["recovery_capabilities"]["rto_minutes"] = test[
                            "result"
                        ].get("total_rto_minutes")
                        summary["recovery_capabilities"]["rto_meets_target"] = test[
                            "result"
                        ].get("meets_target")
                    elif test["test_name"] == "rpo_measurement":
                        summary["recovery_capabilities"]["rpo_minutes"] = test[
                            "result"
                        ].get("backup_interval_minutes")
                        summary["recovery_capabilities"]["rpo_meets_target"] = test[
                            "result"
                        ].get("meets_target")
        except Exception as e:
            logger.warning(f"Could not load latest DR test results: {e}")

        # Generate recommendations
        if not connectivity["accessible"]:
            summary["recommendations"].append(
                "🚨 Database is not accessible - immediate attention required"
            )

        if not summary["backup_status"].get("backup_healthy", False):
            summary["recommendations"].append(
                "⚠️ Backups are outdated - create fresh backup immediately"
            )

        if summary["backup_status"]["total_backups"] < 3:
            summary["recommendations"].append(
                "💡 Increase backup frequency - maintain at least 3 recent backups"
            )

        if summary["recovery_capabilities"].get("rto_meets_target") == False:
            summary["recommendations"].append(
                "⏱️ RTO exceeds target - optimize restore procedures"
            )

        if summary["recovery_capabilities"].get("rpo_meets_target") == False:
            summary["recommendations"].append(
                "💾 RPO exceeds target - increase backup frequency"
            )

        if not summary["recommendations"]:
            summary["recommendations"].append("✅ All disaster recovery checks passed")

        return summary


async def main():
    """Main disaster recovery operations."""
    conn_string = "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db"

    dr_manager = DisasterRecoveryManager(conn_string)

    print("\n" + "=" * 60)
    print("🚨 DISASTER RECOVERY MANAGER")
    print("=" * 60)

    print("\nOptions:")
    print("1. Run comprehensive DR test")
    print("2. Test database connectivity")
    print("3. Run backup verification test")
    print("4. Measure RTO (Recovery Time Objective)")
    print("5. Measure RPO (Recovery Point Objective)")
    print("6. Generate DR summary report")
    print("7. Exit")

    choice = input("\nSelect option (1-7): ")

    if choice == "1":
        print("\n🧪 Running comprehensive disaster recovery test...")
        print("This may take several minutes...")
        result = await dr_manager.run_comprehensive_dr_test()

        print(
            f"\n{'✅' if result['overall_success'] else '❌'} Comprehensive DR Test: {'PASSED' if result['overall_success'] else 'FAILED'}"
        )

        for test in result["tests"]:
            test_result = test["result"]
            status = (
                "✅"
                if test_result.get(
                    "overall_success", test_result.get("accessible", False)
                )
                else "❌"
            )
            print(f"  {status} {test['test_name']}")

    elif choice == "2":
        print("\n🔌 Testing database connectivity...")
        result = await dr_manager.test_database_connectivity()

        if result["accessible"]:
            print("✅ Database is accessible")
            print(f"   Response time: {result['response_time_ms']:.1f}ms")
            print(f"   TimescaleDB version: {result['timescale_version']}")
        else:
            print("❌ Database is not accessible")
            print(f"   Error: {result['error']}")

    elif choice == "3":
        print("\n🔍 Running backup verification test...")
        result = await dr_manager.run_backup_verification_test()

        print(
            f"\n{'✅' if result['overall_success'] else '❌'} Backup Verification: {'PASSED' if result['overall_success'] else 'FAILED'}"
        )

        for step in result["steps"]:
            status = "✅" if step["success"] else "❌"
            print(f"  {status} Step {step['step']}: {step['description']}")
            if "duration_seconds" in step:
                print(f"      Duration: {step['duration_seconds']:.1f}s")

    elif choice == "4":
        print("\n⏱️ Measuring Recovery Time Objective (RTO)...")
        result = await dr_manager.run_rto_test()

        if result["overall_success"]:
            print(f"✅ RTO Test completed: {result['total_rto_minutes']:.1f} minutes")
            print(f"   Target: {result['target_rto_minutes']} minutes")
            print(
                f"   Status: {'MEETS TARGET' if result['meets_target'] else 'EXCEEDS TARGET'}"
            )
        else:
            print("❌ RTO Test failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")

    elif choice == "5":
        print("\n💾 Measuring Recovery Point Objective (RPO)...")
        result = await dr_manager.run_rpo_test()

        if result["overall_success"]:
            print(
                f"✅ RPO Test completed: {result.get('backup_interval_minutes', 0):.1f} minutes"
            )
            print(f"   Target: {result['target_rpo_minutes']} minutes")
            print(
                f"   Status: {'MEETS TARGET' if result['meets_target'] else 'EXCEEDS TARGET'}"
            )
        else:
            print("❌ RPO Test failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")

    elif choice == "6":
        print("\n📊 Generating DR summary report...")
        summary = await dr_manager.generate_dr_summary_report()

        print("\n=== DISASTER RECOVERY SUMMARY ===")

        # Database Status
        db_status = (
            "✅ ONLINE" if summary["database_status"]["accessible"] else "❌ OFFLINE"
        )
        print(f"\n🗄️  Database Status: {db_status}")
        if summary["database_status"]["accessible"]:
            print(
                f"   Response Time: {summary['database_status']['response_time_ms']:.1f}ms"
            )

        # Backup Status
        backup_status = (
            "✅ HEALTHY"
            if summary["backup_status"].get("backup_healthy", False)
            else "⚠️ NEEDS ATTENTION"
        )
        print(f"\n💾 Backup Status: {backup_status}")
        print(f"   Total Backups: {summary['backup_status']['total_backups']}")
        if summary["backup_status"]["total_backups"] > 0:
            print(f"   Latest: {summary['backup_status']['latest_backup']}")
            print(
                f"   Age: {summary['backup_status']['latest_backup_age_hours']:.1f} hours"
            )

        # Recovery Capabilities
        if summary["recovery_capabilities"]:
            print(f"\n🔄 Recovery Capabilities:")
            if "rto_minutes" in summary["recovery_capabilities"]:
                rto_status = (
                    "✅"
                    if summary["recovery_capabilities"]["rto_meets_target"]
                    else "⚠️"
                )
                print(
                    f"   {rto_status} RTO: {summary['recovery_capabilities']['rto_minutes']:.1f} minutes"
                )
            if "rpo_minutes" in summary["recovery_capabilities"]:
                rpo_status = (
                    "✅"
                    if summary["recovery_capabilities"]["rpo_meets_target"]
                    else "⚠️"
                )
                print(
                    f"   {rpo_status} RPO: {summary['recovery_capabilities']['rpo_minutes']:.1f} minutes"
                )

        # Recommendations
        print(f"\n💡 Recommendations:")
        for recommendation in summary["recommendations"]:
            print(f"   {recommendation}")

    elif choice == "7":
        print("👋 Goodbye!")

    else:
        print("Invalid option")


if __name__ == "__main__":
    asyncio.run(main())
