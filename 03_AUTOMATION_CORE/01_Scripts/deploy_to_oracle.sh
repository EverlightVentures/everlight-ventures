#!/bin/bash
# Auto-deploy bot changes to Oracle production
# Syncs local xlm_bot code to Oracle Micro (163.192.19.196)
# and scripts/configs to Oracle E5 (129.159.38.250)
#
# Usage:
#   bash deploy_to_oracle.sh          # deploy everything
#   bash deploy_to_oracle.sh bot      # bot code only
#   bash deploy_to_oracle.sh scripts  # scripts only
#   bash deploy_to_oracle.sh config   # config.yaml only
#
# Cron: runs every 10 min to catch any uncommitted changes
# */10 * * * * bash /path/to/deploy_to_oracle.sh >> _logs/deploy.log 2>&1

KEY="/root/.ssh/oracle_key.pem"
# Everything consolidated on E5 now (2026-03-24). Old Micro IP dead.
BOT_VM="opc@129.159.38.250"
E5_VM="opc@129.159.38.250"
LOCAL_BOT="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/xlm_bot"
REMOTE_BOT="/home/opc/xlm-bot"
LOG="/mnt/sdcard/AA_MY_DRIVE/_logs/deploy_oracle.log"
SLACK_WH="https://hooks.slack.com/services/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"  # dead
SLACK_BOT_TOKEN="xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy"
SLACK_DEPLOY_CH="C0AN4GSTMT5"  # #deploy-log
DEPLOY_HASH_FILE="/tmp/last_deploy_hash"

ts() { date '+%Y-%m-%d %H:%M:%S PT'; }
log() { echo "[$(ts)] $1" >> "$LOG"; echo "[$(ts)] $1"; }

# Check if files actually changed since last deploy
current_hash=$(find "$LOCAL_BOT" -name "*.py" -o -name "*.yaml" | sort | xargs md5sum 2>/dev/null | md5sum | cut -d' ' -f1)
last_hash=$(cat "$DEPLOY_HASH_FILE" 2>/dev/null || echo "none")

if [ "$current_hash" = "$last_hash" ] && [ -z "$1" ]; then
    # No changes, skip deploy
    exit 0
fi

MODE="${1:-all}"
DEPLOYED=""

