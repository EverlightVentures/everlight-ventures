#!/bin/bash
# oracle_watchdog.sh -- Phone-side self-healing for Oracle VM
# Cron (Termux): */5 * * * * flock -xn /tmp/oracle_wd.lock /mnt/sdcard/AA_MY_DRIVE/xlm_bot/oracle_watchdog.sh
#
# FSM:
#   RUNNING+SSH_OK (healthy)
#   RUNNING+SSH_FAIL (3x) -> SOFTRESET -> wait 3min -> retry
#   still fails            -> RESET     -> wait 5min -> retry
#   still fails            -> ALERT_HUMAN (give up, notify)
#   STOPPING (stuck)       -> RESET (immediate)
#   STOPPED                -> START (immediate)
#
# Cooldown: max 3 hard RESETs per 6-hour window (prevents death loops)
# All actions logged + Slack notified

set -euo pipefail

# == Config ==
INSTANCE_ID="ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgachuw5tsdglraq4cuco4qoznrtarctqspta52mta5qf5aq"
ORACLE_IP="163.192.19.196"
ORACLE_USER="opc"
SSH_KEY="/root/.ssh/oracle_key.pem"
# Source secrets from central .env if not already set
_ENV_FILE="${EVERLIGHT_ENV:-/home/opc/xlm-bot/secrets/runtime.env}"
[ -f "$_ENV_FILE" ] || _ENV_FILE="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"
[ -f "$_ENV_FILE" ] && set -a && . "$_ENV_FILE" && set +a 2>/dev/null

SLACK_WEBHOOK="${SLACK_WEBHOOK_ALERTS:-}"

LOG="/tmp/oracle_watchdog.log"
STATE_DIR="/tmp/oracle_wd_state"
mkdir -p "$STATE_DIR"

# State files (persist across cron runs via /tmp)
RESET_COUNT_FILE="$STATE_DIR/reset_count"
RESET_WINDOW_FILE="$STATE_DIR/reset_window_start"
SOFTRESET_TS_FILE="$STATE_DIR/last_softreset"
RESET_TS_FILE="$STATE_DIR/last_reset"
LAST_ACTION_FILE="$STATE_DIR/last_action"
FAILURE_COUNT_FILE="$STATE_DIR/consecutive_failures"

MAX_RESETS_PER_WINDOW=3
RESET_WINDOW_SECS=21600   # 6 hours
SOFTRESET_WAIT=180        # 3 min after softreset before re-check
RESET_WAIT=300            # 5 min after hard reset before re-check
SSH_TIMEOUT=12            # seconds for banner exchange probe

# == Helpers ==
ts()  { date '+%Y-%m-%d %H:%M:%S PT'; }
now() { date +%s; }

log() { echo "[$(ts)] $1" | tee -a "$LOG"; }

slack() {
    curl -s -X POST "$SLACK_WEBHOOK" \
        -H 'Content-type: application/json' \
        -d "{\"text\": \"[OracleWD] $1\"}" >/dev/null 2>&1 &
}

get_reset_count() {
    local count=0
    local window_start=0
    [ -f "$RESET_COUNT_FILE" ]  && count=$(cat "$RESET_COUNT_FILE")
    [ -f "$RESET_WINDOW_FILE" ] && window_start=$(cat "$RESET_WINDOW_FILE")
    local age=$(( $(now) - ${window_start:-0} ))
    if [ "$age" -gt "$RESET_WINDOW_SECS" ]; then
        echo 0 > "$RESET_COUNT_FILE"
        now > "$RESET_WINDOW_FILE"
        count=0
    fi
    echo "$count"
}

increment_reset_count() {
    local count
    count=$(get_reset_count)
    count=$(( count + 1 ))
    echo "$count" > "$RESET_COUNT_FILE"
    [ -f "$RESET_WINDOW_FILE" ] || now > "$RESET_WINDOW_FILE"
}

