#!/usr/bin/env bash
# restore_250_to_new_instance.sh
# ------------------------------------------------------------------
# Moves the recovered .250 ("E5 mother") production tree onto the NEW
# Ampere 4/24 instance. Runs AFTER the phone has provisioned the box with
# e5_mother/provision.sh (which already brought up Blinko, agentmemory,
# Open WebUI, hive-voice, nginx).
#
# This script restores the half provision.sh does NOT cover:
#   - .env + secrets/  (all production API keys)
#   - the hive orchestrator scripts, content_tools/, broker_os/, hive_*.py
#   - hive_reports/ archive
#   - the systemd units for hive-action-engine / hive-self-healer /
#     hive-task-runner / hive-reports / hive-slack-agent / hive-directory /
#     hive-dashboard / the mcp-*-proxy fleet
#   - (OPTIONAL, --with-django) hive_django  -- deferred by doctrine; flag-gated
#
# It deliberately SKIPS: blinko, n8n (parked), Open WebUI, agentmemory,
# hive-voice  -- provision.sh owns those. xlm-bot is NOT here (lives on the
# Oracle Micro, verified live).
#
# Path/user translation applied:  /home/opc -> /home/ubuntu
#                                 /mnt/sdcard/AA_MY_DRIVE -> $HIVE_PROD_WS
#                                 systemd  User=opc -> User=ubuntu
#
# Usage:
#   bash restore_250_to_new_instance.sh             # full restore, auto
#   bash restore_250_to_new_instance.sh --dry-run   # show plan, move nothing
#   bash restore_250_to_new_instance.sh --with-django
#   bash restore_250_to_new_instance.sh --only=data|units|docker|smoke
#
# Prereqs: hive_hosts.env values verified for the landed box; SSH works.
# ------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/hive_hosts.env"

DRY=""; WITH_DJANGO=""; ONLY=""
for a in "$@"; do
  case "$a" in
    --dry-run)     DRY="--dry-run" ;;
    --with-django) WITH_DJANGO="1" ;;
    --only=*)      ONLY="${a#--only=}" ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

LOG="${HIVE_LOCAL_WS}/_logs/restore_250_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG")"
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }
run_only() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ]; }

SSH="$(hive_prod_ssh)"
RSH="$(hive_prod_rsh)"
REC="$HIVE_RECOVERY_DIR"
SRC="$REC/home_opc_full"
CRIT="$REC/home_opc_critical"
UNITS="$REC/systemd_units"
DEST_HOME="$HIVE_PROD_HOME"

# ---------------------------------------------------------------
phase_preflight() {
  log "=== PREFLIGHT ==="
  hive_hosts_show | tee -a "$LOG"
  [ -d "$SRC" ]   || { log "FATAL: recovery tree missing: $SRC"; exit 3; }
  [ -f "$CRIT/.env" ] || { log "FATAL: recovered .env missing: $CRIT/.env"; exit 3; }
  [ -d "$UNITS" ] || { log "FATAL: systemd units missing: $UNITS"; exit 3; }
  log "recovery tree: $(du -sh "$SRC" | cut -f1) at $SRC"
  if ! hive_prod_up; then
    log "FATAL: cannot SSH to prod ($HIVE_PROD_USER@$HIVE_PROD_HOST:$HIVE_PROD_SSH_PORT)."
    log "       Confirm the box is up and hive_hosts.env values are correct."
    exit 4
  fi
  log "prod reachable: $($SSH 'hostname; uname -m; echo -n "RAM "; free -h | awk "/Mem:/{print \$2}"')"
  $SSH "mkdir -p $DEST_HOME/secrets $DEST_HOME/content_tools $DEST_HOME/broker $DEST_HOME/_logs" 2>>"$LOG"
}

