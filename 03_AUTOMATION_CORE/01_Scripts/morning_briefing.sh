#!/bin/bash
#
# morning_briefing.sh -- Marquise's single-command morning startup.
#
# Run this at 7 AM PT Tuesday and Wednesday. Does:
#   1. Loads credentials
#   2. Re-scores all leads (Filter)
#   3. Rebuilds dial lists from latest data (with Justine compliance filter)
#   4. Prints today's dial sheet
#   5. Runs rex_sdr morning batch (sends what's eligible via Resend)
#   6. Reports state of pipeline + 3 URGENT actions
#
# Usage: bash morning_briefing.sh

set -e

WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
SCRIPTS="$WORKSPACE/03_AUTOMATION_CORE/01_Scripts"
WHOLESALE="$WORKSPACE/01_BUSINESSES/Everlight_Ventures/Wholesale"
AGENT="$WORKSPACE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"
LOG_DIR="$WORKSPACE/_logs/morning_briefings"
mkdir -p "$LOG_DIR"

echo "==============================================="
echo " EVERLIGHT VENTURES -- MORNING BRIEFING"
echo " $(TZ='America/Los_Angeles' date)"
echo "==============================================="
echo ""

# Step 0: Load creds
set -a
. "$WORKSPACE/03_AUTOMATION_CORE/03_Credentials/.env" 2>/dev/null || echo "WARN: creds not loaded"
set +a
test -n "$RESEND_API_KEY" && echo "[OK] RESEND_API_KEY loaded" || echo "[FAIL] RESEND_API_KEY missing"
test -n "$SLACK_BOT_TOKEN" && echo "[OK] SLACK_BOT_TOKEN loaded" || echo "[FAIL] SLACK_BOT_TOKEN missing"
echo ""

# Step 1: Score all leads
echo "--- STEP 1: Scoring leads (Filter Banks) ---"
python3 "$SCRIPTS/filter_score_leads.py" 2>&1 | grep -E "Total|Queue|band|TOP|EMAIL|PHONE" | head -20
echo ""

# Step 2: Build dial lists
echo "--- STEP 2: Building dial lists (Justine compliance enforced) ---"
python3 "$SCRIPTS/build_phone_dial_list.py" 2>&1 | head -10
echo ""

# Step 3: Print today's dial sheet
echo "--- STEP 3: Today's dial sheet ---"
python3 "$SCRIPTS/dial_prep.py" --limit 32 2>&1
echo ""

# Step 4: Reply check (Resend + Slack)
echo "--- STEP 4: Reply check (last 24h) ---"
echo "Resend dashboard: https://resend.com/emails"
echo "Slack #wholesale-deals: scroll for replies"
echo "(IMAP-direct check pending Gmail app password rotation)"
echo ""

# Step 5: Run rex_sdr morning batch
echo "--- STEP 5: Run rex_sdr morning batch ---"
echo "(If you want to skip, hit Ctrl+C now. Otherwise sending in 5s...)"
sleep 5 || true
cd "$AGENT"
TS=$(date +%Y%m%d_%H%M%S)
LOG="$LOG_DIR/rex_sdr_$TS.log"
timeout 240 python3 rex_sdr.py all > "$LOG" 2>&1 || true
echo "rex_sdr exit code: $?"
echo "Last 8 lines:"
tail -8 "$LOG"
echo "Full log: $LOG"
echo ""

# Step 6: Pipeline status + URGENT actions
echo "--- STEP 6: Pipeline status ---"
python3 -c "
import json
from pathlib import Path
db = json.loads(Path('$AGENT/leads_db.json').read_text())
from collections import Counter
status = Counter(l.get('status','?') for l in db)
queue = Counter(l.get('queue','?') for l in db)
print(f'  Total leads: {len(db)}')
print(f'  Status breakdown: {dict(status)}')
print(f'  Queue breakdown: {dict(queue)}')

# Hot leads (status=engaged or contacted with sequence_step>=2)
hot = [l for l in db if l.get('status') == 'engaged' or (l.get('status') == 'contacted' and l.get('sequence_step', 0) >= 2)]
print(f'  Hot/warming leads (engaged + step>=2): {len(hot)}')
"
echo ""

echo "--- 3 URGENT MARQUISE ACTIONS (still gating) ---"
echo "  1. Verify Oracle E5 reachability (Cloud Console)"
echo "     curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:2200/"
echo "  2. Rotate Gmail app password (5 min, runbook ready)"
echo "     File: 06_DEVELOPMENT/everlight_os/hive_mind/runbooks/gmail_app_password_rotation.md"
echo "  3. File GA + TX d/b/a (~\$300, 2-3 weeks parallel)"
echo "     File: 06_DEVELOPMENT/everlight_os/hive_mind/dba_filings.md"
echo ""

echo "==============================================="
echo " BRIEFING COMPLETE"
echo " Next: dial top of dial sheet + Hammer title calls 9-11 AM PT"
echo "==============================================="
