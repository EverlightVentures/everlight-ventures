#!/usr/bin/env bash
# Alley Kingz CARD ART daily batch (free Leonardo ~10-15/day). Paints the 106-card
# roster (58 new variants first) from card_art_manifest.json. Self-retires at 106.
set -uo pipefail
ROOT=/mnt/sdcard/AA_MY_DRIVE
ENVF=$ROOT/03_AUTOMATION_CORE/03_Credentials/.env
export LEONARDO_API_KEY=$(grep -m1 '^LEONARDO_API_KEY=' "$ENVF" 2>/dev/null | cut -d= -f2- | tr -d ' "\r')
cd "$ROOT/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/art" || exit 1
LOG=$ROOT/_logs/ak_cardart_cron.log; mkdir -p "$ROOT/_logs"
echo "=== $(date) AK card-art daily batch ===" >> "$LOG"
python3 generate_card_art.py --limit 12 >> "$LOG" 2>&1
DONE=$(find ../game/assets/cards -name '*.png' 2>/dev/null | wc -l)
echo "  progress: ${DONE}/106 cards" >> "$LOG"
if [ "$DONE" -ge 106 ]; then
  echo "  ALL 106 CARDS DONE -- removing cron." >> "$LOG"
  crontab -l 2>/dev/null | grep -v 'generate_card_art_cron.sh' | crontab -
fi
