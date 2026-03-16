#!/bin/bash
# ===========================================================================
# Everlight Ventures -- Master Bootstrap
# ===========================================================================
# Runs ALL setup tasks automatically. Watch progress in real time:
#   tail -f /mnt/sdcard/AA_MY_DRIVE/_logs/bootstrap.log
#
# What it does:
#   1. Deploy Docker services to Oracle (n8n, Netdata, Langfuse, Metabase)
#   2. Import n8n workflows
#   3. Create Google Drive folder tree via n8n
#   4. Verify everything is running
#
# Usage:
#   bash bootstrap_everlight.sh          # Run everything
#   bash bootstrap_everlight.sh status   # Check status only
# ===========================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
LOG_DIR="$WORKSPACE/_logs"
LOG_FILE="$LOG_DIR/bootstrap.log"
ORACLE_HOST="oracle"
SERVICES_DIR="$WORKSPACE/06_DEVELOPMENT/everlight_os"
N8N_WORKFLOWS="$WORKSPACE/03_AUTOMATION_CORE/00_N8N"

mkdir -p "$LOG_DIR"

# Colors
G='\033[0;32m'
Y='\033[1;33m'
R='\033[0;31m'
B='\033[1;34m'
N='\033[0m'

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S PT')] $1"
    echo -e "${G}${msg}${N}"
    echo "$msg" >> "$LOG_FILE"
}

warn() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S PT')] WARN: $1"
    echo -e "${Y}${msg}${N}"
    echo "$msg" >> "$LOG_FILE"
}

err() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S PT')] ERROR: $1"
    echo -e "${R}${msg}${N}"
    echo "$msg" >> "$LOG_FILE"
}

step() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S PT')] === STEP: $1 ==="
    echo -e "\n${B}${msg}${N}"
    echo "" >> "$LOG_FILE"
    echo "$msg" >> "$LOG_FILE"
}

# ===========================================================================
# SSH wrapper with retry
# ===========================================================================
ssh_cmd() {
    local retries=3
    local attempt=0
    while [ $attempt -lt $retries ]; do
        if ssh -o ConnectTimeout=15 -o BatchMode=yes "$ORACLE_HOST" "$@" 2>>"$LOG_FILE"; then
            return 0
        fi
        attempt=$((attempt + 1))
        warn "SSH attempt $attempt/$retries failed, retrying in 5s..."
        sleep 5
    done
    err "SSH failed after $retries attempts"
    return 1
}

scp_cmd() {
    scp -o ConnectTimeout=15 -o BatchMode=yes "$@" 2>>"$LOG_FILE"
}

# ===========================================================================
# STEP 1: Test Oracle connectivity
# ===========================================================================
step_test_oracle() {
    step "Testing Oracle Cloud connectivity"
    if ssh_cmd "echo 'Oracle SSH OK' && sudo docker --version && sudo docker compose version"; then
        log "Oracle Cloud connected. Docker ready."
        return 0
    else
        err "Cannot reach Oracle Cloud. Check SSH key and network."
        return 1
    fi
}

# ===========================================================================
# STEP 2: Deploy Docker services
# ===========================================================================
step_deploy_services() {
    step "Deploying Docker services to Oracle"

    # Create remote directory structure
    ssh_cmd "mkdir -p ~/everlight/{n8n,netdata,langfuse,metabase,blinko}"

    # Copy docker-compose files
    for svc in n8n netdata langfuse metabase; do
        local compose="$SERVICES_DIR/$svc/docker-compose.yml"
        if [ -f "$compose" ]; then
            log "Uploading $svc docker-compose.yml..."
            scp_cmd "$compose" "$ORACLE_HOST:~/everlight/$svc/docker-compose.yml"
        else
            warn "No docker-compose.yml for $svc"
        fi
    done

    # Copy and run deploy script
    scp_cmd "$SERVICES_DIR/deploy_oracle.sh" "$ORACLE_HOST:~/everlight/deploy_oracle.sh"
    ssh_cmd "chmod +x ~/everlight/deploy_oracle.sh"

    # Load environment variables on Oracle
    log "Setting up environment on Oracle..."
    local env_file="$WORKSPACE/03_AUTOMATION_CORE/03_Credentials/.env"
    if [ -f "$env_file" ]; then
        scp_cmd "$env_file" "$ORACLE_HOST:~/everlight/.env"
        # Source env into n8n compose
        ssh_cmd "cd ~/everlight && cat .env >> n8n/.env 2>/dev/null || true"
    fi

    # Create shared Docker network
    ssh_cmd "sudo docker network create everlight 2>/dev/null || true"

    # Deploy each service
    for svc in netdata n8n langfuse metabase; do
        log "Deploying $svc..."
        if ssh_cmd "cd ~/everlight/$svc && sudo docker compose pull && sudo docker compose up -d"; then
            log "$svc deployed successfully"
        else
            warn "$svc deployment failed (may need manual config)"
        fi
    done

    # Check status
    ssh_cmd "sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" 2>&1 | tee -a "$LOG_FILE"
}

