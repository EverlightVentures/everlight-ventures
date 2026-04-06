#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mcp.server import Server
from mcp.types import TextContent, Tool

WORKSPACE = Path(os.environ.get("WORKSPACE", "/mnt/sdcard/AA_MY_DRIVE"))
BLINKO_URL = os.environ.get("BLINKO_URL", "http://129.159.38.250:1111").rstrip("/")
BLINKO_TOKEN = os.environ.get("BLINKO_TOKEN", "").strip()

server = Server("blinko-memory")

TOOLS = [
    Tool(
        name="blinko_query_memory",
        description="Query the Blinko memory layer for prior decisions, summaries, and notes.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language query"},
                "limit": {"type": "integer", "description": "Maximum matches", "default": 8},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="blinko_ai_query",
        description="Ask Blinko's AI query endpoint to synthesize memory-backed context.",
        inputSchema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Question to answer against Blinko memory"},
            },
            "required": ["question"],
        },
    ),
    Tool(
        name="blinko_ingest_note",
        description="Write a durable note into Blinko memory.",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Markdown note content"},
                "note_type": {"type": "integer", "description": "0=flash note, 1=full note", "default": 1},
            },
            "required": ["content"],
        },
    ),
]


def _api(method: str, endpoint: str, payload: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if BLINKO_TOKEN:
        headers["Authorization"] = f"Bearer {BLINKO_TOKEN}"

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(f"{BLINKO_URL}{endpoint}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"error": f"http_{exc.code}", "detail": detail[:400]}
    except URLError as exc:
        return {"error": "unreachable", "detail": str(exc.reason)}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict | None):
    arguments = arguments or {}
    if name == "blinko_query_memory":
        payload = _api("POST", "/api/v1/note/list", {
            "searchText": str(arguments.get("query") or "").strip(),
            "page": 1,
            "size": int(arguments.get("limit") or 8),
        })
    elif name == "blinko_ai_query":
        payload = _api("POST", "/api/v1/note/ai-query", {
            "query": str(arguments.get("question") or "").strip(),
        })
    elif name == "blinko_ingest_note":
        payload = _api("POST", "/api/v1/note/upsert", {
            "content": str(arguments.get("content") or "").strip(),
            "type": int(arguments.get("note_type") or 1),
        })
    else:
        payload = {"error": "unknown_tool", "tool": name}

    return [TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]


async def main() -> None:
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
