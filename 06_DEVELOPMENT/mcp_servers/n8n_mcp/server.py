#!/usr/bin/env python3
"""n8n MCP Server -- Trigger n8n workflows from Claude/Gemini via webhooks."""
from __future__ import annotations
import os, json, sys, asyncio, logging
from urllib.request import Request, urlopen

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server
except ImportError:
    print("MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

N8N_BASE = os.environ.get("N8N_URL", "http://129.159.38.250:5678")
server = Server("n8n-mcp")

WEBHOOKS = {
    "log_to_gdoc": {
        "path": "/webhook/SU0qTaKHBX1r3oLX/r/hive-log-to-gdoc",
        "description": "Create a Google Doc. Input: title, content (markdown).",
        "params": ["title", "content"],
    },
}

def _call_webhook(path, payload):
    url = f"{N8N_BASE}{path}"
    data = json.dumps(payload).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

@server.list_tools()
async def list_tools():
    tools = []
    for name, cfg in WEBHOOKS.items():
        props = {p: {"type": "string", "description": p} for p in cfg["params"]}
        tools.append(Tool(name=f"n8n_{name}", description=cfg["description"],
            inputSchema={"type": "object", "properties": props, "required": cfg["params"]}))
    tools.append(Tool(name="n8n_trigger_webhook",
        description="Trigger any n8n webhook by path with JSON payload.",
        inputSchema={"type": "object", "properties": {
            "webhook_path": {"type": "string", "description": "Webhook path"},
            "payload": {"type": "string", "description": "JSON payload string"}},
            "required": ["webhook_path"]}))
    return tools

@server.call_tool()
async def call_tool(name, arguments):
    if name == "n8n_trigger_webhook":
        result = _call_webhook(arguments["webhook_path"], json.loads(arguments.get("payload", "{}")))
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    tool_name = name.replace("n8n_", "")
    if tool_name in WEBHOOKS:
        cfg = WEBHOOKS[tool_name]
        result = _call_webhook(cfg["path"], {p: arguments.get(p, "") for p in cfg["params"]})
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
