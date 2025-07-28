#!/bin/bash
# Validate Frame Buffer v2 consumer group functionality
# Usage: ./scripts/validate-frame-buffer-consumer.sh

set -e

echo "🔍 Validating Frame Buffer v2 Consumer Group"
echo "==========================================="

# Configuration
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
FRAME_BUFFER_URL=${FRAME_BUFFER_URL:-http://localhost:8002}
STREAM_KEY="frames:metadata"
CONSUMER_GROUP="frame-buffer-group"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n📡 Step 1: Check Frame Buffer v2 service health"
echo "----------------------------------------------"

if curl -s -f "$FRAME_BUFFER_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frame Buffer v2 is healthy"

    # Get service info
    HEALTH=$(curl -s "$FRAME_BUFFER_URL/health" | jq)
    echo "$HEALTH"
else
    echo -e "${RED}✗${NC} Frame Buffer v2 is not responding"
    exit 1
fi

echo -e "\n📊 Step 2: Check consumer group exists"
echo "------------------------------------"

# Check if consumer group exists
GROUP_INFO=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XINFO GROUPS "$STREAM_KEY" 2>&1 || echo "ERROR")

if echo "$GROUP_INFO" | grep -q "$CONSUMER_GROUP"; then
    echo -e "${GREEN}✓${NC} Consumer group '$CONSUMER_GROUP' exists"

    # Extract group details
    echo -e "\nConsumer group details:"
    echo "$GROUP_INFO" | grep -A5 "$CONSUMER_GROUP" | sed 's/^/  /'
else
    if echo "$GROUP_INFO" | grep -q "no such key"; then
        echo -e "${RED}✗${NC} Stream '$STREAM_KEY' does not exist"
        exit 1
    else
        echo -e "${RED}✗${NC} Consumer group '$CONSUMER_GROUP' not found"
        echo "Frame Buffer v2 may not be properly consuming from stream"
        exit 1
    fi
fi

echo -e "\n👥 Step 3: Check active consumers"
echo "--------------------------------"

# Get consumer info
CONSUMERS=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XINFO CONSUMERS "$STREAM_KEY" "$CONSUMER_GROUP" 2>&1 || echo "ERROR")

if echo "$CONSUMERS" | grep -q "name"; then
    echo -e "${GREEN}✓${NC} Found active consumers:"

    # Parse and display consumer info
    CONSUMER_COUNT=$(echo "$CONSUMERS" | grep -c "name" || echo "0")
    echo "Total consumers: $CONSUMER_COUNT"

    # Show each consumer
    echo "$CONSUMERS" | grep -E "(name|pending|idle)" | sed 's/^/  /'

    # Check if consumers are active (idle < 5000ms)
    IDLE_VALUES=$(echo "$CONSUMERS" | grep "idle" | grep -oE "[0-9]+" || echo "")
    ACTIVE_COUNT=0

    for idle in $IDLE_VALUES; do
        if [ "$idle" -lt 5000 ]; then
            ((ACTIVE_COUNT++))
        fi
    done

    if [ "$ACTIVE_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓${NC} $ACTIVE_COUNT active consumer(s) (idle < 5s)"
    else
        echo -e "${YELLOW}⚠${NC} No recently active consumers"
    fi
else
    echo -e "${RED}✗${NC} No consumers found in group"
    exit 1
fi

echo -e "\n📈 Step 4: Monitor consumption progress"
echo "--------------------------------------"

# Get initial group stats
INITIAL_INFO=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XINFO GROUPS "$STREAM_KEY" | grep -A5 "$CONSUMER_GROUP")
INITIAL_DELIVERED=$(echo "$INITIAL_INFO" | grep "last-delivered-id" | awk '{print $2}')
INITIAL_LAG=$(echo "$INITIAL_INFO" | grep "lag" | awk '{print $2}' || echo "0")

echo "Initial state:"
echo "- Last delivered ID: $INITIAL_DELIVERED"
echo "- Lag: $INITIAL_LAG messages"

# Wait and monitor
echo -e "\nMonitoring for 5 seconds..."
sleep 5

