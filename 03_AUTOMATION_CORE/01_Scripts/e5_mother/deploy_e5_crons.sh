#!/usr/bin/env bash
# deploy_e5_crons.sh -- install the DAILY wholesale crons on e5-mother (always-on, no Android
# doze), so scheduled runs stop silently missing on the phone. This IS the cron failover:
# short-interval crons stay on the phone, daily/scheduled crons run on e5.
#
# MUST be run from a TAILNET-CONNECTED context (a device on Tailscale, or the phone once the
# proot is on the tailnet). The proot today CANNOT reach e5 (tailnet no-route) -- see
# feedback_tailscale_e5_reach_FINAL. This script no-ops safely if e5 is unreachable.
set -uo pipefail
E5="${E5_HOST:-100.125.115.95}"        # tailnet IP; works from a tailnet runner
KEY="${E5_KEY:-/root/.ssh/github_deploy}"
USER_E5="${E5_USER:-ubuntu}"
REMOTE="/home/$USER_E5/AA_MY_DRIVE"
SSH="ssh -o ConnectTimeout=8 -o BatchMode=yes -i $KEY $USER_E5@$E5"

echo "[deploy_e5_crons] target $E5"
if ! $SSH true 2>/dev/null; then
  echo "[deploy_e5_crons] e5 unreachable from here -- run this from a tailnet-connected device."
  echo "  (proot is not on the tailnet; see feedback_tailscale_e5_reach_FINAL)"
  exit 0
fi
echo "[deploy_e5_crons] e5 reachable. syncing wholesale stack + installing daily crons..."

# 1. sync the scripts the daily crons need
rsync -az -e "$SSH" --relative \
  ./01_BUSINESSES/Everlight_Ventures/Wholesale/scripts/ \
  ./01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/ \
  ./03_AUTOMATION_CORE/01_Scripts/content_tools/ \
  "$USER_E5@$E5:$REMOTE/" 2>/dev/null || echo "  (rsync partial -- check paths)"

# 2. install the DAILY crons on e5 (idempotent: marker-fenced block)
$SSH "crontab -l 2>/dev/null | grep -v '# EV-DAILY-WHOLESALE' > /tmp/ec.txt || true
cat >> /tmp/ec.txt <<CRON
0 15 * * * cd $REMOTE && python3 03_AUTOMATION_CORE/01_Scripts/wholesale_hive_pipeline.py --stage scout qualify match pitch >> _logs/wholesale_hive_pipeline.log 2>&1  # EV-DAILY-WHOLESALE
0 16 * * * bash $REMOTE/03_AUTOMATION_CORE/01_Scripts/tn_deal_engine.sh >/dev/null 2>&1  # EV-DAILY-WHOLESALE
0 11 * * * cd $REMOTE && python3 01_BUSINESSES/Everlight_Ventures/Wholesale/scripts/daily_lead_pipeline.py >> _logs/daily_lead_pipeline.log 2>&1  # EV-DAILY-WHOLESALE
*/30 * * * * date -u +\%FT\%TZ > $REMOTE/_state/e5_cron_heartbeat.txt  # EV-DAILY-WHOLESALE
CRON
crontab /tmp/ec.txt && echo '  e5 crontab installed (EV-DAILY-WHOLESALE block)'"
echo "[deploy_e5_crons] done. Phone should DROP the same daily crons to avoid double-fire once e5 owns them."
