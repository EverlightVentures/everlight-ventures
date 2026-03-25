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
SLACK_WH="https://hooks.slack.com/services/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"
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

    # Strategy
    scp -o ConnectTimeout=10 -r -i "$KEY" "$LOCAL_BOT/strategy/" "$BOT_VM:$REMOTE_BOT/strategy_new/" 2>/dev/null
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "cp -f $REMOTE_BOT/strategy_new/strategy/*.py $REMOTE_BOT/strategy/ 2>/dev/null; cp -f $REMOTE_BOT/strategy_new/*.py $REMOTE_BOT/strategy/ 2>/dev/null" 2>/dev/null
    DEPLOYED="$DEPLOYED strategy/"

    # AI prompts
    scp -o ConnectTimeout=10 -r -i "$KEY" "$LOCAL_BOT/ai/" "$BOT_VM:$REMOTE_BOT/ai_new/" 2>/dev/null
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "cp -f $REMOTE_BOT/ai_new/ai/*.py $REMOTE_BOT/ai/ 2>/dev/null; cp -f $REMOTE_BOT/ai_new/*.py $REMOTE_BOT/ai/ 2>/dev/null" 2>/dev/null
    DEPLOYED="$DEPLOYED ai/"

    # Alerts (SMS + Slack)
    scp -o ConnectTimeout=10 -r -i "$KEY" "$LOCAL_BOT/alerts/" "$BOT_VM:$REMOTE_BOT/alerts_new/" 2>/dev/null
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "cp -f $REMOTE_BOT/alerts_new/alerts/*.py $REMOTE_BOT/alerts/ 2>/dev/null; cp -f $REMOTE_BOT/alerts_new/*.py $REMOTE_BOT/alerts/ 2>/dev/null" 2>/dev/null
    DEPLOYED="$DEPLOYED alerts/"

    # Dashboard
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_BOT/dashboard.py" "$BOT_VM:$REMOTE_BOT/dashboard.py" 2>/dev/null
    DEPLOYED="$DEPLOYED dashboard.py"

    # Data module (candles, etc)
    scp -o ConnectTimeout=10 -r -i "$KEY" "$LOCAL_BOT/data/" "$BOT_VM:$REMOTE_BOT/data_new/" 2>/dev/null
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "cp -f $REMOTE_BOT/data_new/data/*.py $REMOTE_BOT/data/ 2>/dev/null; cp -f $REMOTE_BOT/data_new/*.py $REMOTE_BOT/data/ 2>/dev/null" 2>/dev/null
    DEPLOYED="$DEPLOYED data/"

    # Market module (score_modifiers, etc)
    scp -o ConnectTimeout=10 -r -i "$KEY" "$LOCAL_BOT/market/" "$BOT_VM:$REMOTE_BOT/market_new/" 2>/dev/null
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "cp -f $REMOTE_BOT/market_new/market/*.py $REMOTE_BOT/market/ 2>/dev/null; cp -f $REMOTE_BOT/market_new/*.py $REMOTE_BOT/market/ 2>/dev/null" 2>/dev/null
    DEPLOYED="$DEPLOYED market/"

    # Restart bot + dashboard
    ssh -o ConnectTimeout=10 -i "$KEY" "$BOT_VM" "sudo systemctl restart xlm-bot.service" 2>/dev/null
    DEPLOYED="$DEPLOYED [restarted]"

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

case "$MODE" in
    bot) deploy_bot ;;
    scripts) deploy_scripts ;;
    config) deploy_config ;;
    watchdog) deploy_scripts; install_watchdog_cron ;;
    all) deploy_bot; deploy_scripts; install_watchdog_cron ;;
esac

# Save hash to skip unchanged deploys
echo "$current_hash" > "$DEPLOY_HASH_FILE"

# Slack notification
curl -s -X POST "$SLACK_WH" -H "Content-type: application/json" \
    -d "{\"text\": \"[DEPLOY] Code pushed to Oracle. $DEPLOYED\"}" 2>/dev/null

log "Deploy complete: $MODE"
