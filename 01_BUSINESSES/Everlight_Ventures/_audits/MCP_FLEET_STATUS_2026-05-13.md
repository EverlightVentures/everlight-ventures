# MCP Fleet Status -- 2026-05-13 (Loop 5)

## Top-line

The three MCP servers in `06_DEVELOPMENT/mcp_servers/` use **stdio transport**, NOT HTTP.
They cannot live on the 2700-port band, cannot be HTTP-health-checked by
`dashboards_watchdog.sh`, and shouldn't run as background daemons. The original plan
to put them on 2701-2704 was based on a misread of the FLEET_PLAN.md aspirational
HTTP/SSE architecture vs the actual implementation.

**What this means in practice:** Claude Code spawns stdio MCPs as child processes
when you start a session. They live for the lifetime of the session and exit when
Claude Code exits. There is no port to bind, no daemon to monitor.

## What's on disk

| Server | Path | Transport | Status |
|---|---|---|---|
| `broker_os` | `06_DEVELOPMENT/mcp_servers/broker_os/server.py` | stdio | EXISTS, IMPORTS OK |
| `blinko_memory` | `.../blinko_memory/server.py` | stdio | EXISTS, IMPORTS OK |
| `market_intel` | `.../market_intel/server.py` | stdio | EXISTS, IMPORTS OK |
| `slack`, `gmail`, `calendar`, `hive_orchestrator` | not on disk | (planned) | SKIPPED by start_all.sh |

Confirmed via:
```bash
grep -E "stdio_server|stdio" 06_DEVELOPMENT/mcp_servers/*/server.py
# returns:
#   broker_os/server.py: Transport: stdio (for Claude Code integration)
#   broker_os/server.py: from mcp.server.stdio import stdio_server
#   (same for blinko_memory + market_intel)
```

## What changed in this session

1. **`start_all.sh` FLEET ports** moved from 3101-3107 → 2701-2707 (per 2100-band doctrine).
   The port assignment is now mostly cosmetic since stdio MCPs ignore `MCP_PORT` env;
   it's preserved as future-proofing if any of these are later rewritten to HTTP.

2. **Blinko RAG (`blinko_lite.py`) on 2700** is genuinely live (HTTP). It IS in the
   watchdog and IS the data source for the `blinko_memory` MCP. Loop 6 handles that.

3. **No daemon zombies left behind.** The three test-spawned stdio processes exited
   cleanly when their stdin closed.

## The wire-in Rich needs to do (manual)

The auto-mode classifier blocks me from editing `~/.claude.json` (correct safeguard --
that's Claude Code's own startup config). To activate the three MCPs in future Claude
Code sessions, Rich runs ONE of these:

### Option A -- Claude Code CLI (recommended)

```bash
claude mcp add broker-os python3 /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/mcp_servers/broker_os/server.py
claude mcp add blinko-memory --env BLINKO_URL=http://127.0.0.1:2700 python3 /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/mcp_servers/blinko_memory/server.py
claude mcp add market-intel python3 /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/mcp_servers/market_intel/server.py
claude mcp list
```

### Option B -- direct ~/.claude.json edit

Paste this block into `~/.claude.json` under `"mcpServers"`:

```json
{
  "mcpServers": {
    "broker_os": {
      "command": "python3",
      "args": ["/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/mcp_servers/broker_os/server.py"],
      "env": {}
    },
    "blinko_memory": {
      "command": "python3",
      "args": ["/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/mcp_servers/blinko_memory/server.py"],
      "env": { "BLINKO_URL": "http://127.0.0.1:2700" }
    },
    "market_intel": {
      "command": "python3",
      "args": ["/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/mcp_servers/market_intel/server.py"],
      "env": {}
    }
  }
}
```

After either path, restart Claude Code to load the new MCPs. Then `/mcp` inside
Claude Code should list `broker_os`, `blinko_memory`, `market_intel` as connected.

## Doctrine clarification (CLAUDE.md should reflect this)

Current CLAUDE.md says:
> MCP tools: broker-os, blinko-memory, market-intel, Gmail, Slack, Calendar.
> Bridge via SSH tunnel to e5-mother once provisioned.

That's the **e5-mother HTTP/SSE plan** (still aspirational). The local-phone version
is stdio + per-session. Both can co-exist: stdio for the phone where Claude Code
lives, HTTP/SSE for ev-box / e5-mother where multiple agents need to share state.

Once Rich runs the Option A commands above, future Claude Code sessions on the
phone get full local MCP access. The dashboards_watchdog.sh changes here
(2700-band port reservation) become live the day a server is migrated to HTTP.

## What NOT to do

- Do NOT add stdio MCPs to `dashboards_watchdog.sh`. HTTP health checks fail by
  design on stdio servers (nothing to bind to).
- Do NOT run `start_all.sh` as a cron job. stdio MCPs lose their stdin partner and
  exit immediately when run that way.
- Do NOT rebuild these as HTTP servers just to make watchdog happy. Wait until
  e5-mother is back online; the HTTP variant lives there.
