#!/bin/bash
BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot"
VENV="/tmp/crypto_bot_venv"

cd "$BOT_DIR" || exit 1

if [ -d "$VENV" ]; then
  source "$VENV/bin/activate"
fi

python daily_report.py "$@"