get_failure_count() { [ -f "$FAILURE_COUNT_FILE" ] && cat "$FAILURE_COUNT_FILE" || echo 0; }
set_failure_count() { echo "$1" > "$FAILURE_COUNT_FILE"; }

secs_since() {
    local ts_file="$1"
    [ -f "$ts_file" ] || { echo 9999999; return; }
    local ts
    ts=$(cat "$ts_file")
    echo $(( $(now) - ${ts:-0} ))
}

# == SSH probe ==
# Returns 0 if SSH succeeds, 1 if timeout/fail
ssh_ok() {
    # Fast TCP check first (3s)
    if ! nc -z -w 3 "$ORACLE_IP" 22 2>/dev/null; then
        log "TCP port 22 unreachable"
        return 1
    fi
    # Full SSH banner + auth probe
    timeout "$SSH_TIMEOUT" ssh \
        -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o BatchMode=yes \
        -o ConnectTimeout=10 \
        -o GSSAPIAuthentication=no \
        -o AddressFamily=inet \
        -o Ciphers=aes128-ctr,aes256-ctr \
        -o KexAlgorithms=curve25519-sha256,ecdh-sha2-nistp256 \
        -o LogLevel=ERROR \
        "$ORACLE_USER@$ORACLE_IP" \
        "echo ok" 2>/dev/null
}

# == OCI actions ==
get_vm_state() {
    oci compute instance get \
        --instance-id "$INSTANCE_ID" \
        --query 'data."lifecycle-state"' \
        --raw-output 2>/dev/null || echo "UNKNOWN"
}

do_softreset() {
    now > "$SOFTRESET_TS_FILE"
    oci compute instance action \
        --instance-id "$INSTANCE_ID" \
        --action SOFTRESET \
        --wait-for-state RUNNING \
        --max-wait-seconds 240 2>/dev/null
}

do_reset() {
    increment_reset_count
    now > "$RESET_TS_FILE"
    oci compute instance action \
        --instance-id "$INSTANCE_ID" \
        --action RESET \
        --wait-for-state RUNNING \
        --max-wait-seconds 360 2>/dev/null
}

do_start() {
    oci compute instance action \
        --instance-id "$INSTANCE_ID" \
        --action START \
        --wait-for-state RUNNING \
        --max-wait-seconds 360 2>/dev/null
}

