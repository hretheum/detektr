#!/usr/bin/env python3
"""Setup monitoring for TimescaleDB metadata storage.

Configure Prometheus exporters, Grafana dashboards, and alerts.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MonitoringSetup:
    """Setup monitoring components."""

    def __init__(
        self,
        grafana_url: str = "http://nebula:3000",
        grafana_user: str = "admin",
        grafana_password: str = "admin",
        prometheus_url: str = "http://nebula:9090",
    ):
        """Initialize monitoring setup."""
        self.grafana_url = grafana_url
        self.grafana_auth = (grafana_user, grafana_password)
        self.prometheus_url = prometheus_url
        self.monitoring_dir = Path(__file__).parent

    def check_prometheus_connection(self) -> bool:
        """Check if Prometheus is accessible."""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query?query=up", timeout=5
            )
            if response.status_code == 200:
                logger.info("✅ Prometheus is accessible")
                return True
            else:
                logger.error(f"❌ Prometheus returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Cannot connect to Prometheus: {e}")
            return False

    def check_grafana_connection(self) -> bool:
        """Check if Grafana is accessible."""
        try:
            response = requests.get(f"{self.grafana_url}/api/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Grafana is accessible")
                return True
            else:
                logger.error(f"❌ Grafana returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Cannot connect to Grafana: {e}")
            return False

    def setup_prometheus_datasource(self) -> bool:
        """Setup Prometheus datasource in Grafana."""
        logger.info("Setting up Prometheus datasource...")

        datasource_config = {
            "name": "Prometheus",
            "type": "prometheus",
            "url": self.prometheus_url,
            "access": "proxy",
            "isDefault": True,
            "basicAuth": False,
        }

        try:
            # Check if datasource already exists
            response = requests.get(
                f"{self.grafana_url}/api/datasources/name/Prometheus",
                auth=self.grafana_auth,
                timeout=5,
            )

            if response.status_code == 200:
                logger.info("Prometheus datasource already exists")
                return True

            # Create new datasource
            response = requests.post(
                f"{self.grafana_url}/api/datasources",
                json=datasource_config,
                auth=self.grafana_auth,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info("✅ Prometheus datasource created")
                return True
            else:
                logger.error(f"❌ Failed to create datasource: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error setting up datasource: {e}")
            return False

    def import_dashboard(self, dashboard_file: Path) -> bool:
        """Import a dashboard into Grafana."""
        logger.info(f"Importing dashboard: {dashboard_file.name}")

        try:
            with open(dashboard_file, "r") as f:
                dashboard_json = json.load(f)

            # Prepare dashboard import payload
            import_payload = {
                "dashboard": dashboard_json,
                "overwrite": True,
                "inputs": [
                    {
                        "name": "DS_PROMETHEUS",
                        "type": "datasource",
                        "pluginId": "prometheus",
                        "value": "Prometheus",
                    }
                ],
            }

            response = requests.post(
                f"{self.grafana_url}/api/dashboards/import",
                json=import_payload,
                auth=self.grafana_auth,
                timeout=15,
            )

            if response.status_code == 200:
                result = response.json()
                dashboard_url = f"{self.grafana_url}/d/{result['uid']}"
                logger.info(f"✅ Dashboard imported: {dashboard_url}")
                return True
            else:
                logger.error(f"❌ Failed to import dashboard: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error importing dashboard {dashboard_file.name}: {e}")
            return False

    def setup_dashboards(self) -> List[str]:
        """Setup all Grafana dashboards."""
        logger.info("Setting up Grafana dashboards...")

        dashboard_dir = self.monitoring_dir / "dashboards"
        dashboard_files = list(dashboard_dir.glob("*.json"))

        imported_dashboards = []

        for dashboard_file in dashboard_files:
            if self.import_dashboard(dashboard_file):
                imported_dashboards.append(dashboard_file.name)

        logger.info(f"✅ Imported {len(imported_dashboards)} dashboards")
        return imported_dashboards

    def validate_alerts_config(self) -> bool:
        """Validate alert rules configuration."""
        logger.info("Validating alert rules...")

        alerts_file = self.monitoring_dir / "alerts" / "timescaledb-alerts.yml"

        if not alerts_file.exists():
            logger.error(f"❌ Alert rules file not found: {alerts_file}")
            return False

        try:
            # Use promtool to validate if available
            result = subprocess.run(
                ["promtool", "check", "rules", str(alerts_file)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                logger.info("✅ Alert rules are valid")
                return True
            else:
                logger.error(f"❌ Alert rules validation failed: {result.stderr}")
                return False

        except FileNotFoundError:
            logger.warning("⚠️  promtool not found, skipping validation")
            # Basic YAML validation
            try:
                import yaml

                with open(alerts_file, "r") as f:
                    yaml.safe_load(f)
                logger.info("✅ Alert rules YAML syntax is valid")
                return True
            except Exception as e:
                logger.error(f"❌ Alert rules YAML syntax error: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Error validating alert rules: {e}")
            return False

    def check_postgres_exporter(self) -> bool:
        """Check if postgres_exporter is running and collecting metrics."""
        logger.info("Checking postgres_exporter...")

        try:
            # Check if postgres_exporter metrics are available
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query?query=pg_up",
                timeout=5,
            )

            if response.status_code == 200:
                result = response.json()
                if result["data"]["result"]:
                    logger.info("✅ postgres_exporter is collecting metrics")
                    return True
                else:
                    logger.error("❌ No postgres_exporter metrics found")
                    return False
            else:
                logger.error(f"❌ Failed to query Prometheus: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Error checking postgres_exporter: {e}")
            return False

    def create_monitoring_summary(self) -> Dict:
        """Create a summary of monitoring setup."""
        summary = {
            "prometheus_accessible": self.check_prometheus_connection(),
            "grafana_accessible": self.check_grafana_connection(),
            "postgres_exporter_running": False,
            "datasource_configured": False,
            "dashboards_imported": [],
            "alerts_valid": False,
        }

        if summary["prometheus_accessible"]:
            summary["postgres_exporter_running"] = self.check_postgres_exporter()

        if summary["grafana_accessible"]:
            summary["datasource_configured"] = self.setup_prometheus_datasource()
            if summary["datasource_configured"]:
                summary["dashboards_imported"] = self.setup_dashboards()

        summary["alerts_valid"] = self.validate_alerts_config()

        return summary

    def generate_monitoring_docs(self) -> str:
        """Generate monitoring documentation."""
        docs = """# TimescaleDB Monitoring Setup

