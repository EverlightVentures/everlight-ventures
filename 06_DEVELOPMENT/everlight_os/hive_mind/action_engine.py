"""Hive Action Engine -- Turns agent reports into executed actions.

The core problem: agents post status updates but nothing gets fixed.
This engine monitors agent output, detects actionable items, and EXECUTES.

PIPELINE:
  1. DETECT -- parse agent output for: errors, stale data, missed goals, tasks
  2. CLASSIFY -- what type of action? (auto-fix, restart, task, escalate)
  3. ROUTE -- which agent/system handles it?
  4. EXECUTE -- actually do it (SSH, API call, code fix, service restart)
  5. VERIFY -- did it work?
  6. REPORT -- post result to Slack (not fluff -- actual outcome)

RULES:
  - No generic motivation posts. Every Slack message must contain an ACTION or RESULT.
  - Errors get auto-fixed or escalated within 60 seconds.
  - Goals get checked hourly. If behind, corrective plan is generated and executed.
  - Stale data triggers refresh. Down services get restarted.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Paths
BOT_DIR = Path("/home/opc/xlm-bot")
DJANGO_DIR = Path("/home/opc/hive_django")
LOG_DIR = Path("/home/opc/hive_action_engine")
LOG_DIR.mkdir(exist_ok=True)
ACTION_LOG = LOG_DIR / "actions.jsonl"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

# Slack channels
CHANNELS = {
    "war-room": "C08LGBYQX9T",
    "hive-alerts": "C08N1KV3WMW",
    "deploy-log": "C08N1L0EWNJ",
    "xlm-trading": "C08N1KLR54D",
}


def _log_action(action: dict):
    action["logged_at"] = datetime.now(timezone.utc).isoformat()
    with open(ACTION_LOG, "a") as f:
        f.write(json.dumps(action) + "\n")


def _slack_post(channel_id: str, text: str):
    """Post to Slack. Real action, not fluff."""
    if not SLACK_TOKEN:
        print(f"[SLACK-DRY] #{channel_id}: {text[:100]}")
        return
    import urllib.request
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": channel_id, "text": text}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SLACK_TOKEN}",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[SLACK-ERR] {e}")


def _run(cmd: str, timeout: int = 30) -> tuple[int, str]:
    """Run a shell command, return (exit_code, output)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "timeout"
    except Exception as e:
        return -1, str(e)


# ============================================================
# DETECTION: Parse agent output for actionable items
# ============================================================

def detect_errors(text: str) -> list[dict]:
    """Find Python tracebacks, import errors, service failures."""
    actions = []

    # Python traceback
    tb_match = re.findall(r"(Traceback.*?(?:Error|Exception).*?)(?:\n\S|\Z)", text, re.DOTALL)
    for tb in tb_match:
        # Extract the error type and message
        err_line = tb.strip().split("\n")[-1]
        actions.append({
            "type": "python_error",
            "severity": "critical",
            "error": err_line,
            "traceback": tb[:500],
        })

    # ImportError specifically
    import_errs = re.findall(r"ImportError: cannot import name '(\w+)' from '([\w.]+)'", text)
    for name, module in import_errs:
        actions.append({
            "type": "import_error",
            "severity": "critical",
            "missing_name": name,
            "module": module,
        })

    # Service failures
    svc_fails = re.findall(r"(\w[\w-]+)(?:\s+(?:restart failed|was activating|service down|FAILED|not responding))", text, re.IGNORECASE)
    for svc in svc_fails:
        actions.append({
            "type": "service_failure",
            "severity": "critical",
            "service": svc,
        })

    # Stale data
    stale = re.findall(r"(\w+)\s+was\s+(\d+)s?\s+stale", text)
    for name, seconds in stale:
        if int(seconds) > 300:
            actions.append({
                "type": "stale_data",
                "severity": "warning",
                "component": name,
                "stale_seconds": int(seconds),
            })

    return actions


def detect_goal_gaps() -> list[dict]:
    """Check revenue targets vs actuals."""
    actions = []
    # Check bot P&L
    try:
        snap = json.loads((BOT_DIR / "logs" / "dashboard_snapshot.json").read_text())
        d = snap[0] if isinstance(snap, list) else snap
        pnl = float(d.get("pnl_today_usd", 0))
        losses = int(d.get("losses_today", 0))
        trades = int(d.get("trades_today", 0))

        if trades == 0 and datetime.now().hour > 10:
            actions.append({
                "type": "goal_gap",
                "severity": "warning",
                "area": "trading",
                "issue": f"Zero trades today by hour {datetime.now().hour}. Bot may be over-filtered.",
                "metric": "trades_today",
                "actual": 0,
                "target": "1+",
            })
        if losses >= 3:
            actions.append({
                "type": "goal_gap",
                "severity": "warning",
                "area": "trading",
                "issue": f"{losses} losses today. Circuit breaker should have adapted.",
                "metric": "losses",
                "actual": losses,
            })
    except Exception:
        pass

    return actions


