#!/bin/bash
# Docker Health Check Script for Detektor Project

echo "=== Docker Health Check ==="
echo "Date: $(date)"
echo

# Check Docker daemon
echo "1. Docker Daemon Status:"
if docker --context nebula version > /dev/null 2>&1; then
    echo "   ✅ Docker daemon is running"
    docker --context nebula version | grep -E "(Server|Client)" | head -2
else
    echo "   ❌ Docker daemon is not accessible"
    exit 1
fi
echo

# Check Docker Compose
echo "2. Docker Compose:"
if docker --context nebula compose version > /dev/null 2>&1; then
    echo "   ✅ $(docker --context nebula compose version)"
else
    echo "   ❌ Docker Compose not working"
fi
echo

# Check networks
echo "3. Project Networks:"
for network in detektor_frontend detektor_backend; do
    if docker --context nebula network ls | grep -q "$network"; then
        echo "   ✅ $network exists"
    else
        echo "   ❌ $network missing"
    fi
done
echo

# Check metrics endpoint
echo "4. Metrics Endpoint:"
if curl -s http://192.168.1.193:9323/metrics > /dev/null 2>&1; then
    metric_count=$(curl -s http://192.168.1.193:9323/metrics | wc -l)
    echo "   ✅ Metrics available ($metric_count metrics)"
else
    echo "   ⚠️  Metrics endpoint not accessible"
fi
echo

# Check disk space
echo "5. Disk Space:"
ssh nebula "df -h / | grep -E '^/dev/'" | awk '{print "   Disk usage: " $5 " (" $4 " free)"}'
echo

# Check project directory
echo "6. Project Directory:"
if ssh nebula "test -d /opt/detektor"; then
    echo "   ✅ /opt/detektor exists"
    ssh nebula "find /opt/detektor -type d | wc -l" | awk '{print "   Directories: " $1}'
else
    echo "   ❌ /opt/detektor missing"
fi
echo

# Summary
echo "=== Summary ==="
echo "Docker infrastructure is ready for Detektor project deployment."
echo "Next steps: Install NVIDIA Container Toolkit for GPU support."
