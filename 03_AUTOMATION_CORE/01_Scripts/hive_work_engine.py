#!/usr/bin/env python3
"""
Hive Work Engine -- Real task execution for Everlight Ventures agents.

The shift system (hive_shift_system.py) handles AI chat and personality.
This engine handles ACTUAL TASK EXECUTION. It runs the real commands,
captures real output, and posts real results to Slack.

Runs every hour via cron, 5 minutes after the shift system chat.

Cron:
  5 * * * * source /home/opc/.env && cd /home/opc && python3 hive_work_engine.py >> /tmp/hive_work.log 2>&1

CLI:
  python3 hive_work_engine.py           # Run engine (execute tasks for current shift)
  python3 hive_work_engine.py --status  # Print last execution status for all agents
  python3 hive_work_engine.py --dry-run # Show what would run without executing
"""

import subprocess
import json
import time
import os
import sys
import logging
import argparse
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SLACK_BOT_TOKEN = os.environ.get(
    "SLACK_BOT_TOKEN",
    "xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy",
)

CHANNELS = {
    "war-room": "C0ANAU30UQ2",
    "ft-hunters": "C0AMVEWLT9D",
    "ft-consult": "C0ANEG19WQ4",
    "ft-markets": "C0AP56SFQG0",
    "ft-profit-engine": "C0AN7FT5JBF",
    "ai-consulting": "C0AN8SGAS22",
    "xlm-trading": "C0AN8SG030W",
    "ceo-brief": "C0AP56SQM08",
    "hive-alerts": "C0ANPRCA4AD",
    "watercooler": "C0AN0NQR17Z",
}

PT = timezone(timedelta(hours=-7))  # PDT
WORK_LEDGER = Path("/home/opc/hive_work_ledger.json")
TASK_TIMEOUT = 60  # seconds

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WORK] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("hive_work_engine")

