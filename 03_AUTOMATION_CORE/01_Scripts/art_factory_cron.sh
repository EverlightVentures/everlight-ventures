#!/usr/bin/env bash
# ALLEY KINGZ -- UNIFIED ART FACTORY daily batch (free Leonardo ~10-15/day).
# THE standing auto-paint pipeline (operator law 2026-06-07): one prioritized
# drainer over ad-hoc queue -> cards -> maps, so the free cap is spent coherently
# instead of split across competing crons. Replaces generate_world_maps_cron.sh +
# generate_card_art_cron.sh. NEVER self-retires -- the queue can always grow when a
# new item ships with a placeholder; on an empty worklist it no-ops (no API calls).
set -uo pipefail
ROOT=/mnt/sdcard/AA_MY_DRIVE
ENVF=$ROOT/03_AUTOMATION_CORE/03_Credentials/.env
export LEONARDO_API_KEY=$(grep -m1 '^LEONARDO_API_KEY=' "$ENVF" 2>/dev/null | cut -d= -f2- | tr -d ' "\r')
export CF_AI_TOKEN=$(grep -m1 '^CF_AI_TOKEN=' "$ENVF" 2>/dev/null | cut -d= -f2- | tr -d ' "\r')
cd "$ROOT/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/art" || exit 1
LOG=$ROOT/_logs/ak_art_factory_cron.log; mkdir -p "$ROOT/_logs"
echo "=== $(date) AK unified art-factory batch ===" >> "$LOG"
python3 art_factory.py --limit 12 >> "$LOG" 2>&1
CARDS=$(find ../game/assets/cards -name '*.png' 2>/dev/null | wc -l)
MAPS=$(find ../game/assets/maps -name '*.png' 2>/dev/null | wc -l)
echo "  progress: cards ${CARDS}/106  maps ${MAPS}/400" >> "$LOG"
# auto-deploy freshly painted art to prod (idempotent; safe no-op if nothing changed)
bash "$ROOT/03_AUTOMATION_CORE/01_Scripts/deploy_to_oracle.sh" >> "$LOG" 2>&1 || true
# ALSO ship painted art to the LIVE game (alleykingz.online via CF Pages direct upload).
# Without this the art lands on disk but never reaches players (gap found 2026-06-09).
export CLOUDFLARE_ACCOUNT_ID=d06376317522c7451e390a9af44aebba
python3 "$ROOT/03_AUTOMATION_CORE/01_Scripts/deploy/cf_pages_direct_upload.py" \
  --dir "$ROOT/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game" \
  --project alley-kingz --branch main --exclude "assets/maps" >> "$LOG" 2>&1 || true
