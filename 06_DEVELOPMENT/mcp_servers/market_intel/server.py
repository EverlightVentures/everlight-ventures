#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.types import Resource, ResourceTemplate, TextContent, TextResourceContents, Tool

WORKSPACE = Path(os.environ.get("WORKSPACE", "/mnt/sdcard/AA_MY_DRIVE"))
BOT_DIR = WORKSPACE / "06_DEVELOPMENT" / "xlm_bot"
DATA_DIR = BOT_DIR / "data"
LOGS_DIR = BOT_DIR / "logs"

STATE_FILE = DATA_DIR / "market_intel_state.json"
PLAYBOOK_FILE = DATA_DIR / "weekly_playbook.json"
CALENDAR_FILE = DATA_DIR / "market_event_calendar.json"
SOURCES_FILE = DATA_DIR / "source_scoreboard.json"
CROWDING_FILE = DATA_DIR / "crowding_summary.json"
RUNS_FILE = LOGS_DIR / "market_intel_runs.jsonl"
DOCS_FILE = LOGS_DIR / "market_intel_documents.jsonl"
CLAIMS_FILE = LOGS_DIR / "market_intel_claims.jsonl"

server = Server("market-intel")

TOOLS = [
    Tool(
        name="get_market_intel_state",
        description="Return the current structured market-intel state bundle used by the XLM bot.",
        inputSchema={
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Optional state section to return.",
                    "enum": ["all", "intraday", "weekly", "playbook", "calendar", "sources", "crowding"],
                    "default": "all",
                }
            },
        },
    ),
    Tool(
        name="read_market_intel_resource",
        description="Read a specific market-intel MCP resource URI via tool call.",
        inputSchema={
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "description": "Resource URI, for example market://state/intraday",
                }
            },
            "required": ["uri"],
        },
    ),
]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_jsonl(path: Path, limit: int = 50) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        if not path.exists():
            return rows
        with path.open() as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    item = json.loads(raw)
                except Exception:
                    continue
                if isinstance(item, dict):
                    rows.append(item)
    except Exception:
        return rows
    rows.sort(key=lambda row: str(row.get("generated_at") or row.get("collected_at") or ""), reverse=True)
    return rows[:limit]


def _json_resource(uri: str, payload: Any) -> list[TextResourceContents]:
    return [
        TextResourceContents(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(payload, indent=2, default=str),
        )
    ]


def _load_payloads() -> dict[str, Any]:
    return {
        "state": _read_json(STATE_FILE),
        "playbook": _read_json(PLAYBOOK_FILE),
        "calendar": _read_json(CALENDAR_FILE),
        "sources": _read_json(SOURCES_FILE),
        "crowding": _read_json(CROWDING_FILE),
        "runs": _read_jsonl(RUNS_FILE, limit=50),
        "docs": _read_jsonl(DOCS_FILE, limit=100),
        "claims": _read_jsonl(CLAIMS_FILE, limit=100),
    }


def _resource_payload(uri_str: str, payloads: dict[str, Any] | None = None) -> Any:
    payloads = payloads or _load_payloads()
    state = payloads.get("state") or {}
    playbook = payloads.get("playbook") or {}
    calendar = payloads.get("calendar") or {}
    sources = payloads.get("sources") or {}
    crowding = payloads.get("crowding") or {}
    runs = payloads.get("runs") or []
    docs = payloads.get("docs") or []
    claims = payloads.get("claims") or []

    if uri_str == "market://state/intraday":
        return state.get("intraday") or {"error": "missing_intraday_state"}
    if uri_str == "market://state/weekly":
        return state.get("weekly") or {"error": "missing_weekly_state"}
    if uri_str == "market://runs/recent":
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "runs": runs[:15]}
    if uri_str == "market://claims/recent":
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "claims": claims[:25]}
    if uri_str == "market://documents/recent":
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "documents": docs[:25]}
    if uri_str == "market://playbook/weekly":
        return playbook or {"error": "missing_weekly_playbook"}
    if uri_str == "market://calendar/upcoming":
        return calendar or {"error": "missing_market_calendar"}
    if uri_str == "market://sources/top":
        return sources or {"error": "missing_source_scoreboard"}
    if uri_str == "market://crowding/current":
        return crowding or {"error": "missing_crowding_summary"}
    if uri_str.startswith("market://run/"):
        target = uri_str.rsplit("/", 1)[-1]
        for row in runs:
            if str(row.get("run_id")) == target:
                run_docs = [d for d in docs if str(d.get("run_id")) == target][:20]
                run_claims = [c for c in claims if str(c.get("run_id")) == target][:20]
                return {"run": row, "documents": run_docs, "claims": run_claims}
        return {"error": "run_not_found", "run_id": target}
    if uri_str.startswith("market://claim/"):
        target = uri_str.rsplit("/", 1)[-1]
        for row in claims:
            if str(row.get("claim_id")) == target:
                return row
        return {"error": "claim_not_found", "claim_id": target}
    return {"error": "unknown_resource"}


