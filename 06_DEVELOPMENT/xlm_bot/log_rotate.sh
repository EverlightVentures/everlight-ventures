#!/bin/bash
# Log Rotation + Pruning for XLM Bot
# Cron: 0 * * * * flock -xn /tmp/xlm_logrotate.lock /home/opc/xlm-bot/log_rotate.sh
#
# Keeps each hot log under a configurable line/size limit.
# Trims from the top (oldest first). Never deletes trades.csv.
# Alerts Slack when disk is high.

BOT_DIR="/home/opc/xlm-bot"
LOGS="$BOT_DIR/logs"
DATA="$BOT_DIR/data"
SLACK_WEBHOOK="https://hooks.slack.com/services/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"

# Limits
MAX_JSONL_LINES=50000     # ~50k lines per .jsonl (decisions, signals, margin, etc.)
MAX_TIMESERIES_LINES=20000  # timeseries grows fast -- tighter cap
MAX_LOG_LINES=10000       # .log files (dashboard.log, live_ws.log, etc.)
MAX_MD_LINES=5000         # markdown reports
DISK_WARN_PCT=80          # warn at 80%
DISK_TRIM_PCT=85          # aggressively trim at 85%

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] LOG_ROTATE: $1" >> "$LOGS/watchdog.log"; }

slack() {
    curl -s -X POST "$SLACK_WEBHOOK" \
        -H 'Content-type: application/json' \
        -d "{\"text\": \"$1\"}" >/dev/null 2>&1
}

# Trim a file to last N lines if it exceeds that count.
trim_to() {
    local file="$1"
    local max="$2"
    [ -f "$file" ] || return
    local lines
    lines=$(wc -l < "$file" 2>/dev/null || echo 0)
    if [ "$lines" -gt "$max" ]; then
        local keep=$(( lines - max ))
        local tmp="${file}.tmp.$$"
        tail -n "$max" "$file" > "$tmp" && mv "$tmp" "$file"
        log "Trimmed $(basename $file): $lines -> $max lines (removed $keep)"
    fi
}

# Standard JSONL logs
for f in \
    decisions.jsonl \
    signals.jsonl \
    fills.jsonl \
    incidents.jsonl \
    margin_policy.jsonl \
    plrl3.jsonl \
    contract_context.jsonl \
    market_news.jsonl \
    atr_regime_audit.jsonl \
    cash_movements.jsonl \
    equity_series.jsonl; do
    trim_to "$LOGS/$f" "$MAX_JSONL_LINES"
done

# Timeseries grows fastest
trim_to "$LOGS/dashboard_timeseries.jsonl" "$MAX_TIMESERIES_LINES"

# Log files
for f in \
    dashboard.log \
    live_ws.log \
    ddr.log \
    notify.log \
    hive_dashboard.log \
    ai_debug.log \
    watchdog.log; do
    trim_to "$LOGS/$f" "$MAX_LOG_LINES"
done

# Markdown reports
for f in daily_report.md recommended_changes.md; do
    trim_to "$LOGS/$f" "$MAX_MD_LINES"
done

# Check disk usage
DISK_PCT=$(df "$BOT_DIR" 2>/dev/null | tail -1 | awk '{gsub(/%/,""); print $5}')
DISK_PCT=${DISK_PCT:-0}

if [ "$DISK_PCT" -ge "$DISK_TRIM_PCT" ]; then
    log "DISK CRITICAL: ${DISK_PCT}% -- emergency trim"
    # Emergency: halve all limits
    for f in decisions.jsonl signals.jsonl fills.jsonl margin_policy.jsonl; do
        trim_to "$LOGS/$f" $(( MAX_JSONL_LINES / 2 ))
    done
    trim_to "$LOGS/dashboard_timeseries.jsonl" $(( MAX_TIMESERIES_LINES / 2 ))
    # Remove old backup csv files (phantom/bak copies, keep primary trades.csv)
    rm -f "$LOGS/trades.csv.bak2" "$LOGS/trades.csv.bak_phantom"
    slack "[LOG_ROTATE] :warning: Disk ${DISK_PCT}% -- emergency trim done. Check Oracle VM."
elif [ "$DISK_PCT" -ge "$DISK_WARN_PCT" ]; then
    log "DISK WARNING: ${DISK_PCT}% used"
    slack "[LOG_ROTATE] :warning: Disk ${DISK_PCT}% -- approaching limit on Oracle VM."
fi

log "Rotation complete. Disk: ${DISK_PCT}%"
