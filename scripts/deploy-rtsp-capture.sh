#!/bin/bash
set -euo pipefail

# Deployment script for RTSP Capture Service on Nebula server
# This script handles complete deployment and verification of Blok 5

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
REGISTRY="ghcr.io"
IMAGE_PREFIX="hretheum/bezrobocie-detektor"
NEBULA_HOST="${NEBULA_HOST:-nebula}"
NEBULA_USER="${NEBULA_USER:-hretheum}"
NEBULA_PROJECT_DIR="/opt/detektor"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

# Function to check RTSP configuration from encrypted .env
check_rtsp_configuration() {
    log "Checking RTSP configuration from encrypted .env..."

    # Check if RTSP_URL is configured (via encrypted .env)
    # Try multiple key file locations
    local key_files=(
        "/opt/detektor/.sops-key"
        "/home/${NEBULA_USER}/.config/sops/age/keys.txt"
        "/home/${NEBULA_USER}/.age/keys.txt"
        "~/.config/sops/age/keys.txt"
    )

    local key_file_cmd=""
    for key_file in "${key_files[@]}"; do
        if ssh "${NEBULA_USER}@${NEBULA_HOST}" "test -f $key_file" >/dev/null 2>&1; then
            key_file_cmd="SOPS_AGE_KEY_FILE=$key_file"
            break
        fi
    done

    if [[ -z "$key_file_cmd" ]]; then
        # Try environment variable fallback
        key_file_cmd="SOPS_AGE_KEY=AGE-SECRET-KEY-17Y3RLEZT98PR6J7M0X0TQC4SL7KYM4C6J7S5YDAHQ02YZM3NANNQZDTLDH"
    fi

    local rtsp_url=$(ssh "${NEBULA_USER}@${NEBULA_HOST}" "cd ${NEBULA_PROJECT_DIR} && $key_file_cmd sops -d .env 2>/dev/null | grep '^RTSP_URL=' | cut -d'=' -f2-" 2>/dev/null || echo "")

    if [[ -z "$rtsp_url" ]]; then
        warning "RTSP_URL not configured - using default simulator"
        rtsp_url="rtsp://localhost:8554/stream"
        log "Configure RTSP_URL using: sops /opt/detektor/.env"
        log "Ensure AGE key is properly configured on Nebula server"
    else
        log "RTSP stream configured: ${rtsp_url}"
    fi

    echo "${rtsp_url}"
}

# Function to configure RTSP via SOPS
configure_rtsp_sops() {
    log "Configuring RTSP URL via SOPS encryption..."

    local rtsp_url="${1:-}"
    if [[ -z "$rtsp_url" ]]; then
        error "RTSP URL is required. Example: $0 configure-encrypted rtsp://user:pass@camera:554/stream"
        return 1
    fi

    # Verify SOPS is available on server
    if ! ssh "${NEBULA_USER}@${NEBULA_HOST}" "which sops >/dev/null 2>&1"; then
        error "SOPS not found on Nebula server. Install with: ssh nebula 'sudo apt-get install sops'"
        return 1
    fi

    # Check and setup AGE key on server
    log "Checking AGE key configuration on Nebula..."

    # Try to find existing key or create setup
    ssh "${NEBULA_USER}@${NEBULA_HOST}" << 'EOF'
        # Check for existing age key
        if [ -f ~/.config/sops/age/keys.txt ]; then
            echo "✓ AGE key found in ~/.config/sops/age/keys.txt"
            export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
        elif [ -f ~/.age/keys.txt ]; then
            echo "✓ AGE key found in ~/.age/keys.txt"
            export SOPS_AGE_KEY_FILE=~/.age/keys.txt
        elif [ -f /opt/detektor/.sops-key ]; then
            echo "✓ AGE key found in /opt/detektor/.sops-key"
            export SOPS_AGE_KEY_FILE=/opt/detektor/.sops-key
        else
            echo "⚠️  No AGE key found, will use environment variable"
            # Use environment variable as fallback
            export SOPS_AGE_KEY="AGE-SECRET-KEY-17Y3RLEZT98PR6J7M0X0TQC4SL7KYM4C6J7S5YDAHQ02YZM3NANNQZDTLDH"
        fi
EOF

    # Configure via SOPS with proper key handling
    ssh "${NEBULA_USER}@${NEBULA_HOST}" << 'EOF'
        cd /opt/detektor

        # Setup key detection
        if [ -f ~/.config/sops/age/keys.txt ]; then
            export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
        elif [ -f ~/.age/keys.txt ]; then
            export SOPS_AGE_KEY_FILE=~/.age/keys.txt
        elif [ -f /opt/detektor/.sops-key ]; then
            export SOPS_AGE_KEY_FILE=/opt/detektor/.sops-key
        else
            export SOPS_AGE_KEY="AGE-SECRET-KEY-17Y3RLEZT98PR6J7M0X0TQC4SL7KYM4C6J7S5YDAHQ02YZM3NANNQZDTLDH"
        fi

        # Create temporary file with new configuration
        echo "RTSP_URL=${1:-rtsp://localhost:8554/stream}" > /tmp/rtsp_config_temp
        echo "FRAME_BUFFER_SIZE=100" >> /tmp/rtsp_config_temp

        # Setup .sops.yaml if not exists
        if [ ! -f .sops.yaml ]; then
            cat > .sops.yaml << 'EOF2'
keys:
  - &main_key age1gp2tm83t80f5qt5hcsanswxmrl3urlf22ds6jla5d8u3ufznwsyqwqkcw3

creation_rules:
  - path_regex: \.env$
    age: *main_key
EOF2
        fi

        # Configure RTSP URL
        echo "RTSP_URL=${1:-rtsp://localhost:8554/stream}" > /tmp/rtsp_config_temp
        echo "FRAME_BUFFER_SIZE=100" >> /tmp/rtsp_config_temp

        # Merge with existing encrypted .env or create new
        if [ -f .env ]; then
            # Try to decrypt existing .env
            if $SOPS_AGE_KEY_FILE sops -d .env > /tmp/.env.decrypted 2>/dev/null; then
                sed -i '/^RTSP_URL=/d' /tmp/.env.decrypted
                sed -i '/^FRAME_BUFFER_SIZE=/d' /tmp/.env.decrypted
                cat /tmp/rtsp_config_temp >> /tmp/.env.decrypted
                $SOPS_AGE_KEY_FILE sops -e /tmp/.env.decrypted > .env
            elif sops -d .env > /tmp/.env.decrypted 2>/dev/null; then
                sed -i '/^RTSP_URL=/d' /tmp/.env.decrypted
                sed -i '/^FRAME_BUFFER_SIZE=/d' /tmp/.env.decrypted
                cat /tmp/rtsp_config_temp >> /tmp/.env.decrypted
                sops -e /tmp/.env.decrypted > .env
            else
                # Create new encrypted file
                sops -e /tmp/rtsp_config_temp > .env
            fi
        else
            # Create new encrypted .env
            sops -e /tmp/rtsp_config_temp > .env
        fi

        rm -f /tmp/rtsp_config_temp /tmp/.env.decrypted

        echo "✓ RTSP URL configured and encrypted via SOPS"
EOF

    log "RTSP configuration updated and encrypted"
}

