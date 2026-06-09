#!/usr/bin/env bash
# hive_inner_startup.sh -- canonical Hive in-proot startup script.
#
# Runs INSIDE the proot-debian (or ubuntu) container. Fired from outside via:
#   proot-distro login ubuntu -- bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/hive_inner_startup.sh
#
# This is the canonical replacement for /root/.termux/boot/start_hive.sh.
# That old script lived in the WRONG filesystem (proot home) and never fired
# from Termux:Boot. See HARD LAW feedback_termux_boot_filesystem_trap.
#
# Outer trigger: /data/data/com.termux/files/home/.termux/boot/hive_full_startup.sh
# (which lives at the REAL Termux home path that Termux:Boot scans).
#
# Idempotency: every action checks before starting. Safe to run repeatedly:
#   - cron daemon: skipped if already running
#   - SSH tunnels: skipped if ssh process already binds the local port
#   - Claude chat bridge: skipped if process already running
#   - BlinkoLite: skipped if :2700 already responding (dashboards_watchdog handles)
#   - dashboards: fully delegated to dashboards_watchdog.sh (its own idempotency)

set -u

ROOT=/mnt/sdcard/AA_MY_DRIVE
LOG=$ROOT/_logs/hive_inner_startup.log
mkdir -p "$(dirname "$LOG")" 2>/dev/null

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" >> "$LOG"; }

log "=== hive_inner_startup begin (pid=$$) ==="

# ------------------------------------------------------------------------------
# 1. Credentials -- source the canonical .env so every child process inherits.
#    Phoenix v3 pattern from start_hive.sh.
# ------------------------------------------------------------------------------
ENV_FILE=$ROOT/03_AUTOMATION_CORE/03_Credentials/.env
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE" 2>/dev/null || true
  set +a
  log "  credentials loaded from $ENV_FILE"
else
  log "  WARN no credentials file at $ENV_FILE (services may fail auth)"
fi

