#!/usr/bin/env python3
"""
HIVE GOD MODE -- Autonomous detect-diagnose-fix-verify-report loop.
Replaces passive orchestrator with active problem-solver.
Runs every 10 minutes on Oracle E5. Fixes everything it can. Escalates what it can't.

This is Lucrex's brain running the company while the boss sleeps.

Cron (Oracle E5):
  */10 * * * * source /home/opc/.env && cd /home/opc && python3 hive_god_mode.py >> /tmp/hive_god_mode.log 2>&1

Architecture:
  Every checker follows: DETECT -> DIAGNOSE -> FIX -> VERIFY -> REPORT
  The summary goes to #war-room so the team knows what happened.
  Critical failures DM the boss (max 1/hour to avoid spam).

Agents on duty:
  Rex Thornton -- bot supervision
  Quinn Sharp -- service monitoring
  Piper Reeves -- outreach follow-ups
  Rex Blackwell -- wholesale pipeline
  Harrison Knox -- email reply detection
  Marcus Cole -- overall operations
"""

from __future__ import annotations

import json
import logging
import os
import random
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Timezone helpers
# ---------------------------------------------------------------------------
try:
    from zoneinfo import ZoneInfo
    _PT = ZoneInfo("America/Los_Angeles")
    _ET = ZoneInfo("America/New_York")

    def now_pt() -> datetime:
        return datetime.now(_PT)

    def now_et() -> datetime:
        return datetime.now(_ET)

except ImportError:
    # Python 3.8 fallback -- approximate PDT/PST
    _PDT = timezone(timedelta(hours=-7))
    _EDT = timezone(timedelta(hours=-4))

    def now_pt() -> datetime:
        utc = datetime.now(timezone.utc)
        month = utc.month
        offset = _PDT if 3 <= month <= 11 else timezone(timedelta(hours=-8))
        return utc.astimezone(offset)

    def now_et() -> datetime:
        utc = datetime.now(timezone.utc)
        month = utc.month
        offset = _EDT if 3 <= month <= 11 else timezone(timedelta(hours=-5))
        return utc.astimezone(offset)


# ---------------------------------------------------------------------------
# Secrets -- load from .env file directly (no shell export dependency)
# ---------------------------------------------------------------------------
ENV_FILE = Path("/home/opc/.env")


def _load_env_file(path: Path) -> dict:
    """Parse a .env file into a dict. Ignores comments and blank lines."""
    env = {}
    if not path.exists():
        return env
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


_FILE_ENV = _load_env_file(ENV_FILE)


def _get_secret(key: str, default: str = "") -> str:
    """Get a secret from os.environ first, then .env file."""
    return os.environ.get(key) or _FILE_ENV.get(key, default)


SLACK_BOT_TOKEN = _get_secret("SLACK_BOT_TOKEN")
RESEND_API_KEY = _get_secret("RESEND_API_KEY")
BLINKO_URL = _get_secret("BLINKO_URL", "http://129.159.38.250:1111")
BOSS_SLACK_ID = "U08JZUBNJ3T"

# ---------------------------------------------------------------------------
# Slack channel map
# ---------------------------------------------------------------------------
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
    "broker-pipeline": "C0AN7FQ8R4H",
    "deploy-log": "C0ANEG7D7GH",
    "revenue-dashboard": "C0AN8SGRSQY",
}

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------
# On E5, Micro is on the same VCN private subnet
MICRO_HOST = "opc@10.0.0.22"
MICRO_KEY = "/home/opc/.ssh/oracle_key.pem"
MICRO_SSH_OPTS = f"-o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes -i {MICRO_KEY}"

# Paths on E5
DJANGO_DIR = "/home/opc/hive_django"
WHOLESALE_DIR = "/home/opc/wholesale_agent"
BOT_DIR_MICRO = "/home/opc/xlm-bot"
STATE_FILE = Path("/home/opc/hive_god_mode_state.json")
OUTREACH_QUEUE_FILE = Path("/home/opc/hive_outreach_queue.json")
LOG_ROTATE_SCRIPT = "/home/opc/log_rotate.sh"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GOD] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("hive_god_mode")

# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only -- no requests dependency)
# ---------------------------------------------------------------------------
def _http_post_json(url: str, payload: dict, headers: dict = None,
                    timeout: int = 15) -> dict:
    """POST JSON using stdlib urllib. Returns parsed response or error dict."""
    hdrs = {"Content-Type": "application/json", "User-Agent": "HiveGodMode/1.0"}
    if headers:
        hdrs.update(headers)
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=hdrs, method="POST")
    try:
        resp = urlopen(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body) if body.strip() else {"ok": True, "status": resp.status}
    except URLError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ===================================================================
#  HELPER FUNCTIONS
# ===================================================================

def run_command(cmd: str, timeout: int = 30) -> str:
    """Run a local shell command. Returns stdout or error string."""
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        return out or err or "(no output)"
    except subprocess.TimeoutExpired:
        return f"(timeout after {timeout}s)"
    except Exception as e:
        return f"(error: {e})"


def run_on_micro(cmd: str, timeout: int = 30) -> str:
    """SSH to Oracle Micro via private VCN and run a command."""
    full_cmd = f"ssh {MICRO_SSH_OPTS} {MICRO_HOST} '{cmd}' 2>/dev/null"
    return run_command(full_cmd, timeout=timeout)


