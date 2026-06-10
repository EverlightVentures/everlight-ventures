#!/usr/bin/env bash
# halt_check.sh -- 30-second outbound-system sanity dashboard.
#
# Run any time. Exit 0 if all green; exit 1 if anything red.
# Output: 8-line dashboard with the things that matter most.
#
# Companion to restart_harness.py. Use this when Rich asks "are we safe to send?"

set -uo pipefail

# Source project .env so persistent flags (WHOLESALE_OUTBOUND_HALT, AUDIT_REPO_*, RESEND_API_KEY)
# propagate into halt_check regardless of invoking shell or cron context.
if [[ -f /AA_MY_DRIVE/.env ]]; then
    set -a; source /AA_MY_DRIVE/.env 2>/dev/null || true; set +a
fi

# Colors (only if stdout is a TTY)
if [[ -t 1 ]]; then
    GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; YELLOW=$'\033[0;33m'; CYAN=$'\033[0;36m'; NC=$'\033[0m'
else
    GREEN=""; RED=""; YELLOW=""; CYAN=""; NC=""
fi

red_count=0
mark_ok()   { echo "${GREEN}OK${NC}    $1"; }
mark_warn() { echo "${YELLOW}WARN${NC}  $1"; red_count=$((red_count + 1)); }
mark_red()  { echo "${RED}RED${NC}   $1"; red_count=$((red_count + 1)); }

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "${CYAN}=== Everlight Outbound Halt Check -- $ts ===${NC}"

# ── 1. WHOLESALE_OUTBOUND_HALT flag ────────────────────────────────
halt_val="${WHOLESALE_OUTBOUND_HALT:-}"
case "${halt_val,,}" in
    1|true|yes|on)
        mark_warn "WHOLESALE_OUTBOUND_HALT=$halt_val (cold/bulk sends blocked)"
        ;;
    ""|0|false|no|off)
        mark_ok "WHOLESALE_OUTBOUND_HALT off (cold/bulk allowed if other gates pass)"
        ;;
    *)
        mark_warn "WHOLESALE_OUTBOUND_HALT='$halt_val' (unrecognized -- treated as off)"
        ;;
esac

# ── 2. DNC reconcile -- last run + sink count diff ─────────────────
dnc_log_dir="/AA_MY_DRIVE/_logs/dnc_reconcile"
if [[ -d "$dnc_log_dir" ]]; then
    latest_dnc="$(ls -t "$dnc_log_dir"/*.md "$dnc_log_dir"/*.json 2>/dev/null | head -1)"
    if [[ -n "$latest_dnc" ]]; then
        age_h="$(( ( $(date +%s) - $(stat -c %Y "$latest_dnc") ) / 3600 ))"
        if [[ "$age_h" -gt 26 ]]; then
            mark_warn "DNC reconcile last run ${age_h}h ago (cron drift?)"
        else
            mark_ok "DNC reconcile last run ${age_h}h ago"
        fi
    else
        mark_warn "DNC reconcile log dir exists but empty"
    fi
else
    # Fall back to checking dnc_list.json mtime
    dnc_json="/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json"
    if [[ -f "$dnc_json" ]]; then
        mark_warn "DNC reconcile log dir missing -- last dnc_list.json edit $(stat -c %y "$dnc_json" | cut -d. -f1)"
    else
        mark_red "DNC list missing entirely"
    fi
fi

# ── 3. Audit log push -- last commit timestamp ─────────────────────
audit_repo="${AUDIT_REPO_DIR:-/AA_MY_DRIVE/_audit_repo}"
if [[ -d "$audit_repo/.git" ]]; then
    last_commit_ts="$(GIT_DIR="$audit_repo/.git" git log -1 --format=%ct 2>/dev/null || echo 0)"
    if [[ "$last_commit_ts" -gt 0 ]]; then
        age_min="$(( ( $(date +%s) - last_commit_ts ) / 60 ))"
        if [[ "$age_min" -gt 120 ]]; then
            mark_warn "audit-log last push ${age_min}min ago (cron may be stuck)"
        else
            mark_ok "audit-log last push ${age_min}min ago"
        fi
    else
        mark_warn "audit-log repo present but no commits"
    fi
else
    mark_warn "audit-log repo not cloned (run audit_log_cron.sh once)"
fi

# ── 4. Resend budget remaining today ───────────────────────────────
resend_budget_file="/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/resend_budget_state.json"
if [[ -f "$resend_budget_file" ]]; then
    today_count="$(python3 -c "
import json,sys
from datetime import date
try:
    d = json.load(open('$resend_budget_file'))
    t = str(date.today())
    print(int(d.get('daily', {}).get(t, 0)))
except Exception:
    print(0)
" 2>/dev/null || echo 0)"
    daily_cap="${RESEND_DAILY_CAP:-100}"
    remaining="$((daily_cap - today_count))"
    if [[ "$remaining" -lt 10 ]]; then
        mark_warn "Resend daily budget: ${today_count}/${daily_cap} used (${remaining} left)"
    else
        mark_ok "Resend daily budget: ${today_count}/${daily_cap} used (${remaining} left)"
    fi
else
    mark_ok "Resend budget tracker not yet started today (0 sent)"
fi

# ── 5. Open compliance halts in last 24h ───────────────────────────
phrase_scrub="/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/phrase_scrub_blocks.jsonl"
if [[ -f "$phrase_scrub" ]]; then
    blocks_24h="$(python3 -c "
import json
from datetime import datetime, timezone, timedelta
cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
n = 0
try:
    with open('$phrase_scrub', 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line: continue
            try:
                rec = json.loads(line)
                ts = rec.get('ts', '')
                if not ts: continue
                t = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                if t >= cutoff: n += 1
            except Exception:
                continue
except Exception:
    pass
print(n)
" 2>/dev/null || echo 0)"
    if [[ "$blocks_24h" -gt 50 ]]; then
        mark_warn "Compliance blocks last 24h: $blocks_24h (high -- investigate)"
    else
        mark_ok "Compliance blocks last 24h: $blocks_24h"
    fi
else
    mark_ok "Compliance blocks last 24h: 0 (no log yet)"
fi

# ── 6. Recipient class tokens file freshness ───────────────────────
tokens="/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/blocked_domain_tokens.json"
if [[ -f "$tokens" ]]; then
    age_d="$(( ( $(date +%s) - $(stat -c %Y "$tokens") ) / 86400 ))"
    if [[ "$age_d" -gt 90 ]]; then
        mark_warn "blocked_domain_tokens.json ${age_d}d old (audit overdue)"
    else
        mark_ok "blocked_domain_tokens.json ${age_d}d old"
    fi
else
    mark_red "blocked_domain_tokens.json MISSING"
fi

# ── 7. 2L/3L API key separation status ─────────────────────────────
if [[ -n "${ANTHROPIC_API_KEY_COMPLIANCE:-}" && -n "${ANTHROPIC_API_KEY_AUDIT:-}" ]]; then
    mark_ok "2L+3L API keys provisioned (separation active)"
elif [[ -n "${ANTHROPIC_API_KEY_COMPLIANCE:-}" ]]; then
    mark_warn "2L key present, 3L missing (partial separation)"
else
    mark_warn "2L/3L API keys not yet provisioned (tier separation inactive)"
fi

# ── 8. Summary ─────────────────────────────────────────────────────
echo "------------------------------------------------------------"
if [[ "$red_count" -eq 0 ]]; then
    echo "${GREEN}ALL GREEN${NC} -- safe to operate"
    exit 0
else
    echo "${RED}$red_count RED/WARN${NC} -- investigate before lifting halt"
    exit 1
fi
