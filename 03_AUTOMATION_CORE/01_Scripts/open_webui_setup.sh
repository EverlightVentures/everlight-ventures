#!/usr/bin/env bash
# open_webui_setup.sh -- One-shot installer for Open WebUI on the phone.
#
# Open WebUI = open-source MIT/BSD chat frontend that talks to OpenAI / Anthropic /
# Ollama / any OpenAI-compatible API. We install via pip (no Docker dependency,
# works in PRoot Ubuntu).
#
# Port: 2800 (the "human-facing chat surface" band; sibling to 2700 memory)
# RAM:  ~400 MB once running. Phone has ~2.8 GB available -- workable.
# Auth: First run prompts you to create a local admin account (it's all local;
#       no Open WebUI cloud service involved).
#
# Usage:  bash 03_AUTOMATION_CORE/01_Scripts/open_webui_setup.sh
# After:  open http://127.0.0.1:2800/ (or hub.everlightventures.io once tunnel is up)
#
# Stop:   pkill -f open-webui
# Update: pip install --upgrade open-webui

set -euo pipefail

ROOT=/mnt/sdcard/AA_MY_DRIVE
PORT=2800
DATA_DIR="$ROOT/06_DEVELOPMENT/open_webui_data"
ENV_FILE="$ROOT/03_AUTOMATION_CORE/03_Credentials/.env"

ts() { date '+%H:%M:%S'; }
say() { echo "[$(ts)] $*"; }
ok()  { echo "  ✓ $*"; }

# ── 1. Install ─────────────────────────────────────────────────────────────
say "STEP 1/4 -- pip install open-webui (~3-5 min on phone)"
if python3 -c "import open_webui" 2>/dev/null; then
  ok "open-webui Python package already installed"
else
  pip install --break-system-packages --user open-webui 2>&1 | tail -3
  ok "installed"
fi

# ── 2. Data dir + env ──────────────────────────────────────────────────────
say "STEP 2/4 -- data directory + env config"
mkdir -p "$DATA_DIR"
ok "data dir: $DATA_DIR (sqlite + uploads land here, survives reinstalls)"

# Load Everlight creds so Open WebUI can reach OpenAI / Anthropic / Perplexity
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  ok "loaded .env -- OPENAI_API_KEY, ANTHROPIC_API_KEY, PERPLEXITY_API_KEY available to webui"
fi

# ── 3. Launch ──────────────────────────────────────────────────────────────
say "STEP 3/4 -- start Open WebUI on port $PORT"
pkill -f "open-webui" 2>/dev/null || true
sleep 1
DATA_DIR="$DATA_DIR" \
WEBUI_AUTH=true \
DEFAULT_USER_ROLE=admin \
WEBUI_NAME="Everlight Ultra Mind" \
PORT="$PORT" \
HOST=127.0.0.1 \
nohup open-webui serve --port "$PORT" --host 127.0.0.1 > /tmp/svc_2800.log 2>&1 &
ok "spawned -- pid $!"

say "  waiting for first-time DB init (can take 30-60s on first ever run)..."
until curl -s -o /dev/null -w "%{http_code}" -m 2 "http://127.0.0.1:$PORT/" | grep -qE "200|302|307"; do
  sleep 3
done
ok "Open WebUI live at http://127.0.0.1:$PORT/"

# ── 4. Add to watchdog ─────────────────────────────────────────────────────
say "STEP 4/4 -- add to dashboards_watchdog.sh for self-healing"
WD="$ROOT/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh"
if grep -q '"2800|' "$WD"; then
  ok "watchdog already covers :2800"
else
  python3 - <<'PY'
from pathlib import Path
wd = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/dashboards_watchdog.sh")
text = wd.read_text(encoding="utf-8")
new_entry = '  "2800|/|cd $ROOT && nohup open-webui serve --port 2800 --host 127.0.0.1 > /tmp/svc_2800.log 2>&1 &|Open WebUI"'
# Insert before the closing ")" of SERVICES=( ... )
needle = '|MCP HTTP Bridge"'
if needle in text and '|Open WebUI"' not in text:
    text = text.replace(needle, needle + "\n" + new_entry, 1)
    wd.write_text(text, encoding="utf-8")
    print("  inserted")
else:
    print("  already present or anchor missing")
PY
  ok "watchdog updated"
fi

echo
say "DONE."
echo
echo "  Open WebUI:        http://127.0.0.1:$PORT/"
echo "  First-run setup:   create your admin account (LOCAL only -- no Open WebUI cloud)"
echo "  Configure models:  Settings → Connections → add your API keys"
echo "                     OpenAI key already in env (paste it from .env)"
echo "                     Anthropic via 'Custom OpenAI Compatible' pointing at api.anthropic.com"
echo "  Data dir:          $DATA_DIR (survives upgrades + reinstalls)"
echo "  RAM check:         $(free -m | awk '/^Mem:/ {print int(\$3)\"MB used / \"int(\$2)\"MB total\"}')"
echo
echo "  Once Cloudflare Tunnel is live, this surfaces at:"
echo "    https://hub.everlightventures.io     (after adding 2800 to tunnel ingress)"
echo
echo "  Stop:   pkill -f open-webui"
echo "  Update: pip install --upgrade --user --break-system-packages open-webui"
echo "  Logs:   tail -f /tmp/svc_2800.log"
