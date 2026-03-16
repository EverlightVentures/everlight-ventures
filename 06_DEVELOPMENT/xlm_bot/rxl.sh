#!/bin/bash
# rxl - Tail XLM bot logs

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/xlm_bot"
tail -f "$BOT_DIR/logs/decisions.jsonl"
