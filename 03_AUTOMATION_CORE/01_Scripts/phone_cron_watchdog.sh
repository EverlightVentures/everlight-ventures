#!/usr/bin/env bash
# phone_cron_watchdog.sh
#
# Watches for phone-cron silence. If no log file under _logs/ has been
# updated in the last 30 minutes, it:
#   1. logs to _logs/cron_watchdog.log
#   2. attempts to (re)start crond if it's missing
#   3. fires a branded Slack alert to #hive-alerts so Marquise sees it
#
# Wire this to run on Oracle every 5 minutes. The phone is the patient,
# Oracle is the doctor. We do NOT run this on the phone itself, because
# if the phone is dead, the watchdog dies with it.
#
# Cron line on Oracle (add to opc crontab via crontab -e):
#   */5 * * * * ssh -o ConnectTimeout=10 -i /home/opc/.ssh/phone_key phone_user@phone_ip 'bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/phone_cron_watchdog.sh' >> /home/opc/_logs/phone_watchdog.log 2>&1
#
# Or, simpler: run this ON the phone itself via Termux boot script,
# and have IT alert Slack on silence (the phone dying scenario is already
# being addressed by the Oracle-resident migration; this is the "just in case"
# layer).

set -uo pipefail

WORKSPACE="${WORKSPACE:-/mnt/sdcard/AA_MY_DRIVE}"
LOGS_DIR="$WORKSPACE/_logs"
WATCHDOG_LOG="$LOGS_DIR/cron_watchdog.log"
SILENCE_THRESHOLD_MIN="${SILENCE_THRESHOLD_MIN:-30}"
SLACK_BOT_TOKEN="${SLACK_BOT_TOKEN:-}"
SLACK_CHANNEL_ALERTS="${SLACK_CHANNEL_ALERTS:-C08L9TJSFQE}"  # #hive-alerts -- update if different

mkdir -p "$LOGS_DIR"

now_ts="$(date +%s)"
now_human="$(date '+%Y-%m-%d %H:%M:%S %Z')"

# Find the most recently modified log under _logs/, return its mtime in epoch.
last_mtime=0
last_name=""
for f in "$LOGS_DIR"/*.log; do
  [ -f "$f" ] || continue
  m=$(stat -c "%Y" "$f" 2>/dev/null || echo 0)
  if [ "$m" -gt "$last_mtime" ]; then
    last_mtime=$m
    last_name=$(basename "$f")
  fi
done

age_min=$(( (now_ts - last_mtime) / 60 ))

echo "[$now_human] last_log=$last_name age=${age_min}m" >> "$WATCHDOG_LOG"

if [ "$age_min" -lt "$SILENCE_THRESHOLD_MIN" ]; then
  exit 0
fi

# We are in silence. Check whether crond is alive.
crond_alive=0
if pgrep -f "crond" > /dev/null 2>&1; then
  crond_alive=1
fi

echo "[$now_human] SILENCE: ${age_min}m without log fire. crond_alive=$crond_alive" >> "$WATCHDOG_LOG"

# Try to start crond if it's missing. Termux uses /usr/sbin/crond.
if [ "$crond_alive" -eq 0 ]; then
  for crond_bin in /usr/sbin/crond /usr/bin/crond /system/bin/crond; do
    if [ -x "$crond_bin" ]; then
      "$crond_bin" -b 2>>"$WATCHDOG_LOG" || true
      echo "[$now_human] attempted to start $crond_bin" >> "$WATCHDOG_LOG"
      sleep 2
      if pgrep -f "crond" > /dev/null 2>&1; then
        echo "[$now_human] crond restart OK" >> "$WATCHDOG_LOG"
        break
      fi
    fi
  done
fi

# Fire Slack alert. Best-effort -- if no token, log only.
if [ -z "$SLACK_BOT_TOKEN" ]; then
  echo "[$now_human] no SLACK_BOT_TOKEN, alert skipped" >> "$WATCHDOG_LOG"
  exit 0
fi

text="Phone cron silence ${age_min}m. Last log: ${last_name}. crond_alive=${crond_alive}. Watchdog tried restart. Open Termux on the phone if this persists."

curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-type: application/json" \
  --data "{\"channel\":\"$SLACK_CHANNEL_ALERTS\",\"text\":\"$text\"}" \
  >> "$WATCHDOG_LOG" 2>&1

exit 0
