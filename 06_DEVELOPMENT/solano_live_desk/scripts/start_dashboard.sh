#!/usr/bin/env bash
# Self-healing launcher: free the port no matter what is holding it, then run
# the dashboard. Safe to run repeatedly. Open http://127.0.0.1:2600 after.
set -uo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-2600}"

echo "[start] freeing port ${PORT} ..."
# Kill anything already bound to the port (stale uvicorn, another service).
fuser -k "${PORT}/tcp" 2>/dev/null || true
pkill -f "uvicorn sld.api:app" 2>/dev/null || true
pkill -f "sld.ingest" 2>/dev/null || true
pkill -f "poll_loop" 2>/dev/null || true

# Give the OS a beat to release the socket, without a foreground sleep call.
for _ in 1 2 3; do fuser "${PORT}/tcp" >/dev/null 2>&1 && : || break; done

echo "[start] launching Solano Live Desk on 127.0.0.1:${PORT} ..."
# run.sh backgrounds the ingest loop and execs uvicorn. exec so systemd tracks it.
exec bash scripts/run.sh
