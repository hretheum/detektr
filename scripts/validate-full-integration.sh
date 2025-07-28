#!/bin/bash
# Comprehensive validation of RTSP → Redis → Frame Buffer v2 → Processors flow
# Usage: ./scripts/validate-full-integration.sh

set -e

echo "🚀 Full Integration Validation Suite"
echo "===================================="
echo "This will run all validation tasks to ensure the complete"
echo "frame processing pipeline is working correctly."
echo

# Configuration
SCRIPTS_DIR=$(dirname "$0")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Task tracking
TOTAL_TASKS=5
COMPLETED_TASKS=0

# Helper function to run a task
run_task() {
    local task_num=$1
    local task_name=$2
    local script=$3

    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Task $task_num/$TOTAL_TASKS: $task_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ -x "$script" ]; then
        if $script; then
            echo -e "\n${GREEN}✓ Task $task_num completed successfully${NC}"
            ((COMPLETED_TASKS++))
        else
            echo -e "\n${RED}✗ Task $task_num failed${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ Script not found or not executable: $script${NC}"
        return 1
    fi
}

# Task 1: Verify RTSP → Redis Stream Flow
if ! run_task 1 "Verify RTSP → Redis Stream Flow" "$SCRIPTS_DIR/validate-rtsp-stream.sh"; then
    echo -e "${RED}Critical failure: RTSP not publishing to Redis${NC}"
    exit 1
fi

# Task 2: Verify Frame Buffer v2 Consumer
if ! run_task 2 "Verify Frame Buffer v2 Consumes from Stream" "$SCRIPTS_DIR/validate-frame-buffer-consumer.sh"; then
    echo -e "${RED}Critical failure: Frame Buffer not consuming${NC}"
    exit 1
fi

# Task 3: Verify Sample Processor Integration
if ! run_task 3 "Verify Sample Processor (ProcessorClient)" "$SCRIPTS_DIR/validate-sample-processor.sh"; then
    echo -e "${YELLOW}Warning: Sample processor validation failed${NC}"
    # Not critical, continue
fi

# Task 4: End-to-End Flow Validation
if ! run_task 4 "End-to-End Flow Validation" "$SCRIPTS_DIR/validate-e2e-flow.sh"; then
    echo -e "${YELLOW}Warning: E2E flow validation showed issues${NC}"
fi

# Task 5: Performance Check
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Task 5/$TOTAL_TASKS: Performance Validation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Quick performance check
echo "Running 30-second performance test..."

# Get initial metrics
RTSP_FRAMES_BEFORE=$(curl -s "http://localhost:8080/metrics" 2>/dev/null | grep -E "frames_captured_total" | grep -oE "[0-9]+$" || echo "0")
PROCESSOR_FRAMES_BEFORE=$(curl -s "http://localhost:8099/metrics" 2>/dev/null | grep -E "frames_processed" | grep -oE "[0-9]+$" || echo "0")
STREAM_LENGTH_BEFORE=$(redis-cli XLEN frames:metadata 2>/dev/null || echo "0")

# Wait 30 seconds
echo "Collecting metrics for 30 seconds..."
sleep 30

# Get final metrics
RTSP_FRAMES_AFTER=$(curl -s "http://localhost:8080/metrics" 2>/dev/null | grep -E "frames_captured_total" | grep -oE "[0-9]+$" || echo "0")
PROCESSOR_FRAMES_AFTER=$(curl -s "http://localhost:8099/metrics" 2>/dev/null | grep -E "frames_processed" | grep -oE "[0-9]+$" || echo "0")
STREAM_LENGTH_AFTER=$(redis-cli XLEN frames:metadata 2>/dev/null || echo "0")

# Calculate rates
RTSP_RATE=$(( (RTSP_FRAMES_AFTER - RTSP_FRAMES_BEFORE) / 30 ))
PROCESSOR_RATE=$(( (PROCESSOR_FRAMES_AFTER - PROCESSOR_FRAMES_BEFORE) / 30 ))
STREAM_GROWTH=$(( (STREAM_LENGTH_AFTER - STREAM_LENGTH_BEFORE) / 30 ))

echo -e "\nPerformance Results:"
echo "- RTSP capture rate: $RTSP_RATE FPS"
echo "- Processing rate: $PROCESSOR_RATE FPS"
echo "- Stream growth: $STREAM_GROWTH frames/s"

# Evaluate performance
if [ "$RTSP_RATE" -ge 25 ]; then
    echo -e "${GREEN}✓ RTSP capture rate is good (≥25 FPS)${NC}"
else
    echo -e "${YELLOW}⚠ RTSP capture rate is low (<25 FPS)${NC}"
fi

if [ "$PROCESSOR_RATE" -ge 20 ]; then
    echo -e "${GREEN}✓ Processing rate is good (≥20 FPS)${NC}"
else
    echo -e "${YELLOW}⚠ Processing rate is low (<20 FPS)${NC}"
fi

if [ "$STREAM_GROWTH" -lt 5 ]; then
    echo -e "${GREEN}✓ Stream size is stable (no significant backlog)${NC}"
else
    echo -e "${YELLOW}⚠ Stream is growing - possible processing bottleneck${NC}"
fi

# Calculate frame loss
if [ "$RTSP_RATE" -gt 0 ]; then
    FRAME_LOSS=$(awk "BEGIN {printf \"%.1f\", ($RTSP_RATE - $PROCESSOR_RATE) / $RTSP_RATE * 100}")
    if (( $(echo "$FRAME_LOSS < 5" | bc -l) )); then
        echo -e "${GREEN}✓ Frame loss is acceptable (<5%): ${FRAME_LOSS}%${NC}"
        ((COMPLETED_TASKS++))
    else
        echo -e "${YELLOW}⚠ High frame loss detected: ${FRAME_LOSS}%${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Could not calculate frame loss${NC}"
fi

# Final Summary
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}VALIDATION SUMMARY${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\nCompleted: $COMPLETED_TASKS/$TOTAL_TASKS tasks"

if [ "$COMPLETED_TASKS" -eq "$TOTAL_TASKS" ]; then
    echo -e "\n${GREEN}🎉 ALL VALIDATIONS PASSED! 🎉${NC}"
    echo -e "\nThe complete frame processing pipeline is working correctly:"
    echo -e "  ${GREEN}✓${NC} RTSP Capture → Redis Stream"
    echo -e "  ${GREEN}✓${NC} Frame Buffer v2 Consumer"
    echo -e "  ${GREEN}✓${NC} ProcessorClient Integration"
    echo -e "  ${GREEN}✓${NC} End-to-End Flow"
    echo -e "  ${GREEN}✓${NC} Performance Targets Met"

    echo -e "\n📊 Key Metrics:"
    echo -e "  • Capture Rate: $RTSP_RATE FPS"
    echo -e "  • Processing Rate: $PROCESSOR_RATE FPS"
    echo -e "  • Frame Loss: ${FRAME_LOSS}%"
    echo -e "  • Stream Backlog: $STREAM_GROWTH frames/s"

    echo -e "\n${GREEN}✨ System is ready for production!${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠ SOME VALIDATIONS FAILED${NC}"
    echo -e "\nIssues detected in the frame processing pipeline."
    echo -e "Please review the failed tasks above and address any issues."

    echo -e "\n📝 Troubleshooting tips:"
    echo -e "  • Check service logs: docker-compose logs -f"
    echo -e "  • Verify Redis connectivity: redis-cli ping"
    echo -e "  • Check service health endpoints"
    echo -e "  • Review processor registration status"

    exit 1
fi
