#!/usr/bin/env python3
"""
hive_orchestrator/server.py -- The 4th MCP server (after broker, blinko, market).

Exposes agent-level operations:
  - list_agents()                    -- read 94 agents from .claude/agents/*.md
  - dispatch_agent(name, prompt)     -- queue a dispatch request (non-blocking)
  - query_blinko(q, limit)           -- thin facade over local Blinko :2700
  - pipeline_status(pipeline_name)   -- read deal_execution_log + cron state
  - list_pipelines()                 -- inventory of running pipelines

Transport: stdio for Claude Code per the standard MCP pattern.
HTTP exposure: http_bridge.py auto-picks up _dispatch() and exposes
  POST /tool/hive_orchestrator/<tool_name>

Per HARD LAW memory `feedback_stdio_mcp_needs_http_bridge_for_cron.md`:
both transports share the same Python dispatcher. Adding a 5th MCP is just
another `_load_module(...)` call in http_bridge.py.

Design choices:
  - Dispatch is NON-BLOCKING -- writes to a queue file, returns request_id
    immediately. A separate worker (or a human-driven Claude Code session)
    picks the request up later. Cron callers don't wait minutes.
  - Agent metadata comes from filesystem .md frontmatter, not a DB.
    Single source of truth.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
AGENTS_DIR = ROOT / ".claude" / "agents"
DISPATCH_QUEUE = ROOT / "_logs" / "hive_dispatch_queue.jsonl"
DEAL_LOG_DB = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "audit" / "deal_execution.sqlite"
BLINKO_URL = "http://127.0.0.1:2700"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _parse_agent(path: Path) -> dict:
    """Extract identity fields from an agent .md file."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}
    info = {"file": path.name, "id": path.stem}
    patterns = {
        "name": r"\*\*Name:\*\*\s*(.+)",
        "email": r"\*\*Email:\*\*\s*(.+)",
        "department": r"\*\*Department:\*\*\s*(.+)",
        "role": r"^You are ([^\.\n]+)",
        "tone": r"\*\*Tone:\*\*\s*(.+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.MULTILINE)
        if m:
            info[key] = m.group(1).strip().rstrip(".")
    return info


def _list_agents_impl(department: str | None = None, search: str | None = None) -> list[dict]:
    if not AGENTS_DIR.exists():
        return []
    out: list[dict] = []
    q = (search or "").strip().lower()
    for p in sorted(AGENTS_DIR.glob("*.md")):
        info = _parse_agent(p)
        if not info:
            continue
        if department and (info.get("department", "").lower() != department.lower()):
            continue
        if q:
            haystack = " ".join(str(v) for v in info.values()).lower()
            if q not in haystack:
                continue
        out.append(info)
    return out


def _dispatch_agent_impl(name: str, prompt: str, priority: str = "normal", metadata: dict | None = None) -> dict:
    """Enqueue a dispatch request. Non-blocking. Returns request_id immediately.

    A separate worker (or an interactive Claude Code session) picks the request
    up later. We don't run the agent inline because:
      - HTTP callers (cron, Workers) can't wait minutes
      - Stdio MCP callers also don't want to block their session
      - The Hive's actual dispatch logic lives in hive_deal_orchestrator and
        related scripts; this just records the intent.
    """
    DISPATCH_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    request_id = f"hod-{uuid.uuid4().hex[:12]}"
    record = {
        "request_id": request_id,
        "queued_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "agent": name,
        "prompt": prompt[:2000],  # cap to keep queue file manageable
        "priority": priority,
        "metadata": metadata or {},
        "status": "queued",
    }
    with DISPATCH_QUEUE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return {
        "ok": True,
        "request_id": request_id,
        "status": "queued",
        "note": "Picked up by next claude-code session or worker poll.",
        "queue_path": str(DISPATCH_QUEUE.relative_to(ROOT)),
    }


def _query_blinko_impl(query: str, limit: int = 5) -> dict:
    """Thin facade over the local Blinko /api/v1/note/list endpoint."""
    payload = json.dumps({"searchText": query, "page": 1, "size": int(limit)}).encode()
    req = urllib.request.Request(
        f"{BLINKO_URL}/api/v1/note/list",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": "blinko_unreachable", "detail": str(e)}


def _pipeline_status_impl(pipeline: str | None = None) -> dict:
    """Read deal_execution audit chain for pipeline status. Returns event counts + last event."""
    import sqlite3
    if not DEAL_LOG_DB.exists():
        return {"error": "audit_db_missing", "path": str(DEAL_LOG_DB)}
    try:
        conn = sqlite3.connect(DEAL_LOG_DB)
        conn.row_factory = sqlite3.Row
        # Count events; if pipeline filter passed, scope to that deal
        if pipeline:
            rows = conn.execute(
                "SELECT event, COUNT(*) c FROM deal_events WHERE deal_key = ? GROUP BY event",
                (pipeline,),
            ).fetchall()
            last = conn.execute(
                "SELECT * FROM deal_events WHERE deal_key = ? ORDER BY id DESC LIMIT 1",
                (pipeline,),
            ).fetchone()
        else:
            rows = conn.execute("SELECT event, COUNT(*) c FROM deal_events GROUP BY event").fetchall()
            last = conn.execute("SELECT * FROM deal_events ORDER BY id DESC LIMIT 1").fetchone()
        return {
            "ok": True,
            "pipeline": pipeline or "all",
            "event_counts": {r["event"]: r["c"] for r in rows},
            "last_event": dict(last) if last else None,
        }
    except Exception as e:
        return {"error": "audit_query_failed", "detail": str(e)}


def _list_pipelines_impl() -> dict:
    """Inventory of distinct deal_keys + their last event timestamp."""
    import sqlite3
    if not DEAL_LOG_DB.exists():
        return {"pipelines": []}
    try:
        conn = sqlite3.connect(DEAL_LOG_DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT deal_key, COUNT(*) c, MAX(ts) last_ts FROM deal_events GROUP BY deal_key ORDER BY last_ts DESC"
        ).fetchall()
        return {"pipelines": [dict(r) for r in rows]}
    except Exception as e:
        return {"error": "audit_query_failed", "detail": str(e)}


# ── Public surface for both stdio MCP + HTTP bridge ─────────────────────────

TOOLS = [
    {"name": "list_agents", "description": "List Hive agents (filter by department/search). Returns name, email, department, role per agent."},
    {"name": "dispatch_agent", "description": "Queue a dispatch request for a named agent. Non-blocking: returns request_id; a worker or Claude Code session executes asynchronously."},
    {"name": "query_blinko", "description": "Search Blinko RAG memory (local :2700) for prior decisions, audits, agent reports."},
    {"name": "pipeline_status", "description": "Get pipeline state from deal audit chain. Pass 'pipeline' (deal_key) to scope; otherwise returns aggregate."},
    {"name": "list_pipelines", "description": "Inventory of distinct deal pipelines with event counts + last event timestamp."},
]


def _dispatch(name: str, args: dict) -> dict:
    """The HTTP bridge auto-pickup contract."""
    args = args or {}
    if name == "list_agents":
        return {"agents": _list_agents_impl(
            department=args.get("department"),
            search=args.get("search"),
        )}
    if name == "dispatch_agent":
        agent = args.get("agent") or args.get("name")
        if not agent:
            return {"error": "missing_agent", "detail": "Pass 'agent' (e.g. marquise_reed_acquisitions)"}
        return _dispatch_agent_impl(
            name=agent,
            prompt=args.get("prompt", ""),
            priority=args.get("priority", "normal"),
            metadata=args.get("metadata"),
        )
    if name == "query_blinko":
        return _query_blinko_impl(
            query=args.get("query", "") or args.get("q", ""),
            limit=int(args.get("limit", 5) or 5),
        )
    if name == "pipeline_status":
        return _pipeline_status_impl(pipeline=args.get("pipeline") or args.get("deal_key"))
    if name == "list_pipelines":
        return _list_pipelines_impl()
    return {"error": "unknown_tool", "tool": name, "available": [t["name"] for t in TOOLS]}


# ── Stdio MCP transport (for Claude Code) ──────────────────────────────────

async def _serve_stdio() -> None:
    """Optional stdio path for Claude Code. The HTTP bridge can run without this."""
    try:
        from mcp.server import Server  # type: ignore
        from mcp.types import TextContent, Tool  # type: ignore
    except Exception as e:
        print(f"# mcp SDK not available ({e}); stdio path skipped", file=sys.stderr)
        return

    server = Server("hive-orchestrator")

    @server.list_tools()
    async def list_tools() -> list:
        return [Tool(name=t["name"], description=t["description"], inputSchema={"type": "object"}) for t in TOOLS]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict | None):
        payload = _dispatch(name, arguments or {})
        return [TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]

    from mcp.server.stdio import stdio_server  # type: ignore
    async with stdio_server() as (rs, ws):
        await server.run(rs, ws, server.create_initialization_options())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Quick smoke test
        import pprint
        pprint.pprint(_dispatch("list_agents", {"search": "marquise"}))
        pprint.pprint(_dispatch("list_pipelines", {}))
    else:
        import asyncio
        asyncio.run(_serve_stdio())
