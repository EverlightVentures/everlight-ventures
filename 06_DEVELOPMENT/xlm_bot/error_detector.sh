#!/bin/bash
# Error Pattern Detector -- Native Canvas redirection

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/xlm_bot"
LOGS="$BOT_DIR/logs"
BRIDGE="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/slack_canvas_bridge.py"

WINDOW="3 hours"
ALERT_FILE="/tmp/xlm_error_digest.md"

> "$ALERT_FILE"
ISSUES=0

add_issue() {
    echo "- $1" >> "$ALERT_FILE"
    ISSUES=$((ISSUES + 1))
}

# ... [Error scanning logic remains same, writing to $ALERT_FILE] ...

# Send digest if issues found via Canvas Bridge
if [ "$ISSUES" -gt 0 ]; then
    python3 "$BRIDGE" "$ALERT_FILE" xlmbot
fi

rm -f "$ALERT_FILE"
