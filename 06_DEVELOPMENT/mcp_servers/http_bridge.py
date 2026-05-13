"""
http_bridge.py -- One FastAPI app that exposes every MCP tool over HTTP.

WHY: stdio MCPs live only for a Claude Code session. Cron jobs, n8n flows, Workers,
or any non-interactive workflow needs HTTP access. This bridge calls the SAME tool
dispatcher functions that the stdio servers use, so:
  - Claude Code  -> stdio servers (per ~/.claude.json mcpServers)
  - cron / shell -> POST http://127.0.0.1:2701/<service>/<tool_name>
  - Workers      -> same HTTP path through cloudflare tunnel (when up)

Both surfaces call the SAME Python functions; no duplicated logic.

Run:
  cd /mnt/sdcard/AA_MY_DRIVE
  uvicorn 06_DEVELOPMENT.mcp_servers.http_bridge:app --host 127.0.0.1 --port 2701
  # or via dashboards_watchdog.sh entry

Endpoints:
  GET  /healthz                          -> {"ok": true, ...}
  GET  /list_tools                       -> all tools across all services
  GET  /list_tools/{service}             -> tools for one service
  POST /tool/{service}/{tool_name}       -> body = JSON args, returns dict
  POST /broker/{tool_name}               -> alias for /tool/broker/{name}
  POST /blinko/{tool_name}               -> alias for /tool/blinko/{name}
  POST /market/{tool_name}               -> alias for /tool/market/{name}

Auth: bound to 127.0.0.1 by default; only reachable on-device or through the
cloudflared tunnel (which gates by hostname). Add a bearer token if needed via
EVERLIGHT_MCP_TOKEN env var.

Memory: feedback_reuse_existing_infra_first.md, feedback_autonomous_stack_first.md
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MCP = ROOT / "06_DEVELOPMENT" / "mcp_servers"

# Make sibling MCP servers importable (the directories use Python identifiers)
sys.path.insert(0, str(MCP))

from fastapi import FastAPI, HTTPException, Header  # type: ignore  # noqa: E402
from fastapi.responses import JSONResponse  # type: ignore  # noqa: E402

EXPECTED_TOKEN = os.environ.get("EVERLIGHT_MCP_TOKEN", "").strip()

# ---------------------------------------------------------------------------
# Lazy-load the three MCP modules. If any one fails (missing dep), the bridge
# still serves the others.
# ---------------------------------------------------------------------------

_modules: dict[str, dict[str, Any]] = {}


def _load_module(service: str, module_path: str, dispatch_attr: str) -> None:
    """Import an MCP server.py and capture its dispatcher + TOOLS list."""
    try:
        mod = __import__(module_path, fromlist=["*"])
    except Exception as e:
        _modules[service] = {"error": f"import_failed: {e}"}
        return
    dispatch = getattr(mod, dispatch_attr, None)
    tools = getattr(mod, "TOOLS", None)
    if not tools and hasattr(mod, "list_tools"):
        try:
            tools = asyncio.run(mod.list_tools())
        except Exception:
            tools = []
    _modules[service] = {
        "module": mod,
        "dispatch": dispatch,
        "dispatch_attr": dispatch_attr,
        "tools": tools or [],
    }


# Each MCP server uses a slightly different dispatcher attribute:
#   broker_os.server      -> async def _dispatch(name, args) -> dict
#   blinko_memory.server  -> async def call_tool(name, args) -> list[TextContent]
#   market_intel.server   -> def _tool_payload(name, args) -> dict
_load_module("broker", "broker_os.server", "_dispatch")
_load_module("blinko", "blinko_memory.server", "call_tool")
_load_module("market", "market_intel.server", "_tool_payload")

# Intel Center -- pure Python helper, no MCP server.py needed. Auto-exposes
# search_by_capability / search / list_categories at /tool/intel/{name}.
sys.path.insert(0, str(ROOT / "Everlight_Intel_Center" / "lib"))
_load_module("intel", "intel_query", "_dispatch")

# Hive orchestrator -- agent list/dispatch/pipeline state
_load_module("hive", "hive_orchestrator.server", "_dispatch")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Everlight MCP HTTP Bridge",
    version="1.0",
    description="HTTP shim over stdio MCP tool dispatchers for cron/Workers/scripts.",
)


def _check_token(token: str | None) -> None:
    if EXPECTED_TOKEN and token != EXPECTED_TOKEN:
        raise HTTPException(status_code=401, detail="invalid or missing token")


def _tool_to_dict(t: Any) -> dict:
    """Normalize an mcp.types.Tool object to a serializable dict."""
    try:
        return {
            "name": getattr(t, "name", None),
            "description": getattr(t, "description", None),
            "inputSchema": getattr(t, "inputSchema", None),
        }
    except Exception:
        return {"raw": repr(t)}


async def _call(service: str, tool_name: str, args: dict) -> dict:
    info = _modules.get(service)
    if not info or "error" in info:
        raise HTTPException(status_code=503, detail=f"{service} unavailable: {info.get('error', 'not loaded')}")
    dispatch = info["dispatch"]
    if dispatch is None:
        raise HTTPException(status_code=500, detail=f"{service} has no dispatcher attribute")
    try:
        result = dispatch(tool_name, args)
        if asyncio.iscoroutine(result):
            result = await result
    except HTTPException:
        raise
    except Exception as e:
        return {"error": "dispatch_failed", "detail": str(e), "service": service, "tool": tool_name}

    # Normalize TextContent / list-of-TextContent outputs from blinko-style servers
    if isinstance(result, list) and result and hasattr(result[0], "text"):
        try:
            return json.loads(result[0].text)
        except Exception:
            return {"text": getattr(result[0], "text", str(result[0]))}
    return result if isinstance(result, dict) else {"value": result}


@app.get("/healthz")
async def healthz():
    return {
        "ok": True,
        "service": "everlight-mcp-http-bridge",
        "modules": {
            svc: ("ready" if "dispatch" in info and info["dispatch"] else info.get("error", "no_dispatch"))
            for svc, info in _modules.items()
        },
    }


@app.get("/")
async def root():
    return await healthz()


@app.get("/list_tools")
async def list_all_tools():
    out: dict[str, list[dict]] = {}
    for svc, info in _modules.items():
        if "error" in info:
            out[svc] = [{"error": info["error"]}]
            continue
        out[svc] = [_tool_to_dict(t) for t in info.get("tools", [])]
    return out


@app.get("/list_tools/{service}")
async def list_service_tools(service: str):
    info = _modules.get(service)
    if not info or "error" in info:
        raise HTTPException(status_code=404, detail=f"unknown service {service}")
    return {"service": service, "tools": [_tool_to_dict(t) for t in info.get("tools", [])]}


@app.post("/tool/{service}/{tool_name}")
async def call_any_tool(
    service: str,
    tool_name: str,
    args: dict | None = None,
    x_everlight_token: str | None = Header(None, alias="X-Everlight-Token"),
):
    _check_token(x_everlight_token)
    return await _call(service, tool_name, args or {})


@app.post("/broker/{tool_name}")
async def call_broker(
    tool_name: str,
    args: dict | None = None,
    x_everlight_token: str | None = Header(None, alias="X-Everlight-Token"),
):
    _check_token(x_everlight_token)
    return await _call("broker", tool_name, args or {})


@app.post("/blinko/{tool_name}")
async def call_blinko(
    tool_name: str,
    args: dict | None = None,
    x_everlight_token: str | None = Header(None, alias="X-Everlight-Token"),
):
    _check_token(x_everlight_token)
    return await _call("blinko", tool_name, args or {})


@app.post("/market/{tool_name}")
async def call_market(
    tool_name: str,
    args: dict | None = None,
    x_everlight_token: str | None = Header(None, alias="X-Everlight-Token"),
):
    _check_token(x_everlight_token)
    return await _call("market", tool_name, args or {})


@app.post("/intel/{tool_name}")
async def call_intel(
    tool_name: str,
    args: dict | None = None,
    x_everlight_token: str | None = Header(None, alias="X-Everlight-Token"),
):
    _check_token(x_everlight_token)
    return await _call("intel", tool_name, args or {})


@app.post("/hive/{tool_name}")
async def call_hive(
    tool_name: str,
    args: dict | None = None,
    x_everlight_token: str | None = Header(None, alias="X-Everlight-Token"),
):
    _check_token(x_everlight_token)
    return await _call("hive", tool_name, args or {})


@app.exception_handler(Exception)
async def _catch_all(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "unhandled", "detail": str(exc), "path": str(request.url.path)},
    )