## Overview
This monitoring setup provides comprehensive observability for the
TimescaleDB metadata storage system.

## Components

### Dashboards
1. **TimescaleDB Metadata Storage** (`timescaledb-dashboard.json`)
   - Database status and health
   - Query performance metrics
   - Cache hit ratios
   - Connection monitoring
   - I/O performance

2. **TimescaleDB Hypertables & Chunks** (`timescaledb-hypertables.json`)
   - Hypertable-specific metrics
   - Chunk statistics
   - Compression ratios
   - Table operations

### Alerts (`timescaledb-alerts.yml`)
- **Critical**: Database down, replication lag
- **Warning**: High connections, low cache hit ratio, disk usage
- **Info**: Low compression ratio

### Key Metrics

#### Database Health
- `pg_up`: Database availability
- `pg_stat_database_numbackends`: Active connections
- `pg_database_size_bytes`: Database size

#### Performance
- Cache hit ratio calculation
- Query execution times
- I/O operations (reads/writes)

#### TimescaleDB Specific
- `timescaledb_hypertable_chunks_total`: Number of chunks
- `timescaledb_hypertable_compression_ratio`: Compression efficiency

## Setup Instructions

1. Ensure postgres_exporter is running:
   ```bash
   docker run -d \\
     --name postgres_exporter \\
     -p 9187:9187 \\
     -e DATA_SOURCE_NAME="postgresql://exporter:password@\\
timescaledb:5432/detektor_db?sslmode=disable" \\
     prometheuscommunity/postgres-exporter
   ```

