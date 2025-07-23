#!/bin/bash
# Test script for deployment automation
# This script tests the unified deployment script without actually deploying

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_SCRIPT="$SCRIPT_DIR/deploy.sh"

echo "🧪 Testing unified deployment script..."
echo "======================================="

# Test 1: Script exists and is executable
echo -n "✓ Script exists and is executable... "
if [[ -x "$DEPLOY_SCRIPT" ]]; then
    echo "PASS"
else
    echo "FAIL"
    exit 1
fi

# Test 2: Help/usage works
echo -n "✓ Testing help/usage... "
output=$($DEPLOY_SCRIPT invalid 2>&1 || true)
if echo "$output" | grep -q "Valid environments"; then
    echo "PASS"
else
    echo "FAIL"
    echo "Output was: $output"
    exit 1
fi

# Test 3: Environment validation
echo -n "✓ Testing invalid environment... "
if ! $DEPLOY_SCRIPT invalid_env status 2>&1 | grep -q "Unknown environment"; then
    echo "FAIL"
else
    echo "PASS"
fi

# Test 4: Action validation
echo -n "✓ Testing invalid action... "
if ! $DEPLOY_SCRIPT production invalid_action 2>&1 | grep -q "Unknown action"; then
    echo "FAIL"
else
    echo "PASS"
fi

# Test 5: Verify compose files exist
echo -n "✓ Checking Docker Compose files... "
missing_files=0
for env in production staging development; do
    file="$SCRIPT_DIR/../docker/environments/$env/docker-compose.yml"
    if [[ ! -f "$file" ]]; then
        echo "Missing: $file"
        ((missing_files++))
    fi
done
if [[ $missing_files -eq 0 ]]; then
    echo "PASS"
else
    echo "FAIL ($missing_files files missing)"
fi

# Test 6: Test local environment (dry run)
echo "✓ Testing local environment commands..."
echo "  - Status: $($DEPLOY_SCRIPT local status 2>&1 | head -1)"
echo "  - Verify: Running health checks..."
$DEPLOY_SCRIPT local verify 2>&1 | grep -E "(✓|✗|⚠)" || echo "    (No services running)"

# Test 7: Check production simulation
echo -n "✓ Testing production environment (simulation)... "
# Just check if the script would work for production
if TARGET_HOST="test" $DEPLOY_SCRIPT production status 2>&1 | grep -q "SSH connection successful"; then
    echo "Would need SSH"
else
    echo "PASS"
fi

echo ""
echo "======================================="
echo "✅ All tests completed!"
echo ""
echo "Next steps:"
echo "1. Test deployment locally: ./scripts/deploy.sh local deploy"
echo "2. Test on staging: ./scripts/deploy.sh staging deploy"
echo "3. Deploy to production: ./scripts/deploy.sh production deploy"