# Also pick up secondary secrets if present (e.g. /root/.config/everlight/secrets.env)
ALT_ENV=/root/.config/everlight/secrets.env
if [ -f "$ALT_ENV" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ALT_ENV" 2>/dev/null || true
  set +a
  log "  secondary secrets loaded from $ALT_ENV"
fi

# ------------------------------------------------------------------------------
# 2. cron daemon -- required for the dashboards_watchdog cron line + all
#    Broker OS / wholesale pipeline crons. Without this, NOTHING auto-fires.
# ------------------------------------------------------------------------------
if pgrep -x crond > /dev/null 2>&1 || pgrep -x cron > /dev/null 2>&1; then
  log "  cron already running, skipping"
else
  if command -v crond > /dev/null 2>&1; then
    crond 2>>"$LOG" &
    log "  crond started (pid=$!)"
  elif command -v cron > /dev/null 2>&1; then
    cron 2>>"$LOG" &
    log "  cron started (pid=$!)"
  else
    log "  ERROR no cron binary found, cron-driven services will not fire"
  fi
fi

# ------------------------------------------------------------------------------
# 3. SSH tunnels to Oracle. Uses ssh-config aliases (oracle-e5, oracle-mcp-tunnel)
#    so credential + host management lives in ~/.ssh/config, not here.
#    NOTE: n8n :5678 tunnel intentionally DROPPED (n8n parked 2026-04-24
#    per content_tools/n8n_replacements policy).
# ------------------------------------------------------------------------------
# MCP fleet tunnel (oracle-mcp-tunnel forwards 3101-3107 + reverse 8600/3011)
if pgrep -f "ssh.*oracle-mcp-tunnel" > /dev/null 2>&1; then
  log "  oracle-mcp-tunnel already up, skipping"
elif [ -f /root/.ssh/oracle_key.pem ]; then
  ssh -f -N oracle-mcp-tunnel 2>>"$LOG" \
    && log "  oracle-mcp-tunnel established (MCP ports 3101-3107)" \
    || log "  WARN oracle-mcp-tunnel failed (Oracle unreachable?)"
else
  log "  WARN /root/.ssh/oracle_key.pem missing, oracle tunnels skipped"
fi

# ------------------------------------------------------------------------------
# 4. Dashboards -- fully delegated to dashboards_watchdog.sh.
#    The watchdog has its own idempotency (curl-or-pkill-then-restart per port).
#    Running it ONCE here ensures cold-boot brings up all 10 dashboard services.
#    The */5 cron line keeps them healed thereafter.
# ------------------------------------------------------------------------------
log "  firing dashboards_watchdog one-shot (cold-boot warmup)"
nohup bash $ROOT/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh --quiet \
  >> $ROOT/_logs/dashboards_watchdog_boot.log 2>&1 &
log "  dashboards_watchdog spawned (pid=$!)"

# ------------------------------------------------------------------------------
# 4b. MCP watchdog -- brings up the 6 MCP HTTP servers on cold boot.
#     Same idempotency pattern as dashboards. The */1 cron line keeps them
#     healed thereafter; failures queue for it_triage auto-repair.
# ------------------------------------------------------------------------------
log "  firing mcp_watchdog one-shot (cold-boot warmup)"
nohup bash $ROOT/03_AUTOMATION_CORE/01_Scripts/mcp_watchdog.sh --quiet \
  >> $ROOT/_logs/mcp_watchdog_boot.log 2>&1 &
log "  mcp_watchdog spawned (pid=$!)"

# ------------------------------------------------------------------------------
# 5. Claude Chat Bridge -- powers the dashboard AI-chat bubble. Idempotent.
# ------------------------------------------------------------------------------
if pgrep -f "claude_chat_bridge.py" > /dev/null 2>&1; then
  log "  claude_chat_bridge already running, skipping"
else
  nohup python3 $ROOT/03_AUTOMATION_CORE/01_Scripts/claude_chat_bridge.py \
    > $ROOT/_logs/claude_bridge.log 2>&1 &
  log "  claude_chat_bridge spawned (pid=$!)"
fi

# ------------------------------------------------------------------------------
# 6. SSH reverse tunnel -- exposes Claude chat bridge :8510 to Oracle dashboard.
#    Uses oracle-e5 ssh alias (canonical Oracle IP from ssh config).
# ------------------------------------------------------------------------------
if pgrep -f "ssh.*8510:localhost:8510" > /dev/null 2>&1; then
  log "  ssh reverse tunnel :8510 already up, skipping"
elif [ -f /root/.ssh/oracle_key.pem ]; then
  ssh -f -N -R 8510:localhost:8510 oracle-e5 2>>"$LOG" \
    && log "  ssh reverse tunnel :8510 to oracle-e5 established" \
    || log "  WARN ssh reverse tunnel :8510 failed (oracle-e5 unreachable?)"
fi

# ------------------------------------------------------------------------------
# 7. Claude config sync to AceMagician PC (one-shot, Tailscale).
#    Queues silently if PC asleep; next boot catches up.
# ------------------------------------------------------------------------------
if [ -x $ROOT/03_AUTOMATION_CORE/01_Scripts/claude_sync_acemagician.sh ]; then
  nohup bash $ROOT/03_AUTOMATION_CORE/01_Scripts/claude_sync_acemagician.sh --full \
    > $ROOT/_logs/claude_sync_boot.log 2>&1 &
  log "  claude_sync_acemagician spawned (pid=$!)"
fi

# ------------------------------------------------------------------------------
# 8. Workspace push to e5-mother (Oracle 24/7 hub). Reachability-gated.
# ------------------------------------------------------------------------------
if [ -x $ROOT/03_AUTOMATION_CORE/01_Scripts/sync_to_mother.sh ]; then
  nohup bash $ROOT/03_AUTOMATION_CORE/01_Scripts/sync_to_mother.sh \
    > $ROOT/_logs/sync_to_mother_boot.log 2>&1 &
  log "  sync_to_mother spawned (pid=$!)"
fi

# ------------------------------------------------------------------------------
# 9. Sync queue drain -- per HARD LAW feedback_offline_first_bidirectional_sync.
#    Ships any phone-originated writes that queued offline.
# ------------------------------------------------------------------------------
if [ -f $ROOT/03_AUTOMATION_CORE/01_Scripts/sync_queue.py ]; then
  nohup python3 $ROOT/03_AUTOMATION_CORE/01_Scripts/sync_queue.py drain \
    > $ROOT/_logs/sync_queue_drain_boot.log 2>&1 &
  log "  sync_queue drain spawned (pid=$!)"
fi

# ------------------------------------------------------------------------------
# 10. Blinko brain sync phone <-> e5. Additive + content-deduped, never deletes.
#     Runs once on boot so any doze gap reconciles immediately; the */20 cron
#     keeps it current thereafter. e5 cannot reach the phone (cellular NAT), so
#     the phone must initiate -- this on-wake trigger is what makes it durable.
#     blinko_sync.py self-ships to e5 over the public-IP `ssh e5` host.
# ------------------------------------------------------------------------------
if [ -f $ROOT/03_AUTOMATION_CORE/01_Scripts/blinko_sync.py ]; then
  nohup python3 $ROOT/03_AUTOMATION_CORE/01_Scripts/blinko_sync.py \
    > $ROOT/_logs/blinko_sync_boot.log 2>&1 &
  log "  blinko_sync (brain phone<->e5) spawned (pid=$!)"
fi

# ------------------------------------------------------------------------------
# 11. THE CROWN -- Alley Kingz daily art daemon. Paints the free-Leonardo max/day
#     and ships to alley-kingz.pages.dev. A daemon LOOP (not a cron) because crond
#     is not installed here; it re-checks every 20 min so it auto-catches-up the
#     first time the phone is awake after Leonardo's 00:00 UTC reset. Singleton-
#     guarded, so this boot launch is a safe no-op if a Crown is already running.
# ------------------------------------------------------------------------------
if [ -f $ROOT/03_AUTOMATION_CORE/01_Scripts/ak_crown_daemon.sh ]; then
  nohup bash $ROOT/03_AUTOMATION_CORE/01_Scripts/ak_crown_daemon.sh \
    > /dev/null 2>&1 &
  log "  ak_crown (AK daily art -> pages.dev) spawned (pid=$!)"
fi

log "=== hive_inner_startup complete ==="

# Write heartbeat so the meta-watchdog (Phase 5) can detect "boot completed"
echo "$(ts)" > $ROOT/_logs/hive_inner_startup.heartbeat
