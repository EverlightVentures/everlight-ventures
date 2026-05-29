#!/bin/bash
# Auto-deploy bot changes to Oracle production
# Syncs local xlm_bot code to Oracle Micro (163.192.19.196)
# and scripts/configs to Oracle E5 (163.192.19.196)
#
# Usage:
#   bash deploy_to_oracle.sh          # deploy everything
#   bash deploy_to_oracle.sh bot      # bot code only
#   bash deploy_to_oracle.sh scripts  # scripts only
#   bash deploy_to_oracle.sh config   # config.yaml only
#
# Cron: runs every 10 min to catch any uncommitted changes
# */10 * * * * bash /path/to/deploy_to_oracle.sh >> _logs/deploy.log 2>&1

# --- hostname-addressed config (sources the mesh keystone) -------------------
# Rewritten 2026-05-14: was hardcoded to the dead 163.192.19.196 E5 + phone-only
# /mnt/sdcard paths + a committed Slack token. Now sources hive_hosts.env so it
# runs from ANY device (phone, PC, the box itself) and survives a failover --
# change HIVE_PROD_HOST in hive_hosts.env and this script follows automatically.
MESH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/mesh" 2>/dev/null && pwd)"
[ -f "$MESH_DIR/hive_hosts.env" ] || MESH_DIR="/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/mesh"
# shellcheck disable=SC1091
source "$MESH_DIR/hive_hosts.env"

KEY="$HIVE_SSH_KEY"                          # unified mesh key (github_deploy)
BOT_KEY="$HIVE_BOT_SSH_KEY"                  # Oracle Micro key (oracle_key.pem)
BOT_VM="${HIVE_BOT_USER}@${HIVE_BOT_HOST}"   # xlm-bot Micro -- verified LIVE 2026-05-14
BOT_PORT="$HIVE_BOT_SSH_PORT"
E5_VM="${HIVE_PROD_USER}@${HIVE_PROD_HOST}"  # new Ampere 4/24 hive box (replaces dead .250)
E5_PORT="$HIVE_PROD_SSH_PORT"
LOCAL_BOT="${HIVE_LOCAL_WS}/06_DEVELOPMENT/xlm_bot"
REMOTE_BOT="${HIVE_BOT_HOME}/xlm-bot"
WS="$HIVE_LOCAL_WS"                          # workspace root on whatever device runs this
LOG="${HIVE_LOCAL_WS}/_logs/deploy_oracle.log"
SLACK_BOT_TOKEN="${SLACK_BOT_TOKEN:-}"       # source from env/.env -- never commit the token
SLACK_DEPLOY_CH="C0AN4GSTMT5"                # #deploy-log
DEPLOY_HASH_FILE="/tmp/last_deploy_hash"

# NOTE(mesh 2026-05-14): deploy_bot works from any device now ($LOCAL_BOT is
# resolved). The deploy_scripts / deploy_django / etc. functions still carry
# old /mnt/sdcard absolute paths + no -P port flag -- they no-op safely on the
# PC but need their paths swapped to "$WS/..." and a -P "$E5_PORT" added once
# the new box's real SSH coordinates are confirmed. Tracked as a mesh task.

ts() { date '+%Y-%m-%d %H:%M:%S PT'; }
log() { echo "[$(ts)] $1" >> "$LOG"; echo "[$(ts)] $1"; }

