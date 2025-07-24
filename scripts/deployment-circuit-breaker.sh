#!/bin/bash
# Deployment Circuit Breaker
# Prevents cascading failures by stopping deployments after repeated failures

set -euo pipefail

# Configuration
STATE_FILE="/var/lib/detektor/circuit-breaker.state"
LOG_FILE="/var/log/detektor/circuit-breaker.log"
MAX_FAILURES=3
RESET_TIMEOUT=3600  # 1 hour in seconds
ALERT_EMAIL="${ALERT_EMAIL:-admin@example.com}"

# Ensure directories exist
mkdir -p "$(dirname "$STATE_FILE")" "$(dirname "$LOG_FILE")"

# Helper functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

get_state() {
    if [[ -f "$STATE_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$STATE_FILE"
        echo "${CIRCUIT_STATE:-closed}"
    else
        echo "closed"
    fi
}

get_failure_count() {
    if [[ -f "$STATE_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$STATE_FILE"
        echo "${FAILURE_COUNT:-0}"
    else
        echo "0"
    fi
}

get_last_failure_time() {
    if [[ -f "$STATE_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$STATE_FILE"
        echo "${LAST_FAILURE_TIME:-0}"
    else
        echo "0"
    fi
}

save_state() {
    local state=$1
    local failures=$2
    local last_failure=$3

    cat > "$STATE_FILE" <<EOF
CIRCUIT_STATE="$state"
FAILURE_COUNT=$failures
LAST_FAILURE_TIME=$last_failure
EOF
}

send_alert() {
    local subject=$1
    local message=$2

    echo "$message" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || \
        log "Failed to send email alert: $subject"
}

# Circuit breaker functions
check_circuit() {
    local state
    local failures
    local last_failure
    local current_time

    state=$(get_state)
    failures=$(get_failure_count)
    last_failure=$(get_last_failure_time)
    current_time=$(date +%s)

    case "$state" in
        "closed")
            # Circuit is closed, deployments allowed
            return 0
            ;;

        "open")
            # Check if timeout has passed
            local time_since_failure=$((current_time - last_failure))
            if [[ $time_since_failure -gt $RESET_TIMEOUT ]]; then
                log "Circuit timeout expired, moving to half-open state"
                save_state "half-open" "$failures" "$last_failure"
                return 0
            else
                local remaining=$((RESET_TIMEOUT - time_since_failure))
                log "Circuit is OPEN. Deployments blocked for $((remaining / 60)) more minutes"
                return 1
            fi
            ;;

        "half-open")
            # Allow one attempt
            log "Circuit is HALF-OPEN. Allowing one deployment attempt"
            return 0
            ;;

        *)
            log "Unknown circuit state: $state. Resetting to closed"
            save_state "closed" 0 0
            return 0
            ;;
    esac
}

record_success() {
    local state
    state=$(get_state)

    case "$state" in
        "closed")
            # Already closed, nothing to do
            ;;

        "half-open")
            log "Deployment successful in half-open state. Closing circuit"
            save_state "closed" 0 0
            send_alert "Circuit Breaker Closed" "Deployment circuit breaker has been closed after successful deployment"
            ;;

        "open")
            # Shouldn't happen, but handle it
            log "Success recorded while circuit open (unexpected). Closing circuit"
            save_state "closed" 0 0
            ;;
    esac
}

record_failure() {
    local state
    local failures
    local current_time

    state=$(get_state)
    failures=$(get_failure_count)
    current_time=$(date +%s)

    case "$state" in
        "closed")
            failures=$((failures + 1))
            log "Deployment failed. Failure count: $failures/$MAX_FAILURES"

            if [[ $failures -ge $MAX_FAILURES ]]; then
                log "Maximum failures reached. Opening circuit"
                save_state "open" "$failures" "$current_time"
                send_alert "Circuit Breaker OPEN" "Deployment circuit breaker opened after $failures consecutive failures. Deployments blocked for $((RESET_TIMEOUT / 60)) minutes."
            else
                save_state "closed" "$failures" "$current_time"
            fi
            ;;

        "half-open")
            log "Deployment failed in half-open state. Re-opening circuit"
            save_state "open" "$failures" "$current_time"
            send_alert "Circuit Breaker Re-opened" "Deployment circuit breaker re-opened after failure in half-open state"
            ;;

        "open")
            # Already open, update timestamp
            log "Failure recorded while circuit already open"
            save_state "open" "$failures" "$current_time"
            ;;
    esac
}

reset_circuit() {
    log "Manually resetting circuit breaker"
    save_state "closed" 0 0
    send_alert "Circuit Breaker Reset" "Deployment circuit breaker has been manually reset"
}

get_status() {
    local state
    local failures
    local last_failure

    state=$(get_state)
    failures=$(get_failure_count)
    last_failure=$(get_last_failure_time)

    echo "Circuit Breaker Status:"
    echo "  State: $state"
    echo "  Failure Count: $failures/$MAX_FAILURES"

    if [[ "$state" == "open" ]] && [[ $last_failure -gt 0 ]]; then
        local current_time
        local time_since_failure

        current_time=$(date +%s)
        time_since_failure=$((current_time - last_failure))
        local remaining=$((RESET_TIMEOUT - time_since_failure))

        if [[ $remaining -gt 0 ]]; then
            echo "  Time until reset: $((remaining / 60)) minutes"
        else
            echo "  Ready for half-open state"
        fi
    fi
}

# Main command handling
case "${1:-status}" in
    "check")
        if check_circuit; then
            exit 0
        else
            exit 1
        fi
        ;;

    "success")
        record_success
        ;;

    "failure")
        record_failure
        ;;

    "reset")
        reset_circuit
        ;;

    "status")
        get_status
        ;;

    *)
        echo "Usage: $0 {check|success|failure|reset|status}"
        echo ""
        echo "Commands:"
        echo "  check    - Check if deployments are allowed (exit 0 if yes, 1 if no)"
        echo "  success  - Record a successful deployment"
        echo "  failure  - Record a failed deployment"
        echo "  reset    - Manually reset the circuit breaker"
        echo "  status   - Show current circuit breaker status"
        exit 1
        ;;
esac