# Deploy bot code to Oracle Micro
deploy_bot() {
    log "Deploying bot code to Oracle Micro..."

    # Config
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT/config.yaml" "$BOT_VM:$REMOTE_BOT/config.yaml" 2>/dev/null
    DEPLOYED="$DEPLOYED config"

    # Main
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT/main.py" "$BOT_VM:$REMOTE_BOT/main.py" 2>/dev/null
    DEPLOYED="$DEPLOYED main.py"

    # Strategy -- rsync all .py files directly (fixes nested path bug)
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "mkdir -p $REMOTE_BOT/strategy" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT"/strategy/*.py "$BOT_VM:$REMOTE_BOT/strategy/" 2>/dev/null
    DEPLOYED="$DEPLOYED strategy/"

    # AI prompts
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "mkdir -p $REMOTE_BOT/ai" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT"/ai/*.py "$BOT_VM:$REMOTE_BOT/ai/" 2>/dev/null
    DEPLOYED="$DEPLOYED ai/"

    # Alerts (SMS + Slack)
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "mkdir -p $REMOTE_BOT/alerts" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT"/alerts/*.py "$BOT_VM:$REMOTE_BOT/alerts/" 2>/dev/null
    DEPLOYED="$DEPLOYED alerts/"

    # Dashboard
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT/dashboard.py" "$BOT_VM:$REMOTE_BOT/dashboard.py" 2>/dev/null
    DEPLOYED="$DEPLOYED dashboard.py"

    # Data module (candles, etc)
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "mkdir -p $REMOTE_BOT/data" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT"/data/*.py "$BOT_VM:$REMOTE_BOT/data/" 2>/dev/null
    DEPLOYED="$DEPLOYED data/"

    # Market module (score_modifiers, etc)
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "mkdir -p $REMOTE_BOT/market" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT"/market/*.py "$BOT_VM:$REMOTE_BOT/market/" 2>/dev/null
    DEPLOYED="$DEPLOYED market/"

    # Root-level modules (unified_scorer, risk_gate, etc)
    for f in unified_scorer.py risk_gate.py feature_store.py trade_reviewer.py market_intel_service.py state_store.py stop_watcher.py house_money.py recovery.py live_ws.py export_metrics.py push_metrics_supabase.py; do
        [ -f "$LOCAL_BOT/$f" ] && scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT/$f" "$BOT_VM:$REMOTE_BOT/$f" 2>/dev/null
    done
    DEPLOYED="$DEPLOYED root-modules"

    # Dashboard React (API + components)
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT/dashboard_react/api.py" "$BOT_VM:$REMOTE_BOT/dashboard_react/api.py" 2>/dev/null
    scp -o ConnectTimeout=10 -r -i "$KEY" "$LOCAL_BOT/dashboard_react/src/" "$BOT_VM:$REMOTE_BOT/dashboard_react/src_new/" 2>/dev/null
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "cp -rf $REMOTE_BOT/dashboard_react/src_new/* $REMOTE_BOT/dashboard_react/src/ 2>/dev/null" 2>/dev/null
    DEPLOYED="$DEPLOYED dashboard_react/"

    # Risk module
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "mkdir -p $REMOTE_BOT/risk" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT"/risk/*.py "$BOT_VM:$REMOTE_BOT/risk/" 2>/dev/null
    DEPLOYED="$DEPLOYED risk/"

    # Indicators module
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "mkdir -p $REMOTE_BOT/indicators" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT"/indicators/*.py "$BOT_VM:$REMOTE_BOT/indicators/" 2>/dev/null
    DEPLOYED="$DEPLOYED indicators/"

    # Structure module
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "mkdir -p $REMOTE_BOT/structure" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT"/structure/*.py "$BOT_VM:$REMOTE_BOT/structure/" 2>/dev/null
    DEPLOYED="$DEPLOYED structure/"

    # Execution module
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "mkdir -p $REMOTE_BOT/execution" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT"/execution/*.py "$BOT_VM:$REMOTE_BOT/execution/" 2>/dev/null
    DEPLOYED="$DEPLOYED execution/"

    # Timing module
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "mkdir -p $REMOTE_BOT/timing" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT"/timing/*.py "$BOT_VM:$REMOTE_BOT/timing/" 2>/dev/null
    DEPLOYED="$DEPLOYED timing/"

    # Restart bot + dashboard
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "sudo systemctl restart xlm-bot.service" 2>/dev/null
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "sudo systemctl restart xlm-dash-react.service" 2>/dev/null
    DEPLOYED="$DEPLOYED [restarted bot+dashboard]"

    log "Bot deployed: $DEPLOYED"
}

# Deploy scripts to Oracle E5
deploy_scripts() {
    log "Deploying scripts to Oracle E5..."

    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ceo_daily_brief.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/hourly_status_pulse.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/hive_health_monitor.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/hive_voice_handler.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/broker_daily_orchestrator.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/wholesale_hive_pipeline.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/hive_deal_orchestrator.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/hive_god_mode.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/hive_watchdog.py \
        "$E5_VM:/home/opc/" 2>/dev/null

    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/gdocs_bridge.py \
        "$E5_VM:/home/opc/content_tools/" 2>/dev/null

    # Broker enrichment modules
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "mkdir -p /home/opc/broker" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/broker/attom_enrichment.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/broker/contact_enrichment.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/broker/__init__.py \
        "$E5_VM:/home/opc/broker/" 2>/dev/null

    # Hive firmware + employee directory (large files -- always keep Oracle in sync)
    scp -o ConnectTimeout=30 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/TEAM_FIRMWARE.md \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/EMPLOYEE_DIRECTORY.md \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/agent_metrics.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/messaging.py \
        "$E5_VM:/home/opc/06_DEVELOPMENT/everlight_os/hive_mind/" 2>/dev/null

    # Restart voice handler
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "sudo systemctl restart hive-voice" 2>/dev/null

    log "Scripts deployed to E5"
}

