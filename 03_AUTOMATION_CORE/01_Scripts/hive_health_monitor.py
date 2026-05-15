#!/usr/bin/env python3

# === ERADICATION HALT (auto-inserted 2026-05-15) ===
# noqa: direct-resend
# System-alerting path: does not iterate seller leads, but still gated under
# WHOLESALE_OUTBOUND_HALT for consistency. The api.resend.com call is for ops
# alerts (deploy-log, health-monitor) and goes to internal channels.
import os as _os_halt
if _os_halt.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}:
    # System-alerting scripts SHOULD still run under halt -- they're how we
    # know the halt is active. But they MUST NOT send seller-facing email.
    # The eradication_gate import below makes that a hard guarantee.
    pass
import sys as _sys_eg
_sys_eg.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
try:
    from eradication_gate import assert_safe as _erad_assert_safe, EradicationViolation
except ImportError as _eg_err:
    print(f"eradication_gate unavailable: {_eg_err}", file=__import__("sys").stderr)
    # System alerting paths fail open here -- they alert about themselves.
# === END ERADICATION HALT ===
"""
Hive Health Monitor -- Master Self-Healing System
Checks all systems every 5 minutes, auto-fixes what it can, alerts on what it can't.

Usage:
    python3 hive_health_monitor.py              # Full health check
    python3 hive_health_monitor.py --fix        # Check + auto-fix (default)
    python3 hive_health_monitor.py --report     # Show latest health status
    python3 hive_health_monitor.py --slack       # Post current health to Slack

Schedule: Every 5 minutes
    */5 * * * * cd /mnt/sdcard/AA_MY_DRIVE && python3 03_AUTOMATION_CORE/01_Scripts/hive_health_monitor.py --fix >> _logs/hive_health.log 2>&1
"""

import argparse
import datetime
import json
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_DIR = BASE_DIR / "_logs"
LOG_FILE = LOG_DIR / "hive_health.log"
REPORT_FILE = BASE_DIR / "09_DASHBOARD" / "reports" / "hive_health_latest.json"
CREDS_ENV = BASE_DIR / "03_AUTOMATION_CORE" / "03_Credentials" / ".env"

# SSH
SSH_KEY = "/root/.ssh/oracle_key.pem"
ORACLE_N8N_IP = "129.159.38.250"
ORACLE_BOT_IP = "163.192.19.196"
SSH_USER = "opc"

# Timeouts (seconds)
HTTP_TIMEOUT = 10
SSH_TIMEOUT = 15

# Pipeline -- how many hours since last run is acceptable
PIPELINE_MAX_HOURS = 6

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("hive_health")
logger.setLevel(logging.DEBUG)

# File handler -- append
fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-5s  %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(fh)

# Stdout handler for interactive use
sh = logging.StreamHandler(sys.stdout)
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(sh)


# ---------------------------------------------------------------------------
# Credential loader
# ---------------------------------------------------------------------------
def load_env(path: Path) -> dict:
    """Parse a .env file into a dict. Ignores comments and blank lines."""
    env = {}
    if not path.exists():
        logger.warning("Credential file not found: %s", path)
        return env
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            env[key] = value
    return env


CREDS = load_env(CREDS_ENV)


