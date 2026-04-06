#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
RUNTIME_DIR="$BACKEND_DIR/runtime"
ENV_FILE="$BACKEND_DIR/.env"
VENV_DIR="$ROOT_DIR/.venv"
BLINKO_CTL="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/blinko/bk"
BLINKO_MCP_SERVER="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/mcp_servers/blinko_memory/server.py"

mkdir -p "$RUNTIME_DIR"

generate_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    return
  fi

  python3 - <<'PY' > "$ENV_FILE"
import base64
import hashlib
import secrets
from pathlib import Path

root = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/hivemind_saas/backend")
jwt_secret = secrets.token_urlsafe(48)
enc_key = base64.urlsafe_b64encode(hashlib.sha256(jwt_secret.encode()).digest()).decode()
print("ENVIRONMENT=development")
print("DEBUG=false")
print("WORKSPACE_ROOT=/mnt/sdcard/AA_MY_DRIVE")
print(f"DATABASE_URL=sqlite+aiosqlite:///{root / 'runtime' / 'hivemind.db'}")
print(f"JWT_SECRET={jwt_secret}")
print("JWT_EXPIRE_MINUTES=10080")
print("ALLOW_SIGNUP=true")
print("BOOTSTRAP_EMAIL=admin@local.hive")
print(f"BOOTSTRAP_PASSWORD={secrets.token_urlsafe(12)}")
print(f"ENCRYPTION_KEY={enc_key}")
print("CORS_ORIGINS=[\"http://localhost:3000\",\"http://127.0.0.1:3000\",\"http://localhost:8504\",\"http://127.0.0.1:8504\"]")
print("BILLING_BASE_URL=https://app.everlight.ai/settings/billing")
print("FRONTEND_URL=http://localhost:3000")
PY
}

setup_python_env() {
  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
}

start_blinko() {
  if [[ -x "$BLINKO_CTL" ]]; then
    "$BLINKO_CTL" start >/dev/null 2>&1 || true
  fi
}

register_mcp() {
  if command -v codex >/dev/null 2>&1; then
    if ! codex mcp list | grep -q "blinko-memory"; then
      codex mcp add blinko-memory --env WORKSPACE=/mnt/sdcard/AA_MY_DRIVE -- python3 "$BLINKO_MCP_SERVER" >/dev/null
    fi
  fi
}

generate_env_file
setup_python_env
start_blinko
register_mcp

echo "Hive bootstrap complete."
echo "Backend env: $ENV_FILE"
echo "Start API: cd $BACKEND_DIR && ../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000"
echo "Bootstrap credentials:"
grep '^BOOTSTRAP_' "$ENV_FILE"