# ---------------------------------------------------------------------------
# Agent Task Assignments
# ---------------------------------------------------------------------------
AGENT_TASKS = {
    # REX BLACKWELL -- Wholesale Scout
    "Rex Blackwell": {
        "channel": "ft-hunters",
        "shift": "morning",
        "tasks": [
            {
                "name": "surplus_scan",
                "description": "Scan LA County excess proceeds for claims >$10k",
                "command": (
                    "cd /home/opc/wholesale_agent && "
                    "python3 surplus_funds_finder.py --county la --min-amount 10000"
                ),
                "frequency": "daily",
                "output_key": "leads_found",
                "report_template": "Surplus scan: {leads_found}",
            },
            {
                "name": "pipeline_check",
                "description": "Check wholesale pipeline status from Django",
                "command": (
                    "cd /home/opc/hive_django && python3 -c \""
                    "import django,os;"
                    "os.environ['DJANGO_SETTINGS_MODULE']='hive_dashboard.settings';"
                    "django.setup();"
                    "from broker_ops.models import PropertyLead,InvestorBuyer,BrokerMatch,Deal;"
                    "active = Deal.objects.filter(stage__in=[\\\"intro\\\",\\\"negotiating\\\",\\\"contracted\\\",\\\"active\\\"]).count();"
                    "won = Deal.objects.filter(stage=\\\"closed_won\\\").count();"
                    "print(f'property_leads={PropertyLead.objects.count()},"
                    "buyers={InvestorBuyer.objects.count()},"
                    "pending_matches={BrokerMatch.objects.filter(status=\\\"pending\\\").count()},"
                    "approved_matches={BrokerMatch.objects.filter(status=\\\"approved\\\").count()},"
                    "active_deals={active},won={won}')\""
                ),
                "frequency": "hourly",
                "output_key": "pipeline_stats",
                "report_template": "Pipeline: {pipeline_stats}",
            },
        ],
    },
    # PIPER REEVES -- Outreach
    "Piper Reeves": {
        "channel": "ft-hunters",
        "shift": "morning",
        "tasks": [
            {
                "name": "outreach_status",
                "description": "Check outreach email status and tracker",
                "command": (
                    "cd /home/opc/hive_django && python3 -c \""
                    "import django,os;"
                    "os.environ['DJANGO_SETTINGS_MODULE']='hive_dashboard.settings';"
                    "django.setup();"
                    "from broker_ops.models import OutreachSequence,BrokerMatch;"
                    "print(f'pending={OutreachSequence.objects.filter(status=\\\"pending\\\").count()},"
                    "sent={OutreachSequence.objects.filter(status=\\\"sent\\\").count()},"
                    "replied={OutreachSequence.objects.filter(status=\\\"replied\\\").count()},"
                    "bounced={OutreachSequence.objects.filter(status=\\\"bounced\\\").count()},"
                    "approved_matches={BrokerMatch.objects.filter(status=\\\"approved\\\").count()}')\""
                ),
                "frequency": "hourly",
                "output_key": "outreach_stats",
                "report_template": "Outreach status: {outreach_stats}",
            },
        ],
    },
    # PENNY VANCE -- Finance
    "Penny Vance": {
        "channel": "ft-profit-engine",
        "shift": "morning",
        "tasks": [
            {
                "name": "revenue_check",
                "description": "Pull revenue numbers across all streams",
                "command": (
                    "cd /home/opc/hive_django && python3 -c \""
                    "import django,os;"
                    "os.environ['DJANGO_SETTINGS_MODULE']='hive_dashboard.settings';"
                    "django.setup();"
                    "from django.db.models import Sum;"
                    "from broker_ops.models import Deal,CommissionRecord;"
                    "active = Deal.objects.filter(stage__in=[\\\"intro\\\",\\\"negotiating\\\",\\\"contracted\\\",\\\"active\\\"]).count();"
                    "won = Deal.objects.filter(stage=\\\"closed_won\\\").count();"
                    "pending = CommissionRecord.objects.filter(record_type=\\\"pending\\\").aggregate(total=Sum(\\\"amount\\\")).get(\\\"total\\\") or 0;"
                    "paid = CommissionRecord.objects.filter(record_type=\\\"paid\\\").aggregate(total=Sum(\\\"amount\\\")).get(\\\"total\\\") or 0;"
                    "print(f'active_deals={active},closed_won={won},pending_commission=${float(pending):,.0f},paid_commission=${float(paid):,.0f}')\""
                    " 2>/dev/null || echo 'revenue=unavailable'"
                ),
                "frequency": "hourly",
                "output_key": "revenue_stats",
                "report_template": "Revenue check: {revenue_stats}",
            },
            {
                "name": "bot_pnl",
                "description": "Pull XLM bot P&L data",
                "command": (
                    "cat /home/opc/xlm-bot/data/state.json 2>/dev/null | python3 -c \""
                    "import sys,json;"
                    "s=json.load(sys.stdin);"
                    "print(f'equity=${float(s.get(\\\"equity_start_usd\\\",0) or 0):,.2f},"
                    "pnl_today=${float(s.get(\\\"pnl_today_usd\\\",0) or 0):,.2f},"
                    "trades={int(s.get(\\\"trades\\\",0) or 0)},"
                    "vol={s.get(\\\"vol_state\\\",\\\"unknown\\\")},"
                    "safe_mode={\\\"yes\\\" if s.get(\\\"safe_mode\\\") else \\\"no\\\"}')\" "
                    "2>/dev/null || echo 'bot=offline'"
                ),
                "frequency": "hourly",
                "output_key": "bot_stats",
                "report_template": "Bot P&L: {bot_stats}",
            },
        ],
    },
    # REX THORNTON -- Trading Risk
    "Rex Thornton": {
        "channel": "xlm-trading",
        "shift": "swing",
        "tasks": [
            {
                "name": "market_intel",
                "description": "Pull latest market intel from sentiment + correlation + onchain",
                "command": "cd /home/opc/xlm-bot && python3 -m market.intel_runner 2>&1 | tail -5",
                "frequency": "hourly",
                "output_key": "intel_result",
                "report_template": "Market intel refresh: {intel_result}",
            },
            {
                "name": "trade_log",
                "description": "Check current trade/risk state from live bot state",
                "command": (
                    "cat /home/opc/xlm-bot/data/state.json 2>/dev/null | python3 -c \""
                    "import sys,json;"
                    "s=json.load(sys.stdin);"
                    "hist=s.get(\\\"adaptive_direction_history\\\") or [];"
                    "last=hist[-1] if hist else {};"
                    "print(f'trades={int(s.get(\\\"trades\\\",0) or 0)},"
                    "last_exit={s.get(\\\"last_exit_direction\\\",\\\"flat\\\")}@{s.get(\\\"last_exit_price\\\",\\\"n/a\\\")},"
                    "last_result={last.get(\\\"result\\\",\\\"n/a\\\")},"
                    "safe_mode={\\\"yes\\\" if s.get(\\\"safe_mode\\\") else \\\"no\\\"},"
                    "reason={s.get(\\\"safe_mode_reason\\\",\\\"none\\\")}')\" "
                    "2>/dev/null || echo 'trade_state=unavailable'"
                ),
                "frequency": "hourly",
                "output_key": "recent_trades",
                "report_template": "Recent trades:\n{recent_trades}",
            },
        ],
    },
    # RYAN KIM -- GTM / Consulting
    "Ryan Kim": {
        "channel": "ft-consult",
        "shift": "morning",
        "tasks": [
            {
                "name": "scout_deals",
                "description": "Scout fresh SaaS/AI deals from HN and Product Hunt",
                "command": (
                    "cd /home/opc/hive_django && python3 manage.py broker_run status 2>&1 | tail -8"
                ),
                "frequency": "daily",
                "output_key": "scout_stats",
                "report_template": "Deal scout: {scout_stats}",
            },
        ],
    },
    # QUINN SHARP -- Systems / Infrastructure
    "Quinn Sharp": {
        "channel": "hive-alerts",
        "shift": "night",
        "tasks": [
            {
                "name": "health_check",
                "description": "Check all Oracle services and disk",
                "command": (
                    "echo disk=$(df -h / | tail -1 | awk '{print $5}') && "
                    "for svc in blinko n8n hive-django hive-dashboard hive-voice hive-slack-agent xlm-bot xlm-dashboard; do "
                    "echo $svc=$(systemctl is-active $svc.service 2>/dev/null || echo 'unknown'); done"
                ),
                "frequency": "hourly",
                "output_key": "health",
                "report_template": "System health:\n{health}",
            },
        ],
    },
    # CHRISTOPHER WOLFE -- Data Verification (night lead)
    "Christopher Wolfe": {
        "channel": "ft-markets",
        "shift": "night",
        "tasks": [
            {
                "name": "verify_data",
                "description": "Cross-check market data freshness",
                "command": (
                    "for f in sentiment_shift.json onchain_alerts.json correlation_drift.json market_brief.json; do "
                    "echo -n \"$f: \"; "
                    "stat -c '%Y' /home/opc/xlm-bot/data/$f 2>/dev/null | "
                    "python3 -c \""
                    "import sys,time;"
                    "ts=int(sys.stdin.read());"
                    "age=int(time.time()-ts);"
                    "h=age//3600;m=(age%3600)//60;"
                    "print(f'{h}h{m}m old')\" "
                    "2>/dev/null || echo 'missing'; done"
                ),
                "frequency": "hourly",
                "output_key": "data_freshness",
                "report_template": "Data verification:\n{data_freshness}",
            },
        ],
    },
    # MARCUS COLE -- CEO, always runs
    "Marcus Cole": {
        "channel": "war-room",
        "shift": "all",
        "tasks": [
            {
                "name": "daily_brief",
                "description": "Compile CEO daily brief data",
                "command": (
                    "cat /home/opc/xlm-bot/data/state.json 2>/dev/null | python3 -c \""
                    "import sys,json;"
                    "s=json.load(sys.stdin);"
                    "print(f'equity=${float(s.get(\\\"equity_start_usd\\\",0) or 0):,.2f},"
                    "pnl_today=${float(s.get(\\\"pnl_today_usd\\\",0) or 0):,.2f},"
                    "trades={int(s.get(\\\"trades\\\",0) or 0)},"
                    "position={\\\"open\\\" if s.get(\\\"open_position\\\") else \\\"flat\\\"},"
                    "safe_mode={\\\"yes\\\" if s.get(\\\"safe_mode\\\") else \\\"no\\\"}')\" "
                    "2>/dev/null || echo 'bot=offline'"
                ),
                "frequency": "daily_7am",
                "output_key": "brief_data",
                "report_template": "CEO Brief: {brief_data}",
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Slack Posting
# ---------------------------------------------------------------------------
def post(channel_name: str, text: str) -> bool:
    """Post a message to Slack via bot token. Returns True on success."""
    cid = CHANNELS.get(channel_name)
    if not cid or not text:
        log.warning("Slack skip: channel=%s text=%s", channel_name, bool(text))
        return False
    try:
        r = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"channel": cid, "text": text},
            timeout=15,
        )
        ok = r.json().get("ok", False)
        if not ok:
            log.warning("Slack error: %s", r.json().get("error", "unknown"))
        return ok
    except Exception as e:
        log.error("Slack post failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Ledger Management
# ---------------------------------------------------------------------------
def load_ledger() -> dict:
    """Load work ledger from disk."""
    if WORK_LEDGER.exists():
        try:
            return json.loads(WORK_LEDGER.read_text())
        except (json.JSONDecodeError, OSError) as e:
            log.error("Ledger corrupt, starting fresh: %s", e)
    return {"entries": [], "last_run": {}}


def save_ledger(ledger: dict):
    """Save work ledger to disk."""
    try:
        WORK_LEDGER.write_text(json.dumps(ledger, indent=2, default=str))
    except OSError as e:
        log.error("Failed to save ledger: %s", e)


# ---------------------------------------------------------------------------
# Scheduling Logic
# ---------------------------------------------------------------------------
def get_current_shift() -> str:
    """Determine current shift based on PT hour."""
    hour = datetime.now(PT).hour
    if 6 <= hour < 14:
        return "morning"
    elif 14 <= hour < 22:
        return "swing"
    else:
        return "night"


def should_run(task: dict, ledger: dict) -> bool:
    """Check if a task should run this cycle based on its frequency."""
    key = task["name"]
    last = ledger.get("last_run", {}).get(key, "")
    now = datetime.now(PT)

    freq = task.get("frequency", "hourly")

    if freq == "hourly":
        # Don't re-run if we already ran in the same clock hour
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                if last_dt.hour == now.hour and last_dt.date() == now.date():
                    return False
            except ValueError:
                pass
        return True
    elif freq == "daily":
        return last[:10] != now.strftime("%Y-%m-%d")
    elif freq == "daily_7am":
        return now.hour == 7 and last[:10] != now.strftime("%Y-%m-%d")
    return True


# ---------------------------------------------------------------------------
# Task Execution
# ---------------------------------------------------------------------------
def execute_task(task: dict) -> dict:
    """Run the actual shell command and capture output."""
    try:
        result = subprocess.run(
            task["command"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=TASK_TIMEOUT,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        output = stdout or stderr or "no output"
        success = result.returncode == 0
        return {"success": success, "output": output, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": f"timeout after {TASK_TIMEOUT}s", "returncode": -1}
    except Exception as e:
        return {"success": False, "output": str(e), "returncode": -1}


def _classify_result(task: dict, result: dict) -> str:
    """Return OK, WARN, or FAIL based on command success and evidence quality."""
    output = str(result.get("output") or "").strip()
    collapsed = " ".join(output.split())
    lower = collapsed.lower()

    if not result.get("success"):
        return "FAIL"
    if any(marker in lower for marker in ("traceback", "importerror", "modulenotfounderror", "error:", "exception")):
        return "FAIL"
    if collapsed in ("", "(no output)", "0"):
        return "WARN"

    task_name = str(task.get("name") or "")
    warn_markers = {
        "outreach_status": ("pending=0,sent=0,replied=0,bounced=0", "approved_matches=0"),
        "bot_pnl": ("equity=$0.00,pnl_today=$0.00,trades=0", "bot=offline"),
        "daily_brief": ("equity=$0.00,pnl_today=$0.00,trades=0", "bot=offline"),
        "trade_log": ("trade_state=unavailable",),
        "scout_deals": ("offers:  0 total", "leads:   0 total", "matches: 0 total", "deals:   0 total"),
        "revenue_check": ("revenue=unavailable",),
    }
    if any(marker in lower for marker in warn_markers.get(task_name, ())):
        return "WARN"
    return "OK"


def format_report(task: dict, result: dict, status: str) -> str:
    """Format the task result into a Slack-ready report string."""
    output_short = result["output"][:500]
    try:
        report = task["report_template"].format(**{task["output_key"]: output_short})
    except (KeyError, IndexError):
        report = f"{task['description']}: {output_short}"
    label = {
        "OK": "Evidence",
        "WARN": "Current signal",
        "FAIL": "Error",
    }.get(status, "Evidence")
    if output_short:
        report = f"{report}\n{label}: {output_short}"
    return report


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------
def run_engine(dry_run: bool = False):
    """Execute tasks for the current shift. Posts results to Slack."""
    now = datetime.now(PT)
    current_shift = get_current_shift()
    ledger = load_ledger()

    log.info("=" * 60)
    log.info("Work Engine | %s | %s shift", now.strftime("%Y-%m-%d %I:%M %p PT"), current_shift)
    log.info("=" * 60)

    executed = 0
    skipped = 0
    failed = 0
    warned = 0

    for agent_name, config in AGENT_TASKS.items():
        agent_shift = config["shift"]
        if agent_shift not in (current_shift, "all"):
            continue

        for task in config["tasks"]:
            if not should_run(task, ledger):
                log.info("  SKIP %s/%s (already ran this cycle)", agent_name, task["name"])
                skipped += 1
                continue

            if dry_run:
                log.info("  DRY-RUN %s/%s: %s", agent_name, task["name"], task["command"][:80])
                skipped += 1
                continue

            log.info("  EXEC %s/%s ...", agent_name, task["name"])
            result = execute_task(task)
            status = _classify_result(task, result)

            status_tag = status
            log.info("    [%s] %s", status_tag, result["output"][:120])

            # Record in ledger
            ledger.setdefault("last_run", {})[task["name"]] = now.isoformat()
            ledger.setdefault("entries", []).append({
                "agent": agent_name,
                "task": task["name"],
                "timestamp": now.isoformat(),
                "shift": current_shift,
                "success": result["success"],
                "status": status,
                "output": result["output"][:500],
            })

            # Keep ledger bounded
            if len(ledger["entries"]) > 500:
                ledger["entries"] = ledger["entries"][-500:]

            # Post to Slack
            report = format_report(task, result, status)
            status_emoji = {
                "OK": "[VERIFIED WORK]",
                "WARN": "[ACTION NEEDED]",
                "FAIL": "[WORK FAILED]",
            }.get(status, "[WORK CHECK]")
            slack_msg = f"*{agent_name}* {status_emoji}\n{report}"
            post(config["channel"], slack_msg)

            executed += 1
            if status == "FAIL":
                failed += 1
            elif status == "WARN":
                warned += 1

            time.sleep(1)  # Rate-limit Slack posts

    save_ledger(ledger)

    summary = (
        f"Work Engine done: {executed} executed, {skipped} skipped, "
        f"{warned} attention-needed, {failed} failed"
    )
    log.info(summary)

    # Post summary to war-room if anything ran
    if executed > 0:
        post("war-room", f"[WORK ENGINE] {now.strftime('%I:%M %p PT')} | {summary}")

    return executed


# ---------------------------------------------------------------------------
# Status Report
# ---------------------------------------------------------------------------
def print_status():
    """Print the last execution status for every agent/task from the ledger."""
    if not WORK_LEDGER.exists():
        print("No work ledger found at", WORK_LEDGER)
        return

    try:
        ledger = json.loads(WORK_LEDGER.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading ledger: {e}")
        return

    last_run = ledger.get("last_run", {})
    entries = ledger.get("entries", [])

    # Build lookup: task_name -> most recent entry
    latest = {}
    for entry in entries:
        key = f"{entry['agent']}/{entry['task']}"
        latest[key] = entry

    print("=" * 70)
    print(f"HIVE WORK ENGINE STATUS -- {datetime.now(PT).strftime('%Y-%m-%d %I:%M %p PT')}")
    print(f"Current shift: {get_current_shift()}")
    print(f"Ledger entries: {len(entries)}")
    print("=" * 70)

    for agent_name, config in AGENT_TASKS.items():
        print(f"\n  {agent_name} ({config['shift']} shift -> #{config['channel']})")
        for task in config["tasks"]:
            key = f"{agent_name}/{task['name']}"
            entry = latest.get(key)
            last = last_run.get(task["name"], "never")

            if entry:
                status = "OK" if entry.get("success") else "FAIL"
                output_preview = entry.get("output", "")[:80].replace("\n", " ")
                print(f"    [{status}] {task['name']} (freq={task['frequency']})")
                print(f"           last: {last}")
                print(f"           out:  {output_preview}")
            else:
                print(f"    [--] {task['name']} (freq={task['frequency']})")
                print(f"           never executed")

    # Show last 10 entries chronologically
    print("\n" + "-" * 70)
    print("RECENT EXECUTIONS (last 10):")
    print("-" * 70)
    for entry in entries[-10:]:
        status = "OK" if entry.get("success") else "FAIL"
        ts = entry.get("timestamp", "?")
        out = entry.get("output", "")[:60].replace("\n", " ")
        print(f"  {ts}  [{status}] {entry.get('agent')}/{entry.get('task')}: {out}")

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Hive Work Engine -- real task execution for Everlight agents"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Print last execution status for all agents",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would run without executing",
    )
    args = parser.parse_args()

    if args.status:
        print_status()
    else:
        run_engine(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
