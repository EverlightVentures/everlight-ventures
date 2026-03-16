#!/bin/bash
set -euo pipefail

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/xlm_bot"
VENV="/tmp/xlm_bot_venv"
REQ="$BOT_DIR/requirements.txt"
STAMP="$VENV/.req_stamp"

mkdir -p "$BOT_DIR/logs"

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi

# shellcheck disable=SC1090
source "$VENV/bin/activate"

req_hash="$(python3 - <<PY
import hashlib
from pathlib import Path
p=Path("$REQ")
print(hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "missing")
PY
)"

old_hash=""
if [ -f "$STAMP" ]; then
  old_hash="$(cat "$STAMP" || true)"
fi

if [ "$req_hash" != "$old_hash" ]; then
  pip install -q -r "$REQ"
  pip install -q streamlit
  echo "$req_hash" > "$STAMP"
fi
