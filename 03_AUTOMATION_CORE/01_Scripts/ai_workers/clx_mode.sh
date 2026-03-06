#!/bin/bash
# Launch Claude in a mode-specific posture using project settings + mode prompts.

set -euo pipefail

WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
SETTINGS_FILE="$WORKSPACE/.claude/settings.json"
MCP_FILE="$WORKSPACE/.mcp.json"
MODE="${1:-execute}"
if [ $# -gt 0 ]; then
  shift
fi

case "$MODE" in
  execute)
    PERMISSION_MODE="acceptEdits"
    MODE_FILE="$WORKSPACE/.claude/modes/execute.md"
    ;;
  plan)
    PERMISSION_MODE="plan"
    MODE_FILE="$WORKSPACE/.claude/modes/plan.md"
    ;;
  review)
    PERMISSION_MODE="plan"
    MODE_FILE="$WORKSPACE/.claude/modes/review.md"
    ;;
  *)
    echo "Usage: claude-mode [execute|plan|review] [claude args...]"
    exit 2
    ;;
esac

cd "$WORKSPACE"

CMD=(claude --permission-mode "$PERMISSION_MODE" --add-dir "$WORKSPACE")

if [ -f "$SETTINGS_FILE" ]; then
  CMD+=(--settings "$SETTINGS_FILE")
fi

if [ -f "$MCP_FILE" ]; then
  CMD+=(--mcp-config "$MCP_FILE")
fi

if [ -f "$MODE_FILE" ]; then
  MODE_PROMPT="$(cat "$MODE_FILE")"
  CMD+=(--append-system-prompt "$MODE_PROMPT")
fi

exec "${CMD[@]}" "$@"
