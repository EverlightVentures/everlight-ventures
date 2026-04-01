#!/bin/bash
set -euo pipefail
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$BOT_DIR/venv"
RUNTIME_ENV="$BOT_DIR/secrets/runtime.env"
CONFIG="${XLM_CONFIG_FILE:-config.yaml}"
IDLE_SLEEP="${IDLE_SLEEP:-30}"
IN_TRADE_SLEEP="${IN_TRADE_SLEEP:-5}"

cd "$BOT_DIR"

if [ -f "$RUNTIME_ENV" ]; then
    set -a
    . "$RUNTIME_ENV"
    set +a
fi

source "$VENV/bin/activate"

# Detect paper vs live
is_paper=$("$VENV/bin/python" -c "
import yaml
from pathlib import Path
cfg = yaml.safe_load(Path('$CONFIG').read_text()) if Path('$CONFIG').exists() else {}
print('true' if bool(cfg.get('paper', True)) else 'false')
")

if [ "$is_paper" = "true" ]; then
    CMD=("$VENV/bin/python" main.py --config "$CONFIG" --paper)
else
    CMD=("$VENV/bin/python" main.py --config "$CONFIG" --live --i-understand-live)
fi

echo "[$(date)] Bot starting (paper=$is_paper, config=$CONFIG)"

while true; do
    if ! "${CMD[@]}"; then
        rc=$?
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] bot exited code $rc; retrying" >&2
    fi
    S=$("$VENV/bin/python" -c "
import json
from pathlib import Path
p = Path('data/state.json')
try:
    s = json.loads(p.read_text()) if p.exists() else {}
except Exception:
    s = {}
print($IN_TRADE_SLEEP if s.get('open_position') else $IDLE_SLEEP)
")
    sleep "$S"
done
