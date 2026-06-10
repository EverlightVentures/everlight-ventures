#!/usr/bin/env bash
# failover_to_acemagician.sh
# ------------------------------------------------------------------
# Brings the full hive stack UP on the AceMagician PC using the warm-standby
# snapshot, then flips HIVE_PROD_HOST so the whole mesh re-points here.
# "Nothing changes except the IP" -- this script IS that change.
#
# Run this when:
#   (a) the cloud instance is dead and you need the enterprise back NOW, or
#   (b) you want a failover DRILL (use --drill: brings the stack up but does
#       NOT flip HIVE_PROD_HOST, so prod stays authoritative).
#
# Prereq: acemagician_warm_standby.sh has run at least once (need the snapshot).
#
# Usage:
#   bash failover_to_acemagician.sh --drill     # rehearse, non-destructive
#   bash failover_to_acemagician.sh             # REAL failover (interactive confirm)
#   bash failover_to_acemagician.sh --force     # REAL failover, no prompt
#   bash failover_to_acemagician.sh --failback  # revert: flip prod back to cloud
# ------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOSTS_FILE="$SCRIPT_DIR/hive_hosts.env"
source "$HOSTS_FILE"

MODE="real"; FORCE=""
for a in "$@"; do
  case "$a" in
    --drill)    MODE="drill" ;;
    --failback) MODE="failback" ;;
    --force)    FORCE="1" ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

STATE="$HIVE_STANDBY_STATE_DIR"
LOG="${HIVE_LOCAL_WS}/_logs/failover_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG")"
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }

log "######## FAILOVER  mode=$MODE ########"

# --- failback path: just flip the pointer back to cloud ----------------------
if [ "$MODE" = "failback" ]; then
  log "failback -- pointing HIVE_PROD_HOST back to the cloud box"
  read -r -p "  cloud box tailnet name / IP to fail back to: " NEWPROD
  [ -n "$NEWPROD" ] || { log "no host given, abort"; exit 2; }
  sed -i "s|^HIVE_PROD_HOST=.*|HIVE_PROD_HOST=\"\${HIVE_PROD_HOST:-$NEWPROD}\"|" "$HOSTS_FILE"
  log "HIVE_PROD_HOST -> $NEWPROD. Stop local stack with: cd <compose dirs> && docker compose down"
  log "Commit hive_hosts.env + push so all devices pick it up."
  exit 0
fi

# --- preflight ---------------------------------------------------------------
[ -f "$STATE/MANIFEST.json" ] || { log "FATAL: no warm-standby snapshot at $STATE. Run acemagician_warm_standby.sh first."; exit 3; }
command -v docker >/dev/null 2>&1 || { log "FATAL: docker not installed on this PC"; exit 3; }
log "snapshot manifest:"; cat "$STATE/MANIFEST.json" | tee -a "$LOG"

if [ "$MODE" = "real" ] && [ -z "$FORCE" ]; then
  echo
  echo "  >>> REAL FAILOVER. This brings the hive stack up locally AND flips"
  echo "      HIVE_PROD_HOST to '$HIVE_STANDBY_HOST' for the whole mesh."
  read -r -p "  Type 'failover' to proceed: " ans
  [ "$ans" = "failover" ] || { log "aborted by user"; exit 0; }
fi

LOCAL_HOME="$STATE/home"