# == Main FSM ==
main() {
    log "=== Oracle watchdog check ==="

    local VM_STATE
    VM_STATE=$(get_vm_state)
    log "VM state: $VM_STATE"

    case "$VM_STATE" in
        STOPPED)
            log "VM STOPPED -- starting"
            slack "VM is STOPPED. Starting now..."
            do_start
            sleep 30
            if ssh_ok; then
                log "VM started, SSH OK"
                slack "VM started -- SSH OK. xlm-bot coming back online."
                set_failure_count 0
            else
                log "VM started but SSH still failing"
                slack "VM started but SSH failed. Check OCI console."
            fi
            echo "START" > "$LAST_ACTION_FILE"
            exit 0
            ;;
        STOPPING)
            log "VM STUCK in STOPPING -- forcing RESET"
            local RC
            RC=$(get_reset_count)
            if [ "$RC" -ge "$MAX_RESETS_PER_WINDOW" ]; then
                log "RESET limit ($MAX_RESETS_PER_WINDOW) reached -- alerting human"
                slack "CRITICAL: RESET limit reached. VM stuck STOPPING. Manual intervention needed. IP: $ORACLE_IP"
                exit 1
            fi
            slack "VM stuck STOPPING. Forcing RESET (count: $((RC+1))/$MAX_RESETS_PER_WINDOW)..."
            do_reset
            echo "RESET" > "$LAST_ACTION_FILE"
            exit 0
            ;;
        RUNNING)
            : # handled below
            ;;
        UNKNOWN)
            log "OCI returned UNKNOWN state -- skipping"
            exit 0
            ;;
        *)
            log "Unhandled VM state: $VM_STATE -- skipping"
            exit 0
            ;;
    esac

    # VM is RUNNING -- check SSH
    if ssh_ok; then
        log "SSH OK -- VM healthy"
        set_failure_count 0
        rm -f "$SOFTRESET_TS_FILE" "$LAST_ACTION_FILE"
        exit 0
    fi

    # SSH failed
    local FAILURES
    FAILURES=$(get_failure_count)
    FAILURES=$(( FAILURES + 1 ))
    set_failure_count "$FAILURES"
    log "SSH FAILED (consecutive: $FAILURES)"

    local LAST_ACTION
    LAST_ACTION=$(cat "$LAST_ACTION_FILE" 2>/dev/null || echo "none")
    local SECS_SINCE_SOFT
    SECS_SINCE_SOFT=$(secs_since "$SOFTRESET_TS_FILE")
    local SECS_SINCE_HARD
    SECS_SINCE_HARD=$(secs_since "$RESET_TS_FILE")

    # SOFTRESET issued, still in wait window
    if [ "$LAST_ACTION" = "SOFTRESET" ] && [ "$SECS_SINCE_SOFT" -lt "$SOFTRESET_WAIT" ]; then
        log "SOFTRESET issued ${SECS_SINCE_SOFT}s ago -- waiting (${SOFTRESET_WAIT}s window)"
        exit 0
    fi

    # SOFTRESET wait elapsed, SSH still down -> escalate to RESET
    if [ "$LAST_ACTION" = "SOFTRESET" ] && [ "$SECS_SINCE_SOFT" -ge "$SOFTRESET_WAIT" ]; then
        local RC
        RC=$(get_reset_count)
        if [ "$RC" -ge "$MAX_RESETS_PER_WINDOW" ]; then
            log "RESET limit ($MAX_RESETS_PER_WINDOW/6h) reached -- alerting human"
            slack "CRITICAL: Oracle VM SSH failed after SOFTRESET + $RC RESETs. MANUAL INTERVENTION NEEDED. IP: $ORACLE_IP"
            exit 1
        fi
        log "SOFTRESET elapsed, SSH still down -- escalating to RESET"
        slack "VM RUNNING but SSH still down after SOFTRESET. Issuing HARD RESET (count: $((RC+1))/$MAX_RESETS_PER_WINDOW)..."
        do_reset
        echo "RESET" > "$LAST_ACTION_FILE"
        exit 0
    fi

    # RESET issued, still in wait window
    if [ "$LAST_ACTION" = "RESET" ] && [ "$SECS_SINCE_HARD" -lt "$RESET_WAIT" ]; then
        log "RESET issued ${SECS_SINCE_HARD}s ago -- waiting (${RESET_WAIT}s window)"
        exit 0
    fi

    # RESET wait elapsed, SSH still down -> give up
    if [ "$LAST_ACTION" = "RESET" ] && [ "$SECS_SINCE_HARD" -ge "$RESET_WAIT" ]; then
        log "RESET issued ${SECS_SINCE_HARD}s ago, SSH still down -- ESCALATING to human"
        slack "CRITICAL: Oracle VM unreachable after HARD RESET (${SECS_SINCE_HARD}s). IP: $ORACLE_IP. OCI state: $(get_vm_state). Auto-recovery exhausted."
        exit 1
    fi

    # Not enough failures yet -- wait for 3 consecutive before acting
    if [ "$FAILURES" -lt 3 ]; then
        log "SSH failed (failure #$FAILURES) -- need 3 consecutive before action"
        exit 0
    fi

    # 3+ consecutive failures -- issue SOFTRESET
    log "3 consecutive SSH failures -- issuing SOFTRESET"
    slack "Oracle VM SSH unreachable x3. Issuing SOFTRESET. IP: $ORACLE_IP"
    echo "SOFTRESET" > "$LAST_ACTION_FILE"
    # Run async so cron slot doesn't block
    do_softreset &
    log "SOFTRESET issued (async) -- next check in ~3min"
}

main "$@"