# Fast reachability gate. e5-mother is tailnet-only; when the tailnet is down it
# does not resolve, so every E5-targeted scp/ssh would burn ConnectTimeout=10
# sequentially across dozens of calls (the "deploy hang"). Probe once, skip the
# whole E5 block fast if it's down. Bot deploys (Oracle Micro) are unaffected.
e5_up() {
    getent hosts "$HIVE_PROD_HOST" >/dev/null 2>&1 || \
      [[ "$HIVE_PROD_HOST" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
    ssh -o ConnectTimeout=6 -o BatchMode=yes -i "$KEY" -p "$E5_PORT" "$E5_VM" true 2>/dev/null
}

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
    for f in unified_scorer.py risk_gate.py feature_store.py trade_reviewer.py market_intel_service.py state_store.py stop_watcher.py house_money.py recovery.py live_ws.py export_metrics.py push_metrics_supabase.py perplexity_poller.py; do
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
    if ! e5_up; then log "SKIP deploy_scripts: e5-mother ($HIVE_PROD_HOST) unreachable -- cron will retry"; return 0; fi
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
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/broker_outreach_sdr.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/broker_gmail_monitor.py \
        "$E5_VM:/home/opc/" 2>/dev/null

    # AI Consulting prospect scraper (with enrichment)
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "mkdir -p /home/opc/ai_consulting" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/AI_Consulting/pipeline/prospect_scraper.py \
        "$E5_VM:/home/opc/ai_consulting/" 2>/dev/null

    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/gdocs_bridge.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/report_template.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/hive_logger.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/hive_tags.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/HIVE_LOGGER_API.md \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/n8n_replacements.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/resend_budget.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/branded_mailer.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/resend_guard.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/branded_slack.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/branded_calendar.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/branded_sms.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/imap_fetch.py \
        "$E5_VM:/home/opc/content_tools/" 2>/dev/null

    # Hive Logger standalone scripts (live at 01_Scripts/ root)
    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/hive_3format.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/regenerate_index.py \
        "$E5_VM:/home/opc/" 2>/dev/null

    # Photo guard pair (claude-safe wrapper + prep script). Cloud crons that
    # feed photo paths to claude must invoke claude-safe instead of claude
    # to avoid glibc malloc.c:4512 assertion crashes under image-decode load.
    # Pillow must be installed on the cloud node (pip install --user Pillow).
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "mkdir -p /home/opc/photo_guard /home/opc/.local/bin" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/claude_photo_prep.py \
        "$E5_VM:/home/opc/photo_guard/" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" \
        /root/.local/bin/claude-safe \
        "$E5_VM:/home/opc/.local/bin/claude-safe" 2>/dev/null
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" \
        "chmod +x /home/opc/.local/bin/claude-safe /home/opc/photo_guard/claude_photo_prep.py 2>/dev/null; \
         sed -i 's|/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/claude_photo_prep.py|/home/opc/photo_guard/claude_photo_prep.py|g' /home/opc/.local/bin/claude-safe 2>/dev/null" 2>/dev/null

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

    # Hive Roundtable -- Solomon Vale's 5-phase persona orchestration engine
    # (constitutional Article III branch -- always keep e5-mother in sync)
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" \
        "mkdir -p /home/opc/06_DEVELOPMENT/everlight_os/hive_mind/roundtable/guests" 2>/dev/null
    scp -o ConnectTimeout=30 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/roundtable/__init__.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/roundtable/roundtable.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/roundtable/participant_resolver.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/roundtable/persona_builder.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/roundtable/smoke_test.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/roundtable/process_templates.yaml \
        "$E5_VM:/home/opc/06_DEVELOPMENT/everlight_os/hive_mind/roundtable/" 2>/dev/null

    # Persona dossiers (.claude/agents/) -- needed by Roundtable engine to load voices
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" \
        "mkdir -p /home/opc/.claude/agents" 2>/dev/null
    rsync -az --include='*.md' --exclude='*' \
        -e "ssh -o ConnectTimeout=10 -i $KEY" \
        /mnt/sdcard/AA_MY_DRIVE/.claude/agents/ \
        "$E5_VM:/home/opc/.claude/agents/" 2>/dev/null

    # Roundtable archives -- one-way push (08_BACKUPS gitignored, sync via deploy)
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" \
        "mkdir -p /home/opc/08_BACKUPS/roundtables" 2>/dev/null
    rsync -az -e "ssh -o ConnectTimeout=10 -i $KEY" \
        /mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/roundtables/ \
        "$E5_VM:/home/opc/08_BACKUPS/roundtables/" 2>/dev/null

    # Neuromorphic modules (NLP, brain policy, LLM gateway, pipeline API)
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "mkdir -p /home/opc/06_DEVELOPMENT/everlight_os/neuromorphic" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/neuromorphic/__init__.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/neuromorphic/nlp_engine.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/neuromorphic/brain_policy.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/neuromorphic/pipeline_api.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/neuromorphic/llm_gateway.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/neuromorphic/ml_models.py \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/neuromorphic/deal_state_machine.py \
        "$E5_VM:/home/opc/06_DEVELOPMENT/everlight_os/neuromorphic/" 2>/dev/null

    # Flip OS retail arbitrage pipeline
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "mkdir -p /home/opc/flip_os" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/flip_os/__init__.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/flip_os/penny_scraper.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/flip_os/demand_scorer.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/flip_os/daily_brief.py \
        /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/flip_os/run_pipeline.py \
        "$E5_VM:/home/opc/flip_os/" 2>/dev/null

    # Restart voice handler
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "sudo systemctl restart hive-voice" 2>/dev/null

    # CRITICAL: Fix phone paths in deployed scripts
    # Scripts are written with /mnt/sdcard/AA_MY_DRIVE (phone dev env)
    # but Oracle uses /home/opc as the base directory
    log "Fixing phone paths in Oracle scripts..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "
        for f in /home/opc/*.py /home/opc/ai_consulting/*.py /home/opc/broker/*.py /home/opc/content_tools/*.py /home/opc/flip_os/*.py; do
            [ -f \"\$f\" ] && sed -i 's|/mnt/sdcard/AA_MY_DRIVE|/home/opc|g' \"\$f\" 2>/dev/null
        done
        # Also fix Django app (excluding migrations)
        find /home/opc/hive_django -name '*.py' -not -path '*/migrations/*' -not -path '*__pycache__*' -exec grep -l '/mnt/sdcard/AA_MY_DRIVE' {} \; 2>/dev/null | while read f; do
            sed -i 's|/mnt/sdcard/AA_MY_DRIVE|/home/opc|g' \"\$f\" 2>/dev/null
        done
    " 2>/dev/null
    log "Phone paths fixed on Oracle"

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
    if ! e5_up; then log "SKIP install_watchdog_cron: e5-mother ($HIVE_PROD_HOST) unreachable"; return 0; fi
    log "Installing watchdog cron on Oracle E5..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "
        (crontab -l 2>/dev/null | grep -v hive_watchdog; echo '*/2 * * * * /usr/bin/python3 /home/opc/hive_watchdog.py >> /tmp/hive_watchdog.log 2>&1') | crontab -
    " 2>/dev/null
    log "Watchdog cron installed (*/2 * * * *)"
}

# Install broker execution crons on Oracle (idempotent, uses markers)
install_broker_crons() {
    if ! e5_up; then log "SKIP install_broker_crons: e5-mother ($HIVE_PROD_HOST) unreachable"; return 0; fi
    log "Installing broker execution crons on Oracle E5..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" '
        # Remove everything between BEGIN/END BROKER markers, then re-insert
        crontab -l 2>/dev/null | sed "/^# --- BEGIN BROKER CRONS/,/^# --- END BROKER CRONS/d" | {
            cat
            echo "# --- BEGIN BROKER CRONS (managed by deploy script) ---"
            echo "0 */2 * * * cd /home/opc && source .env && python3 broker_daily_orchestrator.py replies >> /tmp/broker_replies.log 2>&1"
            echo "0 17,0 * * * cd /home/opc && source .env && python3 broker_daily_orchestrator.py outreach >> /tmp/broker_outreach.log 2>&1"
            echo "15 * * * * cd /home/opc && python3 hive_deal_orchestrator.py --pipeline broker >> /tmp/hive_orchestrator_broker.log 2>&1"
            echo "# --- END BROKER CRONS ---"
        } | crontab -
    ' 2>/dev/null
    log "Broker crons installed (marker-based, no duplicates)"
}

# Deploy Computer Use container via Podman
deploy_computer_use() {
    if ! e5_up; then log "SKIP deploy_computer_use: e5-mother ($HIVE_PROD_HOST) unreachable"; return 0; fi
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

# Deploy Stark AI voice command center
deploy_stark() {
    if ! e5_up; then log "SKIP deploy_stark: e5-mother ($HIVE_PROD_HOST) unreachable -- cron will retry"; return 0; fi
    log "Deploying Stark AI to Oracle E5..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "mkdir -p /home/opc/stark-ai" 2>/dev/null
    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/stark_ai/{server.py,config.py,auth.py,voice.py,commands.py,__init__.py,requirements.txt} \
        "$E5_VM:/home/opc/stark-ai/" 2>/dev/null

    # Install service if not present
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "
        if [ ! -f /etc/systemd/system/stark-ai.service ]; then
            sudo cp /home/opc/stark-ai/stark-ai.service /etc/systemd/system/
            sudo systemctl daemon-reload
            sudo systemctl enable stark-ai
        fi
        sudo systemctl restart stark-ai
    " 2>/dev/null

    # Copy service file for future updates
    scp -o ConnectTimeout=10 -i "$KEY" \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/stark_ai/stark-ai.service \
        "$E5_VM:/home/opc/stark-ai/" 2>/dev/null

    DEPLOYED="$DEPLOYED [stark-ai]"
    log "Stark AI deployed to E5"
}

# Deploy Polymarket Live Trader (full package) via Podman + systemd
deploy_polymarket() {
    if ! e5_up; then log "SKIP deploy_polymarket: e5-mother ($HIVE_PROD_HOST) unreachable"; return 0; fi
    log "Deploying Polymarket Live Trader on Oracle E5 via Podman..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "mkdir -p /home/opc/polymarket_agent /home/opc/secrets" 2>/dev/null

    # Rsync the WHOLE package (execution/ dataflows/ agents/ + requirements + compose
    # + Dockerfile + systemd). Exclude local-only state + venv + tests.
    rsync -az --delete -e "ssh -o ConnectTimeout=10 -i $KEY" \
        --exclude '.venv' --exclude '__pycache__' --exclude 'data' \
        --exclude 'logs' --exclude '*.pyc' \
        /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/polymarket_agent/ \
        "$E5_VM:/home/opc/polymarket_agent/" 2>/dev/null

    # Wallet key -> host secrets dir (chmod 600 on ext4). The key is gitignored
    # and NEVER baked into the image; the compose mounts it read-only into /secrets.
    if [ -f /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.key ]; then
        scp -o ConnectTimeout=10 -i "$KEY" \
            /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.{key,addr} \
            "$E5_VM:/home/opc/secrets/" 2>/dev/null
        ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" \
            "chmod 600 /home/opc/secrets/polymarket_wallet.key /home/opc/secrets/polymarket_wallet.addr" 2>/dev/null
    fi

    # Build + bring up (agent + rsshub sidecar), install systemd units + weekly timer.
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "
        cd /home/opc/polymarket_agent &&
        podman-compose up -d --build &&
        sudo cp systemd/polymarket-agent.service /etc/systemd/system/ 2>/dev/null;
        sudo cp systemd/polymarket-postmortem.service /etc/systemd/system/ 2>/dev/null;
        sudo cp systemd/polymarket-postmortem.timer /etc/systemd/system/ 2>/dev/null;
        sudo systemctl daemon-reload 2>/dev/null;
        sudo systemctl enable --now polymarket-postmortem.timer 2>/dev/null;
        echo deployed
    " 2>/dev/null
    log "Polymarket Live Trader deployed (paper mode; LIVE_TRADING=false until funded + calibrated)"
}

# Deploy Django hive_dashboard to Oracle E5
deploy_django() {
    if ! e5_up; then log "SKIP deploy_django: e5-mother ($HIVE_PROD_HOST) unreachable -- cron will retry"; return 0; fi
    log "Deploying Django hive_dashboard to Oracle E5..."
    LOCAL_DJANGO="/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"
    REMOTE_DJANGO="/home/opc/hive_django"

    # Sync all Django apps
    for app in hive payments funnel broker_ops taskboard blackjack rewards business_os flip_os hive_dashboard; do
        rsync -az --delete -e "ssh -o ConnectTimeout=10 -i $KEY" \
            "$LOCAL_DJANGO/$app/" "$E5_VM:$REMOTE_DJANGO/$app/" 2>/dev/null
    done

    # Sync templates
    rsync -az -e "ssh -o ConnectTimeout=10 -i $KEY" \
        "$LOCAL_DJANGO/staticfiles/" "$E5_VM:$REMOTE_DJANGO/staticfiles/" 2>/dev/null

    # Sync manage.py and start.sh
    scp -o ConnectTimeout=10 -i "$KEY" \
        "$LOCAL_DJANGO/manage.py" \
        "$LOCAL_DJANGO/start.sh" \
        "$E5_VM:$REMOTE_DJANGO/" 2>/dev/null

    # Restart Django
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" "sudo systemctl restart hive-django" 2>/dev/null

    DEPLOYED="$DEPLOYED [django]"
    log "Django deployed to E5"
}

# Install Flip OS daily pipeline cron on Oracle (idempotent, uses markers)
install_flip_crons() {
    if ! e5_up; then log "SKIP install_flip_crons: e5-mother ($HIVE_PROD_HOST) unreachable"; return 0; fi
    log "Installing Flip OS crons on Oracle E5..."
    ssh -o ConnectTimeout=10 -i "$KEY" "$E5_VM" '
        crontab -l 2>/dev/null | sed "/^# --- BEGIN FLIP OS CRONS/,/^# --- END FLIP OS CRONS/d" | {
            cat
            echo "# --- BEGIN FLIP OS CRONS (managed by deploy script) ---"
            echo "0 12 * * * cd /home/opc/flip_os && source /home/opc/.env && python3 run_pipeline.py >> /tmp/flip_os.log 2>&1"
            echo "# --- END FLIP OS CRONS ---"
        } | crontab -
    ' 2>/dev/null
    log "Flip OS cron installed (marker-based, no duplicates)"
}

case "$MODE" in
    bot) deploy_bot ;;
    scripts) deploy_scripts ;;
    config) deploy_config ;;
    django) deploy_django ;;
    watchdog) deploy_scripts; install_watchdog_cron ;;
    broker-crons) install_broker_crons ;;
    flip-crons) install_flip_crons ;;
    computer-use) deploy_computer_use ;;
    polymarket) deploy_polymarket ;;
    stark) deploy_stark ;;
    all) deploy_bot; deploy_scripts; deploy_django; deploy_stark; install_watchdog_cron; install_broker_crons; install_flip_crons ;;
    full) deploy_bot; deploy_scripts; deploy_django; deploy_stark; install_watchdog_cron; install_broker_crons; install_flip_crons; deploy_computer_use; deploy_polymarket ;;
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

