#!/usr/bin/env bash
# Cron migration -- moves phone-side recurring jobs to ev-box.
# Per feedback_oracle_only_crons.md: recurring jobs belong on a 24/7 cloud box.
#
# Usage:
#   bash migrate_crons.sh             # interactive: shows diff, asks y/n
#   bash migrate_crons.sh --auto      # applies diff, posts to Slack
#   bash migrate_crons.sh --rollback  # restores from latest backup
set -euo pipefail

MODE="interactive"
[[ "${1:-}" == "--auto" ]] && MODE="auto"
[[ "${1:-}" == "--rollback" ]] && MODE="rollback"

WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
BACKUP_DIR="$WORKSPACE/_logs/cron_backups"
mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d_%H%M%S)
PHONE_BACKUP="$BACKUP_DIR/phone_crontab_${TS}.bak"
EVBOX_BACKUP="$BACKUP_DIR/evbox_crontab_${TS}.bak"

# ---------- rollback path ----------
if [[ "$MODE" == "rollback" ]]; then
  LATEST_PHONE=$(ls -t "$BACKUP_DIR"/phone_crontab_*.bak 2>/dev/null | head -1)
  LATEST_EVBOX=$(ls -t "$BACKUP_DIR"/evbox_crontab_*.bak 2>/dev/null | head -1)
  [[ -z "$LATEST_PHONE" ]] && { echo "No backup found in $BACKUP_DIR"; exit 1; }
  echo "Restoring phone crontab from: $LATEST_PHONE"
  crontab "$LATEST_PHONE"
  if [[ -n "$LATEST_EVBOX" ]]; then
    echo "Restoring ev-box crontab from: $LATEST_EVBOX"
    ssh ev-box "crontab -" < "$LATEST_EVBOX"
  fi
  echo "Rollback complete."
  exit 0
fi

# ---------- classification rules ----------
# Patterns matched against the COMMAND part of each crontab line.
# A line matches MIGRATE if it matches any MIGRATE pattern AND no STAY pattern.
declare -a MIGRATE_PATTERNS=(
  "inbound_watch"
  "gmail.*watcher"
  "resend.*reconcil"
  "true.*people.*search"
  "cuyahoga"
  "zillow"
  "wholesale_engine"
  "boomerang"
  "blinko.*ingest"
  "ceo_brief"
  "hive_pulse"
  "hive_3format"
  "publish.*report"
)
declare -a STAY_PHONE_PATTERNS=(
  "sdcard"
  "fastfetch"
  "organizer"
  "dedupe"
  "rclone.*proton"
)
declare -a STAY_E5_PATTERNS=(
  "xlm"
  "xpb"
  "xdr"
  "xws"
)

classify() {
  local cmd="$1"
  for p in "${STAY_E5_PATTERNS[@]}"; do
    [[ "$cmd" =~ $p ]] && { echo "ORACLE_E5"; return; }
  done
  for p in "${STAY_PHONE_PATTERNS[@]}"; do
    [[ "$cmd" =~ $p ]] && { echo "STAY_PHONE"; return; }
  done
  for p in "${MIGRATE_PATTERNS[@]}"; do
    [[ "$cmd" =~ $p ]] && { echo "MIGRATE"; return; }
  done
  echo "STAY_PHONE"  # default = leave alone
}

# ---------- read current state ----------
crontab -l > "$PHONE_BACKUP" 2>/dev/null || echo "" > "$PHONE_BACKUP"
ssh ev-box "crontab -l 2>/dev/null" > "$EVBOX_BACKUP" || echo "" > "$EVBOX_BACKUP"

# ---------- build new crontabs ----------
NEW_PHONE=$(mktemp)
NEW_EVBOX=$(mktemp)
DIFF_REPORT=$(mktemp)
echo "" > "$NEW_EVBOX"
echo "" > "$NEW_PHONE"
cat "$EVBOX_BACKUP" >> "$NEW_EVBOX"

mig=0; stay=0; e5=0
while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^# ]] && { echo "$line" >> "$NEW_PHONE"; continue; }
  cmd=$(echo "$line" | awk '{for(i=6;i<=NF;i++) printf "%s ", $i; print ""}')
  verdict=$(classify "$cmd")
  case "$verdict" in
    MIGRATE)
      # rewrite path: /mnt/sdcard/AA_MY_DRIVE -> /home/ubuntu/AA_MY_DRIVE
      ev_line=$(echo "$line" | sed 's|/mnt/sdcard/AA_MY_DRIVE|/home/ubuntu/AA_MY_DRIVE|g')
      echo "$ev_line" >> "$NEW_EVBOX"
      echo "MIGRATE  | $line" >> "$DIFF_REPORT"
      mig=$((mig+1))
      ;;
    STAY_PHONE)
      echo "$line" >> "$NEW_PHONE"
      echo "PHONE    | $line" >> "$DIFF_REPORT"
      stay=$((stay+1))
      ;;
    ORACLE_E5)
      echo "$line" >> "$NEW_PHONE"  # phone may have a control wrapper, keep it
      echo "E5_KEEP  | $line" >> "$DIFF_REPORT"
      e5=$((e5+1))
      ;;
  esac
done < "$PHONE_BACKUP"

# ---------- show diff ----------
echo ""
echo "==================================================================="
echo "  CRON MIGRATION DIFF -- $(date)"
echo "==================================================================="
echo "  MIGRATE to ev-box: $mig"
echo "  STAY on phone:     $stay"
echo "  E5 control wrap:   $e5"
echo "==================================================================="
column -t -s'|' "$DIFF_REPORT" | head -80
echo "==================================================================="
echo ""
echo "Backups:"
echo "  phone: $PHONE_BACKUP"
echo "  ev-box: $EVBOX_BACKUP"

# ---------- apply ----------
APPLY="no"
if [[ "$MODE" == "auto" ]]; then
  APPLY="yes"
else
  read -p "Apply this migration? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] && APPLY="yes"
fi

if [[ "$APPLY" == "yes" ]]; then
  echo "Applying..."
  crontab "$NEW_PHONE"
  ssh ev-box "crontab -" < "$NEW_EVBOX"
  echo "Done. Rollback any time with: bash migrate_crons.sh --rollback"
  if [[ "$MODE" == "auto" ]]; then
    python3 -c "
from content_tools.branded_slack import post_branded_slack
with open('$DIFF_REPORT') as f:
    diff = f.read()
post_branded_slack(channel='#deploy-log', category='ops',
                   title='Cron migration applied (auto)',
                   body=f'Migrated $mig | Phone $stay | E5 $e5\n\n```\n{diff[:2000]}\n```')
" 2>/dev/null || echo "  (slack post skipped)"
  fi
else
  echo "Aborted. No changes made."
fi

rm -f "$NEW_PHONE" "$NEW_EVBOX" "$DIFF_REPORT"
