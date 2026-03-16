#!/bin/sh
# Live bot loop — runs main.py in a cycle, survives parent exit
unset CLAUDECODE CLAUDE_CODE
cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot || exit 1
VENV="/tmp/xlm_bot_venv/bin/python"
while true; do
    $VENV main.py --live --i-understand-live 2>>logs/xlb_console.log
    S=$($VENV -c "import json; from pathlib import Path; p=Path('data/state.json'); s=json.loads(p.read_text()) if p.exists() else {}; print(5 if s.get('open_position') else 15)" 2>/dev/null || echo 15)
    sleep "$S"
done
