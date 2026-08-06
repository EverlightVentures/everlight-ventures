#!/usr/bin/env bash
# sync_on_reconnect.sh -- Device-state-aware sync trigger.
#
# Detects which peers are reachable (tailnet preferred, public fallback), then runs
# the right sync direction for each. Idempotent. Safe to run manually any time, or
# wire into a Tailscale up-hook / phone boot script.
#
# Source-of-truth rules (matches CLAUDE.md doctrine):
#   - Workspace + skills + agents + commands  -> phone is SOT, push to peers
#   - .claude memory (/root/.claude/projects/) -> bidirectional, mtime wins
#   - Blinko notes                            -> mother is SOT (when up)
#   - Deal pipeline / Supabase                -> Supabase cloud is SOT (no local sync)
#
# Usage:
#   bash sync_on_reconnect.sh             # auto-detect peers, sync whichever are up
#   bash sync_on_reconnect.sh --peer=pc   # only sync to AceMagician PC
#   bash sync_on_reconnect.sh --dry-run   # show plan, don't move bytes

set -uo pipefail

DRY=""
ONLY_PEER=""
for arg in "$@"; do
  case "$arg" in
    --dry-run)  DRY="--dry-run" ;;
    --peer=*)   ONLY_PEER="${arg#--peer=}" ;;
  esac
done

WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
MEMORY_DIR="/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory"
LOG_DIR="$WORKSPACE/_logs/network_sync"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/sync_$(date +%Y%m%d_%H%M%S).log"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }

# ---------------------------------------------------------------------------
# 1. Peer registry (sourced from doctrine, IPs auto-discovered when possible)
# ---------------------------------------------------------------------------
# format: name|tailnet_alias|public_fallback|ssh_key|workspace_dest|memory_dest
declare -a PEERS=(
  "pc|richgee@100.93.253.49||/root/.ssh/phone_to_arch|/AA_MY_DRIVE|/home/richgee/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory"
  "mother|ubuntu@e5-mother|ubuntu@e5-mother-public|/root/.ssh/github_deploy|/home/ubuntu/AA_MY_DRIVE|/home/ubuntu/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory"
  "ev-box|ubuntu@ev-box|ubuntu@ev-box-public|/root/.ssh/github_deploy|/home/ubuntu/AA_MY_DRIVE|/home/ubuntu/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory"
  "micro|opc@oracle-e5||/root/.ssh/oracle_key.pem|/home/opc/AA_MY_DRIVE|/home/opc/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory"
)

# ---------------------------------------------------------------------------
# 2. Reachability probe
# ---------------------------------------------------------------------------
peer_up() {
  local target="$1" key="$2"
  timeout 6 ssh -i "$key" \
    -o ConnectTimeout=4 \
    -o BatchMode=yes \
    -o StrictHostKeyChecking=no \
    "$target" "echo UP" 2>/dev/null | grep -q UP
}

# Ensure remote dir exists before rsync (idempotent, cheap). Peers that have
# never been initialized would otherwise fail "No such file or directory".
ensure_remote_dir() {
  local target="$1" key="$2" remote_dir="$3"
  ssh -i "$key" -o ConnectTimeout=6 -o BatchMode=yes -o StrictHostKeyChecking=no \
    "$target" "mkdir -p '$remote_dir'" 2>/dev/null
}

# ---------------------------------------------------------------------------
# 3. Sync workspace one-way (phone -> peer, phone is SOT)
# ---------------------------------------------------------------------------
sync_workspace() {
  local name="$1" target="$2" key="$3" dest="$4"
  log "  workspace -> $name:$dest"
  ensure_remote_dir "$target" "$key" "$dest"
  rsync $DRY -az --delete \
    --exclude '_logs/' \
    --exclude '.git/' \
    --exclude 'node_modules/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '08_BACKUPS/' \
    -e "ssh -i $key -o StrictHostKeyChecking=no" \
    "$WORKSPACE/" "$target:$dest/" 2>&1 | tail -5 | tee -a "$LOG"
}