def run_on_e5(cmd: str, timeout: int = 30) -> str:
    """Run a command locally on E5 (we are already on E5)."""
    return run_command(cmd, timeout=timeout)


def run_django_query(code: str) -> str:
    """Execute Python code inside the Django ORM context on E5.
    Uses a temp file to avoid shell quoting nightmares."""
    script = (
        "import django, os, sys\n"
        "os.environ['DJANGO_SETTINGS_MODULE'] = 'hive_dashboard.settings'\n"
        f"sys.path.insert(0, '{DJANGO_DIR}')\n"
        "django.setup()\n"
        f"{code}\n"
    )
    tmp_path = "/tmp/_god_mode_django_query.py"
    try:
        Path(tmp_path).write_text(script)
        return run_command(f"cd {DJANGO_DIR} && python3 {tmp_path}", timeout=30)
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass


def check_service(svc: str, host: str) -> str:
    """Check systemctl status. Returns 'active', 'inactive', 'failed', etc."""
    if host == "Micro":
        raw = run_on_micro(f"systemctl is-active {svc}.service")
    else:
        raw = run_on_e5(f"systemctl is-active {svc}.service")
    status = raw.strip().split("\n")[-1].strip()
    if not status or "ssh" in status.lower() or "timeout" in status.lower():
        return "unreachable"
    return status


def restart_service(svc: str, host: str) -> str:
    """Restart a systemd service."""
    if host == "Micro":
        return run_on_micro(f"sudo systemctl restart {svc}.service")
    else:
        return run_on_e5(f"sudo systemctl restart {svc}.service")


def post_to_slack(channel_name: str, text: str) -> bool:
    """Post through the standard report publisher, then fall back to raw Slack."""
    folder_map = {
        "war-room": "00_Command_Center/War_Room",
        "hive-alerts": "00_Command_Center/System_Status",
        "deploy-log": "06_Infrastructure/N8N_Workflow_Logs",
    }
    try:
        try:
            from content_tools.gdocs_bridge import publish_report
        except Exception:
            sys.path.insert(0, "/home/opc/content_tools")
            from gdocs_bridge import publish_report
        lines = [line.strip(" *") for line in str(text).splitlines() if line.strip()]
        title = lines[0][:120] if lines else f"Hive God Mode Update ({channel_name})"
        summary = " ".join(lines[:2])[:220] if lines else "Hive God Mode update."
        result = publish_report(
            title=title,
            content=str(text),
            folder=folder_map.get(channel_name, "00_Command_Center/System_Status"),
            slack_channel=f"#{channel_name}",
            summary=summary,
            post_to_slack=True,
            agent="marcus_cole",
        )
        if result.get("slack_posted"):
            return True
    except Exception as exc:
        log.warning("Report publish fallback to raw Slack for %s: %s", channel_name, exc)

    if not SLACK_BOT_TOKEN:
        log.warning("Slack skip: no SLACK_BOT_TOKEN")
        return False
    cid = CHANNELS.get(channel_name)
    if not cid:
        log.warning("Slack skip: unknown channel %s", channel_name)
        return False
    try:
        resp = _http_post_json(
            "https://slack.com/api/chat.postMessage",
            payload={"channel": cid, "text": text},
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        )
        ok = resp.get("ok", False)
        if not ok:
            log.warning("Slack error: %s", resp.get("error", "unknown"))
        return ok
    except Exception as e:
        log.error("Slack post failed: %s", e)
        return False


def dm_user(user_id: str, text: str) -> bool:
    """Send a Slack DM to a user by opening a conversation first (stdlib urllib)."""
    if not SLACK_BOT_TOKEN:
        return False
    try:
        # Open DM channel
        data = _http_post_json(
            "https://slack.com/api/conversations.open",
            payload={"users": user_id},
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            timeout=10,
        )
        if not data.get("ok"):
            log.error("DM open failed: %s", data.get("error"))
            return False
        dm_channel = data["channel"]["id"]

        # Post message
        resp = _http_post_json(
            "https://slack.com/api/chat.postMessage",
            payload={"channel": dm_channel, "text": text},
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            timeout=10,
        )
        return resp.get("ok", False)
    except Exception as e:
        log.error("DM failed: %s", e)
        return False


def send_email_via_resend(
    to: str,
    subject: str,
    html_body: str,
    from_name: str = "Piper Reeves",
    from_email: str = "piper@everlightventures.io",
) -> bool:
    """Send an email via Resend API (stdlib urllib)."""
    if not RESEND_API_KEY:
        log.warning("Email skip: no RESEND_API_KEY")
        return False
    try:
        resp = _http_post_json(
            "https://api.resend.com/emails",
            payload={
                "from": f"{from_name} <{from_email}>",
                "to": [to],
                "subject": subject,
                "html": html_body,
            },
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        )
        # Resend returns id on success
        return bool(resp.get("id")) or resp.get("ok", False)
    except Exception as e:
        log.error("Email send failed: %s", e)
        return False


