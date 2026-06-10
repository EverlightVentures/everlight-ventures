#!/usr/bin/env bash
# voice_to_terminal.sh -- one-press push-to-talk wrapper for KDE Meta+Space.
#
# Records 5s of audio, transcribes via whisper.cpp small.en, types result into
# the currently focused window via xdotool. Falls back to clipboard if xdotool
# can't reach the active window (e.g., Wayland-native apps).
#
# Bind in KDE: System Settings -> Shortcuts -> Custom Shortcuts ->
#   New -> Global Shortcut -> Command/URL ->
#   Trigger: Meta+Space
#   Action:  /AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/voice_to_terminal.sh
#
# Visual feedback: brief notification before + after via notify-send.

set -euo pipefail

DURATION="${VOICE_DURATION:-5}"
SCRIPT="/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/voice/voice_runner.py"
PY="/AA_MY_DRIVE/.venv/bin/python3"

# Quick visual cue that recording started
notify-send -t 1500 -i microphone-sensitivity-high \
    "🎙️ Recording" "Listening for ${DURATION}s..." 2>/dev/null || true

# Capture + transcribe + type into focused window AND clipboard (belt + suspenders)
RESULT=$("$PY" "$SCRIPT" --capture --duration "$DURATION" --type --clip 2>&1) || {
    notify-send -t 2500 -i dialog-error \
        "Voice capture failed" "$(echo "$RESULT" | tail -1)" 2>/dev/null || true
    exit 1
}

# Extract transcript for the notification
TRANSCRIPT=$(echo "$RESULT" | "$PY" -c '
import sys, json
try:
    # The result block is JSON; the transcript line is also printed
    text = sys.stdin.read()
    # Last non-empty line is the transcript (per voice_runner stdout sink fallback)
    obj_start = text.find("{")
    obj_end = text.rfind("}")
    if obj_start >= 0 and obj_end > obj_start:
        d = json.loads(text[obj_start:obj_end+1])
        print((d.get("transcript") or "")[:120])
    else:
        print(text.strip().splitlines()[-1] if text.strip() else "")
except Exception as e:
    pass
' 2>/dev/null || echo "captured")

notify-send -t 2500 -i microphone-sensitivity-muted \
    "✓ Transcribed" "${TRANSCRIPT:-(empty)}" 2>/dev/null || true
