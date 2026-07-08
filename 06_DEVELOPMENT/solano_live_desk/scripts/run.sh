#!/usr/bin/env bash
# Launch Solano Live Desk: background ingest loop + API server.
# Binds 127.0.0.1 by default; set EV_BIND=0.0.0.0 to expose on tailnet.
set -euo pipefail
cd "$(dirname "$0")/.."
export SLD_STORE="${SLD_STORE:-$PWD/store}"
# Pure-Python protobuf avoids the upb C-extension segfault under proot/ARM.
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
# Bind all interfaces by default so the phone reaches it over the tailnet.
# (e5 is tailnet-gated; set EV_BIND=127.0.0.1 to keep it strictly local.)
BIND="${EV_BIND:-0.0.0.0}"
PORT="${PORT:-2600}"

# Print the REAL reachable address(es), not localhost.
TSIP="$(tailscale ip -4 2>/dev/null | head -1)"
echo "[run] Dashboard will be live at:"
[ -n "$TSIP" ] && echo "        http://${TSIP}:${PORT}   (tailnet IP)"
echo "        http://$(hostname):${PORT}   (tailnet name, if MagicDNS)"
echo "        band 2600 = Survival OS"

python3 -c "import asyncio; from sld.ingest import poll_loop; asyncio.run(poll_loop('$SLD_STORE'))" &
INGEST_PID=$!
trap 'kill $INGEST_PID 2>/dev/null || true' EXIT

# python3 -m uvicorn works whether uvicorn is a --user install or on PATH.
exec python3 -m uvicorn sld.api:app --host "$BIND" --port "$PORT"
