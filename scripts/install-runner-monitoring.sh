#!/bin/bash
# Install GitHub Runner monitoring components

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="/opt/detektor-clean"

echo "🚀 Installing GitHub Runner monitoring..."

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root or with sudo"
   exit 1
fi

# Copy scripts to deployment directory
echo "📋 Copying monitoring scripts..."
mkdir -p "$DEPLOY_DIR/scripts"
cp "$SCRIPT_DIR/runner-health-check.sh" "$DEPLOY_DIR/scripts/"
cp "$SCRIPT_DIR/runner-auto-recovery.sh" "$DEPLOY_DIR/scripts/"
chmod +x "$DEPLOY_DIR/scripts/"*.sh

# Install systemd services
echo "🔧 Installing systemd services..."
cp "$SCRIPT_DIR/github-runner.service" /etc/systemd/system/
cp "$SCRIPT_DIR/github-runner-recovery.service" /etc/systemd/system/
cp "$SCRIPT_DIR/notify-admin@.service" /etc/systemd/system/
systemctl daemon-reload

# Install cron job
echo "⏰ Installing cron job..."
crontab -u runner "$SCRIPT_DIR/runner-health.cron" || {
    echo "Failed to install cron job - user 'runner' may not exist"
    echo "Please create the runner user and re-run this script"
}

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p /var/lib/prometheus/node-exporter
mkdir -p /var/log/github-runner/backups
mkdir -p /var/lib/github-runner

# Set permissions
chown -R runner:runner /var/log/github-runner || true
chown -R runner:runner /var/lib/github-runner || true
chown prometheus:prometheus /var/lib/prometheus/node-exporter || true

# Copy Prometheus rules
echo "📊 Installing Prometheus rules..."
PROMETHEUS_RULES_DIR="/etc/prometheus/rules"
if [[ -d "$PROMETHEUS_RULES_DIR" ]]; then
    mkdir -p "$PROMETHEUS_RULES_DIR"
    cp "$SCRIPT_DIR/../monitoring/prometheus/rules/github-runner.yml" "$PROMETHEUS_RULES_DIR/"
    # Reload Prometheus configuration
    pkill -HUP prometheus || true
else
    echo "Prometheus rules directory not found, skipping rules installation"
fi

echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Enable services: systemctl enable github-runner github-runner-recovery"
echo "2. Start services: systemctl start github-runner github-runner-recovery"
echo "3. Check status: systemctl status github-runner github-runner-recovery"
echo "4. View logs: journalctl -u github-runner -f"