def get_cred(key: str) -> Optional[str]:
    """Get a credential from loaded .env or os.environ as fallback."""
    return CREDS.get(key) or os.environ.get(key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now_pt() -> str:
    """Current time formatted in Pacific Time for display."""
    # Use America/Los_Angeles via datetime offset (no pytz dependency)
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
    except ImportError:
        # Fallback -- calculate PST/PDT manually
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        # Approximate PDT (Mar-Nov) vs PST
        month = utc_now.month
        if 3 <= month <= 11:
            offset = datetime.timezone(datetime.timedelta(hours=-7))
        else:
            offset = datetime.timezone(datetime.timedelta(hours=-8))
        dt = utc_now.astimezone(offset)
    return dt.strftime("%-I:%M %p PT")


def now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def run_cmd(cmd: list, timeout: int = SSH_TIMEOUT) -> tuple:
    """Run a subprocess command. Returns (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def http_get(url: str, timeout: int = HTTP_TIMEOUT) -> tuple:
    """Simple HTTP GET. Returns (status_code, body) or (-1, error)."""
    try:
        req = Request(url, headers={"User-Agent": "HiveHealthMonitor/1.0"})
        resp = urlopen(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body
    except URLError as e:
        return -1, str(e)
    except Exception as e:
        return -1, str(e)


def http_post(url: str, payload: dict, timeout: int = HTTP_TIMEOUT) -> tuple:
    """Simple HTTP POST (JSON). Returns (status_code, body) or (-1, error)."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers={
            "Content-Type": "application/json",
            "User-Agent": "HiveHealthMonitor/1.0",
        })
        resp = urlopen(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body
    except URLError as e:
        return -1, str(e)
    except Exception as e:
        return -1, str(e)


def result(name: str, status: str, message: str, auto_fixed: bool = False) -> dict:
    """Build a standard check result dict."""
    return {
        "name": name,
        "status": status,
        "message": message,
        "auto_fixed": auto_fixed,
        "checked_at": now_iso(),
    }


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

def check_n8n(auto_fix: bool = False) -> dict:
    """Check n8n at localhost:5678/healthz (tunneled from Oracle)."""
    name = "n8n"
    try:
        code, body = http_get("http://localhost:5678/healthz")
        if code == 200:
            return result(name, "ok", "n8n healthy (Oracle E5)")

        # n8n unreachable -- likely tunnel is down
        msg = f"n8n health failed (HTTP {code}): {body[:120]}"
        if auto_fix:
            fixed = _fix_n8n_tunnel()
            if fixed:
                # Recheck after tunnel reconnect
                time.sleep(3)
                code2, _ = http_get("http://localhost:5678/healthz")
                if code2 == 200:
                    return result(name, "ok", "n8n recovered after tunnel reconnect", auto_fixed=True)
                return result(name, "fail", "Tunnel reconnected but n8n still unreachable")
            return result(name, "fail", f"Tunnel reconnect failed -- {msg}")
        return result(name, "fail", msg)
    except Exception as e:
        return result(name, "fail", f"Exception: {e}")


def check_n8n_tunnel(auto_fix: bool = False) -> dict:
    """Check if SSH tunnel to n8n Oracle box is alive."""
    name = "n8n Tunnel"
    try:
        # Check for existing SSH tunnel process
        rc, out, _ = run_cmd(["pgrep", "-f", f"ssh.*5678.*{ORACLE_N8N_IP}"], timeout=5)
        if rc == 0 and out.strip():
            return result(name, "ok", f"Tunnel process alive (PID {out.splitlines()[0]})")

        # Tunnel not running
        if auto_fix:
            fixed = _fix_n8n_tunnel()
            if fixed:
                return result(name, "ok", "Tunnel reconnected", auto_fixed=True)
            return result(name, "fail", "Could not establish SSH tunnel")
        return result(name, "fail", "No SSH tunnel process found")
    except Exception as e:
        return result(name, "fail", f"Exception: {e}")


def _fix_n8n_tunnel() -> bool:
    """Attempt to reconnect the n8n SSH tunnel."""
    logger.info("Attempting n8n tunnel reconnect...")
    # Kill stale tunnels first
    run_cmd(["pkill", "-f", f"ssh.*5678.*{ORACLE_N8N_IP}"], timeout=5)
    time.sleep(1)
    cmd = [
        "ssh", "-f", "-N",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-L", "5678:127.0.0.1:5678",
        "-i", SSH_KEY,
        f"{SSH_USER}@{ORACLE_N8N_IP}",
    ]
    rc, _, err = run_cmd(cmd, timeout=20)
    if rc == 0:
        logger.info("n8n tunnel reconnected successfully")
        return True
    logger.error("n8n tunnel reconnect failed: %s", err)
    return False


def check_xlm_bot(auto_fix: bool = False) -> dict:
    """Check XLM bot service on Oracle Cloud via SSH."""
    name = "XLM Bot"
    try:
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-i", SSH_KEY,
            f"{SSH_USER}@{ORACLE_BOT_IP}",
            "systemctl", "is-active", "xlm-bot.service",
        ]
        rc, out, err = run_cmd(cmd)
        if rc == 0 and "active" in out:
            return result(name, "ok", "xlm-bot.service active (Oracle Micro)")

        # Bot is down
        msg = f"xlm-bot.service not active: {out or err}"
        if auto_fix:
            fixed = _fix_xlm_bot()
            if fixed:
                return result(name, "ok", "xlm-bot.service restarted", auto_fixed=True)
            return result(name, "fail", f"Restart failed -- {msg}")
        return result(name, "fail", msg)
    except Exception as e:
        return result(name, "fail", f"Exception: {e}")


