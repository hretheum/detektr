#!/bin/bash
set -euo pipefail

# Test script for RTSP capture service deployment validation
# This script runs all verification steps for Blok 5

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEBULA_HOST="${NEBULA_HOST:-nebula}"
NEBULA_USER="${NEBULA_USER:-hretheum}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[TEST]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

# Test 1: Service Health Check
test_service_health() {
    log "Testing service health..."

    if curl -sf "http://${NEBULA_HOST}:8001/health" >/dev/null 2>&1; then
        log "✓ Service is healthy"
        return 0
    else
        error "✗ Service health check failed"
        return 1
    fi
}

# Test 2: Metrics Endpoint
test_metrics_endpoint() {
    log "Testing metrics endpoint..."

    local metrics=$(curl -s "http://${NEBULA_HOST}:8001/metrics" 2>/dev/null || echo "")

    if [[ -n "$metrics" ]] && echo "$metrics" | grep -q "rtsp_"; then
        log "✓ Metrics endpoint responding with RTSP metrics"

        # Extract key metrics
        local frame_count=$(echo "$metrics" | grep 'rtsp_frames_captured_total' | tail -1 | awk '{print $2}')
        local buffer_size=$(echo "$metrics" | grep 'rtsp_buffer_size' | tail -1 | awk '{print $2}')

        log "  - Frames captured: ${frame_count:-0}"
        log "  - Buffer size: ${buffer_size:-0}"

        return 0
    else
        error "✗ Metrics endpoint not responding or missing RTSP metrics"
        return 1
    fi
}

# Test 3: API Documentation
test_api_docs() {
    log "Testing API documentation..."

    if curl -sf "http://${NEBULA_HOST}:8001/docs" >/dev/null 2>&1; then
        log "✓ API documentation available"
        return 0
    else
        warning "API documentation not accessible"
        return 0
    fi
}

# Test 4: Prometheus Integration
test_prometheus_integration() {
    log "Testing Prometheus integration..."

    if curl -sf "http://${NEBULA_HOST}:9090/-/healthy" >/dev/null 2>&1; then
        log "✓ Prometheus is accessible"

        # Test specific metrics query
        local query="http://${NEBULA_HOST}:9090/api/v1/query?query=rtsp_frames_captured_total"
        local response=$(curl -s "$query" 2>/dev/null || echo "")

        if echo "$response" | grep -q '"status":"success"'; then
            log "✓ RTSP metrics queryable in Prometheus"
            return 0
        else
            warning "RTSP metrics not found in Prometheus"
            return 1
        fi
    else
        error "✗ Prometheus not accessible"
        return 1
    fi
}

# Test 5: Jaeger Integration
test_jaeger_integration() {
    log "Testing Jaeger integration..."

    if curl -sf "http://${NEBULA_HOST}:16686" >/dev/null 2>&1; then
        log "✓ Jaeger is accessible"

        # Test service traces
        local traces_url="http://${NEBULA_HOST}:16686/api/traces?service=rtsp-capture"
        local response=$(curl -s "$traces_url" 2>/dev/null || echo "")

        if echo "$response" | grep -q '"data"'; then
            log "✓ Traces available for rtsp-capture service"
            return 0
        else
            warning "No traces found yet (this might be normal for new deployment)"
            return 0
        fi
    else
        error "✗ Jaeger not accessible"
        return 1
    fi
}

# Test 6: RTSP Connection Test
test_rtsp_connection() {
    log "Testing RTSP connection..."

    # Get RTSP URL from environment
    local rtsp_url=$(ssh "${NEBULA_USER}@${NEBULA_HOST}" "cd /opt/detektor && grep '^RTSP_URL=' .env | cut -d'=' -f2-" 2>/dev/null || echo "")

    if [[ -n "$rtsp_url" ]]; then
        log "RTSP URL configured: $rtsp_url"

        # Test if we can probe the stream
        if ssh "${NEBULA_USER}@${NEBULA_HOST}" "docker exec rtsp-capture ffprobe -v quiet -print_format json -show_streams '${rtsp_url}'" >/dev/null 2>&1; then
            log "✓ RTSP stream accessible"
            return 0
        else
            warning "RTSP stream not accessible (might be camera issue)"
            return 1
        fi
    else
        warning "RTSP_URL not configured in .env"
        return 1
    fi
}

# Test 7: Resource Usage
test_resource_usage() {
    log "Testing resource usage..."

    local stats=$(ssh "${NEBULA_USER}@${NEBULA_HOST}" "docker stats rtsp-capture --no-stream --format 'CPU: {{.CPUPerc}}, MEM: {{.MemUsage}}'" 2>/dev/null || echo "N/A")

    log "Current resource usage: $stats"

    # Simple check - if stats are available, consider it a pass
    if [[ "$stats" != "N/A" ]]; then
        log "✓ Resource monitoring available"
        return 0
    else
        warning "Could not get resource stats"
        return 1
    fi
}

# Main test runner
main() {
    log "Starting RTSP capture service deployment tests..."
    echo

    local failures=0

    # Run all tests
    test_service_health || ((failures++))
    test_metrics_endpoint || ((failures++))
    test_api_docs || ((failures++))
    test_prometheus_integration || ((failures++))
    test_jaeger_integration || ((failures++))
    test_rtsp_connection || ((failures++))
    test_resource_usage || ((failures++))

    echo
    if [[ $failures -eq 0 ]]; then
        log "🎉 All tests passed! RTSP capture service deployment is successful."
    else
        warning "$failures test(s) failed. Check logs for details."
        log "Use: ./scripts/deploy-rtsp-capture.sh verify"
        log "Or: docker logs rtsp-capture"
        exit 1
    fi
}

# Run tests
main "$@"
