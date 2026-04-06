#!/usr/bin/env bash
set -euo pipefail

REAL_CLAUDE="${REAL_CLAUDE_PATH:-/root/.local/share/claude/versions/2.1.86}"
GUARD_PROMPT_FILE="/mnt/sdcard/AA_MY_DRIVE/.claude/guard/no_local_image_reads.txt"

if [[ ! -x "$REAL_CLAUDE" ]]; then
  echo "Claude binary not found at $REAL_CLAUDE" >&2
  exit 127
fi

args=("$@")

for arg in "${args[@]}"; do
  case "$arg" in
    -v|--version|-h|--help|--bare|--append-system-prompt|--system-prompt|--disable-slash-commands)
      exec "$REAL_CLAUDE" "${args[@]}"
      ;;
  esac
done

subcommand=""
for arg in "${args[@]}"; do
  case "$arg" in
    -*) continue ;;
    *) subcommand="$arg"; break ;;
  esac
done

case "$subcommand" in
  auth|install|update|upgrade|doctor|mcp|plugin|plugins|agents|setup-token|auto-mode)
    exec "$REAL_CLAUDE" "${args[@]}"
    ;;
esac

if [[ -f "$GUARD_PROMPT_FILE" ]]; then
  guard_prompt="$(cat "$GUARD_PROMPT_FILE")"
  exec "$REAL_CLAUDE" --append-system-prompt "$guard_prompt" "${args[@]}"
fi

exec "$REAL_CLAUDE" "${args[@]}"
