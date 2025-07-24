#!/bin/bash
# check-deployment-security.sh - Verify deployment security isolation

set -euo pipefail

echo "🔍 Checking deployment security on Nebula..."

# Check if old directory exists
echo -e "\n📁 Checking old deployment directory:"
if ssh nebula "test -d /opt/detektor"; then
    echo "⚠️  Old directory /opt/detektor exists"
    echo "   Files in old directory:"
    ssh nebula "find /opt/detektor -name '*.py' -o -name '*.ts' -o -name '*.js' | head -20"
    echo "   Total source files: $(ssh nebula "find /opt/detektor -name '*.py' -o -name '*.ts' -o -name '*.js' | wc -l")"
else
    echo "✅ Old directory /opt/detektor does not exist"
fi

# Check new clean directory
echo -e "\n📁 Checking new deployment directory:"
if ssh nebula "test -d /opt/detektor-clean"; then
    echo "✅ New directory /opt/detektor-clean exists"
    echo "   Contents:"
    ssh nebula "ls -la /opt/detektor-clean/"
    echo "   Source files check:"
    ssh nebula "find /opt/detektor-clean -name '*.py' -o -name '*.ts' -o -name '*.js' | wc -l" || echo "0"
else
    echo "⚠️  New directory /opt/detektor-clean does not exist yet"
fi

# Check running containers
echo -e "\n🐳 Docker containers status:"
ssh nebula "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' | grep -E '(detektor|detektr|base-)' || echo 'No containers found'"

# Check docker volumes
echo -e "\n💾 Docker volumes:"
ssh nebula "docker volume ls | grep -E '(postgres|detektor)' || echo 'No volumes found'"

echo -e "\n✅ Security check complete"