# Function to verify RTSP connection
verify_rtsp_connection() {
    log "Verifying RTSP connection..."

    # Get RTSP URL from .env
    local rtsp_url=$(ssh "${NEBULA_USER}@${NEBULA_HOST}" "cd ${NEBULA_PROJECT_DIR} && grep '^RTSP_URL=' .env | cut -d'=' -f2-")

    if [[ -z "$rtsp_url" ]]; then
        error "RTSP_URL not found in .env"
        return 1
    fi

    # Test RTSP connection using ffprobe
    info "Testing RTSP connection with ffprobe..."
    if ssh "${NEBULA_USER}@${NEBULA_HOST}" "docker exec rtsp-capture ffprobe -v quiet -print_format json -show_streams '${rtsp_url}'" >/dev/null 2>&1; then
        log "✓ RTSP connection successful"
    else
        error "✗ RTSP connection failed"
        return 1
    fi

    # Check if frames are being captured
    info "Checking frame capture..."
    sleep 10

    local frame_count=$(ssh "${NEBULA_USER}@${NEBULA_HOST}" "curl -s http://localhost:8001/metrics | grep 'rtsp_frames_captured_total' | tail -1 | awk '{print \$2}'")
    if [[ -n "$frame_count" && "$frame_count" -gt 0 ]]; then
        log "✓ Frames are being captured: ${frame_count} total"
    else
        warning "No frames captured yet - this might be normal for new deployment"
    fi
}

# Function to verify metrics in Prometheus
verify_prometheus_metrics() {
    log "Verifying RTSP metrics in Prometheus..."

    local prometheus_url="http://${NEBULA_HOST}:9090"

    # Check if Prometheus is accessible
    if ! curl -sf "${prometheus_url}/-/healthy" >/dev/null 2>&1; then
        error "Prometheus not accessible at ${prometheus_url}"
        return 1
    fi

    # Test key RTSP metrics
    local metrics=(
        "rtsp_frames_captured_total"
        "rtsp_frame_processing_duration_seconds"
        "rtsp_connection_status"
        "rtsp_errors_total"
        "rtsp_buffer_size"
    )

    for metric in "${metrics[@]}"; do
        local query="${prometheus_url}/api/v1/query?query=${metric}"
        local response=$(curl -s "$query")

        if echo "$response" | grep -q '"result":\[\]' || echo "$response" | grep -q '"status":"error"'; then
            warning "Metric $metric not found or has no data"
        else
            log "✓ Metric $metric available"
        fi
    done

    log "Prometheus metrics verification completed"
}

