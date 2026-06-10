#!/usr/bin/env bash
# jarvis_status.sh -- one-shot health view of the entire Lucrex stack.
#
# Run anytime to see what's wired and what's broken. Color-coded:
#   GREEN  = healthy
#   YELLOW = degraded but functional
#   RED    = down

set -uo pipefail

if [[ -t 1 ]]; then
    G=$'\033[0;32m'; Y=$'\033[0;33m'; R=$'\033[0;31m'; C=$'\033[0;36m'
    B=$'\033[1m'; N=$'\033[0m'
else
    G=""; Y=""; R=""; C=""; B=""; N=""
fi

ok()    { echo "${G}✓${N} $1"; }
warn()  { echo "${Y}!${N} $1"; }
red()   { echo "${R}✗${N} $1"; }
header(){ echo ""; echo "${C}${B}━━━ $1 ━━━${N}"; }

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "${B}LUCREX JARVIS STATUS${N}  --  $ts"

# ── 1. CLI <-> Computer runners ────────────────────────────────────
header "Runners (CLI ↔ Computer ↔ Cloud Agent bridges)"
for svc in lucrex-desktop-runner lucrex-browser-use-runner lucrex-managed-agent-runner \
           lucrex-status-indicator lucrex-floating-status \
           bt-levn-keeper hive-sync-watch blinko-lite; do
    s=$(systemctl --user is-active ${svc}.service 2>/dev/null)
    if [[ "$s" == "active" ]]; then
        ok "${svc}: active"
    else
        red "${svc}: ${s}"
    fi
done

# ── 2. MCP fleet (7 servers per FLEET_PLAN.md) ─────────────────────
header "MCP Fleet (HTTP/SSE on 127.0.0.1)"
declare -A mcp_ports=( \
    [blinko-memory]=3101 \
    [market-intel]=3102 \
    [n8n]=3103 \
    [broker-os]=3104 \
    [supabase]=3105 \
    [stripe]=3106 \
    [resend]=3107 \
)
for name in blinko-memory market-intel n8n broker-os supabase stripe resend; do
    port=${mcp_ports[$name]}
    if ss -tln 2>/dev/null | grep -q ":${port}\b"; then
        svc_state=$(systemctl --user is-active mcp-${name}.service 2>/dev/null)
        ok "mcp-${name} (port ${port}, svc=${svc_state})"
    else
        red "mcp-${name} (port ${port}) -- not listening"
    fi
done

# ── 3. Tailscale mesh ──────────────────────────────────────────────
header "Tailscale Mesh"
if command -v tailscale >/dev/null 2>&1; then
    online=$(tailscale status 2>/dev/null | grep -c -v "offline\|^#" || echo 0)
    total=$(tailscale status 2>/dev/null | grep -v "^#" | grep -v "^$" | wc -l)
    if [[ "$online" -gt 0 ]]; then
        ok "tailscale: ${online}/${total} nodes online"
        tailscale status 2>/dev/null | head -5 | sed 's/^/    /'
    else
        warn "tailscale: 0/${total} nodes online (this PC only)"
    fi
else
    red "tailscale: not installed"
fi

# ── 4. Audit log + git sync ────────────────────────────────────────
header "Audit Trail"
if [[ -d /tmp/everlight-audit-log/.git ]]; then
    last_ts=$(GIT_DIR=/tmp/everlight-audit-log/.git git log -1 --format=%ct 2>/dev/null || echo 0)
    age_min=$(( ( $(date +%s) - last_ts ) / 60 ))
    if [[ "$age_min" -lt 120 ]]; then
        ok "audit log: last push ${age_min}min ago"
    else
        warn "audit log: last push ${age_min}min ago (>2h, cron may be stuck)"
    fi
else
    red "audit log: /tmp/everlight-audit-log/.git missing"
fi

# Workspace git -- check we're not pointing at audit-log accidentally
ws_remote=$(git -C /AA_MY_DRIVE remote get-url origin 2>/dev/null || echo "none")
if [[ "$ws_remote" == "none" ]]; then
    warn "workspace: no 'origin' remote (good -- prevents accidental push to wrong repo)"
elif [[ "$ws_remote" == *"audit-log"* ]]; then
    red "workspace: origin points at audit-log repo (DANGER -- any push goes to wrong place)"
else
    ok "workspace: origin -> ${ws_remote}"
fi

# ── 5. Outbound halt + DNC + compliance ────────────────────────────
header "Compliance Gates"
halt=$(grep "^WHOLESALE_OUTBOUND_HALT=" /AA_MY_DRIVE/.env 2>/dev/null | cut -d= -f2 | tr -d '"')
if [[ "$halt" == "1" ]]; then
    warn "WHOLESALE_OUTBOUND_HALT=1 (cold/bulk sends BLOCKED -- intentional)"
else
    ok "WHOLESALE_OUTBOUND_HALT=${halt:-0} (sends allowed -- check this is intentional)"
fi
# 2L/3L keys check
if grep -q "^ANTHROPIC_API_KEY_COMPLIANCE=" /AA_MY_DRIVE/.env 2>/dev/null \
   && grep -q "^ANTHROPIC_API_KEY_AUDIT=" /AA_MY_DRIVE/.env 2>/dev/null; then
    ok "2L+3L API keys provisioned (tier separation active)"
else
    red "2L+3L API keys missing -- halt-lift blocked"
fi

# ── 6. Audio + Bluetooth ────────────────────────────────────────────
header "Audio + Bluetooth"
if pgrep -x pipewire >/dev/null && pgrep -x wireplumber >/dev/null; then
    ok "pipewire + wireplumber: running"
else
    red "audio stack: pipewire or wireplumber not running"
fi
if rfkill list bluetooth 2>/dev/null | grep -q "Soft blocked: no"; then
    bt_ctrl=$(bluetoothctl show 2>/dev/null | grep -c "Powered: yes")
    if [[ "$bt_ctrl" -gt 0 ]]; then
        connected=$(bluetoothctl devices Connected 2>/dev/null | wc -l)
        ok "bluetooth: powered, ${connected} device(s) connected"
        bluetoothctl devices Connected 2>/dev/null | sed 's/^/    /'
    else
        warn "bluetooth: not powered"
    fi
else
    red "bluetooth: rfkill blocked"
fi

# ── 7. Brave CDP for browser_use_runner ─────────────────────────────
header "Brave CDP Bridge"
if curl -s -m 1 http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
    ok "Brave CDP: listening on 9222 (browser_use_runner can attach)"
else
    warn "Brave CDP: not listening (start with --remote-debugging-port=9222 to enable browser_use)"
fi

# ── 8. Storage ──────────────────────────────────────────────────────
header "Storage"
df -h /AA_MY_DRIVE 2>/dev/null | tail -1 | awk '{
    pct=$5; gsub("%","",pct);
    if (pct < 80) print "✓ AA_MY_DRIVE: " $3 " used / " $2 " (" $5 " full)";
    else if (pct < 95) print "! AA_MY_DRIVE: " $5 " full -- approaching limit";
    else print "✗ AA_MY_DRIVE: " $5 " full -- CRITICAL";
}'
echo ""
queue_pending=$(ls /AA_MY_DRIVE/_logs/browser_tasks/pending/ 2>/dev/null | wc -l)
queue_in_progress=$(ls /AA_MY_DRIVE/_logs/browser_tasks/in_progress/ 2>/dev/null | wc -l)
echo "  queue: pending=${queue_pending} in_progress=${queue_in_progress}"

echo ""
echo "${C}${B}━━━ Summary ━━━${N}"
echo "Generated: $ts | Run: bash $0 | Source: /AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/jarvis_status.sh"
