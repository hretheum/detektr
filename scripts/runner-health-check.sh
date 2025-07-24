#!/bin/bash
# GitHub Runner Health Check Script
# Checks runner status and exports metrics for Prometheus

set -euo pipefail

# Configuration
RUNNER_DIR="${RUNNER_DIR:-/opt/github-runner}"
METRICS_FILE="/var/lib/prometheus/node-exporter/github_runner.prom"
LOG_FILE="/var/log/github-runner/health-check.log"

# Ensure directories exist
mkdir -p "$(dirname "$METRICS_FILE")" "$(dirname "$LOG_FILE")"

# Helper functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

write_metric() {
    local metric_name=$1
    local value=$2
    local help=$3
    local type=${4:-gauge}

    {
        echo "# HELP $metric_name $help"
        echo "# TYPE $metric_name $type"
        echo "$metric_name $value"
    } >> "$METRICS_FILE.tmp"
}

# Check if runner process is running
check_runner_process() {
    if pgrep -f "Runner.Listener" > /dev/null; then
        echo 1
    else
        echo 0
    fi
}

# Check last job execution time
check_last_job() {
    local last_job_file
    last_job_file=$(find "$RUNNER_DIR/_diag" -name "Worker_*.log" -type f 2>/dev/null | head -1)
    if [[ -n "$last_job_file" ]] && [[ -f "$last_job_file" ]]; then
        local file_time
        file_time=$(stat -c %Y "$last_job_file" 2>/dev/null)
        if [[ -n "$file_time" ]]; then
            echo $(($(date +%s) - file_time))
        else
            echo -1
        fi
    else
        echo -1
    fi
}

# Check GitHub connectivity
check_github_connection() {
    if curl -sf --max-time 5 https://api.github.com/status > /dev/null 2>&1; then
        echo 1
    else
        echo 0
    fi
}

# Check runner registration status
check_runner_registered() {
    if [[ -f "$RUNNER_DIR/.runner" ]]; then
        echo 1
    else
        echo 0
    fi
}

# Main health check
main() {
    log "Starting health check"

    # Create temporary metrics file
    : > "$METRICS_FILE.tmp"

    # Collect metrics
    local runner_up
    local github_connected
    local runner_registered
    local last_job_seconds

    runner_up=$(check_runner_process)
    github_connected=$(check_github_connection)
    runner_registered=$(check_runner_registered)
    last_job_seconds=$(check_last_job)

    # Write metrics
    write_metric "github_runner_up" "$runner_up" "Whether the GitHub runner process is running"
    write_metric "github_runner_connected" "$github_connected" "Whether the runner can connect to GitHub"
    write_metric "github_runner_registered" "$runner_registered" "Whether the runner is registered"

    if [[ $last_job_seconds -ge 0 ]]; then
        write_metric "github_runner_last_job_seconds" "$last_job_seconds" "Seconds since last job execution"
    fi

    # Add timestamp
    write_metric "github_runner_health_check_timestamp" "$(date +%s)" "Timestamp of last health check"

    # Atomic move
    mv "$METRICS_FILE.tmp" "$METRICS_FILE"

    # Overall health status
    if [[ $runner_up -eq 1 && $github_connected -eq 1 && $runner_registered -eq 1 ]]; then
        log "Health check passed"
        exit 0
    else
        log "Health check failed - runner_up=$runner_up, github_connected=$github_connected, registered=$runner_registered"
        exit 1
    fi
}

# Run main function
main "$@"
