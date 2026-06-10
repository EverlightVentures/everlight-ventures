#!/usr/bin/env bash
# desktop_runner_watchdog.sh -- detects a STUCK (not crashed) desktop_runner.
#
# Crashed = systemd auto-restarts via Restart=always.
# Stuck = process is alive but not making progress (no log activity, no
#         queue movement, possibly hung in xdotool/Anthropic API).
#
# This watchdog runs every 60s via cron. If it sees the runner has not
# logged anything in >5 minutes AND there's a task in_progress, it kills
# the runner. systemd will restart it within 5 seconds.
#
# Usage:
#   - one-shot: bash desktop_runner_watchdog.sh
#   - cron: * * * * * /AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/desktop_runner_watchdog.sh

set -euo pipefail

LOG_FILE="/tmp/desktop_runner.log"
WATCHDOG_LOG="/tmp/desktop_runner_watchdog.log"
IN_PROGRESS_DIR="/AA_MY_DRIVE/_logs/browser_tasks/in_progress"
STUCK_THRESHOLD_SECONDS=300  # 5 minutes of no log activity = stuck
SERVICE_NAME="lucrex-desktop-runner.service"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[$(ts)] $*" >> "$WATCHDOG_LOG"; }

# 1. Is the service even supposed to be running?
if ! systemctl --user is-active --quiet "$SERVICE_NAME"; then
    log "service inactive -- nothing to watch"
    exit 0
fi

# 2. Is there a task in progress that's at risk?
in_progress_count=$(ls "$IN_PROGRESS_DIR"/*.json 2>/dev/null | wc -l)
if [[ "$in_progress_count" -eq 0 ]]; then
    # No active task -- runner is just polling, that's fine
    exit 0
fi

# 3. When was the runner's log last modified?
if [[ ! -f "$LOG_FILE" ]]; then
    log "no log file at $LOG_FILE -- service may be misconfigured"
    exit 0
fi
log_mtime=$(stat -c %Y "$LOG_FILE")
now=$(date +%s)
age=$((now - log_mtime))

if [[ "$age" -lt "$STUCK_THRESHOLD_SECONDS" ]]; then
    # Recent activity -- runner is fine
    exit 0
fi

# 4. STUCK -- kill and let systemd restart
log "STUCK: in_progress=$in_progress_count, log silent for ${age}s -- restarting service"
systemctl --user restart "$SERVICE_NAME" || {
    log "ERROR: systemctl restart failed (need to provide hint?)"
    exit 1
}
log "service restarted -- new instance should pick up in 5-10s"

# 5. Move the stuck task to failed/ with reason so it doesn't get retried infinitely
for f in "$IN_PROGRESS_DIR"/*.json; do
    [[ -f "$f" ]] || continue
    fname=$(basename "$f")
    log "moving stuck task $fname to failed/ (watchdog_kill)"
    mv "$f" "/AA_MY_DRIVE/_logs/browser_tasks/failed/$fname" 2>/dev/null || true
done

exit 0
