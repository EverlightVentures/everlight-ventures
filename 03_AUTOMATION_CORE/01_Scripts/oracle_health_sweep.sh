#!/bin/bash
# ============================================================
# Oracle E5 Weekly Health Sweep
# Companion to the remote codebase hygiene trigger.
# This runs ON Oracle (or via SSH from phone) and checks
# things the remote agent can't: services, disk, .bak files,
# hardcoded tokens in deployed code, /mnt/sdcard path creep.
#
# Posts structured report to Slack #hive-alerts.
#
# Usage:
#   ssh oracle-e5 'bash /home/opc/scripts/oracle_health_sweep.sh'
#   -- or deploy via cron on Oracle (Sundays 2:15 AM PT = 9:15 UTC)
#   15 9 * * 0 /home/opc/scripts/oracle_health_sweep.sh >> /home/opc/logs/health_sweep.log 2>&1
# ============================================================

set -u

SLACK_TOKEN="${SLACK_WARROOM_TOKEN:-xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy}"
SLACK_CHANNEL="C0ANPRCA4AD"  # #hive-alerts
REPORT_DATE=$(date '+%Y-%m-%d %H:%M PT' -d 'TZ="America/Los_Angeles"' 2>/dev/null || date '+%Y-%m-%d %H:%M UTC')

CRITICAL=()
WARNINGS=()
INFO=()

log() { echo "[$(date '+%H:%M:%S')] $1"; }

# ============================================================
# 1. SERVICE STATUS
# ============================================================
log "Checking services..."

SERVICES=(
  "xlm-bot"
  "xlm-dash-react"
  "xlm-ws"
  "xlm-liqfeed"
  "n8n"
  "blinko"
  "hive-voice"
  "hive-django"
  "hive-dashboard"
  "hive-slack-agent"
  "vantaris"
)

for svc in "${SERVICES[@]}"; do
  status=$(systemctl is-active "$svc" 2>/dev/null || echo "not-found")
  if [ "$status" = "active" ]; then
    INFO+=("$svc: running")
  elif [ "$status" = "not-found" ]; then
    INFO+=("$svc: not installed (skipped)")
  else
    CRITICAL+=("Service $svc is $status")
  fi
done

# Check for services that restarted in the last 24h (flapping)
for svc in "${SERVICES[@]}"; do
  restarts=$(systemctl show "$svc" --property=NRestarts 2>/dev/null | cut -d= -f2 || echo "0")
  if [ "${restarts:-0}" -gt 5 ]; then
    WARNINGS+=("$svc has restarted ${restarts} times (possible flapping)")
  fi
done

# ============================================================
# 2. DISK USAGE
# ============================================================
log "Checking disk..."

disk_pct=$(df / --output=pcent | tail -1 | tr -d '% ')
if [ "$disk_pct" -gt 85 ]; then
  CRITICAL+=("Root disk at ${disk_pct}% -- immediate cleanup needed")
elif [ "$disk_pct" -gt 70 ]; then
  WARNINGS+=("Root disk at ${disk_pct}% -- trending high")
else
  INFO+=("Root disk: ${disk_pct}% used")
fi

# Check /home/opc specifically
home_size=$(du -sh /home/opc 2>/dev/null | head -1 | cut -f1)
home_size="${home_size:-unknown}"
INFO+=("/home/opc total: ${home_size}")

# ============================================================
# 3. .BAK FILE ACCUMULATION
# ============================================================
log "Scanning for .bak files..."

bak_count=$(find /home/opc -name "*.bak" -o -name "*.old" -o -name "*.orig" -o -name "*.copy" 2>/dev/null | wc -l)
if [ "$bak_count" -gt 20 ]; then
  WARNINGS+=("${bak_count} .bak/.old/.orig/.copy files under /home/opc")
  # List the biggest ones
  big_baks=$(find /home/opc -name "*.bak" -o -name "*.old" -o -name "*.orig" 2>/dev/null | head -5)
  if [ -n "$big_baks" ]; then
    WARNINGS+=("Top .bak files: $(echo "$big_baks" | tr '\n' ', ')")
  fi
elif [ "$bak_count" -gt 0 ]; then
  INFO+=("${bak_count} .bak/.old files found (manageable)")
fi

# ============================================================
# 4. HARDCODED TOKENS IN DEPLOYED CODE
# ============================================================
log "Scanning for hardcoded tokens..."

