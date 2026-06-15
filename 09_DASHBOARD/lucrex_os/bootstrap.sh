#!/usr/bin/env bash
# Stand up LUCREX OS on any machine. Portable: keys off LUCREX_OS_ROOT.
set -euo pipefail
ROOT="${LUCREX_OS_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
OS_DIR="$ROOT/09_DASHBOARD/lucrex_os"
echo "LUCREX OS root: $ROOT"
echo "engine dir: $OS_DIR"
if [[ "${LX_DRY_RUN:-0}" == "1" ]]; then
  echo "[dry-run] would: validate registry, sync surfaces, start daemon"
  exit 0
fi
python3 "$OS_DIR/sync.py"
nohup bash "$OS_DIR/daemon.sh" >/dev/null 2>&1 &
echo "daemon started."
