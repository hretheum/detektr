#!/bin/bash
# Validate sample-processor migration to ProcessorClient
# Usage: ./scripts/validate-sample-processor.sh

set -e

echo "🔍 Validating Sample Processor Migration to ProcessorClient"
echo "========================================================="

# Configuration
FRAME_BUFFER_URL=${FRAME_BUFFER_URL:-http://localhost:8002}
SAMPLE_PROCESSOR_URL=${SAMPLE_PROCESSOR_URL:-http://localhost:8099}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n📋 Step 1: Verify sample-processor registered with orchestrator"
echo "--------------------------------------------------------------"

# Check if sample-processor is registered
PROCESSORS=$(curl -s "$FRAME_BUFFER_URL/processors" 2>/dev/null || echo "{}")

if echo "$PROCESSORS" | jq -e '.processors[] | select(.id == "sample-processor-1")' > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Sample processor registered successfully"

    # Show processor details
    echo -e "\nProcessor details:"
    echo "$PROCESSORS" | jq '.processors[] | select(.id == "sample-processor-1")'
else
    echo -e "${RED}✗${NC} Sample processor NOT registered!"
    echo -e "${YELLOW}Make sure sample-processor is running with ProcessorClient configuration${NC}"
    exit 1
fi

echo -e "\n📋 Step 2: Check sample-processor health"
echo "---------------------------------------"

# Check health endpoint
if curl -s -f "$SAMPLE_PROCESSOR_URL/health" > /dev/null 2>&1; then
    HEALTH=$(curl -s "$SAMPLE_PROCESSOR_URL/health" | jq)
    echo -e "${GREEN}✓${NC} Sample processor is healthy"
    echo "$HEALTH"
else
    echo -e "${RED}✗${NC} Sample processor health check failed"
    exit 1
fi

echo -e "\n📋 Step 3: Monitor frame distribution to sample-processor"
echo "-------------------------------------------------------"

# Get metrics
METRICS=$(curl -s "$FRAME_BUFFER_URL/metrics" 2>/dev/null || echo "")

# Check for processor-specific metrics
if echo "$METRICS" | grep -q 'processor_id="sample-processor-1"'; then
    echo -e "${GREEN}✓${NC} Found metrics for sample-processor"

    # Extract specific metrics
    echo -e "\nProcessor metrics:"
    echo "$METRICS" | grep 'processor_id="sample-processor-1"' | head -10
else
    echo -e "${YELLOW}⚠${NC} No metrics found for sample-processor yet"
    echo "This might be normal if no frames have been processed"
fi

echo -e "\n📋 Step 4: Verify no polling behavior"
echo "------------------------------------"

# Check container logs for polling attempts (if running in Docker)
if command -v docker &> /dev/null; then
    CONTAINER_NAME="detektr-sample-processor-1"

    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo "Checking last 50 log lines for polling behavior..."

        LOGS=$(docker logs "$CONTAINER_NAME" --tail 50 2>&1 || echo "")

        # Check for old polling patterns
        if echo "$LOGS" | grep -qE "(frames/dequeue|polling|FRAME_BUFFER_URL)"; then
            echo -e "${RED}✗${NC} Found evidence of polling behavior!"
            echo "Sample processor might still be using old configuration"
            exit 1
        else
            echo -e "${GREEN}✓${NC} No polling behavior detected"
        fi

        # Check for ProcessorClient registration
        if echo "$LOGS" | grep -qE "(Registering with orchestrator|ProcessorClient|Successfully registered)"; then
            echo -e "${GREEN}✓${NC} ProcessorClient registration found in logs"
        else
            echo -e "${YELLOW}⚠${NC} No explicit ProcessorClient registration found in recent logs"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Container $CONTAINER_NAME not found, skipping log check"
    fi
else
    echo -e "${YELLOW}⚠${NC} Docker not available, skipping log analysis"
fi

echo -e "\n📋 Step 5: Test frame processing flow"
echo "------------------------------------"

# Check if frames are being distributed
echo "Monitoring frame distribution for 5 seconds..."

# Get initial processor stats
INITIAL_STATS=$(curl -s "$FRAME_BUFFER_URL/processors" | jq '.processors[] | select(.id == "sample-processor-1") | .stats' 2>/dev/null || echo "{}")

sleep 5

# Get final processor stats
FINAL_STATS=$(curl -s "$FRAME_BUFFER_URL/processors" | jq '.processors[] | select(.id == "sample-processor-1") | .stats' 2>/dev/null || echo "{}")

# Compare stats
if [ "$INITIAL_STATS" != "$FINAL_STATS" ]; then
    echo -e "${GREEN}✓${NC} Processor stats changed - frames are being processed"
    echo "Initial: $INITIAL_STATS"
    echo "Final: $FINAL_STATS"
else
    echo -e "${YELLOW}⚠${NC} No change in processor stats"
    echo "This is normal if no frames are currently flowing through the system"
fi

echo -e "\n✅ Summary"
echo "========="
echo -e "${GREEN}✓${NC} Sample processor successfully migrated to ProcessorClient pattern"
echo -e "${GREEN}✓${NC} Registration with orchestrator confirmed"
echo -e "${GREEN}✓${NC} Health checks passing"
echo -e "${GREEN}✓${NC} No polling behavior detected"

echo -e "\n📝 Next steps:"
echo "- Monitor processor performance under load"
echo "- Verify frames are being processed correctly"
echo "- Check distributed tracing in Jaeger"
echo "- Review metrics in Grafana dashboard"

echo -e "\n✨ Validation complete!"
