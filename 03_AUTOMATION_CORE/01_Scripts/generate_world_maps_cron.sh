#!/usr/bin/env bash
# ============================================================
# Alley Kingz WORLD-MAP daily batch (free Leonardo tier ~10-15 imgs/day).
# Idempotent: skips existing, grinds the next missing maps until all 400 done
# (+ the 6 new city music tracks on the first runs). Wired to phone crontab.
#   Progress + ETA: ~12 maps/day -> ~34 days for the full 400.
# ============================================================
set -uo pipefail
ROOT=/mnt/sdcard/AA_MY_DRIVE
ENVF=$ROOT/03_AUTOMATION_CORE/03_Credentials/.env
export ELEVENLABS_API_KEY=$(grep -m1 '^ELEVENLABS_API_KEY=' "$ENVF" 2>/dev/null | cut -d= -f2- | tr -d ' "\r')
export LEONARDO_API_KEY=$(grep -m1 '^LEONARDO_API_KEY=' "$ENVF" 2>/dev/null | cut -d= -f2- | tr -d ' "\r')
cd "$ROOT/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/art" || exit 1
LOG=$ROOT/_logs/ak_worldmaps_cron.log
mkdir -p "$ROOT/_logs"
echo "=== $(date) AK world-map daily batch ===" >> "$LOG"
python3 generate_world_maps.py --limit 12 >> "$LOG" 2>&1
DONE=$(find ../game/assets/maps -name '*.png' 2>/dev/null | wc -l)
echo "  progress: ${DONE}/400 maps generated" >> "$LOG"
# When the world is fully painted, retire the cron so it stops hitting the API.
if [ "$DONE" -ge 400 ]; then
  echo "  ALL 400 MAPS DONE -- removing the daily cron." >> "$LOG"
  crontab -l 2>/dev/null | grep -v 'generate_world_maps_cron.sh' | crontab -
fi
