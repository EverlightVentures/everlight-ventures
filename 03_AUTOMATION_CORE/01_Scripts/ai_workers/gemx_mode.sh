#!/bin/bash
# Launch Gemini in a mode-specific directory so hierarchical GEMINI.md memory is applied.

set -euo pipefail

WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
MODE="${1:-execute}"
if [ $# -gt 0 ]; then
  shift
fi

case "$MODE" in
  execute)
    MODE_DIR="$WORKSPACE"
    APPROVAL_MODE="auto_edit"
    ;;
  plan)
    MODE_DIR="$WORKSPACE/.gemini/plan"
    APPROVAL_MODE="plan"
    ;;
  explain)
    MODE_DIR="$WORKSPACE/.gemini/explain"
    APPROVAL_MODE="plan"
    ;;
  *)
    echo "Usage: gem-mode [execute|plan|explain] [gemini args...]"
    exit 2
    ;;
esac

if [ ! -d "$MODE_DIR" ]; then
    echo "Mode directory not found: $MODE_DIR"
    exit 1
fi

cd "$MODE_DIR"
exec gemini \
  --approval-mode "$APPROVAL_MODE" \
  --include-directories "$WORKSPACE" \
  "$@"
