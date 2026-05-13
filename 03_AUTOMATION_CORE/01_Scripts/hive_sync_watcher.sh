#!/bin/bash
# Hive Sync Watcher -- re-sync on .claude/ edit.
# Requires inotify-tools (`apt install inotify-tools` on Debian/Ubuntu).
# Falls back to a 60s mtime poll if inotifywait is unavailable.

set -euo pipefail
ROOT="/mnt/sdcard/AA_MY_DRIVE"
SYNC="${ROOT}/03_AUTOMATION_CORE/01_Scripts/hive_sync_v2.sh"

cd "$ROOT"

debounce_run() {
    # 5s debounce window so a burst of edits triggers ONE sync.
    sleep 5
    bash "$SYNC" >> _logs/hive_sync_watcher.log 2>&1 || true
    echo "[$(date -Iseconds)] sync ran" >> _logs/hive_sync_watcher.log
}

if command -v inotifywait >/dev/null 2>&1; then
    echo "[watcher] inotify mode -- watching .claude/"
    while inotifywait -rqq -e modify,create,delete,move .claude/ 2>/dev/null; do
        debounce_run
    done
else
    echo "[watcher] poll mode (inotifywait not found)"
    LAST_HASH=""
    while true; do
        NEW_HASH=$(find .claude -type f -newer /tmp/.hive_watcher_marker 2>/dev/null | sha256sum | cut -c1-12)
        if [ "$NEW_HASH" != "$LAST_HASH" ]; then
            touch /tmp/.hive_watcher_marker
            debounce_run
            LAST_HASH="$NEW_HASH"
        fi
        sleep 60
    done
fi
