#!/usr/bin/env bash
set -euo pipefail

REMOTE="protondrive:AA_MY_DRIVE"
LOCAL="/mnt/sdcard/AA_MY_DRIVE/ProtonDrive"

mkdir -p "$LOCAL"

rclone bisync "$LOCAL" "$REMOTE" \
  --resync \
  --progress \
  --create-empty-src-dirs \
  --exclude ".claude/**" \
  --exclude "_logs/**" \
  --exclude "*.tmp" \
  --exclude "*.log"
