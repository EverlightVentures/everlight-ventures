#!/bin/bash
set -euo pipefail

# Resolve bot directory dynamically so this script works on phone and Oracle VM.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="${CRYPTO_BOT_DIR:-$SCRIPT_DIR}"
VENV="${XLM_BOT_VENV:-/tmp/xlm_bot_venv}"
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