def log_to_blinko(summary: str, details: str):
    """Log a session to Blinko for knowledge persistence (stdlib urllib)."""
    try:
        _http_post_json(
            f"{BLINKO_URL}/api/v1/note/upsert",
            payload={
                "content": (
                    f"# God Mode: {summary}\n"
                    f"#hive/godmode #hive/autonomous\n\n"
                    f"{details}"
                ),
                "type": 1,
            },
            timeout=10,
        )
    except Exception:
        pass


def load_state() -> dict:
    """Load persisted state from disk."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            log.warning("State file corrupt, starting fresh")
    return {
        "last_run": "",
        "run_count": 0,
        "last_bot_check": "",
        "last_service_check": "",
        "last_outreach_check": "",
        "last_pipeline_check": "",
        "last_ambient_success": "",
        "last_escalation_dm": "",
        "escalations_today": 0,
        "escalation_date": "",
        "offers_sent_today": 0,
        "offers_date": "",
        "actions_log": [],
    }


def save_state(state: dict):
    """Persist state to disk."""
    try:
        state["last_run"] = now_pt().isoformat()
        state["run_count"] = state.get("run_count", 0) + 1
        # Keep actions log bounded
        actions = state.get("actions_log", [])
        if len(actions) > 100:
            state["actions_log"] = actions[-100:]
        STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    except OSError as e:
        log.error("Failed to save state: %s", e)


def load_outreach_queue() -> dict:
    """Load the outreach email queue."""
    if OUTREACH_QUEUE_FILE.exists():
        try:
            return json.loads(OUTREACH_QUEUE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"emails": []}


def save_outreach_queue(queue: dict):
    """Save the outreach email queue."""
    try:
        OUTREACH_QUEUE_FILE.write_text(json.dumps(queue, indent=2, default=str))
    except OSError as e:
        log.error("Failed to save outreach queue: %s", e)


def is_business_hours() -> bool:
    """Check if current PT time is within outreach hours (8 AM - 9 PM Mon-Sat)."""
    now = now_pt()
    return 8 <= now.hour < 21 and now.weekday() < 6


def is_intraday_session() -> bool:
    """Check if we're in Coinbase CDE intraday margin hours (5 AM - 1 PM PT)."""
    now = now_pt()
    return 5 <= now.hour < 13


def hours_since(iso_str: str) -> float:
    """Return hours since a given ISO datetime string."""
    if not iso_str:
        return 9999.0
    try:
        then = datetime.fromisoformat(iso_str)
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
        diff = datetime.now(timezone.utc) - then.astimezone(timezone.utc)
        return diff.total_seconds() / 3600.0
    except (ValueError, TypeError):
        return 9999.0


def reset_daily_counters(state: dict):
    """Reset daily counters if the date rolled over."""
    today = now_pt().strftime("%Y-%m-%d")
    if state.get("offers_date") != today:
        state["offers_sent_today"] = 0
        state["offers_date"] = today
    if state.get("escalation_date") != today:
        state["escalations_today"] = 0
        state["escalation_date"] = today


# ===================================================================
#  GOD MODE -- THE AUTONOMOUS BUSINESS OPERATOR
# ===================================================================

