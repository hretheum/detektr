#!/bin/bash
# Script to validate frame distribution to processor queues

set -e

echo "🔍 Validating Frame Distribution..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Redis CLI with docker - find actual container name
REDIS_CONTAINER=$(docker ps --format "table {{.Names}}" | grep -E "redis" | head -1)
REDIS_CMD="docker exec $REDIS_CONTAINER redis-cli"

echo -e "\n${YELLOW}1. Checking processor registrations...${NC}"
curl -s http://localhost:8002/processors | jq '.'

echo -e "\n${YELLOW}2. Checking input stream (frames:metadata)...${NC}"
STREAM_LEN=$($REDIS_CMD XLEN frames:metadata)
echo "Stream length: $STREAM_LEN"

echo -e "\n${YELLOW}3. Checking processor queues...${NC}"
# Get all processor queues
QUEUES=$($REDIS_CMD KEYS "frames:ready:*" | tr -d '\r')

if [ -z "$QUEUES" ]; then
    echo -e "${RED}No processor queues found!${NC}"
else
    for queue in $QUEUES; do
        LENGTH=$($REDIS_CMD XLEN "$queue" | tr -d '\r')
        echo "Queue $queue: $LENGTH messages"
    done
fi

echo -e "\n${YELLOW}4. Monitoring frame distribution (10 seconds)...${NC}"
# Get initial counts
declare -A INITIAL_COUNTS
for queue in $QUEUES; do
    INITIAL_COUNTS["$queue"]=$($REDIS_CMD XLEN "$queue" | tr -d '\r')
done

# Add test frame to input stream
echo "Adding test frame to input stream..."
$REDIS_CMD XADD frames:metadata \* \
    frame_id "dist-test-$(date +%s)" \
    camera_id "test-cam" \
    timestamp "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
    size_bytes "1024" \
    width "1920" \
    height "1080" \
    format "jpeg" \
    trace_context "{}" \
    metadata "{\"detection_type\":\"test\"}" > /dev/null

# Wait for distribution
sleep 3

# Get final counts
echo -e "\n${YELLOW}5. Checking distribution results...${NC}"
FRAMES_DISTRIBUTED=0
for queue in $QUEUES; do
    FINAL_COUNT=$($REDIS_CMD XLEN "$queue" | tr -d '\r')
    INITIAL=${INITIAL_COUNTS["$queue"]}
    DIFF=$((FINAL_COUNT - INITIAL))

    if [ $DIFF -gt 0 ]; then
        echo -e "${GREEN}✓ Queue $queue: +$DIFF frames${NC}"
        FRAMES_DISTRIBUTED=$((FRAMES_DISTRIBUTED + DIFF))
    else
        echo "Queue $queue: no change"
    fi
done

echo -e "\n${YELLOW}6. Checking distribution metrics...${NC}"
curl -s http://localhost:8002/metrics | grep -E "frame_buffer_frames_distributed_total|frame_buffer_frames_distributed_total.*success" || echo "No distribution metrics found"

echo -e "\n${YELLOW}7. Checking consumer group status...${NC}"
$REDIS_CMD XINFO GROUPS frames:metadata || echo "No consumer groups found"

# Summary
echo -e "\n${YELLOW}=== SUMMARY ===${NC}"
if [ $FRAMES_DISTRIBUTED -gt 0 ]; then
    echo -e "${GREEN}✓ Frame distribution is working! Distributed $FRAMES_DISTRIBUTED frames.${NC}"
    exit 0
else
    echo -e "${RED}✗ Frame distribution is NOT working!${NC}"
    echo "Possible issues:"
    echo "  - No processors registered"
    echo "  - Processors don't have matching capabilities"
    echo "  - Frame Buffer v2 not consuming from input stream"
    echo "  - Distribution logic not implemented correctly"
    exit 1
fi
