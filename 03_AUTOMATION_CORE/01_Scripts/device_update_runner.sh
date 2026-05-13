#!/usr/bin/env bash
# device_update_runner.sh -- Auto-install queued tasks when target devices come online.
#
# Per Rich (2026-05-13): "I don't wanna have to manually run the command myself
# and that should be with all updates. Whenever any device comes online, any
# updates that need to be installed, go ahead and automatically run em."
#
# How it works:
#   1. Each device has a folder: 03_AUTOMATION_CORE/04_PendingUpdates/<device>/
#   2. Drop a *.sh script into that folder. It will run on the target device the
#      moment we can reach it (next cron tick).
#   3. On success, the script moves to 04_PendingUpdates/_done/<device>_<ts>_<name>.sh
#   4. On failure, stays in pending/ and is retried next cycle. Failures logged.
#
# Devices known:
#   - acemagician  ssh richgee@100.93.253.49 (tailnet)
#   - ev-box       ssh ev-box                 (tailnet, when provisioned)
#   - oracle-micro ssh opc@163.192.19.196     (xlm bot host)
#   - phone        local execution            (no SSH)
#
# Cron: */2 * * * *  bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/device_update_runner.sh

set -u

ROOT=/mnt/sdcard/AA_MY_DRIVE
PEND=$ROOT/03_AUTOMATION_CORE/04_PendingUpdates
DONE=$PEND/_done
LOG=$PEND/_logs/runner.log
mkdir -p "$DONE" "$(dirname "$LOG")"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" >> "$LOG"; }

# Per-device reachability + execution adapters
ssh_opts="-o ConnectTimeout=8 -o BatchMode=yes -o StrictHostKeyChecking=no"

is_reachable() {
  local device="$1"
  case "$device" in
    acemagician)
      timeout 10 ssh $ssh_opts -i /root/.ssh/phone_to_arch richgee@100.93.253.49 'true' 2>/dev/null
      ;;
    ev-box)
      timeout 10 ssh $ssh_opts ev-box 'true' 2>/dev/null
      ;;
    oracle-micro)
      timeout 10 ssh $ssh_opts -i /root/.ssh/oracle_key.pem opc@163.192.19.196 'true' 2>/dev/null
      ;;
    phone)
      true  # always reachable, runs locally
      ;;
    *)
      return 1
      ;;
  esac
}

run_remote() {
  local device="$1"
  local script_path="$2"
  local script_name="$(basename "$script_path")"
  local remote_path="/tmp/${script_name}"
  case "$device" in
    acemagician)
      scp $ssh_opts -i /root/.ssh/phone_to_arch "$script_path" "richgee@100.93.253.49:$remote_path" \
        && timeout 600 ssh $ssh_opts -i /root/.ssh/phone_to_arch richgee@100.93.253.49 "bash $remote_path && rm $remote_path"
      ;;
    ev-box)
      scp $ssh_opts "$script_path" "ev-box:$remote_path" \
        && timeout 600 ssh $ssh_opts ev-box "bash $remote_path && rm $remote_path"
      ;;
    oracle-micro)
      scp $ssh_opts -i /root/.ssh/oracle_key.pem "$script_path" "opc@163.192.19.196:$remote_path" \
        && timeout 600 ssh $ssh_opts -i /root/.ssh/oracle_key.pem opc@163.192.19.196 "bash $remote_path && rm $remote_path"
      ;;
    phone)
      timeout 600 bash "$script_path"
      ;;
  esac
}

process_device() {
  local device="$1"
  local devdir="$PEND/$device"
  [ -d "$devdir" ] || return 0
  # Any pending scripts?
  local pending
  pending=$(find "$devdir" -maxdepth 1 -name "*.sh" -type f 2>/dev/null | head -20)
  [ -z "$pending" ] && return 0

  if ! is_reachable "$device"; then
    log "$device unreachable, $(echo "$pending" | wc -l) tasks queued"
    return 0
  fi

  log "$device REACHABLE -- processing $(echo "$pending" | wc -l) task(s)"
  echo "$pending" | while read -r script; do
    [ -z "$script" ] && continue
    local name
    name=$(basename "$script")
    local stamp
    stamp=$(date '+%Y%m%d_%H%M%S')
    log "  RUN $device :: $name"
    if run_remote "$device" "$script" >> "$LOG" 2>&1; then
      mv "$script" "$DONE/${device}_${stamp}_${name}"
      log "  OK  $device :: $name -> _done/${device}_${stamp}_${name}"
    else
      local rc=$?
      log "  FAIL $device :: $name (rc=$rc) -- left in pending for retry"
    fi
  done
}

# Iterate every known device dir under PEND/
for d in "$PEND"/*/; do
  device=$(basename "$d")
  case "$device" in
    _done|_logs) continue ;;
  esac
  process_device "$device"
done