# Check deployed Python files for raw tokens (not env vars)
token_hits=$(grep -rn "sk-proj-\|sk_live_\|sk_test_\|xoxb-" /home/opc/xlm-bot/ /home/opc/hive_django/ /home/opc/hive_reports/ 2>/dev/null \
  | grep -v ".pyc" | grep -v "__pycache__" | grep -v "node_modules" | grep -v ".env" \
  | wc -l || true)
if [ "$token_hits" -gt 0 ]; then
  CRITICAL+=("${token_hits} hardcoded token references in deployed code (check with: grep -rn 'sk-proj-\|sk_live_\|xoxb-' /home/opc/)")
fi

# ============================================================
# 5. /mnt/sdcard PATH CREEP
# ============================================================
log "Checking for /mnt/sdcard references..."

sdcard_hits=$(grep -rn "/mnt/sdcard" /home/opc/hive_django/ /home/opc/xlm-bot/ 2>/dev/null \
  | grep -v ".pyc" | grep -v "__pycache__" | grep -v "node_modules" \
  | wc -l || true)
if [ "$sdcard_hits" -gt 0 ]; then
  WARNINGS+=("${sdcard_hits} /mnt/sdcard references in Oracle deployed code (should be /home/opc paths)")
fi

# ============================================================
# 6. LOG FILE SIZES
# ============================================================
log "Checking log sizes..."

for logdir in /home/opc/xlm-bot/logs /home/opc/logs /home/opc/hive_reports; do
  if [ -d "$logdir" ]; then
    dir_size=$(du -sh "$logdir" 2>/dev/null | cut -f1)
    INFO+=("$logdir: ${dir_size}")
    # Check for individual huge logs
    huge_logs=$(find "$logdir" -size +100M 2>/dev/null | head -3)
    if [ -n "$huge_logs" ]; then
      WARNINGS+=("Large log files (>100MB): $(echo "$huge_logs" | tr '\n' ', ')")
    fi
  fi
done

# ============================================================
# 7. XLM BOT SPECIFIC CHECKS
# ============================================================
log "Checking XLM bot..."

# Check if decisions.jsonl is growing (bot is trading)
if [ -f /home/opc/xlm-bot/logs/decisions.jsonl ]; then
  last_decision=$(tail -1 /home/opc/xlm-bot/logs/decisions.jsonl 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ts','unknown'))" 2>/dev/null || echo "parse-error")
  INFO+=("Last XLM bot decision: ${last_decision}")

  decision_count=$(wc -l < /home/opc/xlm-bot/logs/decisions.jsonl 2>/dev/null || echo "0")
  INFO+=("Total decisions logged: ${decision_count}")
fi

# Check if bot process ran recently
bot_last=$(systemctl show xlm-bot --property=ActiveEnterTimestamp 2>/dev/null | cut -d= -f2 || echo "unknown")
if [ -n "$bot_last" ] && [ "$bot_last" != "unknown" ]; then
  INFO+=("XLM bot last started: ${bot_last}")
fi

# ============================================================
# BUILD REPORT
# ============================================================
log "Building report..."

c_count=${#CRITICAL[@]}
w_count=${#WARNINGS[@]}
i_count=${#INFO[@]}

report=":mag: *ORACLE E5 HEALTH SWEEP*\nDate: ${REPORT_DATE}\nHost: 129.159.38.250\n\n:bar_chart: Summary: ${c_count} critical | ${w_count} warnings | ${i_count} info\n"

if [ "$c_count" -gt 0 ]; then
  report+="\n:red_circle: *CRITICAL*\n"
  for item in "${CRITICAL[@]}"; do
    report+="\u2022 ${item}\n"
  done
fi

if [ "$w_count" -gt 0 ]; then
  report+="\n:large_yellow_circle: *WARNINGS*\n"
  for item in "${WARNINGS[@]}"; do
    report+="\u2022 ${item}\n"
  done
fi

if [ "$i_count" -gt 0 ]; then
  report+="\n:large_green_circle: *INFO*\n"
  for item in "${INFO[@]}"; do
    report+="\u2022 ${item}\n"
  done
fi

if [ "$c_count" -eq 0 ] && [ "$w_count" -eq 0 ]; then
  report+="\n:white_check_mark: All clear. Oracle E5 is healthy."
fi

# ============================================================
# POST TO SLACK
# ============================================================
log "Posting to Slack #hive-alerts..."

curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer ${SLACK_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"channel\": \"${SLACK_CHANNEL}\",
    \"text\": \"$(echo -e "$report" | sed 's/"/\\"/g')\"
  }" > /dev/null 2>&1

log "Done. ${c_count} critical, ${w_count} warnings, ${i_count} info."
