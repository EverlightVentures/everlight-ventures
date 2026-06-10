#!/usr/bin/env bash
# acemagician_warm_standby.sh
# ------------------------------------------------------------------
# Keeps the AceMagician PC a COLD-to-WARM standby of the prod hive box.
# Pulls everything needed to bring the full stack up locally if the cloud
# instance is ever lost -- so failover is "change one hostname", nothing else.
#
# What it captures from $HIVE_PROD_HOST into $HIVE_STANDBY_STATE_DIR:
#   - prod home tree (.env, secrets, hive orchestrators, content_tools,
#     broker_os, hive_django, docker-compose files)   [rsync, incremental]
#   - docker named-volume contents (blinko data + pg, documenso pg)  [tar via ssh]
#   - the installed systemd unit files
#   - a manifest (timestamp, prod hostname, git HEAD, docker image list)
# It also `docker pull`s the images locally so they're cached for instant
# failover (multi-arch images -- pulls the x86 variant for this PC).
#
# Designed to be idempotent + cron-friendly. Run hourly or on PC wake.
#
# Usage:
#   bash acemagician_warm_standby.sh            # full pull
#   bash acemagician_warm_standby.sh --quick    # tree + units only, skip volumes
#   bash acemagician_warm_standby.sh --dry-run
# ------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/hive_hosts.env"

DRY=""; QUICK=""
for a in "$@"; do
  case "$a" in
    --dry-run) DRY="--dry-run" ;;
    --quick)   QUICK="1" ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

STATE="$HIVE_STANDBY_STATE_DIR"
LOG_DIR="${HIVE_LOCAL_WS}/_logs/warm_standby"
mkdir -p "$STATE/home" "$STATE/volumes" "$STATE/systemd" "$LOG_DIR"
LOG="$LOG_DIR/standby_$(date +%Y%m%d_%H%M%S).log"
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }

SSH="$(hive_prod_ssh)"
RSH="$(hive_prod_rsh)"

log "=== warm standby pull  prod=$HIVE_PROD_HOST  dry=${DRY:-no}  quick=${QUICK:-no} ==="

# --- 0. reachability ---------------------------------------------------------
if ! hive_prod_up; then
  log "prod unreachable -- nothing to pull. (If prod is DEAD, run failover_to_acemagician.sh.)"
  exit 1
fi

# --- 1. home tree ------------------------------------------------------------
log "[1/5] home tree -> $STATE/home"
rsync $DRY -az --delete \
  --exclude '.cache/' --exclude '.npm/' --exclude 'Trash/' \
  --exclude 'node_modules/' --exclude '__pycache__/' --exclude '*.pyc' \
  --exclude '_logs/' \
  -e "$RSH" \
  "${HIVE_PROD_USER}@${HIVE_PROD_HOST}:${HIVE_PROD_HOME}/" "$STATE/home/" 2>&1 | tail -8 | tee -a "$LOG"

# --- 2. systemd units --------------------------------------------------------
log "[2/5] systemd units -> $STATE/systemd"
$SSH 'ls /etc/systemd/system/{hive-*,blinko*,mcp-*,documenso*,agentmemory*}.{service,timer} 2>/dev/null' > "$STATE/systemd/_unit_list.txt" 2>/dev/null || true
if [ -z "$DRY" ]; then
  while read -r u; do
    [ -n "$u" ] || continue
    $SSH "sudo cat '$u'" > "$STATE/systemd/$(basename "$u")" 2>/dev/null && log "  pulled $(basename "$u")"
  done < "$STATE/systemd/_unit_list.txt"
fi

# --- 3. docker volumes (skip on --quick) ------------------------------------
if [ -z "$QUICK" ]; then
  log "[3/5] docker named volumes -> $STATE/volumes"
  # Discover volumes, tar each over ssh. Small DBs -- fine to snapshot whole.
  VOLS="$($SSH 'sudo docker volume ls -q 2>/dev/null | grep -E "blinko|documenso|openwebui" || true')"
  if [ -z "$VOLS" ]; then
    log "  no matching docker volumes found on prod"
  else
    for v in $VOLS; do
      if [ -n "$DRY" ]; then
        log "  (dry-run) would snapshot volume $v"
        continue
      fi
      log "  snapshotting volume $v"
      $SSH "sudo docker run --rm -v ${v}:/v -w /v busybox tar czf - . 2>/dev/null" \
        > "$STATE/volumes/${v}.tar.gz" 2>>"$LOG" \
        && log "    -> $STATE/volumes/${v}.tar.gz ($(du -h "$STATE/volumes/${v}.tar.gz" 2>/dev/null | cut -f1))"
    done
  fi
else
  log "[3/5] docker volumes -- SKIPPED (--quick)"
fi

# --- 4. docker images: pull locally so failover is instant -------------------
log "[4/5] pre-pulling docker images locally for instant failover"
IMAGES="$($SSH 'sudo docker ps --format "{{.Image}}" 2>/dev/null | sort -u')"
if [ -n "$IMAGES" ] && [ -z "$DRY" ] && command -v docker >/dev/null 2>&1; then
  for img in $IMAGES; do
    docker pull "$img" >/dev/null 2>&1 && log "  cached $img" || log "  WARN could not pull $img"
  done
else
  log "  images on prod: ${IMAGES:-none}  (dry-run or no local docker -> skipped pull)"
fi

# --- 5. manifest -------------------------------------------------------------
log "[5/5] writing manifest"
if [ -z "$DRY" ]; then
  cat > "$STATE/MANIFEST.json" <<EOF
{
  "captured_at": "$(date -Iseconds)",
  "prod_host": "$HIVE_PROD_HOST",
  "prod_user": "$HIVE_PROD_USER",
  "prod_home": "$HIVE_PROD_HOME",
  "prod_hostname": "$($SSH 'hostname' 2>/dev/null)",
  "prod_uname": "$($SSH 'uname -m' 2>/dev/null)",
  "git_head": "$(cd "$HIVE_LOCAL_WS" && git rev-parse --short HEAD 2>/dev/null)",
  "home_size": "$(du -sh "$STATE/home" 2>/dev/null | cut -f1)",
  "volumes": [$(ls "$STATE/volumes"/*.tar.gz 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/.*/"&"/' | paste -sd, -)],
  "units": [$(ls "$STATE/systemd"/*.service "$STATE/systemd"/*.timer 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/.*/"&"/' | paste -sd, -)],
  "docker_images": [$(echo "$IMAGES" | sed 's/.*/"&"/' | paste -sd, -)]
}
EOF
  log "manifest: $STATE/MANIFEST.json"
fi

log "=== warm standby pull complete -> $STATE ==="
log "Failover drill / real failover:  bash $SCRIPT_DIR/failover_to_acemagician.sh"
