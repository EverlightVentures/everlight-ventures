#!/usr/bin/env bash
# mcp_install_kit.sh -- stand up server-backed MCPs on e5-mother as HTTP/SSE,
# tunneled to the phone, matching the existing broker-os MCP pattern.
#
# ARCHITECTURE (matches the 7 MCPs already in .mcp.json):
#   MCP server runs on e5-mother (node present) in HTTP/SSE mode on a 31xx port.
#   SSH reverse/forward tunnel maps it to 127.0.0.1:31xx on the phone.
#   Phone .mcp.json adds an {"type":"http","url":"http://127.0.0.1:31xx/mcp"} entry.
#
# WHY NOT "claude plugin install" ON e5-mother:
#   That only helps agents running ON e5-mother. Rich's interactive Claude runs on
#   the phone. And e5-mother has NO claude CLI (probed 2026-05-24). HTTP-tunnel is
#   the correct, infra-consistent path. HARD LAW feedback_phone_proot_cannot_npm_install
#   is why the node processes live on e5-mother, not the phone.
#
# e5-mother probe (2026-05-24): node v20.20.2 OK, npm 10.8.2 OK, python3.10 OK,
#   claude MISSING, uvx MISSING. This kit installs uv (for any uvx MCPs) and uses npx.
#
# RUN:  ssh e5-mother 'bash -s' < mcp_install_kit.sh
# Then on the PHONE: append the printed .mcp.json snippet + add tunnels to start_hive.
set -euo pipefail
log(){ printf '\n=== %s ===\n' "$*"; }

command -v node >/dev/null || { echo "node missing on e5-mother"; exit 1; }
command -v uvx  >/dev/null 2>&1 || { log "installing uv (for serena/semgrep)"; curl -LsSf https://astral.sh/uv/install.sh | sh || echo "uv install failed -- skip uvx MCPs"; }

PORT_PLAYWRIGHT=3110   # browser automation -> hermes_browser_outreach + everlight_hyperframes (MICRO)
PORT_FIRECRAWL=3111    # web scrape/crawl -> intel_center + outreach (MICRO)
PORT_SERENA=3112       # semantic code intel -> 122-agent eng team
PORT_SEMGREP=3113      # security scanning -> 69_security_engineer

mkdir -p ~/mcp_logs
run_bg(){ # name port cmd...
  local name="$1" port="$2"; shift 2
  if curl -fsS "http://127.0.0.1:${port}/" >/dev/null 2>&1; then echo "  ${name} already up on ${port}"; return; fi
  echo "  starting ${name} on 127.0.0.1:${port}"
  EV_BIND=127.0.0.1 nohup "$@" >"$HOME/mcp_logs/${name}.log" 2>&1 &
  sleep 2
}

log "PLAYWRIGHT MCP (HTTP)"
run_bg playwright "$PORT_PLAYWRIGHT" npx -y @playwright/mcp@latest --host 127.0.0.1 --port "$PORT_PLAYWRIGHT"
echo "  post-install: npx playwright install chromium"

log "FIRECRAWL MCP (HTTP) -- needs FIRECRAWL_API_KEY in env, else self-host"
[ -n "${FIRECRAWL_API_KEY:-}" ] && run_bg firecrawl "$PORT_FIRECRAWL" npx -y firecrawl-mcp --host 127.0.0.1 --port "$PORT_FIRECRAWL" || echo "  SKIPPED firecrawl: set FIRECRAWL_API_KEY first"

log "SERENA MCP (SSE) -- semantic code"
command -v uvx >/dev/null 2>&1 && run_bg serena "$PORT_SERENA" uvx --from git+https://github.com/oraios/serena serena start-mcp-server --transport sse --port "$PORT_SERENA" || echo "  SKIPPED serena: uvx unavailable"

log "SEMGREP MCP -- security scanning"
command -v uvx >/dev/null 2>&1 && run_bg semgrep "$PORT_SEMGREP" uvx semgrep-mcp --transport sse --port "$PORT_SEMGREP" || echo "  SKIPPED semgrep: uvx unavailable"

log "PHONE-SIDE WIRING (do these on the phone after this kit succeeds)"
cat <<NOTES
  1) Tunnels (add to the SSH tunnel block in start_hive / boot script):
       ssh -N -L 127.0.0.1:${PORT_PLAYWRIGHT}:127.0.0.1:${PORT_PLAYWRIGHT} \\
              -L 127.0.0.1:${PORT_FIRECRAWL}:127.0.0.1:${PORT_FIRECRAWL} \\
              -L 127.0.0.1:${PORT_SERENA}:127.0.0.1:${PORT_SERENA} \\
              -L 127.0.0.1:${PORT_SEMGREP}:127.0.0.1:${PORT_SEMGREP} e5-mother
  2) Append to /mnt/sdcard/AA_MY_DRIVE/.mcp.json "mcpServers":
       "playwright": {"type":"http","url":"http://127.0.0.1:${PORT_PLAYWRIGHT}/mcp"},
       "firecrawl":  {"type":"http","url":"http://127.0.0.1:${PORT_FIRECRAWL}/mcp"},
       "serena":     {"type":"http","url":"http://127.0.0.1:${PORT_SERENA}/sse"},
       "semgrep":    {"type":"http","url":"http://127.0.0.1:${PORT_SEMGREP}/sse"}
  3) context7 (HOSTED -- no e5-mother server needed) add directly to phone .mcp.json:
       "context7": {"type":"http","url":"https://mcp.context7.com/mcp","headers":{"CONTEXT7_API_KEY":"<key from context7.com>"}}
  4) Restart Claude on the phone to load the new MCP entries.
NOTES
log "DONE"
