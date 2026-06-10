# MCP Server Fleet Plan -- HTTP/SSE Migration

Status: **active build** -- started 2026-04-23
Owner: Lucrex / Marcus Cole (dispatch) / Forge (implementation)
Replaces: per-CLI stdio MCP spawning (fragile on Termux PRoot, 21 cold starts/day)

## Why

Today every CLI launch (Claude / Gemini / Codex) re-spawns every MCP server
via stdio. On PRoot Termux this stacks latency and occasionally hangs the CLI
entirely (observed 2026-04-23: Gemini wedged for 30s+ on startup with 4 Python
servers in config). There is no shared cache, no "always-on" semantics, and if
one server is flaky every CLI inherits the flakiness.

HTTP/SSE flips the model: servers run once as long-lived daemons on Oracle
(or phone for file-I/O-heavy tools), CLIs connect by URL. One fleet, three
clients, instant boot.

## Fleet layout

| Service              | Host       | Bind                  | Port | Transport | Owner proc          |
|----------------------|------------|-----------------------|------|-----------|---------------------|
| mcp-blinko-proxy     | Oracle E5  | 127.0.0.1             | 3101 | SSE       | mcp-proxy + python3 |
| mcp-market-intel-pxy | Oracle E5  | 127.0.0.1             | 3102 | SSE       | mcp-proxy + python3 |
| mcp-n8n-proxy        | Oracle E5  | 127.0.0.1             | 3103 | SSE       | mcp-proxy + python3 |
| mcp-supabase-proxy   | Oracle E5  | 127.0.0.1             | 3105 | SSE       | mcp-proxy + node    |
| mcp-stripe-proxy     | Oracle E5  | 127.0.0.1             | 3106 | SSE       | mcp-proxy + node    |
| mcp-resend-proxy     | Oracle E5  | 127.0.0.1             | 3107 | SSE       | mcp-proxy + node    |
| mcp-broker-os-proxy  | **phone**  | 127.0.0.1 (localhost) | 3104 | SSE       | mcp-proxy + python3 |

`broker-os` stays phone-local because it reads/writes `/mnt/sdcard/...`
heavily -- shipping file bytes over cell LTE would dominate latency.

Ports 3101-3107 are a contiguous block; easy to firewall-deny the whole range
to non-loopback (they are already bound to 127.0.0.1 by design).

## Reach model

Public bind is **not** used. MCP tools can modify Stripe / Supabase / Resend /
the filesystem -- exposing them to the open internet would be reckless even
with a bearer token. We keep Oracle-side services bound to 127.0.0.1 and
tunnel via SSH from the phone.

```
phone ~/.ssh/config (oracle-e5 alias has -L forwards)
 -L 3101:127.0.0.1:3101
 -L 3102:127.0.0.1:3102
 -L 3103:127.0.0.1:3103
 -L 3105:127.0.0.1:3105
 -L 3106:127.0.0.1:3106
 -L 3107:127.0.0.1:3107
```

Tunnel is supervised by `mcp_tunnel.sh` (Termux boot script) so it reconnects
on wake / power cycle. Claude + Gemini + Codex all point at `http://127.0.0.1:<port>/sse`.

## Why mcp-proxy (no code rewrite)

All 4 Python MCP servers use the low-level `mcp.server.Server` + `stdio_server`
pattern. `mcp-proxy` (pip / uvx) wraps any stdio MCP server and re-exposes it
over SSE or StreamableHTTP with zero code changes. Same pattern works for the
Node-based servers (`@stripe/mcp`, `mcp-server-supabase`, `mcp-send-email`)
since they are also stdio servers.

Command shape:

```
uvx mcp-proxy \
  --sse-host 127.0.0.1 --sse-port 3101 \
  --pass-environment \
  -- python3 /opt/mcp_servers/blinko_memory/server.py
```

## systemd pattern (Oracle)

Each server gets a unit file at `/etc/systemd/system/mcp-<name>-proxy.service`.
They all look like this (blinko example):

```ini
[Unit]
Description=MCP Blinko Memory (SSE proxy)
After=network-online.target blinko.service
Wants=network-online.target

[Service]
Type=simple
User=opc
WorkingDirectory=/opt/mcp_servers/blinko_memory
Environment="WORKSPACE=/home/opc/hive_workspace"
Environment="BLINKO_URL=http://163.192.19.196:1111"
Environment="PATH=/home/opc/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/opc/.local/bin/uvx mcp-proxy \
  --sse-host 127.0.0.1 --sse-port 3101 \
  --pass-environment \
  -- /usr/bin/python3 /opt/mcp_servers/blinko_memory/server.py
Restart=always
RestartSec=5
StandardOutput=append:/var/log/mcp/blinko.log
StandardError=append:/var/log/mcp/blinko.err

[Install]
WantedBy=multi-user.target
```

## Rollout phases

1. **FLEET_PLAN.md** (this file) -- done.
2. **Pilot: blinko-memory**. Unit file, deploy script, start on Oracle, verify
   SSE endpoint via `curl http://127.0.0.1:3101/sse`. Tunnel from phone. Wire
   into Claude settings. Test tool-call round trip.
3. **Rollout: remaining 6**. Apply the same pattern to market-intel, n8n,
   supabase, stripe, resend (Oracle). Install broker-os locally on the phone
   as a Termux service.
4. **Update all 3 CLIs** to use URL MCP refs (`{ "url": ".../sse",
   "transport": "sse" }`).
5. **Verify + doc**. Health-check script, MEMORY.md + CLAUDE.md updates,
   Blinko note.

## Settings.json shape (all three CLIs)

```json
{
  "mcpServers": {
    "blinko-memory":  { "url": "http://127.0.0.1:3101/sse", "transport": "sse" },
    "market-intel":   { "url": "http://127.0.0.1:3102/sse", "transport": "sse" },
    "n8n":            { "url": "http://127.0.0.1:3103/sse", "transport": "sse" },
    "broker-os":      { "url": "http://127.0.0.1:3104/sse", "transport": "sse" },
    "supabase":       { "url": "http://127.0.0.1:3105/sse", "transport": "sse" },
    "stripe":         { "url": "http://127.0.0.1:3106/sse", "transport": "sse" },
    "resend":         { "url": "http://127.0.0.1:3107/sse", "transport": "sse" }
  }
}
```

Claude Code and Gemini CLI both accept this shape. Codex CLI uses
`~/.codex/config.toml` with `[mcp_servers.blinko-memory] url = "..."`
(equivalent semantics).

## Health check

`03_AUTOMATION_CORE/01_Scripts/mcp_fleet_health.sh` (to be created):

- For each port 3101-3107: `curl -sS --max-time 3 http://127.0.0.1:$PORT/sse`
  should 200 + emit at least one `event: endpoint` line.
- Oracle-side check: `systemctl is-active mcp-*-proxy.service`.
- Tunnel check on phone: `ss -ltn | grep -E ':310[1-7]'`.

Expected cadence: run hourly via cron; Slack-alert on failures.

## Rollback

Every old stdio config is preserved in `_mcpServersDisabled` within each
settings.json before the cutover. To roll back: rename the keys back and
restart the CLI. Old Python servers on the phone never moved -- they are
still at `06_DEVELOPMENT/mcp_servers/*/server.py` and runnable standalone.

## Non-goals

- Public MCP gateway (would need auth/WAF -- out of scope).
- Multi-tenant usage metrics -- not needed yet.
- Replacing the `hcom` hook stack -- that is orthogonal.