# ---------------------------------------------------------------
phase_data() {
  run_only data || return 0
  log "=== DATA: rsync recovered tree -> $HIVE_PROD_HOST:$DEST_HOME ==="

  # .env + secrets (critical tier) first, synchronously.
  log "  .env + secrets/"
  rsync $DRY -az -e "$RSH" "$CRIT/.env"        "${HIVE_PROD_USER}@${HIVE_PROD_HOST}:$DEST_HOME/.env"        2>&1 | tee -a "$LOG"
  rsync $DRY -az -e "$RSH" "$CRIT/secrets/"    "${HIVE_PROD_USER}@${HIVE_PROD_HOST}:$DEST_HOME/secrets/"    2>&1 | tee -a "$LOG"
  [ -d "$CRIT/.cloudflared" ] && rsync $DRY -az -e "$RSH" "$CRIT/.cloudflared/" "${HIVE_PROD_USER}@${HIVE_PROD_HOST}:$DEST_HOME/.cloudflared/" 2>&1 | tee -a "$LOG"
  [ -z "$DRY" ] && $SSH "chmod 600 $DEST_HOME/.env; chmod -R go-rwx $DEST_HOME/secrets $DEST_HOME/.cloudflared 2>/dev/null"

  # The hive brain: orchestrators, content_tools, broker_os, hive_*.py.
  # Skip what provision.sh owns + heavy caches.
  log "  hive orchestrators + content_tools + broker_os + hive_reports"
  rsync $DRY -az --delete \
    --exclude '.cache/' --exclude '.npm/' --exclude 'Trash/' \
    --exclude 'node_modules/' --exclude '__pycache__/' --exclude '*.pyc' \
    --exclude 'blinko/' --exclude 'n8n/' --exclude 'agentmemory/' \
    --exclude 'xlm-bot/' --exclude 'xlm-dash-react/' \
    $( [ -z "$WITH_DJANGO" ] && echo "--exclude hive_django/ --exclude hive-django/" ) \
    -e "$RSH" \
    "$SRC/" "${HIVE_PROD_USER}@${HIVE_PROD_HOST}:$DEST_HOME/" 2>&1 | tail -12 | tee -a "$LOG"

  # Path/user translation on the restored Python.
  if [ -z "$DRY" ]; then
    log "  translating paths: /home/opc -> $DEST_HOME , /mnt/sdcard/AA_MY_DRIVE -> $HIVE_PROD_WS"
    $SSH "
      find $DEST_HOME -maxdepth 3 -name '*.py' -not -path '*/migrations/*' -not -path '*/__pycache__/*' 2>/dev/null \
        | while read -r f; do
            sed -i 's|/mnt/sdcard/AA_MY_DRIVE|$HIVE_PROD_WS|g; s|/home/opc|$DEST_HOME|g' \"\$f\" 2>/dev/null
          done
      # .env path references too
      sed -i 's|/home/opc|$DEST_HOME|g' $DEST_HOME/.env 2>/dev/null || true
    " 2>>"$LOG"
  fi
  log "  data restore done"
}