# ---------------------------------------------------------------------------
# 4. Sync .claude memory bidirectional (mtime wins via rsync --update)
# ---------------------------------------------------------------------------
sync_memory() {
  local name="$1" target="$2" key="$3" dest="$4"
  log "  memory <-> $name:$dest"
  ensure_remote_dir "$target" "$key" "$dest"
  # Push newer-on-phone (--update = skip files where dest is newer)
  rsync $DRY -az --update \
    -e "ssh -i $key -o StrictHostKeyChecking=no" \
    "$MEMORY_DIR/" "$target:$dest/" 2>&1 | tail -3 | tee -a "$LOG"
  # Pull newer-on-peer (remote dir now guaranteed to exist)
  rsync $DRY -az --update \
    -e "ssh -i $key -o StrictHostKeyChecking=no" \
    "$target:$dest/" "$MEMORY_DIR/" 2>&1 | tail -3 | tee -a "$LOG"
}

# ---------------------------------------------------------------------------
# 5. Pull canonical from mother (when mother is up)
# ---------------------------------------------------------------------------
pull_blinko_snapshot() {
  local target="$1" key="$2"
  log "  pull Blinko snapshot from mother"
  # Placeholder: when Blinko has an export endpoint, hit it here.
  # For now just record that mother was reached.
  date -Iseconds > "$WORKSPACE/_state/last_mother_handshake.txt"
}

# ---------------------------------------------------------------------------
# 6. Main loop
# ---------------------------------------------------------------------------
log "=== sync_on_reconnect start  dry_run=${DRY:-no}  only_peer=${ONLY_PEER:-all} ==="

REACHED=()
SKIPPED=()

for row in "${PEERS[@]}"; do
  IFS='|' read -r name tnet pub key ws_dest mem_dest <<< "$row"
  if [[ -n "$ONLY_PEER" && "$ONLY_PEER" != "$name" ]]; then continue; fi

  log "peer: $name"

  TARGET=""
  if peer_up "$tnet" "$key"; then
    TARGET="$tnet"
    log "  ok via tailnet ($tnet)"
  elif [[ -n "$pub" ]] && peer_up "$pub" "$key"; then
    TARGET="$pub"
    log "  ok via public fallback ($pub)"
  else
    log "  offline -- skipped"
    SKIPPED+=("$name")
    continue
  fi

  # AceMagician PC: delegate to the mature claude_sync_acemagician.sh.
  # It handles bidirectional .claude/ + NOTEPAD with queue-on-sleep, mtime merge,
  # Slack ping, conflict quarantine. Reimplementing here would just diverge.
  if [[ "$name" == "pc" ]]; then
    local_sync_script="$WORKSPACE/03_AUTOMATION_CORE/01_Scripts/claude_sync_acemagician.sh"
    if [[ -x "$local_sync_script" || -r "$local_sync_script" ]]; then
      log "  delegating to claude_sync_acemagician.sh --sync"
      if [[ -n "$DRY" ]]; then
        bash "$local_sync_script" --diff 2>&1 | tail -8 | tee -a "$LOG"
      else
        bash "$local_sync_script" --sync 2>&1 | tail -8 | tee -a "$LOG"
      fi
      REACHED+=("$name (via claude_sync_acemagician)")
      continue
    else
      log "  FALLBACK: claude_sync_acemagician.sh not found, using inline rsync"
      # fall through to default sync_workspace + sync_memory below
    fi
  fi

  sync_workspace "$name" "$TARGET" "$key" "$ws_dest"
  sync_memory    "$name" "$TARGET" "$key" "$mem_dest"
  [[ "$name" == "mother" ]] && pull_blinko_snapshot "$TARGET" "$key"

  REACHED+=("$name")
done

log "=== summary ==="
log "  reached: ${REACHED[*]:-none}"
log "  skipped: ${SKIPPED[*]:-none}"
log "  log: $LOG"

# ---------------------------------------------------------------------------
# 7. Optional Slack handshake (only if any peer reached and creds present)
# ---------------------------------------------------------------------------
if [[ ${#REACHED[@]} -gt 0 && -f /home/opc/.env ]]; then
  : # placeholder for branded_slack ping -- run from mother when wired up
fi