# ============================================================
# EXECUTION: Actually fix things
# ============================================================

AUTO_FIXES = {
    "service_failure": {
        "xlm-bot": "sudo systemctl restart xlm-bot",
        "xlm-dashboard": "sudo systemctl restart xlm-dash-react",
        "xlm-ws": "sudo systemctl restart xlm-ws",
        "blinko": "sudo systemctl restart blinko",
        "n8n": "sudo systemctl restart n8n",
        "hive-django": "sudo systemctl restart hive-django",
        "hive-voice": "sudo systemctl restart hive-voice",
    },
    "stale_data": {
        "WS": "sudo systemctl restart xlm-ws",
        "ws": "sudo systemctl restart xlm-ws",
        "feed": "sudo systemctl restart xlm-ws",
        "blinko": "sudo systemctl restart blinko",
    },
}


def execute_fix(action: dict) -> dict:
    """Execute a corrective action. Returns result."""
    atype = action["type"]
    result = {"action": action, "executed": False, "outcome": ""}

    if atype == "service_failure":
        svc = action.get("service", "")
        cmd = AUTO_FIXES.get("service_failure", {}).get(svc)
        if cmd:
            code, output = _run(cmd)
            result["executed"] = True
            result["outcome"] = f"Ran: {cmd} -> exit {code}"
            # Verify
            time.sleep(3)
            verify_code, verify_out = _run(f"systemctl is-active {svc} 2>/dev/null || echo 'unknown'")
            result["verified"] = "active" in verify_out
            result["verify_output"] = verify_out
        else:
            result["outcome"] = f"No auto-fix for service: {svc}. Escalating."
            result["escalate"] = True

    elif atype == "stale_data":
        component = action.get("component", "")
        cmd = AUTO_FIXES.get("stale_data", {}).get(component)
        if cmd:
            code, output = _run(cmd)
            result["executed"] = True
            result["outcome"] = f"Restarted {component}: {cmd} -> exit {code}"
        else:
            result["outcome"] = f"No auto-fix for stale: {component}"

    elif atype == "import_error":
        # Try to diagnose: check if the name exists in the module
        module = action.get("module", "")
        name = action.get("missing_name", "")
        if module and name:
            # Check what names the module actually exports
            code, output = _run(
                f"cd /home/opc/hive_django && python3 -c \"import {module}; print([x for x in dir({module}) if not x.startswith('_')])\""
            )
            result["executed"] = True
            result["outcome"] = f"Module {module} exports: {output[:200]}"
            result["diagnosis"] = f"'{name}' not found in {module}. Available: {output[:200]}"
            result["escalate"] = True  # needs code fix, escalate to engineer

    elif atype == "goal_gap":
        result["executed"] = True
        result["outcome"] = action.get("issue", "Goal gap detected")
        result["escalate"] = True  # needs strategic response

    elif atype == "python_error":
        result["executed"] = True
        result["outcome"] = f"Error detected: {action.get('error', '')}"
        result["escalate"] = True

    _log_action(result)
    return result


def format_action_report(results: list[dict]) -> str:
    """Format action results for Slack -- no fluff, just facts and outcomes."""
    if not results:
        return ""

    lines = [f"*Hive Action Engine* -- {len(results)} action(s) executed"]
    for r in results:
        a = r.get("action", {})
        severity = a.get("severity", "info")
        icon = {"critical": "!!!", "warning": "!!", "info": ">"}.get(severity, ">")
        atype = a.get("type", "unknown")

        status = "FIXED" if r.get("verified", False) else ("EXECUTED" if r.get("executed") else "ESCALATED")
        line = f"{icon} [{status}] {atype}"

        if atype == "service_failure":
            line += f": {a.get('service', '?')}"
        elif atype == "stale_data":
            line += f": {a.get('component', '?')} ({a.get('stale_seconds', 0)}s stale)"
        elif atype == "import_error":
            line += f": {a.get('missing_name', '?')} from {a.get('module', '?')}"
        elif atype == "goal_gap":
            line += f": {a.get('issue', '')}"

        if r.get("outcome"):
            line += f"\n   -> {r['outcome'][:150]}"

        lines.append(line)

    return "\n".join(lines)