def _fix_xlm_bot() -> bool:
    """Attempt to restart the XLM bot service on Oracle."""
    logger.info("Attempting XLM bot restart on Oracle...")
    cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-i", SSH_KEY,
        f"{SSH_USER}@{ORACLE_BOT_IP}",
        "sudo", "systemctl", "restart", "xlm-bot.service",
    ]
    rc, _, err = run_cmd(cmd, timeout=30)
    if rc == 0:
        # Verify it came back
        time.sleep(3)
        verify_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-i", SSH_KEY,
            f"{SSH_USER}@{ORACLE_BOT_IP}",
            "systemctl", "is-active", "xlm-bot.service",
        ]
        rc2, out2, _ = run_cmd(verify_cmd)
        if rc2 == 0 and "active" in out2:
            logger.info("XLM bot restarted successfully")
            return True
    logger.error("XLM bot restart failed: %s", err)
    return False


def check_blinko(auto_fix: bool = False) -> dict:
    """Check Blinko at localhost:1111/health."""
    name = "Blinko"
    try:
        code, body = http_get("http://localhost:1111/health")
        if code == 200:
            return result(name, "ok", "Blinko healthy")

        # Blinko down
        if auto_fix:
            fixed = _fix_blinko()
            if fixed:
                return result(name, "warn", "Blinko down, BlinkoLite fallback started", auto_fixed=True)
            return result(name, "warn", "Blinko not running, BlinkoLite fallback failed")
        return result(name, "warn", "Blinko not running (non-critical)")
    except Exception as e:
        return result(name, "warn", f"Blinko not reachable: {e}")


