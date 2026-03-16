#!/bin/bash
# Oracle Watchdog v2 -- position-aware, fast recovery
#
# Runs on your PHONE to monitor Oracle Cloud instance.
# If position is open and instance is down, reboots in 2 min (not 10).
# If flat, waits 5 min before reboot (less aggressive).
#
# Usage:
#   bash oracle_watchdog.sh              # loop every 60s (foreground)
#   bash oracle_watchdog.sh --once       # single check
#   bash oracle_watchdog.sh --status     # show current state
#   nohup bash oracle_watchdog.sh &      # run in background

ORACLE_IP="163.192.19.196"
ORACLE_USER="opc"
SSH_KEY="$HOME/.ssh/oracle_key.pem"
# Source secrets from central .env if not already set
_ENV_FILE="${EVERLIGHT_ENV:-/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env}"
[ -f "$_ENV_FILE" ] && set -a && . "$_ENV_FILE" && set +a 2>/dev/null

SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"
LOG_DIR="/mnt/sdcard/AA_MY_DRIVE/_logs"
LOG_FILE="$LOG_DIR/oracle_watchdog.log"
STATE_FILE="$LOG_DIR/.oracle_state"
POSITION_CACHE="$LOG_DIR/.oracle_last_position"
CHECK_INTERVAL=60  # seconds

# OCI CLI config
OCI_INSTANCE_ID="ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgachuw5tsdglraq4cuco4qoznrtarctqspta52mta5qf5aq"
OCI_COMPARTMENT_ID="ocid1.tenancy.oc1..aaaaaaaacm32hkslhfxorfn7jubhjqjffr4roltyjwjrkfcdkup37o7qt4ca"

# Reboot timers (minutes) -- faster when in a trade
REBOOT_WAIT_IN_POSITION=2   # 2 min -- position at risk, act fast
REBOOT_WAIT_FLAT=5           # 5 min -- no urgency when flat
CRITICAL_ESCALATION_MIN=20   # alert every 20 min if still down after reboot

mkdir -p "$LOG_DIR"

ts() { date '+%Y-%m-%d %H:%M:%S PT'; }
log() { echo "[$(ts)] $1" | tee -a "$LOG_FILE"; }

slack() {
    curl -s -X POST "$SLACK_WEBHOOK" \
        -H 'Content-type: application/json' \
        -d "{\"text\": \"$1\"}" >/dev/null 2>&1
}

get_state() { cat "$STATE_FILE" 2>/dev/null || echo "unknown"; }
set_state() { echo "$1" > "$STATE_FILE"; }

# Check if we had an open position last time we could reach the bot
has_position_cached() {
    [ -f "$POSITION_CACHE" ] && grep -q "true" "$POSITION_CACHE" 2>/dev/null
}

check_ssh() {
    ssh -F /root/.ssh/config oracle \
        -o BatchMode=yes -o ConnectTimeout=8 \
        -o ServerAliveInterval=5 -o ServerAliveCountMax=2 \
        "echo ok" 2>/dev/null
}