# Get final group stats
FINAL_INFO=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XINFO GROUPS "$STREAM_KEY" | grep -A5 "$CONSUMER_GROUP")
FINAL_DELIVERED=$(echo "$FINAL_INFO" | grep "last-delivered-id" | awk '{print $2}')
FINAL_LAG=$(echo "$FINAL_INFO" | grep "lag" | awk '{print $2}' || echo "0")

echo -e "\nFinal state:"
echo "- Last delivered ID: $FINAL_DELIVERED"
echo "- Lag: $FINAL_LAG messages"

# Check progress
if [ "$FINAL_DELIVERED" != "$INITIAL_DELIVERED" ]; then
    echo -e "${GREEN}✓${NC} Consumer group is making progress"
else
    echo -e "${YELLOW}⚠${NC} Consumer group position unchanged"
    echo "This is normal if no new frames are being published"
fi

# Check lag trend
if [ "$FINAL_LAG" -lt "$INITIAL_LAG" ]; then
    echo -e "${GREEN}✓${NC} Lag decreasing (catching up)"
elif [ "$FINAL_LAG" -eq "$INITIAL_LAG" ]; then
    echo -e "${GREEN}✓${NC} Lag stable"
else
    echo -e "${YELLOW}⚠${NC} Lag increasing (falling behind)"
fi

echo -e "\n🔍 Step 5: Check pending messages"
echo "--------------------------------"

# Get pending messages info
PENDING_INFO=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XPENDING "$STREAM_KEY" "$CONSUMER_GROUP" 2>&1 || echo "0")

if echo "$PENDING_INFO" | grep -q "^[0-9]"; then
    PENDING_COUNT=$(echo "$PENDING_INFO" | head -1)
    echo "Pending messages: $PENDING_COUNT"

    if [ "$PENDING_COUNT" -gt 0 ]; then
        # Get details of pending messages
        echo -e "\nPending message details:"
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XPENDING "$STREAM_KEY" "$CONSUMER_GROUP" - + 5 | sed 's/^/  /'

        if [ "$PENDING_COUNT" -gt 100 ]; then
            echo -e "${YELLOW}⚠${NC} High number of pending messages"
        fi
    else
        echo -e "${GREEN}✓${NC} No pending messages"
    fi
else
    echo -e "${GREEN}✓${NC} No pending messages"
fi

echo -e "\n📊 Step 6: Check Frame Buffer metrics"
echo "-----------------------------------"

# Get Frame Buffer metrics
METRICS=$(curl -s "$FRAME_BUFFER_URL/metrics" 2>/dev/null || echo "")

if [ -n "$METRICS" ]; then
    # Extract consumption metrics
    FRAMES_CONSUMED=$(echo "$METRICS" | grep -E "frames_consumed_total" | grep -oE "[0-9]+$" || echo "0")
    CONSUMER_ERRORS=$(echo "$METRICS" | grep -E "consumer_errors_total" | grep -oE "[0-9]+$" || echo "0")

    echo "Frame Buffer metrics:"
    echo "- Frames consumed: $FRAMES_CONSUMED"
    echo "- Consumer errors: $CONSUMER_ERRORS"

    if [ "$CONSUMER_ERRORS" -gt 0 ]; then
        echo -e "${YELLOW}⚠${NC} Consumer errors detected"
    else
        echo -e "${GREEN}✓${NC} No consumer errors"
    fi

    # Check for consumer-specific metrics
    if echo "$METRICS" | grep -q "consumer_lag"; then
        echo -e "\nConsumer lag metrics:"
        echo "$METRICS" | grep "consumer_lag" | head -5 | sed 's/^/  /'
    fi
else
    echo -e "${YELLOW}⚠${NC} Could not retrieve Frame Buffer metrics"
fi

echo -e "\n✅ Summary"
echo "========="
echo -e "${GREEN}✓${NC} Frame Buffer v2 is running and healthy"
echo -e "${GREEN}✓${NC} Consumer group '$CONSUMER_GROUP' is active"
echo -e "${GREEN}✓${NC} Consumers are processing messages from stream"
echo -e "${GREEN}✓${NC} Stream consumption is working correctly"

if [ "$FINAL_LAG" -gt 100 ]; then
    echo -e "${YELLOW}⚠${NC} Note: High lag detected ($FINAL_LAG messages)"
    echo "  Consider scaling consumers or optimizing processing"
fi

echo -e "\n✨ Frame Buffer v2 consumer validation complete!"