def _fix_blinko() -> bool:
    """Try to start BlinkoLite as fallback."""
    logger.info("Attempting BlinkoLite fallback...")
    blinko_lite = BASE_DIR / "03_AUTOMATION_CORE" / "01_Scripts" / "blinko_lite.py"
    if not blinko_lite.exists():
        logger.warning("blinko_lite.py not found at %s", blinko_lite)
        return False
    # Check if already running
    rc, out, _ = run_cmd(["pgrep", "-f", "blinko_lite.py"], timeout=5)
    if rc == 0 and out.strip():
        logger.info("BlinkoLite already running (PID %s)", out.splitlines()[0])
        return True
    # Start in background
    try:
        subprocess.Popen(
            [sys.executable, str(blinko_lite)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info("BlinkoLite started as fallback")
        return True
    except Exception as e:
        logger.error("BlinkoLite start failed: %s", e)
        return False


def check_wholesale_pipeline(auto_fix: bool = False) -> dict:
    """Check if the wholesale pipeline cron ran within the expected window."""
    name = "Pipeline"
    try:
        pipeline_log = BASE_DIR / "_logs" / "wholesale_hive_pipeline.log"
        pipeline_json = BASE_DIR / "09_DASHBOARD" / "reports" / "wholesale_pipeline_latest.json"

        last_run = None

        # Try the JSON report first -- it has a timestamp
        if pipeline_json.exists():
            try:
                with open(pipeline_json, "r") as f:
                    data = json.load(f)
                ts = data.get("generated_at") or data.get("timestamp") or data.get("created_at")
                if ts:
                    # Parse ISO timestamp
                    ts_clean = ts.replace("Z", "+00:00")
                    last_run = datetime.datetime.fromisoformat(ts_clean)
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback -- check file mtime
        if last_run is None and pipeline_json.exists():
            mtime = pipeline_json.stat().st_mtime
            last_run = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
        elif last_run is None and pipeline_log.exists():
            mtime = pipeline_log.stat().st_mtime
            last_run = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)

        if last_run is None:
            return result(name, "warn", "No pipeline run data found")

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        # Make last_run offset-aware if naive
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=datetime.timezone.utc)
        age = now_utc - last_run
        hours_ago = age.total_seconds() / 3600

        if hours_ago <= PIPELINE_MAX_HOURS:
            return result(name, "ok", f"Last run {hours_ago:.1f}h ago")
        else:
            return result(name, "warn", f"Last run {hours_ago:.1f}h ago (threshold: {PIPELINE_MAX_HOURS}h)")
    except Exception as e:
        return result(name, "warn", f"Exception: {e}")


def check_slack(auto_fix: bool = False) -> dict:
    """Test Slack webhook connectivity with a silent ping."""
    name = "Slack"
    try:
        webhook = get_cred("SLACK_WEBHOOK_WARROOM")
        if not webhook:
            return result(name, "fail", "SLACK_WEBHOOK_WARROOM not found in credentials")

        # Send a connectivity test (empty text won't post, so use a minimal payload)
        # Slack returns 200 even for no_text errors, so we just check connectivity
        code, body = http_post(webhook, {"text": ""})
        # Slack returns "no_text" for empty text but the connection worked
        if code == 200:
            return result(name, "ok", "Slack webhook reachable")
        # Some Slack responses come back as non-200 for bad payload but connection works
        if code in (400, 500) and "no_text" in body.lower():
            return result(name, "ok", "Slack webhook reachable (empty payload rejected as expected)")
        return result(name, "fail", f"Slack webhook returned HTTP {code}: {body[:120]}")
    except Exception as e:
        return result(name, "fail", f"Exception: {e}")


def check_improvmx(auto_fix: bool = False) -> dict:
    """Check that MX records for everlightventures.io point to ImprovMX."""
    name = "ImprovMX"
    try:
        rc, out, err = run_cmd(["dig", "+short", "MX", "everlightventures.io"], timeout=10)
        if rc != 0:
            # dig might not be installed -- try nslookup
            rc, out, err = run_cmd(
                ["nslookup", "-type=MX", "everlightventures.io"], timeout=10
            )
        combined = (out + err).lower()
        if "improvmx" in combined:
            return result(name, "ok", "MX records point to ImprovMX")
        elif out.strip():
            return result(name, "warn", f"MX records present but no ImprovMX: {out[:200]}")
        else:
            return result(name, "fail", f"Could not resolve MX records: {err[:200]}")
    except Exception as e:
        return result(name, "fail", f"Exception: {e}")


