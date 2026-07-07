#!/usr/bin/env bash
# Launch Solano Live Desk: background ingest loop + API server.
# Binds 127.0.0.1 by default; set EV_BIND=0.0.0.0 to expose on tailnet.
set -euo pipefail
cd "$(dirname "$0")/.."
export SLD_STORE="${SLD_STORE:-$PWD/store}"
# Pure-Python protobuf avoids the upb C-extension segfault under proot/ARM.
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
BIND="${EV_BIND:-127.0.0.1}"
PORT="${PORT:-2600}"

python3 -c "import asyncio; from sld.ingest import poll_loop; asyncio.run(poll_loop('$SLD_STORE'))" &
INGEST_PID=$!
trap 'kill $INGEST_PID 2>/dev/null || true' EXIT

# python3 -m uvicorn works whether uvicorn is a --user install or on PATH.
exec python3 -m uvicorn sld.api:app --host "$BIND" --port "$PORT"
