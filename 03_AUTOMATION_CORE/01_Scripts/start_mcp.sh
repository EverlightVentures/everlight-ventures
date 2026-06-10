#!/usr/bin/env bash
# start_mcp.sh -- one launcher, 7 MCP servers. Wraps stdio MCP servers in
# mcp-proxy so they expose HTTP on 127.0.0.1:PORT, matching the phone's
# .mcp.json registrations (broker-os :3104, blinko-memory :3101, etc).
#
# Usage:
#   start_mcp.sh broker-os
#   start_mcp.sh blinko-memory
#   start_mcp.sh market-intel
#   start_mcp.sh n8n
#   start_mcp.sh supabase
#   start_mcp.sh stripe
#   start_mcp.sh resend
#
# Loads /AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env so API keys are
# available without repeating in 7 systemd units.

set -uo pipefail

EL_HOME="${EL_HOME:-/mnt/sdcard/AA_MY_DRIVE}"
ENV_FILE="$EL_HOME/03_AUTOMATION_CORE/03_Credentials/.env"
# Auto-detect Python: prefer venv if present, fall back to system.
if [[ -x "$EL_HOME/.venv/bin/python3" ]]; then
  VENV="$EL_HOME/.venv/bin/python3"
else
  VENV="$(command -v python3 2>/dev/null || echo /usr/bin/python3)"
fi
# Auto-detect mcp-proxy: PATH first, then user-local, then /usr/local/bin.
if command -v mcp-proxy >/dev/null 2>&1; then
  MCP_PROXY="$(command -v mcp-proxy)"
elif [[ -x "$HOME/.local/bin/mcp-proxy" ]]; then
  MCP_PROXY="$HOME/.local/bin/mcp-proxy"
elif [[ -x "/usr/local/bin/mcp-proxy" ]]; then
  MCP_PROXY="/usr/local/bin/mcp-proxy"
else
  echo "ERROR mcp-proxy binary not found in PATH, ~/.local/bin, or /usr/local/bin" >&2
  exit 3
fi
NPX="${NPX:-$(command -v npx 2>/dev/null || echo /usr/bin/npx)}"

# Load .env (set -a marks all as exported; bash 'source' tolerates comments)
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE" 2>/dev/null || true
  set +a
fi

NAME="${1:?which MCP server? broker-os | blinko-memory | market-intel | n8n | supabase | stripe | resend}"

case "$NAME" in
  broker-os)
    export WORKSPACE="$EL_HOME"
    export DJANGO_URL="http://127.0.0.1:8504"
    exec "$MCP_PROXY" --host 127.0.0.1 --port 3104 --pass-environment \
      -- "$VENV" "$EL_HOME/06_DEVELOPMENT/mcp_servers/broker_os/server.py"
    ;;

  blinko-memory)
    export BLINKO_URL="http://127.0.0.1:1111"
    exec "$MCP_PROXY" --host 127.0.0.1 --port 3101 --pass-environment \
      -- "$VENV" "$EL_HOME/06_DEVELOPMENT/mcp_servers/blinko_memory/server.py"
    ;;

  market-intel)
    export XLM_BOT_DIR="$EL_HOME/06_DEVELOPMENT/xlm_bot"
    exec "$MCP_PROXY" --host 127.0.0.1 --port 3102 --pass-environment \
      -- "$VENV" "$EL_HOME/06_DEVELOPMENT/mcp_servers/market_intel/server.py"
    ;;

  n8n)
    # PC has Docker n8n on :5678 already
    export N8N_URL="${N8N_URL:-http://127.0.0.1:5678}"
    exec "$MCP_PROXY" --host 127.0.0.1 --port 3103 --pass-environment \
      -- "$VENV" "$EL_HOME/06_DEVELOPMENT/mcp_servers/n8n_mcp/server.py"
    ;;

  supabase)
    : "${SUPABASE_ACCESS_TOKEN:?SUPABASE_ACCESS_TOKEN missing in .env}"
    exec "$MCP_PROXY" --host 127.0.0.1 --port 3105 --pass-environment \
      -- "$NPX" -y @supabase/mcp-server-supabase@latest \
        --access-token "$SUPABASE_ACCESS_TOKEN"
    ;;

  stripe)
    : "${STRIPE_SECRET_KEY:?STRIPE_SECRET_KEY missing in .env}"
    exec "$MCP_PROXY" --host 127.0.0.1 --port 3106 --pass-environment \
      -- "$NPX" -y @stripe/mcp --tools=all --api-key "$STRIPE_SECRET_KEY"
    ;;

  resend)
    : "${RESEND_API_KEY:?RESEND_API_KEY missing in .env}"
    export SENDER_EMAIL_ADDRESS="${SENDER_EMAIL_ADDRESS:-noreply@everlightventures.io}"
    exec "$MCP_PROXY" --host 127.0.0.1 --port 3107 --pass-environment \
      -- "$NPX" -y resend-mcp@latest
    ;;

  *)
    echo "unknown MCP: $NAME" >&2
    exit 2
    ;;
esac