# Get bot status + position info in one SSH call (fast)
check_bot_full() {
    ssh -F /root/.ssh/config oracle \
        -o ConnectTimeout=8 \
        -o ServerAliveInterval=5 -o ServerAliveCountMax=2 '
        BOT=$(systemctl is-active xlm-bot 2>/dev/null)
        echo "bot_status=$BOT"
        if [ -f /home/opc/xlm-bot/data/.heartbeat ]; then
            HB=$(cat /home/opc/xlm-bot/data/.heartbeat)
            AGE=$(python3 -c "import time; print(int(time.time()-float('"$HB"')))" 2>/dev/null || echo 999)
            echo "heartbeat_age=$AGE"
        else
            echo "heartbeat_age=999"
        fi
        if [ -f /home/opc/xlm-bot/data/state.json ]; then
            python3 -c "
import json
s=json.load(open(\"/home/opc/xlm-bot/data/state.json\"))
ip=s.get(\"in_position\", False)
op=s.get(\"open_position\", {})
d=op.get(\"direction\",\"\")
ep=op.get(\"entry_price\",\"\")
print(f\"in_position={ip}\")
print(f\"direction={d}\")
print(f\"entry_price={ep}\")
print(f\"pnl_today={s.get(\"pnl_today_usd\",0)}\")
" 2>/dev/null
        fi
        MEM=$(free | awk "/Mem:/ {printf \"%.0f\", \$3/\$2*100}")
        echo "mem_pct=$MEM"
    ' 2>/dev/null
}

try_oci_softreset() {
    if [ -z "$OCI_INSTANCE_ID" ]; then
        log "OCI CLI not configured"
        return 1
    fi
    # Use full path -- cron/nohup PATH doesn't include /usr/local/bin
    OCI_BIN="${OCI_BIN:-/usr/local/bin/oci}"
    if [ -x "$OCI_BIN" ] || command -v oci &>/dev/null; then
        OCI_CMD="${OCI_BIN:-oci}"
        log "Sending OCI SOFTRESET..."
        SUPPRESS_LABEL_WARNING=True $OCI_CMD compute instance action --instance-id "$OCI_INSTANCE_ID" --action SOFTRESET 2>&1
        return $?
    else
        log "OCI CLI not installed (checked $OCI_BIN and PATH)"
        return 1
    fi
}

do_check() {
    PREV_STATE=$(get_state)

    # Try full status check (SSH + bot + position)
    RESULT=$(check_bot_full 2>/dev/null)

    if [ -n "$RESULT" ]; then
        # Parse results
        BOT_STATUS=$(echo "$RESULT" | grep "bot_status=" | cut -d= -f2)
        HB_AGE=$(echo "$RESULT" | grep "heartbeat_age=" | cut -d= -f2)
        IN_POS=$(echo "$RESULT" | grep "in_position=" | cut -d= -f2)
        DIRECTION=$(echo "$RESULT" | grep "direction=" | cut -d= -f2)
        ENTRY=$(echo "$RESULT" | grep "entry_price=" | cut -d= -f2)
        PNL=$(echo "$RESULT" | grep "pnl_today=" | cut -d= -f2)
        MEM=$(echo "$RESULT" | grep "mem_pct=" | cut -d= -f2)

        # Cache position state for when instance goes down
        echo "$IN_POS" > "$POSITION_CACHE"

        if [ "$BOT_STATUS" = "active" ] && [ "${HB_AGE:-999}" -lt 120 ]; then
            # All good
            if [ "$PREV_STATE" != "healthy" ]; then
                POS_MSG=""
                if [ "$IN_POS" = "True" ]; then
                    POS_MSG=" Position: $DIRECTION @ $ENTRY (SAFE)"
                fi
                log "RECOVERED: Bot healthy (HB ${HB_AGE}s).${POS_MSG}"
                slack "[ORACLE RECOVERED] Bot is healthy! Heartbeat ${HB_AGE}s.${POS_MSG} PnL today: \$${PNL}"
            fi
            set_state "healthy"

            # Warn on high memory
            if [ "${MEM:-0}" -ge 90 ]; then
                log "MEMORY WARNING: ${MEM}% on Oracle"
            fi

        elif [ "$BOT_STATUS" = "active" ] && [ "${HB_AGE:-999}" -ge 120 ]; then
            # Bot running but heartbeat stale -- zombie
            log "ZOMBIE: Bot active but heartbeat ${HB_AGE}s stale"
            slack "[ORACLE] Bot zombie -- heartbeat ${HB_AGE}s stale. Restarting service."
            ssh -F /root/.ssh/config oracle "sudo systemctl restart xlm-bot" 2>/dev/null
            set_state "bot_restarted"

        else
            # Bot not active
            POS_MSG=""
            if [ "$IN_POS" = "True" ]; then
                POS_MSG=" POSITION OPEN: $DIRECTION @ $ENTRY!"
            fi
            log "BOT DOWN: $BOT_STATUS.${POS_MSG} Restarting..."
            slack "[ORACLE] Bot is $BOT_STATUS.${POS_MSG} Restarting xlm-bot..."
            ssh -F /root/.ssh/config oracle "sudo systemctl restart xlm-bot" 2>/dev/null
            set_state "bot_restarted"
        fi

    else
        # SSH FAILED -- instance unreachable
        if [ "$PREV_STATE" = "healthy" ] || [ "$PREV_STATE" = "unknown" ]; then
            POS_MSG="(no position)"
            if has_position_cached; then
                POS_MSG="POSITION WAS OPEN -- URGENT"
            fi
            log "ALERT: Oracle UNREACHABLE! $POS_MSG"
            slack "[ORACLE DOWN] Instance unreachable! $POS_MSG Attempting recovery..."
            echo "$(date +%s)" > "$LOG_DIR/.oracle_down_since"
        fi

        # How long down?
        DOWN_SINCE=$(cat "$LOG_DIR/.oracle_down_since" 2>/dev/null || date +%s)
        DOWN_MIN=$(( ($(date +%s) - DOWN_SINCE) / 60 ))
        log "Oracle down ${DOWN_MIN}min"

        # Choose reboot timer based on position
        if has_position_cached; then
            REBOOT_WAIT=$REBOOT_WAIT_IN_POSITION
        else
            REBOOT_WAIT=$REBOOT_WAIT_FLAT
        fi

        # Try OCI reboot after wait period
        if [ "$DOWN_MIN" -ge "$REBOOT_WAIT" ] && [ "$PREV_STATE" != "reboot_attempted" ]; then
            POS_MSG=""
            if has_position_cached; then
                POS_MSG=" (POSITION OPEN -- fast reboot)"
            fi
            if try_oci_softreset; then
                log "OCI SOFTRESET sent.${POS_MSG}"
                slack "[ORACLE] SOFTRESET sent after ${DOWN_MIN}min.${POS_MSG} Waiting for recovery..."
                set_state "reboot_attempted"
            else
                slack "[ORACLE] Cannot auto-reboot. Check Oracle Console NOW!"
                set_state "needs_manual"
            fi

        elif [ "$PREV_STATE" = "reboot_attempted" ]; then
            # Still down after reboot -- escalate periodically
            LAST_ALERT=$(cat "$LOG_DIR/.oracle_last_critical" 2>/dev/null || echo 0)
            SINCE_ALERT=$(( ($(date +%s) - LAST_ALERT) / 60 ))
            if [ "$SINCE_ALERT" -ge "$CRITICAL_ESCALATION_MIN" ]; then
                log "CRITICAL: Still down ${DOWN_MIN}min after reboot"
                slack "[CRITICAL] Oracle still down ${DOWN_MIN}min! Check https://cloud.oracle.com NOW"
                echo "$(date +%s)" > "$LOG_DIR/.oracle_last_critical"
            fi

        else
            set_state "down"
        fi
    fi
}

# -- Main --
case "${1:-loop}" in
    --once)
        do_check
        ;;
    --status)
        STATE=$(get_state)
        echo "Oracle state: $STATE"
        if has_position_cached; then
            echo "Last known position: OPEN"
        else
            echo "Last known position: flat"
        fi
        if [ -f "$LOG_DIR/.oracle_down_since" ]; then
            DOWN_SINCE=$(cat "$LOG_DIR/.oracle_down_since")
            DOWN_MIN=$(( ($(date +%s) - DOWN_SINCE) / 60 ))
            echo "Down for: ${DOWN_MIN} minutes"
        fi
        tail -5 "$LOG_FILE" 2>/dev/null
        ;;
    *)
        log "Oracle watchdog v2 started (check every ${CHECK_INTERVAL}s)"
        while true; do
            do_check
            sleep $CHECK_INTERVAL
        done
        ;;
esac
