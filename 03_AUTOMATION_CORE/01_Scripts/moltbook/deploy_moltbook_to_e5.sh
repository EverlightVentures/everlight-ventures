#!/bin/bash
# ---------------------------------------------------------------------------
# Migrate the Lucrex moltbook engagement loop OFF the phone (SPOF) ONTO
# e5-mother (always-on ARM, tailnet). Fixes the gap where engagement dies
# whenever the phone sleeps (observed cron gap 2026-05-23 -> 05-24).
#
# Per [[reference_infrastructure_hierarchy]]: e5-mother is the always-on AI
# workload host. The phone stays SOT + control plane; mother becomes the
# 24/7 executor for moltbook (like xlm-bot lives on Oracle Micro).
#
# SAFE TO RE-RUN. No-ops with a clear message if mother is unreachable.
# Operator-triggered (not auto) so cron never installs itself unattended.
#
# Usage:
#   bash deploy_moltbook_to_e5.sh            # full migrate (rsync + symlink + crons + verify)
#   bash deploy_moltbook_to_e5.sh --check    # reachability + dry-run only, install nothing
# ---------------------------------------------------------------------------
set -uo pipefail

WS="/mnt/sdcard/AA_MY_DRIVE"
# e5-mother ssh target: prefer the tailnet alias, fall back to tailnet IP.
E5_HOST="${E5_HOST:-e5-mother}"
E5_IP="100.125.115.95"
REMOTE_WS="${REMOTE_WS:-/home/ubuntu/AA_MY_DRIVE}"   # mirror root on mother
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

say() { echo "[deploy-moltbook-e5] $*"; }

# --- 0. Resolve a reachable ssh target -------------------------------------
SSH_TGT=""
for tgt in "$E5_HOST" "$E5_IP"; do
  if timeout 8 ssh -o ConnectTimeout=6 -o BatchMode=yes "$tgt" "echo ok" >/dev/null 2>&1; then
    SSH_TGT="$tgt"; break
  fi
done
if [ -z "$SSH_TGT" ]; then
  say "e5-mother UNREACHABLE (tried $E5_HOST + $E5_IP)."
  say "Mother is down or tailscale is off on this device. Migration deferred."
  say "Re-run this script once 'ssh $E5_HOST' works. Nothing changed."
  exit 3
fi
say "reachable via: $SSH_TGT"

# --- 1. Paths to ship (engine + deps + keys + state) -----------------------
RSYNC_PATHS=(
  "03_AUTOMATION_CORE/01_Scripts/moltbook/"
  "03_AUTOMATION_CORE/01_Scripts/content_tools/"
  "03_AUTOMATION_CORE/01_Scripts/blinko_queue_drain.py"
  "_state/moltbook/"
)
SECRET_SRC="06_DEVELOPMENT/hivemind_saas/backend/.env"

if [ "$CHECK_ONLY" -eq 1 ]; then
  say "--check: would rsync ${#RSYNC_PATHS[@]} path groups + secrets to $SSH_TGT:$REMOTE_WS"
  ssh "$SSH_TGT" "python3 --version; test -d $REMOTE_WS && echo 'remote WS exists' || echo 'remote WS will be created'"
  say "--check done. No changes made."
  exit 0
fi

# --- 2. rsync the engine + state -------------------------------------------
say "rsyncing engine + state to $SSH_TGT:$REMOTE_WS ..."
for p in "${RSYNC_PATHS[@]}"; do
  ssh "$SSH_TGT" "mkdir -p $REMOTE_WS/$(dirname "$p")" 2>/dev/null
  rsync -az --delete-after -e "ssh -o ConnectTimeout=10" \
    "$WS/$p" "$SSH_TGT:$REMOTE_WS/$p" || { say "rsync failed on $p"; exit 4; }
done

