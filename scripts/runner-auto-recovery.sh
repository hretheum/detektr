#!/bin/bash
# GitHub Runner Auto-Recovery Script
# Monitors runner health and performs automatic recovery

set -euo pipefail

# Configuration
RUNNER_DIR="${RUNNER_DIR:-/opt/github-runner}"
HEALTH_CHECK_SCRIPT="${HEALTH_CHECK_SCRIPT:-/opt/detektor-clean/scripts/runner-health-check.sh}"
LOG_FILE="/var/log/github-runner/auto-recovery.log"
STATE_FILE="/var/lib/github-runner/recovery.state"
MAX_FAILURES=3
CHECK_INTERVAL=60

# Ensure directories exist
mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$STATE_FILE")"

# Helper functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

get_failure_count() {
    if [[ -f "$STATE_FILE" ]]; then
        cat "$STATE_FILE" 2>/dev/null || echo 0
    else
        echo 0
    fi
}

set_failure_count() {
    echo "$1" > "$STATE_FILE"
}

rotate_logs() {
    local runner_logs="$RUNNER_DIR/_diag"
    if [[ -d "$runner_logs" ]]; then
        local backup_dir
        backup_dir="/var/log/github-runner/backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        cp -r "$runner_logs"/* "$backup_dir/" 2>/dev/null || true
        log "Logs backed up to $backup_dir"
    fi
}

restart_runner() {
    log "Attempting to restart GitHub runner..."

    # Rotate logs before restart
    rotate_logs

    # Stop runner
    if systemctl is-active --quiet github-runner; then
        systemctl stop github-runner
        sleep 5
    fi

    # Clean up any stuck processes
    pkill -f "Runner.Listener" || true
    sleep 2

    # Start runner
    systemctl start github-runner
    sleep 10

    # Verify it's running
    if systemctl is-active --quiet github-runner; then
        log "Runner restarted successfully"
        return 0
    else
        log "Failed to restart runner"
        return 1
    fi
}

check_and_recover() {
    # Run health check
    if "$HEALTH_CHECK_SCRIPT"; then
        # Health check passed
        local failures
        failures=$(get_failure_count)
        if [[ $failures -gt 0 ]]; then
            log "Health check passed after $failures failures"
            set_failure_count 0
        fi
        return 0
    else
        # Health check failed
        local failures
        failures=$(get_failure_count)
        failures=$((failures + 1))
        set_failure_count $failures

        log "Health check failed (failure #$failures)"

        if [[ $failures -ge $MAX_FAILURES ]]; then
            log "Max failures reached, attempting recovery"

            if restart_runner; then
                log "Recovery successful"
                set_failure_count 0

                # Send notification
                echo "GitHub runner recovered after $failures failures on $(hostname)" | \
                    mail -s "Runner Recovery Success" admin@example.com 2>/dev/null || true
            else
                log "Recovery failed!"

                # Send alert
                echo "GitHub runner recovery failed on $(hostname) after $failures attempts!" | \
                    mail -s "CRITICAL: Runner Recovery Failed" admin@example.com 2>/dev/null || true

                # Don't reset counter - manual intervention needed
            fi
        fi

        return 1
    fi
}

# Main monitoring loop
main() {
    log "Starting GitHub runner auto-recovery monitor"

    # Initial state
    set_failure_count 0

    while true; do
        check_and_recover || true
        sleep $CHECK_INTERVAL
    done
}

# Handle signals
trap 'log "Shutting down auto-recovery monitor"; exit 0' SIGTERM SIGINT

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