# Log deploy to changelog (dashboard API)
log_changelog() {
    curl -s -X POST "http://127.0.0.1:8502/api/changelog/add" \
        -H "Content-type: application/json" \
        -d "{\"category\": \"deploy\", \"summary\": \"Deploy: $MODE -- $DEPLOYED\", \"details\": \"Auto-logged by deploy_to_oracle.sh\", \"files_changed\": [\"$DEPLOYED\"]}" 2>/dev/null
    # Also append locally in case API is down
    CHANGELOG="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/xlm_bot/logs/changelog.jsonl"
    PT_TIME=$(TZ=America/Los_Angeles date '+%Y-%m-%dT%H:%M:%S%z')
    PT_DATE=$(TZ=America/Los_Angeles date '+%Y-%m-%d')
    PT_12HR=$(TZ=America/Los_Angeles date '+%-I:%M %p')
    echo "{\"timestamp\": \"$PT_TIME\", \"date\": \"$PT_DATE\", \"time\": \"$PT_12HR\", \"category\": \"deploy\", \"summary\": \"Deploy: $MODE -- $DEPLOYED\", \"details\": \"Auto-logged by deploy_to_oracle.sh\", \"files_changed\": [\"$DEPLOYED\"]}" >> "$CHANGELOG" 2>/dev/null
}
log_changelog

# Log deploy to Supabase hive_master_log (master ledger)
log_supabase() {
    SUPA_URL="https://jdqqmsmwmbsnlnstyavl.supabase.co"
    SUPA_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"
    PT_TIME=$(TZ=America/Los_Angeles date '+%Y-%m-%dT%H:%M:%S%z')
    curl -s -X POST "$SUPA_URL/rest/v1/hive_master_log" \
        -H "Content-Type: application/json" \
        -H "apikey: $SUPA_KEY" \
        -H "Authorization: Bearer $SUPA_KEY" \
        -H "Prefer: return=minimal" \
        -d "[{\"source\":\"deploy_script\",\"category\":\"deploy\",\"action\":\"Deploy: $MODE\",\"details\":\"$DEPLOYED\",\"system\":\"infrastructure\",\"status\":\"completed\"}]" 2>/dev/null
}
log_supabase

log "Deploy complete: $MODE"
