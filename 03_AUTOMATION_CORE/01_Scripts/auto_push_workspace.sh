#!/usr/bin/env bash
# auto_push_workspace.sh -- if there are commits ahead of origin/main, push them.
# Idempotent: silent when nothing to push.
# Per Rich 2026-05-07: keep GitHub mirror current so phone-side can git-pull.

set -uo pipefail
WORKSPACE=/AA_MY_DRIVE
LOG=/AA_MY_DRIVE/_logs/auto_push.log
mkdir -p "$(dirname "$LOG")"
ts="$(date -Iseconds)"

cd "$WORKSPACE" || exit 1

# Fetch quietly to compare
git fetch origin main --quiet 2>/dev/null || {
    echo "[$ts] FETCH FAILED -- network or auth?" >> "$LOG"
    exit 0
}

ahead=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
behind=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)

if [ "$ahead" = "0" ]; then
    echo "[$ts] up-to-date (behind=$behind)" >> "$LOG"
    exit 0
fi

if [ "$behind" -gt "0" ]; then
    echo "[$ts] DIVERGED ahead=$ahead behind=$behind -- skip auto-push, manual merge needed" >> "$LOG"
    exit 0
fi

# push
out=$(git -c credential.helper="!gh auth git-credential" push origin main 2>&1)
rc=$?
if [ "$rc" = "0" ]; then
    echo "[$ts] PUSHED $ahead commit(s) | $out" >> "$LOG"
else
    echo "[$ts] PUSH FAILED rc=$rc | $out" >> "$LOG"
fi
exit 0
