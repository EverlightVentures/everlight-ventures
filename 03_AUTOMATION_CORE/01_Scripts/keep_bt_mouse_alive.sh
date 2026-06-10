#!/usr/bin/env bash
# keep_bt_mouse_alive.sh -- prevent Bluetooth mouse disconnect during long agent sessions.
#
# Root cause: USB autosuspend on the Realtek BT radio (idVendor 0bda, idProduct b85b)
# kicks in after ~2 seconds of idle, putting the BT controller to sleep. The mouse
# loses its connection and has to re-pair, which interrupts agent tasks.
#
# Fix: set the USB device's power/control to 'on' so it never autosuspends.
# This affects ONLY the BT radio (not all USB devices) -- minimal power impact.
# Persists until reboot. Run again after reboot or add to session_keeper.
#
# Usage:
#   sudo bash keep_bt_mouse_alive.sh         # one-shot
#   sudo bash keep_bt_mouse_alive.sh --watch # daemon mode: keeps re-applying

set -euo pipefail

VID="0bda"   # Realtek
PID="b85b"   # BT Radio

find_bt_usb() {
    for dev in /sys/bus/usb/devices/*/idVendor; do
        [ -f "$dev" ] || continue
        if [ "$(cat "$dev")" = "$VID" ]; then
            local devdir
            devdir=$(dirname "$dev")
            if [ "$(cat "$devdir/idProduct" 2>/dev/null)" = "$PID" ]; then
                echo "$devdir"
                return 0
            fi
        fi
    done
    return 1
}

apply_fix() {
    local devdir="$1"
    local current
    current=$(cat "$devdir/power/control" 2>/dev/null || echo "?")
    if [ "$current" = "on" ]; then
        echo "[ok] $devdir power/control already 'on'"
        return 0
    fi
    echo "on" > "$devdir/power/control"
    echo "[fixed] $devdir power/control: $current -> on (autosuspend disabled)"
}

main() {
    if [ "$EUID" -ne 0 ]; then
        echo "[fatal] needs root to write /sys/bus/usb/devices/*/power/control" >&2
        exit 1
    fi
    local devdir
    if ! devdir=$(find_bt_usb); then
        echo "[fatal] no Realtek BT USB device found ($VID:$PID)" >&2
        exit 2
    fi
    apply_fix "$devdir"

    if [ "${1:-}" = "--watch" ]; then
        echo "[watch] re-applying every 60s -- press Ctrl-C to stop"
        while true; do
            sleep 60
            apply_fix "$devdir" >/dev/null 2>&1 || true
        done
    fi
}

main "$@"