def _tool_payload(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments or {}
    payloads = _load_payloads()

    if name == "get_market_intel_state":
        section = str(arguments.get("section") or "all").lower().strip()
        state = payloads.get("state") or {}
        mapping = {
            "intraday": state.get("intraday") or {"error": "missing_intraday_state"},
            "weekly": state.get("weekly") or {"error": "missing_weekly_state"},
            "playbook": payloads.get("playbook") or {"error": "missing_weekly_playbook"},
            "calendar": payloads.get("calendar") or {"error": "missing_market_calendar"},
            "sources": payloads.get("sources") or {"error": "missing_source_scoreboard"},
            "crowding": payloads.get("crowding") or {"error": "missing_crowding_summary"},
        }
        if section == "all":
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "state": state,
                "weekly_playbook": payloads.get("playbook") or {},
                "event_calendar": payloads.get("calendar") or {},
                "source_scoreboard": payloads.get("sources") or {},
                "crowding_summary": payloads.get("crowding") or {},
            }
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "section": section,
            "payload": mapping.get(section, {"error": "unknown_section", "section": section}),
        }

    if name == "read_market_intel_resource":
        uri = str(arguments.get("uri") or "").strip()
        if not uri:
            return {"error": "missing_uri"}
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "uri": uri,
            "payload": _resource_payload(uri, payloads),
        }

    return {"error": "unknown_tool", "tool": name}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            name="Intraday Market Intel State",
            title="Intraday Market Intel State",
            uri="market://state/intraday",
            description="Current intraday market-intel state used by the XLM bot.",
            mimeType="application/json",
        ),
        Resource(
            name="Weekly Market Intel State",
            title="Weekly Market Intel State",
            uri="market://state/weekly",
            description="Current weekly market-intel state used by the XLM bot.",
            mimeType="application/json",
        ),
        Resource(
            name="Recent Market Intel Runs",
            title="Recent Market Intel Runs",
            uri="market://runs/recent",
            description="Recent structured research runs and reviewer scores.",
            mimeType="application/json",
        ),
        Resource(
            name="Recent Market Intel Claims",
            title="Recent Market Intel Claims",
            uri="market://claims/recent",
            description="Recent structured trade-relevant claims from the market-intel service.",
            mimeType="application/json",
        ),
        Resource(
            name="Recent Market Intel Documents",
            title="Recent Market Intel Documents",
            uri="market://documents/recent",
            description="Recent source documents tracked by the market-intel service.",
            mimeType="application/json",
        ),
        Resource(
            name="Weekly Trading Playbook",
            title="Weekly Trading Playbook",
            uri="market://playbook/weekly",
            description="Current weekly playbook with thesis, setups, invalidations, and Monday readiness.",
            mimeType="application/json",
        ),
        Resource(
            name="Upcoming Market Events",
            title="Upcoming Market Events",
            uri="market://calendar/upcoming",
            description="Structured upcoming event calendar for macro, XLM, exchange, and playbook timing.",
            mimeType="application/json",
        ),
        Resource(
            name="Top Research Sources",
            title="Top Research Sources",
            uri="market://sources/top",
            description="Current research source scoreboard and source-diversity quality state.",
            mimeType="application/json",
        ),
        Resource(
            name="Current Crowding Summary",
            title="Current Crowding Summary",
            uri="market://crowding/current",
            description="Cross-venue crowding summary from futures relativity and liquidation context.",
            mimeType="application/json",
        ),
    ]


@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    return [
        ResourceTemplate(
            name="Market Intel Run Detail",
            title="Market Intel Run Detail",
            uriTemplate="market://run/{id}",
            description="Detailed structured research run by run id.",
            mimeType="application/json",
        ),
        ResourceTemplate(
            name="Market Intel Claim Detail",
            title="Market Intel Claim Detail",
            uriTemplate="market://claim/{id}",
            description="Detailed structured market-intel claim by claim id.",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: Any) -> list[TextResourceContents]:
    uri_str = str(uri)
    return _json_resource(uri_str, _resource_payload(uri_str))


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(_tool_payload(name, arguments), indent=2, default=str))]


async def main() -> None:
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
