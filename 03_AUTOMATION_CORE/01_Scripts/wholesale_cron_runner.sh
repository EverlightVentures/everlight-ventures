#!/usr/bin/env bash
# wholesale_cron_runner.sh -- canonical entry point for wholesale cron jobs.
#
# Wraps the actual job invocation with:
#   1. should-run check (active-passive failover via hive_cron_redundancy.py)
#   2. the job command itself
#   3. heartbeat write on completion
#
# Cron usage (replaces direct python3 calls):
#   0 * * * * cd /AA_MY_DRIVE && . /root/.config/everlight/secrets.env && \
#       bash 03_AUTOMATION_CORE/01_Scripts/wholesale_cron_runner.sh \
#         wholesale_hourly \
#         python3 01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/rex_belfort_sequence.py
#
# Args:
#   $1 = job name (e.g. wholesale_hourly, rex_negotiator_2min)
#   $@ from $2 onward = the command to execute
#
# Exit codes:
#   0  = job ran successfully
#   1  = skipped (peer is primary and fresh)
#   2  = job ran but had an error
#   99 = setup error

set -u
JOB="${1:-}"
shift || true
if [ -z "$JOB" ] || [ "$#" -lt 1 ]; then
  echo "usage: wholesale_cron_runner.sh <job_name> <cmd...>" >&2
  exit 99
fi

WS="${HIVE_LOCAL_WS:-/mnt/sdcard/AA_MY_DRIVE}"
REDUNDANCY="$WS/03_AUTOMATION_CORE/01_Scripts/hive_cron_redundancy.py"
LOG="$WS/_logs/cron_redundancy.log"
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [$JOB] $*" >> "$LOG"; }

# 1. should-run gate
if ! python3 "$REDUNDANCY" should-run "$JOB" >> "$LOG" 2>&1; then
  log "skipped (peer is primary)"
  exit 1
fi

log "running: $*"

# 2. run the job
"$@"
RC=$?
log "exit=$RC"

# 3. write heartbeat regardless of job exit (so we know we tried)
python3 "$REDUNDANCY" heartbeat "$JOB" >> "$LOG" 2>&1

# Surface the job's exit code
if [ "$RC" -ne 0 ]; then
  exit 2
fi
exit 0
