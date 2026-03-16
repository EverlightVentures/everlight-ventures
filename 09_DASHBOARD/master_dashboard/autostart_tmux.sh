#!/usr/bin/env bash
set -euo pipefail

SESSION="aa_os"
CMD="bash /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/master_dashboard/master_launch.sh"

if command -v tmux >/dev/null 2>&1; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux attach -t "$SESSION"
  else
    tmux new -d -s "$SESSION" "$CMD"
    tmux attach -t "$SESSION"
  fi
else
  echo "tmux not installed; running directly"
  exec $CMD
fi
