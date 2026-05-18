#!/bin/bash
# Spawn a Claude session in the right worktree.
# Usage: ./start_session.sh primary | wholesale | buyers
# Or just paste the three commands at the bottom into three Termux tabs.

WORKTREE="${1:-primary}"

case "$WORKTREE" in
    primary|main)
        DIR="/mnt/sdcard/AA_MY_DRIVE"
        LABEL="PRIMARY (main repo)"
        ;;
    wholesale|build)
        DIR="/mnt/sdcard/AA_MY_DRIVE_worktrees/wholesale"
        LABEL="WHOLESALE BUILD (worktree/wholesale-build branch)"
        ;;
    buyers|experiments)
        DIR="/mnt/sdcard/AA_MY_DRIVE_worktrees/buyers"
        LABEL="BUYER EXPERIMENTS (worktree/buyer-list branch)"
        ;;
    *)
        echo "Unknown worktree: $WORKTREE"
        echo "Usage: $0 {primary|wholesale|buyers}"
        exit 1
        ;;
esac

if [ ! -d "$DIR" ]; then
    echo "Directory not found: $DIR"
    echo "Run from /mnt/sdcard/AA_MY_DRIVE: git worktree list"
    exit 1
fi

echo ""
echo "========================================"
echo "  $LABEL"
echo "  $DIR"
echo "========================================"
echo ""

cd "$DIR" || exit 1
exec claude