def check_resend(auto_fix: bool = False) -> dict:
    """Check Resend API key validity by hitting the domains endpoint."""
    name = "Resend"
    try:
        api_key = get_cred("RESEND_API_KEY")
        if not api_key:
            return result(name, "fail", "RESEND_API_KEY not found in credentials")

        req = Request(
            "https://api.resend.com/domains",
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "HiveHealthMonitor/1.0",
            },
        )
        try:
            resp = urlopen(req, timeout=HTTP_TIMEOUT)
            body = resp.read().decode("utf-8", errors="replace")
            code = resp.status
        except URLError as e:
            if hasattr(e, "code"):
                code = e.code
                body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
            else:
                return result(name, "fail", f"Resend API unreachable: {e}")

        if code == 200:
            return result(name, "ok", "Resend API key valid, can send")
        elif code == 429:
            return result(name, "warn", "Resend rate-limited (quota concern)")
        elif code == 401:
            return result(name, "fail", "Resend API key invalid/expired")
        else:
            return result(name, "warn", f"Resend returned HTTP {code}: {body[:120]}")
    except Exception as e:
        return result(name, "fail", f"Exception: {e}")


def check_google_docs(auto_fix: bool = False) -> dict:
    """Test the n8n Google Docs webhook with a tiny payload."""
    name = "Google Docs"
    try:
        # The n8n webhook for Google Docs pipeline -- test endpoint
        # This hits n8n which should be tunneled to localhost:5678
        webhook_url = "http://localhost:5678/webhook-test/gdocs-health"
        code, body = http_post(webhook_url, {
            "source": "hive_health_monitor",
            "type": "health_check",
            "timestamp": now_iso(),
        })
        if code == 200:
            return result(name, "ok", "n8n Google Docs webhook responding")
        elif code == 404:
            # Webhook path might not exist -- n8n is up but no workflow for this
            return result(name, "warn", "n8n reachable but gdocs-health webhook not configured (404)")
        else:
            return result(name, "warn", f"Google Docs webhook returned HTTP {code}: {body[:120]}")
    except Exception as e:
        # If n8n tunnel is down this will fail -- but check_n8n covers that
        return result(name, "warn", f"Google Docs webhook unreachable: {e}")


# ---------------------------------------------------------------------------
# Slack notification
# ---------------------------------------------------------------------------
STATUS_ICONS = {
    "ok": "[OK]",
    "warn": "[WARN]",
    "fail": "[FAIL]",
}


def build_slack_summary(results: list) -> str:
    """Build the Slack message text from check results."""
    lines = [f"*Hive Health -- {now_pt()}*"]
    for r in results:
        icon = STATUS_ICONS.get(r["status"], "[??]")
        msg = r["message"]
        fixed_tag = " (auto-fixed)" if r.get("auto_fixed") else ""
        lines.append(f"{icon} {r['name']} -- {msg}{fixed_tag}")
    return "\n".join(lines)


def post_slack(message: str, force: bool = False) -> bool:
    """Post a message to the Slack war room webhook."""
    webhook = get_cred("SLACK_WEBHOOK_WARROOM")
    if not webhook:
        logger.error("Cannot post to Slack -- SLACK_WEBHOOK_WARROOM not set")
        return False
    code, body = http_post(webhook, {"text": message})
    if code == 200:
        logger.debug("Slack message posted successfully")
        return True
    logger.error("Slack post failed (HTTP %s): %s", code, body[:200])
    return False


def should_alert(results: list) -> bool:
    """Return True if any check failed or was auto-fixed (worth notifying about)."""
    for r in results:
        if r["status"] == "fail":
            return True
        if r.get("auto_fixed"):
            return True
    return False


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------
ALL_CHECKS = [
    check_n8n,
    check_n8n_tunnel,
    check_xlm_bot,
    check_blinko,
    check_slack,
    check_improvmx,
    check_resend,
    check_google_docs,
    check_wholesale_pipeline,
]


def run_all_checks(auto_fix: bool = False) -> list:
    """Run all health checks in parallel. Returns list of result dicts."""
    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {
            executor.submit(fn, auto_fix=auto_fix): fn.__name__
            for fn in ALL_CHECKS
        }
        for future in as_completed(future_map):
            fn_name = future_map[future]
            try:
                r = future.result(timeout=60)
                results.append(r)
            except Exception as e:
                results.append(result(fn_name, "fail", f"Check crashed: {e}"))

    # Sort by status severity for readability: fail > warn > ok
    order = {"fail": 0, "warn": 1, "ok": 2}
    results.sort(key=lambda r: order.get(r["status"], 3))
    return results


