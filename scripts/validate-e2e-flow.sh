#!/bin/bash
# Validate end-to-end flow from RTSP Capture to Processors
# Usage: ./scripts/validate-e2e-flow.sh

set -e

echo "🔍 Frame Buffer v2 E2E Flow Validation"
echo "====================================="

# Configuration
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
FRAME_BUFFER_URL=${FRAME_BUFFER_URL:-http://localhost:8002}
SAMPLE_PROCESSOR_URL=${SAMPLE_PROCESSOR_URL:-http://localhost:8099}
RTSP_CAPTURE_URL=${RTSP_CAPTURE_URL:-http://localhost:8080}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper functions
check_service() {
    local service=$1
    local url=$2

    if curl -s -f "$url/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not responding at $url"
        return 1
    fi
}

# Step 1: Check all services are running
echo -e "\n📡 Checking service health..."
check_service "RTSP Capture" "$RTSP_CAPTURE_URL"
check_service "Frame Buffer v2" "$FRAME_BUFFER_URL"
check_service "Sample Processor" "$SAMPLE_PROCESSOR_URL"

# Step 2: Verify Redis Stream exists
echo -e "\n📊 Checking Redis Stream..."
STREAM_EXISTS=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" EXISTS frames:metadata)
if [ "$STREAM_EXISTS" = "1" ]; then
    STREAM_LENGTH=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XLEN frames:metadata)
    echo -e "${GREEN}✓${NC} Stream 'frames:metadata' exists with $STREAM_LENGTH entries"
else
    echo -e "${RED}✗${NC} Stream 'frames:metadata' does not exist"
    exit 1
fi

# Step 3: Check consumer group
echo -e "\n👥 Checking consumer groups..."
CONSUMER_GROUPS=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XINFO GROUPS frames:metadata 2>/dev/null | grep -c "name" || echo "0")
if [ "$CONSUMER_GROUPS" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Found $CONSUMER_GROUPS consumer group(s)"
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XINFO GROUPS frames:metadata
else
    echo -e "${YELLOW}⚠${NC} No consumer groups found"
fi

# Step 4: Monitor frame flow for 10 seconds
echo -e "\n📈 Monitoring frame flow for 10 seconds..."

# Get initial metrics
RTSP_FRAMES_BEFORE=$(curl -s "$RTSP_CAPTURE_URL/metrics" 2>/dev/null | grep -E "frames_captured_total" | grep -oE "[0-9]+$" || echo "0")
PROCESSOR_FRAMES_BEFORE=$(curl -s "$SAMPLE_PROCESSOR_URL/metrics" 2>/dev/null | grep -E "frames_processed" | grep -oE "[0-9]+$" || echo "0")
STREAM_LENGTH_BEFORE=$STREAM_LENGTH

# Wait
sleep 10

# Get final metrics
RTSP_FRAMES_AFTER=$(curl -s "$RTSP_CAPTURE_URL/metrics" 2>/dev/null | grep -E "frames_captured_total" | grep -oE "[0-9]+$" || echo "0")
PROCESSOR_FRAMES_AFTER=$(curl -s "$SAMPLE_PROCESSOR_URL/metrics" 2>/dev/null | grep -E "frames_processed" | grep -oE "[0-9]+$" || echo "0")
STREAM_LENGTH_AFTER=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XLEN frames:metadata)

# Calculate rates
RTSP_RATE=$(( RTSP_FRAMES_AFTER - RTSP_FRAMES_BEFORE ))
PROCESSOR_RATE=$(( PROCESSOR_FRAMES_AFTER - PROCESSOR_FRAMES_BEFORE ))
STREAM_GROWTH=$(( STREAM_LENGTH_AFTER - STREAM_LENGTH_BEFORE ))

echo -e "\n📊 Results:"
echo "  RTSP Capture:      $RTSP_RATE frames in 10s ($(( RTSP_RATE / 10 )) FPS)"
echo "  Sample Processor:  $PROCESSOR_RATE frames in 10s ($(( PROCESSOR_RATE / 10 )) FPS)"
echo "  Stream growth:     $STREAM_GROWTH entries"

# Step 5: Check Frame Buffer v2 metrics
echo -e "\n🎯 Frame Buffer v2 Metrics:"
curl -s "$FRAME_BUFFER_URL/metrics" 2>/dev/null | grep -E "(frames_distributed|frames_queued|processor_active)" | head -10

# Step 6: Verify processor registration
echo -e "\n🔌 Checking processor registration..."
PROCESSORS=$(curl -s "$FRAME_BUFFER_URL/processors" 2>/dev/null | jq -r '.processors[].id' 2>/dev/null)
if [ -n "$PROCESSORS" ]; then
    echo -e "${GREEN}✓${NC} Registered processors:"
    echo "$PROCESSORS" | while IFS= read -r line; do echo "  - $line"; done
else
    echo -e "${RED}✗${NC} No processors registered"
fi

# Step 7: Summary
echo -e "\n📋 Summary:"
if [ "$RTSP_RATE" -gt 0 ] && [ "$PROCESSOR_RATE" -gt 0 ]; then
    FRAME_LOSS=$(( RTSP_RATE - PROCESSOR_RATE ))
    LOSS_PERCENT=$(( (FRAME_LOSS * 100) / RTSP_RATE ))

    if [ "$LOSS_PERCENT" -lt 5 ]; then
        echo -e "${GREEN}✓${NC} End-to-end flow is working"
        echo -e "${GREEN}✓${NC} Frame loss: $LOSS_PERCENT% (acceptable)"
    else
        echo -e "${YELLOW}⚠${NC} High frame loss detected: $LOSS_PERCENT%"
    fi

    if [ "$STREAM_GROWTH" -gt 100 ]; then
        echo -e "${YELLOW}⚠${NC} Stream is growing rapidly - possible consumption issue"
    else
        echo -e "${GREEN}✓${NC} Stream size is stable"
    fi
else
    echo -e "${RED}✗${NC} No frame flow detected"
    echo "  - Check if RTSP camera is connected"
    echo "  - Verify Frame Buffer v2 is consuming from stream"
    echo "  - Check processor health and registration"
fi

echo -e "\n✨ Validation complete!"
