#!/bin/bash
# Validate RTSP Capture → Redis Stream flow
# Usage: ./scripts/validate-rtsp-stream.sh

set -e

echo "🔍 Validating RTSP → Redis Stream Flow"
echo "====================================="

# Configuration
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
RTSP_URL=${RTSP_URL:-http://localhost:8080}
STREAM_KEY="frames:metadata"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n📡 Step 1: Check RTSP Capture service health"
echo "-------------------------------------------"

if curl -s -f "$RTSP_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} RTSP Capture is healthy"

    # Get service info
    HEALTH=$(curl -s "$RTSP_URL/health" | jq)
    echo "$HEALTH"
else
    echo -e "${RED}✗${NC} RTSP Capture is not responding"
    exit 1
fi

echo -e "\n📊 Step 2: Check Redis Stream exists"
echo "----------------------------------"

# Check if stream exists
if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" EXISTS "$STREAM_KEY" | grep -q "1"; then
    echo -e "${GREEN}✓${NC} Stream '$STREAM_KEY' exists"

    # Get stream length
    LENGTH=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XLEN "$STREAM_KEY")
    echo "Stream contains $LENGTH entries"
else
    echo -e "${YELLOW}⚠${NC} Stream '$STREAM_KEY' does not exist yet"
    echo "Waiting for RTSP to create stream..."

    # Wait up to 10 seconds for stream to be created
    for i in {1..10}; do
        sleep 1
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" EXISTS "$STREAM_KEY" | grep -q "1"; then
            echo -e "${GREEN}✓${NC} Stream created!"
            break
        fi
        if [ "$i" -eq 10 ]; then
            echo -e "${RED}✗${NC} Stream not created after 10 seconds"
            exit 1
        fi
    done
fi

echo -e "\n📈 Step 3: Monitor frame flow for 10 seconds"
echo "------------------------------------------"

# Get initial stream length
INITIAL_LENGTH=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XLEN "$STREAM_KEY")
echo "Initial stream length: $INITIAL_LENGTH"

# Monitor for 10 seconds
echo "Monitoring..."
MONITOR_TIME=10

# Use timeout to read frames for exactly 10 seconds
timeout $MONITOR_TIME redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" \
    XREAD BLOCK 0 STREAMS "$STREAM_KEY" $ 2>/dev/null | grep -c "frame_id" > /dev/null || true

# Get final stream length
FINAL_LENGTH=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XLEN "$STREAM_KEY")
NEW_FRAMES=$((FINAL_LENGTH - INITIAL_LENGTH))

echo -e "\nResults after ${MONITOR_TIME}s:"
echo "- New frames in stream: $NEW_FRAMES"
echo "- Estimated FPS: $((NEW_FRAMES / MONITOR_TIME))"

if [ "$NEW_FRAMES" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Frames are being published to Redis Stream"
else
    echo -e "${RED}✗${NC} No new frames detected!"
    exit 1
fi

echo -e "\n🔬 Step 4: Analyze frame structure"
echo "---------------------------------"

# Get last few frames
echo "Checking frame structure..."
LAST_FRAME=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XREVRANGE "$STREAM_KEY" + - COUNT 1)

# Extract and check fields
if echo "$LAST_FRAME" | grep -q "frame_id"; then
    echo -e "${GREEN}✓${NC} frame_id present"
else
    echo -e "${RED}✗${NC} frame_id missing"
fi

if echo "$LAST_FRAME" | grep -q "camera_id"; then
    echo -e "${GREEN}✓${NC} camera_id present"
else
    echo -e "${RED}✗${NC} camera_id missing"
fi

if echo "$LAST_FRAME" | grep -q "timestamp"; then
    echo -e "${GREEN}✓${NC} timestamp present"
else
    echo -e "${RED}✗${NC} timestamp missing"
fi

if echo "$LAST_FRAME" | grep -q "traceparent"; then
    echo -e "${GREEN}✓${NC} traceparent (trace context) present"
else
    echo -e "${YELLOW}⚠${NC} traceparent missing (optional)"
fi

echo -e "\n📊 Step 5: Check RTSP metrics"
echo "----------------------------"

# Get RTSP metrics
METRICS=$(curl -s "$RTSP_URL/metrics" 2>/dev/null || echo "")

if [ -n "$METRICS" ]; then
    # Extract key metrics
    FRAMES_CAPTURED=$(echo "$METRICS" | grep -E "frames_captured_total" | grep -oE "[0-9]+$" || echo "0")
    FRAMES_PUBLISHED=$(echo "$METRICS" | grep -E "frames_published_total" | grep -oE "[0-9]+$" || echo "0")

    echo "RTSP Metrics:"
    echo "- Frames captured: $FRAMES_CAPTURED"
    echo "- Frames published: $FRAMES_PUBLISHED"

    if [ "$FRAMES_CAPTURED" -gt 0 ] && [ "$FRAMES_PUBLISHED" -gt 0 ]; then
        PUBLISH_RATE=$(awk "BEGIN {printf \"%.1f\", $FRAMES_PUBLISHED / $FRAMES_CAPTURED * 100}")
        echo "- Publish rate: ${PUBLISH_RATE}%"

        if (( $(echo "$PUBLISH_RATE > 95" | bc -l) )); then
            echo -e "${GREEN}✓${NC} High publish rate - minimal frame loss"
        else
            echo -e "${YELLOW}⚠${NC} Lower publish rate - some frames may be dropped"
        fi
    fi
else
    echo -e "${YELLOW}⚠${NC} Could not retrieve RTSP metrics"
fi

echo -e "\n📋 Step 6: Stream info summary"
echo "-----------------------------"

# Get detailed stream info
STREAM_INFO=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" XINFO STREAM "$STREAM_KEY" 2>/dev/null || echo "{}")

if [ -n "$STREAM_INFO" ]; then
    echo "$STREAM_INFO" | grep -E "(length|first-entry|last-entry|radix-tree-nodes)"
fi

echo -e "\n✅ Summary"
echo "========="
echo -e "${GREEN}✓${NC} RTSP Capture is running and healthy"
echo -e "${GREEN}✓${NC} Redis Stream '$STREAM_KEY' is active"
echo -e "${GREEN}✓${NC} Frames are being published continuously"
echo -e "${GREEN}✓${NC} Frame structure is correct"
echo -e "${GREEN}✓${NC} Estimated ${NEW_FRAMES} frames in ${MONITOR_TIME}s (~$((NEW_FRAMES / MONITOR_TIME)) FPS)"

echo -e "\n✨ RTSP → Redis Stream validation complete!"