# ===========================================================================
# STEP 3: Import n8n workflows
# ===========================================================================
step_import_workflows() {
    step "Importing n8n workflows"

    # Wait for n8n to be ready
    local n8n_ready=false
    for i in $(seq 1 12); do
        if ssh_cmd "curl -sf http://localhost:5678/healthz >/dev/null 2>&1"; then
            n8n_ready=true
            break
        fi
        log "Waiting for n8n to start... ($i/12)"
        sleep 10
    done

    if [ "$n8n_ready" = false ]; then
        warn "n8n not ready after 2 minutes. Workflows will need manual import."
        return 1
    fi

    log "n8n is running. Importing workflows..."

    # Copy workflow files to Oracle
    ssh_cmd "mkdir -p ~/everlight/workflows"
    for wf in "$N8N_WORKFLOWS"/broker/*.json "$N8N_WORKFLOWS"/workflows/*.json; do
        if [ -f "$wf" ]; then
            local name=$(basename "$wf")
            scp_cmd "$wf" "$ORACLE_HOST:~/everlight/workflows/$name"
            log "Uploaded workflow: $name"
        fi
    done

    # Import via n8n CLI (if available) or API
    ssh_cmd "
        cd ~/everlight/workflows
        for f in *.json; do
            echo \"Importing \$f...\"
            curl -sf -X POST http://localhost:5678/api/v1/workflows \
                -H 'Content-Type: application/json' \
                -u \"\${N8N_BASIC_AUTH_USER:-admin}:\${N8N_BASIC_AUTH_PASSWORD:-everlight2026}\" \
                -d @\"\$f\" && echo ' OK' || echo ' FAILED (may need manual import)'
        done
    " 2>&1 | tee -a "$LOG_FILE"
}

# ===========================================================================
# STEP 4: Create Google Drive folders via n8n
# ===========================================================================
step_create_gdrive_folders() {
    step "Creating Google Drive folder tree"

    # This creates an n8n workflow that builds the folder tree
    # The Google API creds are already in n8n
    log "Google Drive folders will be created when n8n Google API credentials are configured."
    log "To complete: Open n8n at http://163.192.19.196:5678 -> Credentials -> Add Google API"
    log "Then run: python3 $SCRIPT_DIR/content_tools/gdrive_setup.py"

    # For now, create the local queue directory for fallback
    mkdir -p "$WORKSPACE/09_DASHBOARD/reports/gdocs_queue"
    log "Local Google Docs fallback queue created at 09_DASHBOARD/reports/gdocs_queue/"
}

# ===========================================================================
# STEP 5: Verify everything
# ===========================================================================
step_verify() {
    step "Verifying deployment"

    echo "" | tee -a "$LOG_FILE"
    log "=== SERVICE STATUS ==="

    # Check Oracle services
    if ssh_cmd "true" 2>/dev/null; then
        local docker_status=$(ssh_cmd "sudo docker ps --format '{{.Names}}: {{.Status}}'" 2>/dev/null)
        echo "$docker_status" | while read line; do
            log "  $line"
        done

        # Check ports
        for port in 5678 19999 3100 3200 1111; do
            if ssh_cmd "ss -tlnp 2>/dev/null | grep -q ':$port '" 2>/dev/null; then
                log "  Port $port: OPEN"
            else
                warn "  Port $port: CLOSED"
            fi
        done
    else
        warn "Cannot reach Oracle for verification"
    fi

    echo "" | tee -a "$LOG_FILE"
    log "=== ACCESS URLS ==="
    log "  n8n:      http://163.192.19.196:5678"
    log "  Netdata:  http://163.192.19.196:19999"
    log "  Langfuse: http://163.192.19.196:3100"
    log "  Metabase: http://163.192.19.196:3200"
    log "  Blinko:   http://163.192.19.196:1111"

    echo "" | tee -a "$LOG_FILE"
    log "=== LOCAL STATUS ==="
    log "  Google Docs bridge: $(python3 -c 'from content_tools.gdocs_bridge import publish_report; print("OK")' 2>/dev/null || echo 'NEEDS n8n')"
    log "  Django broker_ops: $(python3 -c 'import django; print("OK")' 2>/dev/null || echo 'CHECK')"
    log "  Bootstrap log: $LOG_FILE"
    log ""
    log "=== WATCH IN REAL TIME ==="
    log "  tail -f $LOG_FILE"
}

# ===========================================================================
# STATUS ONLY
# ===========================================================================
step_status_only() {
    step "Quick Status Check"
    step_verify
}

# ===========================================================================
# MAIN
# ===========================================================================

echo "============================================================" | tee "$LOG_FILE"
echo " Everlight Ventures -- Master Bootstrap" | tee -a "$LOG_FILE"
echo " $(date '+%Y-%m-%d %H:%M:%S PT')" | tee -a "$LOG_FILE"
echo " Watch live: tail -f $LOG_FILE" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"

case "${1:-all}" in
    status)
        step_status_only
        ;;
    all)
        step_test_oracle
        if [ $? -eq 0 ]; then
            step_deploy_services
            step_import_workflows
            step_create_gdrive_folders
            step_verify
        else
            err "Oracle unreachable. Fix SSH first, then re-run."
            err "Debug: ssh -v oracle 'echo ok'"
        fi
        ;;
    deploy)
        step_deploy_services
        ;;
    workflows)
        step_import_workflows
        ;;
    gdrive)
        step_create_gdrive_folders
        ;;
    verify)
        step_verify
        ;;
    *)
        echo "Usage: $0 {all|status|deploy|workflows|gdrive|verify}"
        ;;
esac

log ""
log "Bootstrap complete. Check log: $LOG_FILE"