# Deploy config only (fastest, no restart needed -- bot reads fresh each cycle)
deploy_config() {
    log "Deploying config.yaml only..."
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT/config.yaml" "$BOT_VM:$REMOTE_BOT/config.yaml" 2>/dev/null
    log "Config deployed (no restart needed -- bot reads fresh)"
}

# Install watchdog cron on Oracle (idempotent)
install_watchdog_cron() {
    log "Installing watchdog cron on Oracle E5..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "
        (crontab -l 2>/dev/null | grep -v hive_watchdog; echo '*/2 * * * * /usr/bin/python3 /home/opc/hive_watchdog.py >> /tmp/hive_watchdog.log 2>&1') | crontab -
    " 2>/dev/null
    log "Watchdog cron installed (*/2 * * * *)"
}

# Install broker execution crons on Oracle (idempotent)
install_broker_crons() {
    log "Installing broker execution crons on Oracle E5..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" '
        EXISTING=$(crontab -l 2>/dev/null | grep -v "broker_daily_orchestrator.py replies" | grep -v "broker_daily_orchestrator.py outreach" | grep -v "ceo_daily_brief.py")
        NEW_CRONS="# Broker reply check every 2 hours
0 */2 * * * cd /home/opc && source .env && python3 broker_daily_orchestrator.py replies >> /tmp/broker_replies.log 2>&1
# Broker outreach sends 2x/day (10AM + 4PM PT = 17:00 + 00:00 UTC)
0 17,0 * * * cd /home/opc && source .env && python3 broker_daily_orchestrator.py outreach >> /tmp/broker_outreach.log 2>&1
# CEO daily brief 7AM PT = 14:00 UTC
0 14 * * * cd /home/opc && source .env && python3 ceo_daily_brief.py >> /tmp/ceo_brief.log 2>&1"
        echo "$EXISTING
$NEW_CRONS" | crontab -
    ' 2>/dev/null
    log "Broker crons installed: replies (2h), outreach (2x/day), CEO brief (7AM PT)"
}

# Deploy Computer Use container via Podman
deploy_computer_use() {
    log "Deploying Computer Use container on Oracle E5 via Podman..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "mkdir -p /home/opc/computer_use" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/computer_use/{podman-compose.yml,Dockerfile,requirements.txt,entrypoint.sh,agent.py,server.py} \
        "$E5_VM:/home/opc/computer_use/" 2>/dev/null
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "
        cd /home/opc/computer_use && podman-compose up -d --build
    " 2>/dev/null
    log "Computer Use container deployed"
}

# Deploy Polymarket prediction agent via Podman
deploy_polymarket() {
    log "Deploying Polymarket agent on Oracle E5 via Podman..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "mkdir -p /home/opc/polymarket_agent" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/polymarket_agent/{podman-compose.yml,Dockerfile,main.py,config.yaml} \
        "$E5_VM:/home/opc/polymarket_agent/" 2>/dev/null
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "
        cd /home/opc/polymarket_agent && podman-compose up -d --build
    " 2>/dev/null
    log "Polymarket agent deployed"
}

case "$MODE" in
    bot) deploy_bot ;;
    scripts) deploy_scripts ;;
    config) deploy_config ;;
    watchdog) deploy_scripts; install_watchdog_cron ;;
    broker-crons) install_broker_crons ;;
    computer-use) deploy_computer_use ;;
    polymarket) deploy_polymarket ;;
    all) deploy_bot; deploy_scripts; install_watchdog_cron; install_broker_crons ;;
    full) deploy_bot; deploy_scripts; install_watchdog_cron; install_broker_crons; deploy_computer_use; deploy_polymarket ;;
esac

# Save hash to skip unchanged deploys
echo "$current_hash" > "$DEPLOY_HASH_FILE"

# Slack notification via bot token (webhooks dead since 2026-03-23)
slack_notify() {
    curl -s -X POST "https://slack.com/api/chat.postMessage" \
        -H "Content-type: application/json" \
        -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
        -d "{\"channel\": \"$SLACK_DEPLOY_CH\", \"text\": \"[DEPLOY] Code pushed to Oracle. $DEPLOYED\"}" 2>/dev/null
}
slack_notify

log "Deploy complete: $MODE"