# --- 1. restore docker volumes ----------------------------------------------
log "[1/4] restoring docker volumes from snapshot"
for tgz in "$STATE/volumes"/*.tar.gz; do
  [ -e "$tgz" ] || { log "  no volume snapshots -- skipping"; break; }
  vol="$(basename "$tgz" .tar.gz)"
  docker volume create "$vol" >/dev/null 2>&1
  docker run --rm -v "${vol}:/v" -w /v -i busybox sh -c 'tar xzf - 2>/dev/null' < "$tgz" \
    && log "  restored volume $vol" || log "  WARN restore failed for $vol"
done

# --- 2. bring up docker stacks ----------------------------------------------
log "[2/4] bringing up docker compose stacks"
for d in "$LOCAL_HOME"/blinko "$LOCAL_HOME"/documenso; do
  if [ -f "$d/docker-compose.yml" ]; then
    log "  up: $d"
    ( cd "$d" && docker compose up -d 2>&1 | tail -3 | tee -a "$LOG" )
  fi
done

# --- 3. start hive services -------------------------------------------------
# The PC runs as user 'richgee', not 'ubuntu'. We run the hive Python services
# as user-systemd units (or nohup fallback) -- NOT system units, to avoid
# sudo/path churn. Unit bodies are translated from the snapshot.
log "[3/4] starting hive services (user-mode)"
USER_UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$USER_UNIT_DIR"
STARTED=0
for unit in "$STATE/systemd"/hive-*.service; do
  [ -e "$unit" ] || continue
  base="$(basename "$unit")"
  # translate ubuntu/opc paths -> this PC's snapshot home, drop User= line
  sed -e "s|/home/ubuntu|$LOCAL_HOME|g" \
      -e "s|/home/opc|$LOCAL_HOME|g" \
      -e "s|/mnt/sdcard/AA_MY_DRIVE|$HIVE_LOCAL_WS|g" \
      -e "/^User=/d" \
      -e "/^Group=/d" \
      "$unit" > "$USER_UNIT_DIR/$base"
  systemctl --user daemon-reload 2>/dev/null
  if systemctl --user enable --now "$base" 2>/dev/null; then
    log "  started (user) $base : $(systemctl --user is-active "$base")"
    STARTED=$((STARTED+1))
  else
    log "  WARN could not start $base -- check $USER_UNIT_DIR/$base"
  fi
done
log "  $STARTED hive services started under user-systemd"

# --- 4. flip the pointer (real failover only) -------------------------------
if [ "$MODE" = "drill" ]; then
  log "[4/4] DRILL -- HIVE_PROD_HOST NOT flipped. Cloud box stays authoritative."
  log ""
  log "Drill complete. To tear down the rehearsal:"
  log "  for d in $LOCAL_HOME/blinko $LOCAL_HOME/documenso; do (cd \$d && docker compose down); done"
  log "  for u in $USER_UNIT_DIR/hive-*.service; do systemctl --user disable --now \$(basename \$u); done"
else
  log "[4/4] flipping HIVE_PROD_HOST -> $HIVE_STANDBY_HOST"
  sed -i "s|^HIVE_PROD_HOST=.*|HIVE_PROD_HOST=\"\${HIVE_PROD_HOST:-$HIVE_STANDBY_HOST}\"|"     "$HOSTS_FILE"
  sed -i "s|^HIVE_PROD_USER=.*|HIVE_PROD_USER=\"\${HIVE_PROD_USER:-$HIVE_STANDBY_USER}\"|"     "$HOSTS_FILE"
  sed -i "s|^HIVE_PROD_SSH_PORT=.*|HIVE_PROD_SSH_PORT=\"\${HIVE_PROD_SSH_PORT:-22}\"|"          "$HOSTS_FILE"
  sed -i "s|^HIVE_PROD_HOME=.*|HIVE_PROD_HOME=\"\${HIVE_PROD_HOME:-$LOCAL_HOME}\"|"             "$HOSTS_FILE"
  sed -i "s|^HIVE_PROD_WS=.*|HIVE_PROD_WS=\"\${HIVE_PROD_WS:-$HIVE_LOCAL_WS}\"|"                "$HOSTS_FILE"
  log "  hive_hosts.env updated. The mesh now treats this PC as prod."
  log ""
  log "  >>> COMMIT + PUSH so phone + Dell pick up the new pointer:"
  log "      cd $HIVE_LOCAL_WS && git add 03_AUTOMATION_CORE/01_Scripts/mesh/hive_hosts.env && git commit -m 'failover: prod -> acemagician-pc' && git push"
  log ""
  log "  >>> Optional (cleanest 'nothing changes'): in the Tailscale admin console,"
  log "      remove the dead cloud node and rename THIS node to 'e5-mother'."
  log "      Then even hive_hosts.env needs no edit -- the name just resolves here."
fi

log "######## FAILOVER ($MODE) COMPLETE -- log: $LOG ########"