# secrets: ship .env, lock perms
ssh "$SSH_TGT" "mkdir -p $REMOTE_WS/$(dirname "$SECRET_SRC")"
rsync -az -e ssh "$WS/$SECRET_SRC" "$SSH_TGT:$REMOTE_WS/$SECRET_SRC"
ssh "$SSH_TGT" "chmod 600 $REMOTE_WS/$SECRET_SRC"

# --- 3. Make hardcoded /mnt/sdcard/AA_MY_DRIVE paths resolve on mother ------
# The python scripts hardcode WORKSPACE=/mnt/sdcard/AA_MY_DRIVE. Symlink it to
# the mirror so absolute paths Just Work without editing every file.
say "symlinking /mnt/sdcard/AA_MY_DRIVE -> $REMOTE_WS on mother ..."
ssh "$SSH_TGT" "sudo mkdir -p /mnt/sdcard 2>/dev/null; sudo ln -sfn $REMOTE_WS /mnt/sdcard/AA_MY_DRIVE && echo 'symlink ok'"

# --- 4. Verify the engine runs there (dry-run, no posting) -----------------
say "remote dry-run (must show error:none) ..."
ssh "$SSH_TGT" "cd $REMOTE_WS && python3 03_AUTOMATION_CORE/01_Scripts/moltbook/lucrex_engage.py --once --dry-run 2>&1 | tail -5"

# --- 5. Install the crons on mother (idempotent) ---------------------------
say "installing moltbook crons on mother ..."
ssh "$SSH_TGT" "bash -s" <<REMOTE
set -e
TMP=\$(mktemp)
crontab -l 2>/dev/null | grep -v 'lucrex_engage.py\|blinko_queue_drain.py' > "\$TMP" || true
cat >> "\$TMP" <<CRON
# moltbook: Lucrex reactive engagement (every 3 min) -- migrated from phone 2026-05-24
*/3 * * * * cd $REMOTE_WS && /usr/bin/python3 $REMOTE_WS/03_AUTOMATION_CORE/01_Scripts/moltbook/lucrex_engage.py --once >> $REMOTE_WS/_logs/lucrex_engage_cron.log 2>&1
# moltbook: Lucrex knowledge-intake (every 12 min)
*/12 * * * * cd $REMOTE_WS && /usr/bin/python3 $REMOTE_WS/03_AUTOMATION_CORE/01_Scripts/moltbook/lucrex_engage.py --knowledge-tick >> $REMOTE_WS/_logs/moltbook/knowledge_tick.log 2>&1
# moltbook: Lucrex proactive networking (hourly :22)
22 * * * * cd $REMOTE_WS && /usr/bin/python3 $REMOTE_WS/03_AUTOMATION_CORE/01_Scripts/moltbook/lucrex_engage.py --proactive --max-posts 1 >> $REMOTE_WS/_logs/moltbook/proactive.log 2>&1
# moltbook: Lucrex original posts (broadcast, value-first) 2x/day -- 15:00 + 23:00 UTC = 7a/3p PT
0 15,23 * * * cd $REMOTE_WS && /usr/bin/python3 $REMOTE_WS/03_AUTOMATION_CORE/01_Scripts/moltbook/lucrex_engage.py --post --max-posts 1 >> $REMOTE_WS/_logs/moltbook/original_posts.log 2>&1
# blinko: offline-first queue drainer (every 17 min) -- local Blinko on mother
*/17 * * * * BLINKO_URL=http://127.0.0.1:1111 /usr/bin/python3 $REMOTE_WS/03_AUTOMATION_CORE/01_Scripts/blinko_queue_drain.py >> $REMOTE_WS/_logs/blinko_queue_drain.log 2>&1
CRON
crontab "\$TMP" && rm -f "\$TMP" && echo "mother crontab updated"
REMOTE

say "DONE. Engagement now runs on e5-mother 24/7."
say "NEXT: disable the phone moltbook crons to avoid double-posting:"
say "  crontab -l | grep -v 'lucrex_engage.py' | crontab -"
