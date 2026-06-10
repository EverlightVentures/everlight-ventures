#!/usr/bin/env bash
# bt_levn_keeper.sh -- auto-reconnect Levn LE-HS012 headphones when in range.
#
# Why: Levn is paired+trusted but only allows ONE simultaneous link. When
# Rich's phone grabs it, the PC link drops; when he walks out of range; etc.
# This keeper polls every 30s; if disconnected, attempts a connect.
#
# Cheap: bluetoothctl connect is a no-op if already connected, and fails
# fast if device isn't in scan range. ~50ms per check.

set -uo pipefail

LEVN_MAC="${LEVN_MAC:-41:42:23:02:42:9B}"
INTERVAL="${BT_LEVN_KEEPER_INTERVAL:-30}"
LOG="/tmp/bt_levn_keeper.log"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

while true; do
    state=$(bluetoothctl info "$LEVN_MAC" 2>/dev/null | awk -F': ' '/Connected:/ {print $2; exit}')
    if [[ "$state" != "yes" ]]; then
        # Try to reconnect (silent on failure -- device may be off / out of range)
        out=$(timeout 8 bluetoothctl connect "$LEVN_MAC" 2>&1 || true)
        if grep -q "Connection successful" <<<"$out"; then
            echo "[$(ts)] reconnected $LEVN_MAC" >> "$LOG"
        fi
    fi
    sleep "$INTERVAL"
done
