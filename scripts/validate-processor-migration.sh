#!/bin/bash
# Validation script for ProcessorClient migration

set -e

echo "=== Sample Processor Migration Validation ==="
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if old sample-processor is running
echo "1. Checking for old polling-based processor..."
if docker ps | grep -q "detektr-sample-processor-1"; then
    echo -e "${YELLOW}Found old processor running. Stopping...${NC}"
    docker stop detektr-sample-processor-1 || true
    docker rm detektr-sample-processor-1 || true
else
    echo -e "${GREEN}✓ No old processor running${NC}"
fi

echo
echo "2. Building new ProcessorClient version..."
cd services/sample-processor
docker build -t ghcr.io/hretheum/detektr/sample-processor:v2 .

echo
echo "3. Running new processor with orchestrator URL..."
docker run -d \
    --name detektr-sample-processor-v2 \
    --network detektor-network \
    -e ORCHESTRATOR_URL=http://detektr-frame-buffer-v2-1:8002 \
    -e PROCESSOR_ID=sample-processor-1 \
    -e REDIS_HOST=detektr-redis-1 \
    -e REDIS_PORT=6379 \
    -e LOG_LEVEL=INFO \
    ghcr.io/hretheum/detektr/sample-processor:v2

echo
echo "4. Waiting for processor to start..."
sleep 5

echo
echo "5. Verifying registration with orchestrator..."
REGISTERED=$(curl -s http://localhost:8002/processors 2>/dev/null | jq '.[] | select(.id=="sample-processor-1")' || echo "")

if [ -n "$REGISTERED" ]; then
    echo -e "${GREEN}✓ Processor registered successfully${NC}"
    echo "$REGISTERED" | jq .
else
    echo -e "${RED}✗ Processor not registered${NC}"
    echo "Checking processor logs..."
    docker logs detektr-sample-processor-v2 --tail 20
    exit 1
fi

echo
echo "6. Checking processor is consuming frames..."
docker logs detektr-sample-processor-v2 --tail 20 | grep -E "(Processing frame|Consumer loop|Registered)" || true

echo
echo "7. Verifying NO polling behavior..."
if docker logs detektr-sample-processor-v2 2>&1 | grep -i -E "(dequeue|polling|HTTP GET)"; then
    echo -e "${RED}✗ Found polling behavior - migration failed!${NC}"
    exit 1
else
    echo -e "${GREEN}✓ No polling behavior detected${NC}"
fi

echo
echo "8. Checking Redis consumer group..."
CONSUMER_INFO=$(docker exec detektr-redis-1 redis-cli XINFO CONSUMERS frames:ready:sample-processor-1 frame-processors 2>/dev/null || echo "")

if [ -n "$CONSUMER_INFO" ]; then
    echo -e "${GREEN}✓ Consumer group active${NC}"
    echo "$CONSUMER_INFO"
else
    echo -e "${YELLOW}⚠ Consumer group not found (might not have frames yet)${NC}"
fi

echo
echo "9. Quality Gate Checks:"
echo -n "   - Zero polling requests: "
if ! docker logs detektr-sample-processor-v2 2>&1 | grep -q "/frames/dequeue"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

echo -n "   - Processor registered: "
if [ -n "$REGISTERED" ]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

echo -n "   - Using ProcessorClient pattern: "
if docker logs detektr-sample-processor-v2 2>&1 | grep -q "ProcessorClient"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

echo
echo "=== Migration Validation Complete ==="
