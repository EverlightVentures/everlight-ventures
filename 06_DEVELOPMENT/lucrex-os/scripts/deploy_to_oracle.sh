#!/usr/bin/env bash
# Deploy lucrex-os to Oracle E5
# Usage: bash scripts/deploy_to_oracle.sh

set -euo pipefail

ORACLE_HOST="oracle-bot"
ORACLE_DIR="/home/opc/lucrex-os"
LOCAL_DIR="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/lucrex-os"

echo "[lucrex-os] rsync source to Oracle..."
rsync -avz --delete \
  --exclude node_modules \
  --exclude .next \
  --exclude .env.local \
  --exclude install.log \
  --exclude build.log \
  --exclude server.log \
  --exclude deploy.log \
  -e "ssh -F /root/.ssh/config" \
  "${LOCAL_DIR}/" \
  "${ORACLE_HOST}:${ORACLE_DIR}/"

echo "[lucrex-os] rsync Wealth_OS folder to Oracle..."
rsync -avz --delete \
  -e "ssh -F /root/.ssh/config" \
  "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wealth_OS/" \
  "${ORACLE_HOST}:/home/opc/Wealth_OS/"

# Write the remote install/build script as a HEREDOC, scp it, then exec it.
# This avoids nested-quoting hell with bash -lc "..."
REMOTE_SCRIPT=$(mktemp)
cat > "${REMOTE_SCRIPT}" <<'REMOTE_EOF'
#!/usr/bin/env bash
set -euo pipefail
cd /home/opc/lucrex-os

if [ ! -f .env.local ]; then
  cp .env.example .env.local
  sed -i 's|WEALTH_OS_ROOT=.*|WEALTH_OS_ROOT=/home/opc/Wealth_OS|' .env.local
fi

echo "[remote] npm install..."
npm install --no-audit --no-fund

echo "[remote] npm run build..."
npm run build

echo "[remote] (re)starting server on port 3040..."
pkill -f 'next start.*3040' 2>/dev/null || true
sleep 1
nohup node node_modules/.bin/next start -p 3040 > server.log 2>&1 &
sleep 3

if curl -sf http://localhost:3040 -o /dev/null; then
  echo "[remote] OK -- lucrex-os live on :3040"
else
  echo "[remote] WARNING -- :3040 not responding yet, see server.log"
  tail -20 server.log
fi
REMOTE_EOF

scp -F /root/.ssh/config "${REMOTE_SCRIPT}" "${ORACLE_HOST}:/tmp/lucrex_remote_deploy.sh"
rm -f "${REMOTE_SCRIPT}"

ssh -F /root/.ssh/config "${ORACLE_HOST}" "bash /tmp/lucrex_remote_deploy.sh"

echo ""
echo "[lucrex-os] DONE. Visit http://163.192.19.196:3040"