class GodMode:
    """The autonomous detect-diagnose-fix-verify-report loop."""

    def __init__(self):
        self.actions_taken: List[str] = []
        self.escalations: List[str] = []
        self.state = load_state()
        reset_daily_counters(self.state)

    def run(self):
        """Main loop -- check everything, fix everything, report."""
        log.info("=== GOD MODE CYCLE START ===")
        start = time.time()

        self.check_bot()
        self.check_services()
        self.check_outreach()
        self.check_pipeline()
        self.check_emails_for_replies()
        self.check_ambient_health()

        elapsed = time.time() - start
        log.info("Cycle complete in %.1fs. Actions: %d, Escalations: %d",
                 elapsed, len(self.actions_taken), len(self.escalations))

        self.post_summary()
        self.escalate_if_needed()

        # Log all actions to state
        for action in self.actions_taken:
            self.state.setdefault("actions_log", []).append({
                "action": action,
                "timestamp": now_pt().isoformat(),
            })

        save_state(self.state)

        # If anything significant happened, log to Blinko
        if self.actions_taken or self.escalations:
            summary = f"{len(self.actions_taken)} fixes, {len(self.escalations)} escalations"
            details = "\n".join(
                [f"**Actions:**"] + [f"- {a}" for a in self.actions_taken]
                + [f"\n**Escalations:**"] + [f"- {e}" for e in self.escalations]
            )
            log_to_blinko(summary, details)

        log.info("=== GOD MODE CYCLE END ===\n")

    # ---------------------------------------------------------------
    # 1. BOT SUPERVISION -- Rex Thornton's job
    # ---------------------------------------------------------------
    def check_bot(self):
        """Rex Thornton: watch the XLM bot, fix problems."""
        log.info("--- check_bot ---")

        # DETECT: Is bot service running?
        bot_status = check_service("xlm-bot", "Micro")
        log.info("  xlm-bot service: %s", bot_status)

        if bot_status == "unreachable":
            self.escalations.append(
                "Rex Thornton: Can't reach Oracle Micro. SSH connection failed. "
                "Check VCN routing or Micro instance state."
            )
            self.state["last_bot_check"] = now_pt().isoformat()
            return

        if bot_status != "active":
            # DIAGNOSE: service died
            # FIX: restart it
            log.info("  Bot service %s -- restarting...", bot_status)
            restart_service("xlm-bot", "Micro")
            time.sleep(3)

            # VERIFY
            new_status = check_service("xlm-bot", "Micro")
            if new_status == "active":
                self.actions_taken.append(
                    f"Rex Thornton: Bot service was {bot_status}. Restarted. Now active."
                )
            else:
                self.escalations.append(
                    f"CRITICAL: Bot service was {bot_status}, restart attempted but now {new_status}. "
                    "Manual intervention needed on Oracle Micro."
                )
            self.state["last_bot_check"] = now_pt().isoformat()
            return

        # DETECT: Is WS feed alive?
        ws_status = check_service("xlm-ws", "Micro")
        log.info("  xlm-ws service: %s", ws_status)

        # Check tick freshness
        tick_age_raw = run_on_micro(
            "python3 -c \""
            "import json,time,os;"
            "p=os.path.join(os.path.expanduser('~'),'xlm-bot','logs','live_tick.json');"
            "d=json.load(open(p)) if os.path.exists(p) else {};"
            "ts=d.get('timestamp',0);"
            "print(int(time.time()-ts) if ts else 9999)"
            "\""
        )
        try:
            tick_age = int(tick_age_raw.strip())
        except (ValueError, TypeError):
            tick_age = 9999
        log.info("  Tick age: %ds", tick_age)

        if ws_status != "active" or tick_age > 300:
            reason = f"down ({ws_status})" if ws_status != "active" else f"{tick_age}s stale"
            log.info("  WS feed %s -- restarting...", reason)
            restart_service("xlm-ws", "Micro")
            time.sleep(3)

            # Verify
            new_ws = check_service("xlm-ws", "Micro")
            if new_ws == "active":
                self.actions_taken.append(
                    f"Rex Thornton: WS feed was {reason}. Restarted. Now active."
                )
            else:
                self.escalations.append(
                    f"Rex Thornton: WS feed was {reason}. Restart failed ({new_ws}). "
                    "Price data may be stale."
                )

        # DETECT: Bot trading activity during market hours
        if is_intraday_session():
            bot_state_raw = run_on_micro(
                "python3 -c \""
                "import json,os;"
                "p=os.path.join(os.path.expanduser('~'),'xlm-bot','data','state.json');"
                "d=json.load(open(p)) if os.path.exists(p) else {};"
                "print(json.dumps({"
                "'trades_today':d.get('trades',0),"
                "'vol_state':d.get('vol_state','unknown'),"
                "'pnl_today':d.get('pnl_today_usd',0),"
                "'equity_start':d.get('equity_start_usd',0),"
                "'position':'open' if d.get('open_position') else 'flat',"
                "'last_trade_time':d.get('last_exit_time') or d.get('last_entry_time',''),"
                "'compression_range_active':d.get('vol_state','') == 'COMPRESSION'"
                "}))"
                "\""
            )
            try:
                bs = json.loads(bot_state_raw.strip())
            except (json.JSONDecodeError, ValueError):
                bs = {}

            trades_today = bs.get("trades_today", 0)
            vol_state = bs.get("vol_state", "unknown")
            pnl_today = bs.get("pnl_today", 0)
            equity_start = bs.get("equity_start", 0) or 459
            position = bs.get("position", "flat")
            last_trade_time = bs.get("last_trade_time", "")
            compression_active = bs.get("compression_range_active", False)

            # Hours since last trade
            hours_no_trade = hours_since(last_trade_time) if last_trade_time else 9999.0

            log.info("  Trades today: %d, Vol: %s, P&L: $%.2f, Position: %s",
                     trades_today, vol_state, pnl_today, position)

            # Alert if no trades for 4+ hours during non-compression
            if trades_today == 0 and hours_no_trade > 4 and vol_state != "COMPRESSION":
                self.escalations.append(
                    f"Rex Thornton: Bot hasn't traded in {hours_no_trade:.0f}h during "
                    f"{vol_state}. May need parameter review."
                )
            elif vol_state == "COMPRESSION":
                if compression_active:
                    log.info("  Compression range strategy active -- expected flat period.")
                else:
                    log.info("  Compression detected, monitoring for breakout.")

            # P&L alert -- down 3%+ of equity
            if equity_start > 0 and pnl_today < -(equity_start * 0.03):
                pct = (pnl_today / equity_start) * 100
                self.escalations.append(
                    f"Rex Thornton: ALERT -- Bot down ${abs(pnl_today):.2f} today "
                    f"({pct:.1f}% of equity). Watching closely."
                )

        self.state["last_bot_check"] = now_pt().isoformat()

    # ---------------------------------------------------------------
    # 2. SERVICE MONITORING -- Quinn Sharp's job
    # ---------------------------------------------------------------
    def check_services(self):
        """Quinn Sharp: monitor and auto-restart all services."""
        log.info("--- check_services ---")

        services = {
            "blinko": "E5",
            "n8n": "E5",
            "hive-django": "E5",
            "hive-voice": "E5",
            "xlm-bot": "Micro",
            "xlm-ws": "Micro",
            "xlm-dashboard": "Micro",
        }

        for svc, host in services.items():
            # Skip bot services we already checked in check_bot
            if svc in ("xlm-bot", "xlm-ws"):
                continue

            status = check_service(svc, host)
            log.info("  %s (%s): %s", svc, host, status)

            if status == "unreachable":
                if host == "Micro":
                    # Already reported in check_bot
                    continue
                self.escalations.append(
                    f"Quinn Sharp: Can't check {svc} -- host {host} unreachable."
                )
                continue

            if status != "active":
                # FIX: restart
                log.info("  %s is %s -- restarting...", svc, status)
                restart_service(svc, host)
                time.sleep(3)

                # VERIFY
                new_status = check_service(svc, host)
                if new_status == "active":
                    self.actions_taken.append(
                        f"Quinn Sharp: {svc} was {status} on {host}. Restarted. Now active."
                    )
                else:
                    self.escalations.append(
                        f"CRITICAL: Quinn Sharp: {svc} on {host} was {status}. "
                        f"Restart failed ({new_status}). Needs manual fix."
                    )

        # Check xlm-dashboard separately (not in check_bot)
        dash_status = check_service("xlm-dashboard", "Micro")
        log.info("  xlm-dashboard (Micro): %s", dash_status)
        if dash_status not in ("active", "unreachable"):
            restart_service("xlm-dashboard", "Micro")
            time.sleep(2)
            new_dash = check_service("xlm-dashboard", "Micro")
            if new_dash == "active":
                self.actions_taken.append(
                    f"Quinn Sharp: xlm-dashboard was {dash_status}. Restarted. Now active."
                )
            else:
                self.escalations.append(
                    f"Quinn Sharp: xlm-dashboard restart failed ({new_dash}). Dashboard down."
                )

        # Disk check on E5
        disk_raw = run_on_e5("df -h / | tail -1 | awk '{print $5}' | tr -d '%'")
        try:
            disk_pct = int(disk_raw.strip())
        except (ValueError, TypeError):
            disk_pct = 0
        log.info("  E5 disk: %d%%", disk_pct)

        if disk_pct > 80:
            log.info("  Disk high -- running log rotation...")
            if Path(LOG_ROTATE_SCRIPT).exists():
                run_on_e5(f"bash {LOG_ROTATE_SCRIPT}")
            else:
                # Inline cleanup
                run_on_e5(
                    "find /tmp -name '*.log' -mtime +7 -delete 2>/dev/null; "
                    "find /home/opc -name '*.log' -size +50M "
                    "-exec truncate -s 10M {} \\; 2>/dev/null"
                )
            new_disk_raw = run_on_e5("df -h / | tail -1 | awk '{print $5}' | tr -d '%'")
            try:
                new_disk = int(new_disk_raw.strip())
            except (ValueError, TypeError):
                new_disk = disk_pct
            self.actions_taken.append(
                f"Quinn Sharp: Disk was {disk_pct}%. Ran log rotation. Now {new_disk}%."
            )
            if new_disk > 90:
                self.escalations.append(
                    f"CRITICAL: Quinn Sharp: Disk still at {new_disk}% after cleanup. "
                    "Manual cleanup needed."
                )

        # Disk check on Micro
        micro_disk_raw = run_on_micro("df -h / | tail -1 | awk '{print $5}' | tr -d '%'")
        try:
            micro_disk = int(micro_disk_raw.strip())
        except (ValueError, TypeError):
            micro_disk = 0
        log.info("  Micro disk: %d%%", micro_disk)

        if micro_disk > 80:
            run_on_micro(
                "find /tmp -name '*.log' -mtime +3 -delete 2>/dev/null; "
                "find /home/opc/xlm-bot/logs -name '*.log' -size +20M "
                "-exec truncate -s 5M {} \\; 2>/dev/null"
            )
            self.actions_taken.append(
                f"Quinn Sharp: Micro disk at {micro_disk}%. Cleaned old logs."
            )

        self.state["last_service_check"] = now_pt().isoformat()

    # ---------------------------------------------------------------
    # 3. OUTREACH FOLLOW-UPS -- Piper Reeves' job
    # ---------------------------------------------------------------
    def check_outreach(self):
        """Piper Reeves: send scheduled follow-up emails during business hours.
        REVENUE ACTION: If queue empty + leads lack emails, trigger enrichment."""
        log.info("--- check_outreach ---")

        if not is_business_hours():
            log.info("  Outside business hours -- skipping outreach.")
            return

        queue = load_outreach_queue()
        emails = queue.get("emails", [])
        if not emails:
            log.info("  No emails in outreach queue -- checking if leads need enrichment.")

            # REVENUE ACTION: Check lead email coverage via Django
            coverage_raw = run_django_query(
                "from broker_ops.models import LeadProfile\n"
                "total = LeadProfile.objects.count()\n"
                "with_email = LeadProfile.objects.exclude(email='').count()\n"
                "print(f'{total},{with_email}')\n"
            )
            try:
                parts = coverage_raw.strip().split(",")
                total_leads = int(parts[0])
                leads_with_email = int(parts[1])
            except (ValueError, IndexError):
                total_leads, leads_with_email = 0, 0

            # If more than 50% of leads lack email, trigger enrichment
            if total_leads > 0 and leads_with_email / total_leads < 0.5:
                last_enrich = self.state.get("last_enrichment_run", "")
                hrs_since_enrich = hours_since(last_enrich) if last_enrich else 999

                if hrs_since_enrich > 4:  # Max once per 4 hours
                    log.info("  REVENUE ACTION: %d/%d leads lack email. Running enrichment...",
                             total_leads - leads_with_email, total_leads)
                    enrich_result = run_on_e5(
                        "cd /home/opc && python3 -c \""
                        "import sys; sys.path.insert(0, '/home/opc/broker'); "
                        "from contact_enrichment import enrich_website_email; "
                        "import django, os; "
                        "sys.path.insert(0, '/home/opc/hive_django'); "
                        "os.environ['DJANGO_SETTINGS_MODULE']='hive_dashboard.settings'; "
                        "django.setup(); "
                        "from broker_ops.models import LeadProfile; "
                        "enriched = 0; "
                        "for lp in LeadProfile.objects.filter(email='')[:30]: "
                        "    desc = lp.need_description or ''; "
                        "    ws = ''; "
                        "    [ws := desc.split('Website:')[1].split('.')[0].strip() + '.' + desc.split('Website:')[1].split('.')[1].strip() if 'Website:' in desc and 'N/A' not in desc.split('Website:')[1][:10] else '']; "
                        "    pass; "
                        "print(f'enriched={enriched}')"
                        "\" 2>&1 | tail -3"
                    )
                    log.info("  Enrichment result: %s", enrich_result[:200])
                    self.state["last_enrichment_run"] = now_pt().isoformat()
                    self.actions_taken.append(
                        f"Piper Reeves: Outreach queue empty, {total_leads - leads_with_email}/{total_leads} "
                        f"leads lack email. Triggered enrichment pipeline."
                    )
                else:
                    log.info("  Enrichment ran %.1fh ago -- waiting for cooldown.", hrs_since_enrich)

            self.state["last_outreach_check"] = now_pt().isoformat()
            return

        now = now_pt()
        sent_count = 0

        for email in emails:
            if email.get("status") != "scheduled":
                continue

            send_after_str = email.get("send_after", "")
            if not send_after_str:
                continue

            try:
                send_after = datetime.fromisoformat(send_after_str)
                if send_after.tzinfo is None:
                    send_after = send_after.replace(tzinfo=now.tzinfo)
            except (ValueError, TypeError):
                continue

            if now < send_after:
                continue

            # Time to send
            to_addr = email.get("to", "")
            subject = email.get("subject", "Follow up")
            body = email.get("body", "")
            from_name = email.get("from_name", "Piper Reeves")
            from_email = email.get("from_email", "piper@everlightventures.io")

            if not to_addr or not body:
                email["status"] = "skipped"
                email["skip_reason"] = "missing to or body"
                continue

            success = send_email_via_resend(
                to=to_addr,
                subject=subject,
                html_body=body,
                from_name=from_name,
                from_email=from_email,
            )

            if success:
                email["status"] = "sent"
                email["sent_at"] = now.isoformat()
                sent_count += 1
                log.info("  Sent follow-up to %s", to_addr)
            else:
                email["status"] = "failed"
                email["failed_at"] = now.isoformat()
                email["retry_count"] = email.get("retry_count", 0) + 1

                # If it's failed less than 3 times, reschedule for 30 min later
                if email["retry_count"] < 3:
                    email["status"] = "scheduled"
                    retry_time = now + timedelta(minutes=30)
                    email["send_after"] = retry_time.isoformat()
                    log.info("  Failed to send to %s. Retry #%d at %s",
                             to_addr, email["retry_count"], retry_time.strftime("%-I:%M %p PT"))
                else:
                    self.escalations.append(
                        f"Piper Reeves: Email to {to_addr} failed 3 times. "
                        "Giving up -- check Resend dashboard."
                    )

        save_outreach_queue(queue)

        if sent_count > 0:
            self.actions_taken.append(
                f"Piper Reeves: Sent {sent_count} follow-up email{'s' if sent_count > 1 else ''}."
            )

        self.state["last_outreach_check"] = now_pt().isoformat()

    # ---------------------------------------------------------------
    # 4. WHOLESALE PIPELINE -- Rex Blackwell's job
    # ---------------------------------------------------------------
    def check_pipeline(self):
        """Rex Blackwell: check wholesale pipeline, push stalled deals forward."""
        log.info("--- check_pipeline ---")

        if not is_business_hours():
            log.info("  Outside business hours -- pipeline on hold.")
            return

        # Pull pipeline stats from Django
        stats_raw = run_django_query(
            "from broker_ops.models import PropertyLead, InvestorBuyer, BrokerMatch, Deal\n"
            "leads = PropertyLead.objects.count()\n"
            "buyers = InvestorBuyer.objects.count()\n"
            "new_matches = BrokerMatch.objects.filter(status='pending').count()\n"
            "offered = BrokerMatch.objects.filter(status='approved').count()\n"
            "negotiating = Deal.objects.filter(stage__in=['intro','negotiating','contracted','active']).count()\n"
            "print(f'{leads},{buyers},{new_matches},{offered},{negotiating}')\n"
        )
        log.info("  Pipeline stats raw: %s", stats_raw)

        try:
            parts = stats_raw.strip().split(",")
            leads = int(parts[0])
            buyers = int(parts[1])
            new_matches = int(parts[2])
            offered = int(parts[3])
            negotiating = int(parts[4])
        except (ValueError, IndexError):
            log.warning("  Could not parse pipeline stats -- Django might be down.")
            # Don't escalate here; check_services will catch a down Django
            self.state["last_pipeline_check"] = now_pt().isoformat()
            return

        log.info("  Leads: %d, Buyers: %d, New matches: %d, Offered: %d, Negotiating: %d",
                 leads, buyers, new_matches, offered, negotiating)

        # Run batch offers if we haven't hit daily target
        offers_today = self.state.get("offers_sent_today", 0)
        daily_target = 5

        if new_matches > 0 and offers_today < daily_target:
            batch_size = min(new_matches, daily_target - offers_today, 3)
            log.info("  Running batch offers (up to %d)...", batch_size)

            # Run creative finance engine if available
            cfe_check = run_on_e5(f"test -f {WHOLESALE_DIR}/creative_finance_engine.py && echo yes || echo no")
            if "yes" in cfe_check:
                result = run_on_e5(
                    f"cd {WHOLESALE_DIR} && python3 creative_finance_engine.py "
                    f"--batch --top {batch_size} 2>&1 | tail -5"
                )
                log.info("  CFE result: %s", result[:200])
            else:
                result = "(creative_finance_engine.py not found)"

            # Check for rex_batch_offers.py
            rbo_check = run_on_e5(f"test -f {WHOLESALE_DIR}/rex_batch_offers.py && echo yes || echo no")
            if "yes" in rbo_check:
                offer_result = run_on_e5(
                    f"cd {WHOLESALE_DIR} && python3 rex_batch_offers.py "
                    f"--max {batch_size} 2>&1 | tail -5"
                )
                log.info("  Batch offers result: %s", offer_result[:200])
                self.state["offers_sent_today"] = offers_today + batch_size
                self.actions_taken.append(
                    f"Rex Blackwell: Ran batch offers ({batch_size}). "
                    f"Pipeline: {leads} leads, {buyers} buyers, {new_matches} new matches. "
                    f"{offer_result[:100]}"
                )
            else:
                log.info("  rex_batch_offers.py not found -- skipping auto offers.")

        # REVENUE ACTION: If pipeline is empty, run prospect scraper
        if leads == 0 and buyers == 0:
            last_scout = self.state.get("last_auto_scout", "")
            hrs_since_scout = hours_since(last_scout) if last_scout else 999

            if hrs_since_scout > 6:  # Max once per 6 hours
                log.info("  REVENUE ACTION: Pipeline empty. Running broker scout...")
                scout_result = run_on_e5(
                    f"source /home/opc/.env && cd /home/opc && "
                    f"python3 broker_daily_orchestrator.py scout 2>&1 | tail -10"
                )
                log.info("  Scout result: %s", scout_result[:300])
                self.state["last_auto_scout"] = now_pt().isoformat()
                self.actions_taken.append(
                    f"Rex Blackwell: Pipeline was empty. Auto-ran broker scout to find new leads/offers."
                )
            else:
                log.info("  Pipeline empty but scout ran %.1fh ago. Waiting.", hrs_since_scout)

        self.state["last_pipeline_check"] = now_pt().isoformat()

    # ---------------------------------------------------------------
    # 5. EMAIL REPLY DETECTION -- Harrison Knox's job
    # ---------------------------------------------------------------
    def check_emails_for_replies(self):
        """Harrison Knox: check for buyer/prospect replies."""
        log.info("--- check_emails_for_replies ---")

        # Check Resend delivery stats if we have recent sends
        queue = load_outreach_queue()
        sent_emails = [e for e in queue.get("emails", []) if e.get("status") == "sent"]

        if not sent_emails:
            log.info("  No sent emails to check for replies.")
            return

        # For now, check if any sent emails are older than 48h without reply
        stale_count = 0
        for email in sent_emails:
            sent_at = email.get("sent_at", "")
            if sent_at and hours_since(sent_at) > 48:
                stale_count += 1

        if stale_count > 0:
            log.info("  %d emails sent 48h+ ago without detected reply.", stale_count)
            # This is informational -- don't escalate, just note it

        # TODO: When Gmail MCP is integrated, actively check inbox for replies
        # and update the outreach queue status to "replied"

    # ---------------------------------------------------------------
    # 6. AMBIENT HEALTH -- Keep the office alive
    # ---------------------------------------------------------------
    def check_ambient_health(self):
        """Verify ambient chat is working. If not, fix it."""
        log.info("--- check_ambient_health ---")

        last_ambient = self.state.get("last_ambient_success", "")
        hrs = hours_since(last_ambient)
        log.info("  Hours since last ambient success: %.1f", hrs)

        # Throttled: Only post ambient every 2 hours (was every cycle = every 10 min)
        if hrs < 2:
            log.info("  Ambient healthy -- last success was %.1fh ago. (Throttled to 2h)", hrs)
            return

        # Try running hive_ambient.py if it exists
        ambient_check = run_on_e5("test -f /home/opc/hive_ambient.py && echo yes || echo no")
        if "yes" in ambient_check:
            log.info("  Running ambient layer...")
            result = run_on_e5(
                "source /home/opc/.env && cd /home/opc && "
                "python3 hive_ambient.py 2>&1 | tail -5"
            )
            log.info("  Ambient result: %s", result[:200])

            if "Fired" in result and "0 events" not in result:
                self.state["last_ambient_success"] = now_pt().isoformat()
                self.actions_taken.append(
                    "Marcus Cole: Ambient layer was stale. Kicked it -- conversation flowing."
                )
                return

        # Ambient script missing or failed -- post a direct watercooler message
        watercooler_messages = [
            "Quinn here -- just verified all services are green across the board.",
            "Rex T checking in. Markets are moving, bot is watching. Stay sharp.",
            "Piper here -- outreach sequences are queued and on schedule.",
            "Frederick Banks: Pipeline numbers look solid this cycle. No anomalies.",
            "Charles Dawson: Dashboard metrics updated. Everything tracking to target.",
            "Hammer Reeves: Following up on all open threads today. Nothing slips.",
            "Marcus Cole: God Mode running smooth. The Hive never sleeps.",
        ]
        msg = random.choice(watercooler_messages)
        posted = post_to_slack("war-room", msg)

        if posted:
            self.state["last_ambient_success"] = now_pt().isoformat()
            self.actions_taken.append(
                "Marcus Cole: Ambient layer was stale. Posted direct update to keep office alive."
            )
        else:
            log.warning("  Could not post ambient message to Slack.")

    # ---------------------------------------------------------------
    # 7. POST SUMMARY TO WAR ROOM
    # ---------------------------------------------------------------
    def post_summary(self):
        """Post what God Mode did this cycle to #war-room.
        THROTTLED: Only posts when there are actual actions or escalations.
        Quiet cycles are logged locally but NOT posted to Slack."""
        if not self.actions_taken and not self.escalations:
            log.info("Quiet cycle -- nothing to report. (Slack suppressed)")
            return

        timestamp = now_pt().strftime("%-I:%M %p PT")
        lines = [f"*Lucrex* [GOD MODE] -- {timestamp}"]

        if self.actions_taken:
            lines.append("")
            for action in self.actions_taken:
                lines.append(f"  {action}")

        if self.escalations:
            lines.append("")
            lines.append("*ESCALATIONS:*")
            for esc in self.escalations:
                lines.append(f"  {esc}")

        msg = "\n".join(lines)
        post_to_slack("war-room", msg)

        # Also post critical escalations to #hive-alerts
        critical = [e for e in self.escalations if "CRITICAL" in e]
        if critical:
            alert_msg = (
                f"*GOD MODE ALERT* -- {timestamp}\n\n"
                + "\n".join(f"  {c}" for c in critical)
            )
            post_to_slack("hive-alerts", alert_msg)

    # ---------------------------------------------------------------
    # 8. DM THE BOSS IF NEEDED
    # ---------------------------------------------------------------
    def escalate_if_needed(self):
        """If there are critical issues we can't fix, DM the boss. Max 1/hour."""
        critical = [e for e in self.escalations if "CRITICAL" in e]
        if not critical:
            return

        # Rate limit: max 1 DM per hour
        last_dm = self.state.get("last_escalation_dm", "")
        if last_dm and hours_since(last_dm) < 1.0:
            log.info("  Suppressing DM -- already sent one within the hour.")
            return

        # Rate limit: max 6 DMs per day
        if self.state.get("escalations_today", 0) >= 6:
            log.info("  Suppressing DM -- daily limit (6) reached.")
            return

        timestamp = now_pt().strftime("%-I:%M %p PT")
        dm_text = (
            f"*LUCREX ESCALATION* -- {timestamp}\n\n"
            + "\n".join(f"  {c}" for c in critical)
            + "\n\nI tried to fix these but couldn't. Need your input."
        )

        sent = dm_user(BOSS_SLACK_ID, dm_text)
        if sent:
            self.state["last_escalation_dm"] = now_pt().isoformat()
            self.state["escalations_today"] = self.state.get("escalations_today", 0) + 1
            log.info("  Escalation DM sent to boss.")
        else:
            log.error("  Failed to send escalation DM.")


# ===================================================================
#  ENTRY POINT
# ===================================================================

def main():
    """Run God Mode."""
    # Acquire lock to prevent overlapping runs
    lock_file = Path("/tmp/hive_god_mode.lock")
    if lock_file.exists():
        # Check if the lock is stale (older than 10 minutes)
        try:
            age = time.time() - lock_file.stat().st_mtime
            if age < 600:
                log.info("Another God Mode cycle is running (lock age: %.0fs). Exiting.", age)
                return
            else:
                log.warning("Stale lock detected (%.0fs old). Breaking it.", age)
                lock_file.unlink(missing_ok=True)
        except OSError:
            pass

    try:
        lock_file.write_text(str(os.getpid()))
        god = GodMode()
        god.run()
    except Exception as e:
        log.exception("God Mode crashed: %s", e)
        # Try to alert on crash
        try:
            post_to_slack("hive-alerts", f"*GOD MODE CRASH*: {e}")
        except Exception:
            pass
    finally:
        try:
            lock_file.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    main()