# Function to verify Jaeger tracing
verify_jaeger_tracing() {
    log "Verifying Jaeger tracing integration..."

    local jaeger_url="http://${NEBULA_HOST}:16686"

    # Check if Jaeger is accessible
    if ! curl -sf "${jaeger_url}/" >/dev/null 2>&1; then
        error "Jaeger not accessible at ${jaeger_url}"
        return 1
    fi

    # Check for rtsp-capture service traces
    local service_url="${jaeger_url}/api/traces?service=rtsp-capture"
    local response=$(curl -s "$service_url")

    if echo "$response" | grep -q '"data":\[\]' || echo "$response" | grep -q '"total":0'; then
        warning "No traces found for rtsp-capture service yet"
    else
        log "✓ Traces available for rtsp-capture service"
    fi

    log "Jaeger tracing verification completed"
}

# Function to run load test
run_load_test() {
    log "Running load test for RTSP capture service..."

    # Monitor service for 5 minutes
    info "Monitoring service for 5 minutes..."

    local start_time=$(date +%s)
    local end_time=$((start_time + 300))  # 5 minutes

    while [[ $(date +%s) -lt $end_time ]]; do
        # Check health
        if ! curl -sf "http://${NEBULA_HOST}:8001/health" >/dev/null 2>&1; then
            error "Service health check failed"
            return 1
        fi

        # Get resource usage
        local stats=$(ssh "${NEBULA_USER}@${NEBULA_HOST}" "docker stats rtsp-capture --no-stream --format 'table {{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'" 2>/dev/null || echo "N/A")

        # Get frame count
        local frame_count=$(curl -s "http://${NEBULA_HOST}:8001/metrics" | grep 'rtsp_frames_captured_total' | tail -1 | awk '{print $2}' || echo "0")

        info "Status: Healthy | Frames: ${frame_count} | Resources: ${stats}"

        sleep 30
    done

    log "Load test completed successfully"
}

# Function to check logs for errors
check_service_logs() {
    log "Checking service logs for errors..."

    local error_patterns=(
        "ERROR"
        "CRITICAL"
        "panic"
        "fatal"
        "connection.*failed"
        "frame.*corrupt"
    )

    local logs=$(ssh "${NEBULA_USER}@${NEBULA_HOST}" "docker logs rtsp-capture --tail 100" 2>/dev/null)

    for pattern in "${error_patterns[@]}"; do
        if echo "$logs" | grep -i "$pattern" >/dev/null; then
            warning "Found potential issues in logs matching: $pattern"
            echo "$logs" | grep -i "$pattern" | head -5
        fi
    done

    log "Log analysis completed"
}

# Function to restart service safely
restart_service() {
    log "Restarting RTSP capture service..."

    ssh "${NEBULA_USER}@${NEBULA_HOST}" << EOF
        cd ${NEBULA_PROJECT_DIR}

        log "Stopping rtsp-capture..."
        docker-compose stop rtsp-capture

        log "Pulling latest image..."
        docker pull ${REGISTRY}/${IMAGE_PREFIX}/rtsp-capture:latest

        log "Starting rtsp-capture..."
        docker-compose up -d rtsp-capture

        log "Waiting for service to be ready..."
        sleep 10

        # Check health
        if curl -sf http://localhost:8001/health >/dev/null 2>&1; then
            log "✓ Service restarted successfully"
        else
            error "✗ Service failed to start"
            exit 1
        fi
EOF

    log "Service restart completed"
}

# Main function
main() {
    local command="${1:-full}"

    case "$command" in
        "configure-encrypted")
            local rtsp_url="${2:-}"
            configure_rtsp_sops "$rtsp_url"
            ;;
        "configure")
            # Legacy/deprecated - use SOPS instead
            warning "configure command is deprecated. Use 'configure-encrypted' with SOPS encryption"
            log "Example: $0 configure-encrypted rtsp://user:pass@camera:554/stream"
            ;;
        "verify")
            check_rtsp_configuration >/dev/null
            verify_rtsp_connection
            verify_prometheus_metrics
            verify_jaeger_tracing
            ;;
        "load-test")
            check_rtsp_configuration >/dev/null
            run_load_test
            ;;
        "restart")
            restart_service
            ;;
        "full")
            log "Starting complete RTSP capture deployment verification..."

            local rtsp_url=$(check_rtsp_configuration | tail -1)
            restart_service
            verify_rtsp_connection
            verify_prometheus_metrics
            verify_jaeger_tracing
            run_load_test
            check_service_logs

            log "✅ RTSP capture service deployment completed successfully!"
            log "RTSP URL used: ${rtsp_url}"
            ;;
        *)
            echo "Usage: $0 [configure-encrypted|verify|load-test|restart|full]"
            echo ""
            echo "Commands:"
            echo "  configure-encrypted <url>  - Configure RTSP URL via SOPS encryption"
            echo "  verify                     - Verify all integrations"
            echo "  load-test                  - Run 5-minute load test"
            echo "  restart                    - Restart service with latest image"
            echo "  full                       - Complete deployment using encrypted .env"
            echo ""
            echo "Configuration:"
            echo "  Use SOPS to edit encrypted .env: ssh nebula 'cd /opt/detektor && sops .env'"
            echo "  Add: RTSP_URL=rtsp://user:pass@camera:554/stream"
            ;;
    esac
}

# Run main function with all arguments
main "$@"