2. Configure Prometheus to scrape postgres_exporter:
   ```yaml
   scrape_configs:
     - job_name: 'postgres'
       static_configs:
         - targets: ['postgres_exporter:9187']
   ```

3. Import dashboards and configure alerts using this script:
   ```bash
   python setup-monitoring.py
   ```

## Dashboard URLs
- Main Dashboard: http://nebula:3000/d/timescaledb-metadata
- Hypertables Dashboard: http://nebula:3000/d/timescaledb-hypertables

## Alert Manager
Configure Alertmanager to handle notifications:
- Slack/Discord for critical alerts
- Email for warnings
- PagerDuty for production incidents

## Maintenance
- Review alert thresholds monthly
- Update dashboards based on usage patterns
- Monitor dashboard performance and optimize queries
"""

        docs_file = self.monitoring_dir / "README.md"
        with open(docs_file, "w") as f:
            f.write(docs)

        logger.info(f"📄 Monitoring documentation saved: {docs_file}")
        return str(docs_file)


def main():
    """Main setup function."""
    print("\n" + "=" * 60)
    print("📊 TIMESCALEDB MONITORING SETUP")
    print("=" * 60)

    # Initialize setup
    setup = MonitoringSetup()

    print("\n🔍 Running monitoring setup...")
    summary = setup.create_monitoring_summary()

    # Display results
    print("\n📋 Setup Summary:")
    print(f"  {'✅' if summary['prometheus_accessible'] else '❌'} Prometheus accessible")
    print(f"  {'✅' if summary['grafana_accessible'] else '❌'} Grafana accessible")
    status = "✅" if summary["postgres_exporter_running"] else "❌"
    print(f"  {status} postgres_exporter running")
    print(f"  {'✅' if summary['datasource_configured'] else '❌'} Datasource configured")
    status = "✅" if summary["dashboards_imported"] else "❌"
    count = len(summary["dashboards_imported"])
    print(f"  {status} Dashboards imported ({count})")
    print(f"  {'✅' if summary['alerts_valid'] else '❌'} Alert rules valid")

    if summary["dashboards_imported"]:
        print("\n📊 Imported Dashboards:")
        for dashboard in summary["dashboards_imported"]:
            print(f"    • {dashboard}")

    # Generate documentation
    docs_path = setup.generate_monitoring_docs()
    print(f"\n📄 Documentation: {docs_path}")

    # Final recommendations
    print("\n💡 Next Steps:")

    if not summary["prometheus_accessible"]:
        print("  • Start Prometheus on nebula:9090")

    if not summary["grafana_accessible"]:
        print("  • Start Grafana on nebula:3000")

    if not summary["postgres_exporter_running"]:
        print("  • Deploy postgres_exporter to collect database metrics")
        print("  • Add postgres_exporter to Prometheus scrape config")

    if summary["alerts_valid"]:
        print("  • Deploy alert rules to Prometheus")
        print("  • Configure Alertmanager for notifications")

    print("  • Access dashboards at http://nebula:3000")
    print("  • Review and customize alert thresholds")

    # Overall status
    successful_components = sum(
        [
            summary["prometheus_accessible"],
            summary["grafana_accessible"],
            summary["postgres_exporter_running"],
            summary["datasource_configured"],
            bool(summary["dashboards_imported"]),
            summary["alerts_valid"],
        ]
    )

    total_components = 6
    success_rate = (successful_components / total_components) * 100

    print(
        f"\n🎯 Setup Status: {successful_components}/{total_components} "
        f"components ({success_rate:.0f}%)"
    )

    if success_rate >= 80:
        print("✅ Monitoring setup is ready for production!")
    elif success_rate >= 60:
        print("⚠️  Monitoring setup needs attention")
    else:
        print("❌ Monitoring setup requires significant work")


if __name__ == "__main__":
    main()
