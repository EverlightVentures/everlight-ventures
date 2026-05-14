#!/usr/bin/env bash
# adb_sync_trigger.sh -- PC side. Watches for the phone over ADB/USB and, the
# moment it connects, kicks the whole sync-to-completion handshake.
#
# This is the "when I connect my phone, the PC auto-helps" piece.
#
# Flow:
#   loop forever:
#     adb devices  -- is the Z Fold connected?
#       NO  -> sleep, retry
#       YES -> (just connected this cycle):
#               1. log + desktop-notify "phone connected, syncing"
#               2. run sync_helper.sh  -- PC wakes Syncthing + blocks sleep
#               3. best-effort kick the phone's sync_finisher.sh via adb
#                  (adb -> Termux -> proot chain; if it fails, the phone's
#                   own */5 cron runs it anyway, so this is just a speedup)
#               4. keep refreshing sync_helper every few min while connected
#       phone unplugged -> log it, stop refreshing, back to waiting
#
# Run it as a PC systemd --user service (see install note at bottom) OR
# from a terminal:  bash adb_sync_trigger.sh
#
# Requires: adb on PATH, USB debugging enabled on the phone.

set -u

SCRIPTS="$HOME/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts"
HELPER="$SCRIPTS/sync_helper.sh"
LOG="$HOME/adb_sync_trigger.log"
POLL=20            # seconds between adb checks
REFRESH_CYCLES=12  # re-run helper every REFRESH_CYCLES*POLL sec (~4 min) while connected

# proot path to the phone-side finisher (used for the best-effort adb kick)
PHONE_FINISHER="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/sync_finisher.sh"
PROOT_LOGIN="/data/data/com.termux/files/usr/bin/proot-distro login ubuntu --"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" >> "$LOG"; echo "[$(ts)] $*"; }

notify() {
  command -v notify-send >/dev/null 2>&1 && notify-send "Everlight Sync" "$1" 2>/dev/null || true
}

phone_connected() {
  # a device line that ends in "device" (not "unauthorized"/"offline")
  adb devices 2>/dev/null | awk 'NR>1 && $2=="device" {found=1} END{exit !found}'
}

kick_phone_finisher() {
  # Best-effort: adb -> Termux proot -> run the finisher detached.
  # If the adb->proot chain isn't permitted, the phone's own cron handles it.
  adb shell "$PROOT_LOGIN nohup bash $PHONE_FINISHER >/dev/null 2>&1 &" 2>/dev/null \
    && log "  phone finisher kicked via adb" \
    || log "  adb->proot kick not available (phone cron will run it -- fine)"
}

log "=== adb_sync_trigger watching for phone ==="
was_connected=0
cycle=0

while true; do
  if phone_connected; then
    if [ "$was_connected" -eq 0 ]; then
      # rising edge -- phone JUST connected
      log "PHONE CONNECTED -- starting sync handshake"
      notify "Phone connected -- finishing workspace sync"
      bash "$HELPER" 2>&1 | tail -3 | sed 's/^/  /' >> "$LOG"
      kick_phone_finisher
      was_connected=1
      cycle=0
    else
      # still connected -- refresh the helper periodically to keep PC awake
      cycle=$((cycle+1))
      if [ $(( cycle % REFRESH_CYCLES )) -eq 0 ]; then
        bash "$HELPER" >/dev/null 2>&1
        log "  helper refreshed (PC stays awake while phone is connected)"
      fi
    fi
  else
    if [ "$was_connected" -eq 1 ]; then
      log "phone disconnected -- handshake idle (Syncthing resumes on next connect)"
      notify "Phone disconnected"
      was_connected=0
    fi
  fi
  sleep "$POLL"
done

# ── install as a PC user service (run once on the PC) ──────────────────────
# mkdir -p ~/.config/systemd/user
# cat > ~/.config/systemd/user/adb-sync-trigger.service <<EOF
# [Unit]
# Description=Everlight ADB sync trigger (phone connect -> finish sync)
# After=network.target
# [Service]
# ExecStart=%h/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/adb_sync_trigger.sh
# Restart=always
# RestartSec=15
# [Install]
# WantedBy=default.target
# EOF
# systemctl --user daemon-reload && systemctl --user enable --now adb-sync-trigger.service