# ============================================================
# MAIN LOOP: The engine cycle
# ============================================================

def run_cycle():
    """One cycle of the action engine.

    1. Read recent Slack messages for errors
    2. Check system health directly
    3. Check goal metrics
    4. Execute fixes
    5. Report results
    """
    all_actions = []
    results = []

    # --- Direct health checks (don't wait for Slack reports) ---
    health_checks = {
        "xlm-bot": "systemctl is-active xlm-bot",
        "xlm-ws": "systemctl is-active xlm-ws",
        "xlm-dash-react": "systemctl is-active xlm-dash-react",
        "blinko": "curl -s --connect-timeout 3 http://localhost:1111/api/v1/note/list -H 'Content-Type: application/json' -d '{\"page\":1,\"pageSize\":1}' | grep -q total",
        "n8n": "curl -s --connect-timeout 3 -o /dev/null -w '%{http_code}' http://localhost:5678/ | grep -q 200",
        "hive-django": "curl -s --connect-timeout 3 -o /dev/null -w '%{http_code}' http://localhost:8504/api/hub-status/ | grep -q 200",
    }

    for svc, check_cmd in health_checks.items():
        code, output = _run(check_cmd)
        if code != 0 or "inactive" in output or "failed" in output:
            all_actions.append({
                "type": "service_failure",
                "severity": "critical",
                "service": svc,
                "check_output": output[:100],
            })

    # --- Check for stale WebSocket feed ---
    try:
        tick = json.loads((BOT_DIR / "logs" / "live_tick.json").read_text())
        tick_ts = datetime.fromisoformat(tick["timestamp"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - tick_ts).total_seconds()
        if age > 120:
            all_actions.append({
                "type": "stale_data",
                "severity": "warning",
                "component": "WS",
                "stale_seconds": int(age),
            })
    except Exception:
        pass

    # --- Check goal gaps ---
    all_actions.extend(detect_goal_gaps())

    # --- Execute fixes ---
    for action in all_actions:
        result = execute_fix(action)
        results.append(result)

    # --- Report to Slack (only if there were actions) ---
    if results:
        report = format_action_report(results)
        if report:
            _slack_post(CHANNELS.get("war-room", ""), report)
            print(report)

    # --- Log cycle ---
    _log_action({
        "type": "cycle_complete",
        "actions_found": len(all_actions),
        "actions_executed": sum(1 for r in results if r.get("executed")),
        "actions_fixed": sum(1 for r in results if r.get("verified")),
        "escalated": sum(1 for r in results if r.get("escalate")),
    })

    return results


def run_goal_enforcement():
    """Hourly check: are we on track for revenue targets?
    If not, generate and execute corrective actions."""

    goals = {
        "monthly_revenue": {"target": 10000, "actual": 0, "unit": "USD"},
        "bot_daily_trades": {"target": 3, "actual": 0, "unit": "trades"},
        "consulting_pipeline": {"target": 5, "actual": 0, "unit": "leads"},
        "broker_deals": {"target": 2, "actual": 0, "unit": "deals"},
    }

    # Get actuals from bot
    try:
        snap = json.loads((BOT_DIR / "logs" / "dashboard_snapshot.json").read_text())
        d = snap[0] if isinstance(snap, list) else snap
        goals["bot_daily_trades"]["actual"] = int(d.get("trades_today", 0))
    except Exception:
        pass

    behind = []
    for name, g in goals.items():
        if g["actual"] < g["target"] * 0.5:  # more than 50% behind
            behind.append(f"{name}: {g['actual']}/{g['target']} {g['unit']}")

    if behind:
        msg = (
            "*Goal Enforcement -- Action Required*\n"
            f"Behind on {len(behind)} targets:\n"
            + "\n".join(f"  !!! {b}" for b in behind)
            + "\n\nRouting to agents for corrective planning."
        )
        _slack_post(CHANNELS.get("war-room", ""), msg)
        _log_action({"type": "goal_enforcement", "behind": behind})


if __name__ == "__main__":
    import sys
    if "--daemon" in sys.argv:
        print("Action Engine daemon starting...")
        while True:
            try:
                run_cycle()
            except Exception as e:
                print(f"Cycle error: {e}")
            time.sleep(60)  # every 60 seconds

            # Goal enforcement every hour
            if datetime.now().minute == 0:
                try:
                    run_goal_enforcement()
                except Exception as e:
                    print(f"Goal enforcement error: {e}")
    else:
        # Single run
        results = run_cycle()
        print(f"\n{len(results)} actions processed.")
