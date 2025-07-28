#!/bin/bash
# Manual test script for ProcessorClient pattern

set -e

echo "=== Manual ProcessorClient Test ==="
echo

# Create processor queue and consumer group
echo "1. Creating processor queue and consumer group..."
ssh nebula "docker exec detektr-redis-1 redis-cli XGROUP CREATE frames:ready:sample-processor-1 frame-processors $ MKSTREAM" 2>/dev/null || echo "Group already exists"

echo
echo "2. Injecting test frames directly to processor queue..."
for i in {1..5}; do
    ssh nebula "docker exec detektr-redis-1 redis-cli XADD frames:ready:sample-processor-1 '*' frame_id test_frame_$i camera_id cam01 timestamp \$(date +%s) metadata '{\"test\": true, \"index\": $i}'"
    echo "Injected frame test_frame_$i"
done

echo
echo "3. Checking queue length..."
QUEUE_LEN=$(ssh nebula "docker exec detektr-redis-1 redis-cli XLEN frames:ready:sample-processor-1")
echo "Queue length: $QUEUE_LEN"

echo
echo "4. Checking if processor would consume (if it were running with ProcessorClient)..."
ssh nebula "docker exec detektr-redis-1 redis-cli XINFO GROUPS frames:ready:sample-processor-1"

echo
echo "5. Reading one frame as test..."
ssh nebula "docker exec detektr-redis-1 redis-cli XREADGROUP GROUP frame-processors test-consumer COUNT 1 STREAMS frames:ready:sample-processor-1 '>'"

echo
echo "=== Test Complete ==="
echo
echo "If sample-processor were running with ProcessorClient pattern,"
echo "it would consume these frames from its dedicated queue."
echo
echo "Current issue: Frame Buffer v2 doesn't distribute frames to processor queues yet."
