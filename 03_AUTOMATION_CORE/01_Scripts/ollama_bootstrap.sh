#!/usr/bin/env bash
# ollama_bootstrap.sh - Install Ollama on Oracle E5 as the Hive's Anthropic fallback.
#
# Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/04_Self_Hosting_and_Offline_AI/easily_build_your_own_offline_ai.txt
#
# Run on Oracle E5: ssh oracle-e5, then this script.
# Safe to run repeatedly. Skips steps already done.
#
# What it does:
# 1. Installs Ollama (MIT, https://ollama.com)
# 2. Pulls Llama 3.1 8B (general) + Qwen 2.5 Coder 7B (code)
# 3. Creates a systemd service with auto-restart
# 4. Locks port 11434 to localhost only (firewall)
# 5. Writes a quick-test client to /home/opc/hive/ollama_test.py
# 6. Adds OLLAMA_FALLBACK_URL to Hive .env

set -euo pipefail

OLLAMA_VERSION_MIN="0.1.30"
MODELS=("llama3.1:8b" "qwen2.5-coder:7b")
SERVICE_NAME="ollama"

echo "[1/6] Check Ollama install..."
if ! command -v ollama >/dev/null 2>&1; then
  echo "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
else
  echo "Ollama present: $(ollama --version)"
fi

echo "[2/6] Pull models (this may take 5-15 min first time)..."
for m in "${MODELS[@]}"; do
  if ollama list | grep -q "^${m%:*}.*${m#*:}"; then
    echo "  $m already pulled"
  else
    echo "  Pulling $m..."
    ollama pull "$m"
  fi
done

echo "[3/6] Enable systemd service..."
if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
  sudo systemctl enable "$SERVICE_NAME"
  sudo systemctl restart "$SERVICE_NAME"
  echo "  Service restarted. Status:"
  sudo systemctl status "$SERVICE_NAME" --no-pager --lines=5 || true
else
  echo "  WARN: $SERVICE_NAME service unit not found. Ollama may have started as a daemon via install script."
fi

echo "[4/6] Lock port 11434 to localhost..."
if command -v ufw >/dev/null 2>&1; then
  # Allow only local
  sudo ufw deny 11434/tcp >/dev/null 2>&1 || true
  echo "  Port 11434 not externally reachable (ufw deny applied)"
else
  echo "  ufw not installed; skipping firewall rule. Review iptables manually."
fi

echo "[5/6] Write test client..."
mkdir -p /home/opc/hive
cat > /home/opc/hive/ollama_test.py <<'PY'
#!/usr/bin/env python3
"""Quick Ollama sanity check. Runs a 1-shot prompt on each installed model."""
import json, urllib.request, urllib.error, sys

URL = "http://127.0.0.1:11434/api/generate"
MODELS = ["llama3.1:8b", "qwen2.5-coder:7b"]

def ask(model: str, prompt: str) -> str:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode()).get("response", "")
    except urllib.error.URLError as e:
        return f"ERROR: {e}"

if __name__ == "__main__":
    for m in MODELS:
        print(f"\n=== {m} ===")
        print(ask(m, "Say hello in 3 words, then stop.").strip())
PY
chmod +x /home/opc/hive/ollama_test.py
echo "  Wrote /home/opc/hive/ollama_test.py"

echo "[6/6] Update Hive env hint..."
ENV_FILE="/home/opc/.env"
if [ -f "$ENV_FILE" ]; then
  if ! grep -q "^OLLAMA_FALLBACK_URL=" "$ENV_FILE"; then
    echo "" >> "$ENV_FILE"
    echo "# Ollama local LLM (Anthropic fallback)" >> "$ENV_FILE"
    echo "OLLAMA_FALLBACK_URL=http://127.0.0.1:11434" >> "$ENV_FILE"
    echo "OLLAMA_DEFAULT_MODEL=llama3.1:8b" >> "$ENV_FILE"
    echo "  Added OLLAMA_FALLBACK_URL to $ENV_FILE"
  else
    echo "  OLLAMA_FALLBACK_URL already set in $ENV_FILE"
  fi
else
  echo "  WARN: $ENV_FILE missing. Hive may not pick up Ollama until env is unified."
fi

echo
echo "Bootstrap complete."
echo "Next steps:"
echo "  python3 /home/opc/hive/ollama_test.py   # sanity-check both models"
echo "  Update hive_llm_router.py to call Ollama when both Anthropic + OpenRouter fail"