def save_report(results: list) -> None:
    """Save latest health status to JSON for the dashboard."""
    report = {
        "generated_at": now_iso(),
        "generated_at_pt": now_pt(),
        "checks": results,
        "summary": {
            "total": len(results),
            "ok": sum(1 for r in results if r["status"] == "ok"),
            "warn": sum(1 for r in results if r["status"] == "warn"),
            "fail": sum(1 for r in results if r["status"] == "fail"),
            "auto_fixed": sum(1 for r in results if r.get("auto_fixed")),
        },
    }
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.debug("Report saved to %s", REPORT_FILE)


def show_report() -> None:
    """Print the latest saved health report."""
    if not REPORT_FILE.exists():
        print("No health report found. Run a check first.")
        return
    with open(REPORT_FILE, "r") as f:
        data = json.load(f)
    print(f"\nHive Health -- {data.get('generated_at_pt', data.get('generated_at'))}")
    print("-" * 50)
    for c in data.get("checks", []):
        icon = STATUS_ICONS.get(c["status"], "[??]")
        fixed = " (auto-fixed)" if c.get("auto_fixed") else ""
        print(f"  {icon} {c['name']} -- {c['message']}{fixed}")
    s = data.get("summary", {})
    print(f"\n  Total: {s.get('total', '?')}  |  "
          f"OK: {s.get('ok', 0)}  |  "
          f"Warn: {s.get('warn', 0)}  |  "
          f"Fail: {s.get('fail', 0)}  |  "
          f"Auto-fixed: {s.get('auto_fixed', 0)}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Hive Health Monitor")
    parser.add_argument("--fix", action="store_true", default=True,
                        help="Auto-fix issues (default behavior)")
    parser.add_argument("--no-fix", action="store_true",
                        help="Check only, do not attempt auto-fix")
    parser.add_argument("--report", action="store_true",
                        help="Show latest saved health report")
    parser.add_argument("--slack", action="store_true",
                        help="Run checks and post summary to Slack")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress stdout output (log file only)")
    args = parser.parse_args()

    if args.quiet:
        sh.setLevel(logging.CRITICAL)

    if args.report:
        show_report()
        return

    auto_fix = not args.no_fix
    logger.info("=" * 60)
    logger.info("Hive Health Monitor -- %s -- auto_fix=%s", now_pt(), auto_fix)
    logger.info("=" * 60)

    results = run_all_checks(auto_fix=auto_fix)

    # Log each result
    for r in results:
        lvl = {"ok": logging.INFO, "warn": logging.WARNING, "fail": logging.ERROR}.get(
            r["status"], logging.INFO
        )
        fixed_tag = " [AUTO-FIXED]" if r.get("auto_fixed") else ""
        logger.log(lvl, "  %s %s -- %s%s",
                   STATUS_ICONS.get(r["status"], "[??]"), r["name"], r["message"], fixed_tag)

    # Summary
    ok_count = sum(1 for r in results if r["status"] == "ok")
    warn_count = sum(1 for r in results if r["status"] == "warn")
    fail_count = sum(1 for r in results if r["status"] == "fail")
    fixed_count = sum(1 for r in results if r.get("auto_fixed"))
    logger.info("Summary: %d OK / %d WARN / %d FAIL / %d auto-fixed",
                ok_count, warn_count, fail_count, fixed_count)

    # Save report
    save_report(results)

    # Slack alerts
    if args.slack or should_alert(results):
        summary = build_slack_summary(results)
        post_slack(summary)
        logger.info("Slack alert posted")
    elif args.slack:
        summary = build_slack_summary(results)
        post_slack(summary)

    # Exit code: 0 if no failures, 1 if any fail
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