# ---------------------------------------------------------------
phase_units() {
  run_only units || return 0
  log "=== SYSTEMD UNITS: install hive-* + mcp-*-proxy (skip provision-owned) ==="

  # Units provision.sh already owns -- do NOT reinstall.
  local SKIP_RE='^(blinko|n8n|hive-voice|agentmemory)'
  # Django gated.
  [ -z "$WITH_DJANGO" ] && SKIP_RE="${SKIP_RE}|^hive-django"

  local tmp; tmp="$(mktemp -d)"
  for unit in "$UNITS"/*.service "$UNITS"/*.timer; do
    [ -e "$unit" ] || continue
    local base; base="$(basename "$unit")"
    [[ "$base" == *.bak.* ]] && continue
    if echo "$base" | grep -qE "$SKIP_RE"; then
      log "  skip  $base (provision-owned or deferred)"
      continue
    fi
    # Rewrite opc -> ubuntu paths + user inside the unit before shipping.
    sed -e "s|/home/opc|$DEST_HOME|g" \
        -e "s|^User=opc|User=$HIVE_PROD_USER|" \
        -e "s|/mnt/sdcard/AA_MY_DRIVE|$HIVE_PROD_WS|g" \
        "$unit" > "$tmp/$base"
    log "  stage $base"
  done

  if [ -n "$DRY" ]; then
    log "  (dry-run) would scp $(ls "$tmp" | wc -l) units + daemon-reload + enable"
  else
    rsync -az -e "$RSH" "$tmp/" "${HIVE_PROD_USER}@${HIVE_PROD_HOST}:/tmp/hive_units/" 2>>"$LOG"
    $SSH "
      sudo cp /tmp/hive_units/*.service /tmp/hive_units/*.timer /etc/systemd/system/ 2>/dev/null
      sudo systemctl daemon-reload
      for u in /tmp/hive_units/*; do
        b=\$(basename \"\$u\")
        sudo systemctl enable \"\$b\" 2>/dev/null && echo \"  enabled \$b\"
      done
      # Start services (timers will fire on schedule; services start now)
      for u in /tmp/hive_units/*.service; do
        b=\$(basename \"\$u\")
        sudo systemctl restart \"\$b\" 2>/dev/null && echo \"  started \$b: \$(systemctl is-active \"\$b\")\"
      done
      for u in /tmp/hive_units/*.timer; do
        b=\$(basename \"\$u\")
        sudo systemctl start \"\$b\" 2>/dev/null && echo \"  started \$b\"
      done
      rm -rf /tmp/hive_units
    " 2>&1 | tee -a "$LOG"
  fi
  rm -rf "$tmp"
  log "  units done"
}

# ---------------------------------------------------------------
phase_docker() {
  run_only docker || return 0
  log "=== DOCKER: documenso only (blinko owned by provision.sh) ==="
  # blinko: SKIP -- provision.sh phase_3 already brought it up PG-backed.
  #         Restore the 614 notes separately via blinko_restore_from_lite.py.
  # documenso: restore (document signing -- used by broker contract flow).
  if [ -f "$SRC/documenso/docker-compose.yml" ]; then
    if [ -n "$DRY" ]; then
      log "  (dry-run) would rsync documenso/ + docker compose up -d"
    else
      rsync -az -e "$RSH" "$SRC/documenso/" "${HIVE_PROD_USER}@${HIVE_PROD_HOST}:$DEST_HOME/documenso/" 2>>"$LOG"
      $SSH "cd $DEST_HOME/documenso && sudo docker compose up -d 2>&1 | tail -4" 2>&1 | tee -a "$LOG"
    fi
  else
    log "  documenso compose not found in recovery tree -- skipped"
  fi
  log "  docker done"
}

# ---------------------------------------------------------------
phase_smoke() {
  run_only smoke || return 0
  log "=== SMOKE TEST ==="
  $SSH '
    echo "--- hive systemd units ---"
    for u in hive-action-engine hive-self-healer hive-task-runner hive-reports \
             hive-slack-agent hive-directory hive-dashboard \
             mcp-blinko-proxy mcp-supabase-proxy mcp-resend-proxy; do
      printf "  %-22s " "$u"; systemctl is-active "$u" 2>/dev/null || echo "absent"
    done
    echo "--- timers ---"
    systemctl list-timers --no-pager 2>/dev/null | grep -E "hive-" || echo "  none"
    echo "--- docker ---"
    sudo docker ps --format "  {{.Names}}  {{.Status}}" 2>/dev/null
    echo "--- .env present ---"
    test -f ~/.env && echo "  ~/.env OK ($(wc -l < ~/.env) lines)" || echo "  ~/.env MISSING"
    echo "--- disk ---"
    df -h / | tail -1 | awk "{print \"  root: \"\$3\" used / \"\$2}"
  ' 2>&1 | tee -a "$LOG"
  log "  smoke done -- full log: $LOG"
}

# ---------------------------------------------------------------
log "######## restore_250_to_new_instance  dry_run=${DRY:-no}  django=${WITH_DJANGO:-no}  only=${ONLY:-all} ########"
phase_preflight
phase_data
phase_units
phase_docker
phase_smoke
log "######## RESTORE COMPLETE ########"
log ""
log "NEXT (manual):"
log "  1. Restore Blinko's 614 notes: bash $HIVE_LOCAL_WS/03_AUTOMATION_CORE/01_Scripts/blinko_restore_from_lite.py"
log "  2. Verify .env keys still valid (Resend/Anthropic/Supabase) -- some may have rotated"
log "  3. Point Cloudflare / DNS at the new box if anything was IP-pinned"
log "  4. Run the warm-standby once:  bash $SCRIPT_DIR/acemagician_warm_standby.sh"
log "  5. Wire the sync cron:  see $SCRIPT_DIR/MESH_PLAN.md section 4"
