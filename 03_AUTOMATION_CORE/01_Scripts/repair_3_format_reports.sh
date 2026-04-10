#!/bin/bash
set -euo pipefail

KEY="/root/.ssh/oracle_key.pem"
ORACLE="${ORACLE_USER:-opc}@${ORACLE_HOST:-129.159.38.250}"
ROOT="/mnt/sdcard/AA_MY_DRIVE"

echo "[1/4] Syncing bridge + template files to Oracle"
scp -o ConnectTimeout=10 -i "$KEY" \
  "$ROOT/03_AUTOMATION_CORE/01_Scripts/content_tools/gdocs_bridge.py" \
  "$ROOT/03_AUTOMATION_CORE/01_Scripts/content_tools/report_template.py" \
  "$ORACLE:/home/opc/content_tools/"

scp -o ConnectTimeout=10 -i "$KEY" \
  "$ROOT/06_DEVELOPMENT/xlm_bot/vendor/gdocs_bridge.py" \
  "$ROOT/06_DEVELOPMENT/xlm_bot/vendor/report_template.py" \
  "$ORACLE:/home/opc/xlm-bot/vendor/"

echo "[2/4] Materializing direct Google Docs credentials from n8n"
ssh -o ConnectTimeout=10 -i "$KEY" "$ORACLE" 'python3 - <<'"'"'PY'"'"'
import json
import subprocess
from pathlib import Path

cred_id = "gj69Vb5Ty4lyLw9j"
tmp_path = Path("/tmp/gdocs_cred.json")
subprocess.run(
    ["n8n", "export:credentials", f"--id={cred_id}", "--decrypted", f"--output={tmp_path}"],
    check=True,
    stdout=subprocess.DEVNULL,
)
data = json.loads(tmp_path.read_text())[0]["data"]
oauth = data["oauthTokenData"]
secret_dir = Path("/home/opc/secrets")
secret_dir.mkdir(parents=True, exist_ok=True)

client_secret = {
    "installed": {
        "client_id": data["clientId"],
        "client_secret": data["clientSecret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}
token_payload = {
    "token": oauth.get("access_token", ""),
    "refresh_token": oauth["refresh_token"],
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": data["clientId"],
    "client_secret": data["clientSecret"],
    "scopes": oauth.get("scope", "").split(),
    "type": "authorized_user",
}

(secret_dir / "google_client_secret.json").write_text(json.dumps(client_secret, indent=2))
(secret_dir / "google_docs_token.json").write_text(json.dumps(token_payload, indent=2))
subprocess.run(["chmod", "600", str(secret_dir / "google_client_secret.json"), str(secret_dir / "google_docs_token.json")], check=True)
tmp_path.unlink(missing_ok=True)
print("Wrote /home/opc/secrets/google_client_secret.json")
print("Wrote /home/opc/secrets/google_docs_token.json")
PY'

echo "[3/4] Smoke testing the 3-format publisher on Oracle"
ssh -o ConnectTimeout=10 -i "$KEY" "$ORACLE" 'cd /home/opc && source .env && python3 - <<'"'"'PY'"'"'
import json
import sys
sys.path.insert(0, "/home/opc/content_tools")
from gdocs_bridge import publish_report

result = publish_report(
    title="3-Format Pipeline Smoke Test",
    content="## Status\n- HTML render OK\n- Google Doc write OK\n- Slack links ready",
    folder="06_Infrastructure/N8N_Workflow_Logs",
    slack_channel="#deploy-log",
    summary="Smoke test for the standard report pipeline",
    post_to_slack=False,
    agent="marcus_cole",
)
print(json.dumps(result, indent=2))
PY'

echo "[4/4] Optional deploy sync complete"
echo "Run 'bash $ROOT/03_AUTOMATION_CORE/01_Scripts/deploy_to_oracle.sh scripts' if you changed reporting scripts too."
