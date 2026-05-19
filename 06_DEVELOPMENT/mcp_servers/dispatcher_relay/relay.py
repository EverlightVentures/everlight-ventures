"""dispatcher_relay -- public webhook receiver on Oracle.

Listens on 0.0.0.0:8503 (or RELAY_PORT env). Receives Supabase Database
Webhooks (and other external events) and forwards them to the phone's
hive_dispatcher via the reverse SSH tunnel at [::1]:8600.

Security: bearer-token auth required. Token lives in
/etc/mcp/dispatcher_relay.env (mode 600).

Reconstructed 2026-05-15 from session-context audit log entry
2026-05-15-001-mcp-servers-recovered + cheat sheet section on the
relay flow + first 37 lines preserved in claude session transcript.

Environment:
  PHONE_DISPATCHER_BASE  -- e.g. http://[::1]:8600
  RELAY_BEARER_TOKEN     -- required, validated against Authorization header
  RELAY_HOST             -- default 0.0.0.0
  RELAY_PORT             -- default 8503
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("relay")

PHONE_BASE = os.environ.get("PHONE_DISPATCHER_BASE", "http://[::1]:8600")
RELAY_TOKEN = os.environ.get("RELAY_BEARER_TOKEN", "").strip()
HOST = os.environ.get("RELAY_HOST", "0.0.0.0")  # bind:public-by-design Supabase webhook receiver, see NETWORK_BINDING_POLICY.md
PORT = int(os.environ.get("RELAY_PORT", "8503"))

app = FastAPI(title="Hive Dispatcher Relay", version="1.0.0")


def _require_token(request: Request) -> None:
    if not RELAY_TOKEN:
        raise HTTPException(status_code=500, detail="RELAY_BEARER_TOKEN unset on server")
    hdr = request.headers.get("authorization", "")
    if not hdr.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer")
    if hdr[len("Bearer "):].strip() != RELAY_TOKEN:
        raise HTTPException(status_code=403, detail="bad token")


def _forward_to_phone(path: str, payload: dict[str, Any], timeout: float = 8.0) -> dict[str, Any]:
    """POST the payload to the phone's hive_dispatcher and return its JSON response."""
    url = f"{PHONE_BASE.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {"status": resp.status, "body": body}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode("utf-8", errors="replace")}
    except urllib.error.URLError as e:
        log.warning("phone unreachable: %s", e)
        return {"status": 0, "body": f"phone unreachable: {e.reason}"}


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "phone_base": PHONE_BASE, "token_set": bool(RELAY_TOKEN)}


@app.post("/webhook/supabase")
async def supabase_webhook(request: Request) -> JSONResponse:
    """Receive Supabase Database Webhook event; forward to phone dispatcher."""
    _require_token(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")
    log.info("supabase event: table=%s type=%s", payload.get("table"), payload.get("type"))
    result = _forward_to_phone("/dispatch/supabase", payload)
    return JSONResponse(status_code=result["status"] or 502, content={"forwarded": True, "phone": result})


@app.post("/webhook/{source}")
async def generic_webhook(source: str, request: Request) -> JSONResponse:
    """Catch-all webhook endpoint; forwards to /dispatch/<source> on phone."""
    _require_token(request)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    log.info("event from %s: keys=%s", source, list(payload.keys())[:8])
    result = _forward_to_phone(f"/dispatch/{source}", payload)
    return JSONResponse(status_code=result["status"] or 502, content={"forwarded": True, "phone": result})


if __name__ == "__main__":
    log.info("starting dispatcher_relay on %s:%s -> %s", HOST, PORT, PHONE_BASE)
    if not RELAY_TOKEN:
        log.warning("RELAY_BEARER_TOKEN is empty; all webhook routes will return 500")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
