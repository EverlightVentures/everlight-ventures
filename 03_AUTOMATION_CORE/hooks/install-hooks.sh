#!/bin/bash
# Install Everlight git hooks.
#
# The workspace lives on sdcard (vfat/fuse on PRoot) which strips exec bits,
# so we install hooks to /root/.everlight-hooks (ext4, preserves modes) and
# point git there via core.hooksPath. Safe to re-run (idempotent).

set -e

HOOKS_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DEST="${EVERLIGHT_HOOKS_DIR:-/root/.everlight-hooks}"

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Not inside a git repo. Run from the workspace root." >&2
    exit 1
fi

mkdir -p "$HOOKS_DEST"

install_hook() {
    local name="$1"
    local src="$HOOKS_SRC/$name"
    local dst="$HOOKS_DEST/$name"
    if [ ! -f "$src" ]; then
        echo "skip: $name (no source)"
        return
    fi
    cp "$src" "$dst"
    chmod 755 "$dst"
    echo "installed: $name -> $dst"
}

install_hook pre-commit

# Point git at the ext4 hooks dir (local only; doesn't affect other clones).
git config --local core.hooksPath "$HOOKS_DEST"
echo ""
echo "git core.hooksPath = $(git config --local core.hooksPath)"
echo ""
echo "Hooks ready. Bypass with --no-verify in emergencies only."
echo "Re-run this script after editing any hook in $HOOKS_SRC."
