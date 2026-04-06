#!/usr/bin/env python3
"""
Hive Watchdog -- Service Health Monitor + Auto-Restart

Runs every 2 minutes via cron on Oracle E5.
Monitors all critical services, restarts them if down,
and posts alerts to #hive-alerts if a service is flapping.

Cron: */2 * * * * /usr/bin/python3 /home/opc/hive_watchdog.py >> /tmp/hive_watchdog.log 2>&1

Monitors:
  - xlm-bot, xlm-ws, xlm-dashboard, xlm-liqfeed (trading stack)
  - n8n, blinko (automation + knowledge)
  - hive-django, hive-slack-agent (ops)

Also checks:
  - XLM WS live tick freshness (stale data = dead feed)
  - n8n HTTP health
  - Blinko HTTP health
  - Disk usage > 85%
  - RAM usage > 90%
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# --- Config ---
LOG_FILE = "/tmp/hive_watchdog.log"
STATE_FILE = "/tmp/watchdog_state.json"
LIVE_TICK_PATH = "/home/opc/xlm-bot/logs/live_tick.json"

# Slack config
SLACK_TOKEN = "xoxb-8645963765681-10594020158069-eJRt13YP8qedI6DnQwupuFfy"
SLACK_CHANNEL = "C0ANPRCA4AD"  # #hive-alerts

# Services to monitor
CRITICAL_SERVICES = [
    "xlm-bot",
    "xlm-ws",
    "xlm-dashboard",
    "xlm-liqfeed",
    "n8n",
    "blinko",
    "hive-django",
    "hive-slack-agent",
    "ollama",
    "netdata",
]

# Container services (managed by podman, checked differently)
CONTAINER_SERVICES = [
    "langfuse",
    "nextcloud",
    "polymarket",
    "computer-use",
]

# Health check endpoints
HEALTH_CHECKS = {
    "n8n": "http://localhost:5678",
    "blinko": "http://localhost:1111",
    "langfuse": "http://localhost:3100",
    "nextcloud": "http://localhost:8580/status.php",
    "ollama": "http://localhost:11434/api/tags",
}

# Thresholds
MAX_RESTARTS_PER_HOUR = 3
LIVE_TICK_STALE_SECONDS = 120  # 2 minutes
DISK_THRESHOLD_PCT = 85
RAM_THRESHOLD_PCT = 90


def log(msg: str, level: str = "INFO") -> None:
    """Log with timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_state() -> dict:
    """Load restart tracking state."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {"restarts": {}, "alerts_sent": {}}


def save_state(state: dict) -> None:
    """Persist restart tracking state."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"State save failed: {e}", "WARN")


def slack_alert(message: str) -> None:
    """Post alert to #hive-alerts via Slack API."""
    try:
        payload = json.dumps({
            "channel": SLACK_CHANNEL,
            "text": message,
            "unfurl_links": False,
        }).encode()
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=payload,
            headers={
                "Authorization": f"Bearer {SLACK_TOKEN}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                log(f"Slack alert failed: {result.get('error')}", "WARN")
    except Exception as e:
        log(f"Slack alert error: {e}", "WARN")


def check_service(name: str) -> bool:
    """Check if a systemd service is active. Returns True if active."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def restart_service(name: str) -> bool:
    """Restart a systemd service. Returns True on success."""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "restart", name],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except Exception as e:
        log(f"Restart failed for {name}: {e}", "ERROR")
        return False


def get_restart_count_last_hour(state: dict, service: str) -> int:
    """Count restarts in the last hour for a service."""
    now = time.time()
    restarts = state.get("restarts", {}).get(service, [])
    # Filter to last hour
    recent = [t for t in restarts if now - t < 3600]
    # Update state to only keep recent
    if service not in state.get("restarts", {}):
        state.setdefault("restarts", {})[service] = []
    state["restarts"][service] = recent
    return len(recent)


def record_restart(state: dict, service: str) -> None:
    """Record a restart event."""
    state.setdefault("restarts", {}).setdefault(service, []).append(time.time())


def check_live_tick_freshness() -> tuple[bool, float]:
    """Check if XLM WS is producing fresh ticks. Returns (is_fresh, age_seconds)."""
    try:
        if not os.path.exists(LIVE_TICK_PATH):
            return False, float("inf")
        mtime = os.path.getmtime(LIVE_TICK_PATH)
        age = time.time() - mtime
        return age < LIVE_TICK_STALE_SECONDS, age
    except Exception:
        return False, float("inf")


def check_http_health(url: str, timeout: int = 5) -> bool:
    """Check if an HTTP endpoint is responding."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False


def check_disk_usage() -> tuple[bool, float]:
    """Check disk usage. Returns (is_ok, usage_pct)."""
    try:
        result = subprocess.run(
            ["df", "/", "--output=pcent"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            pct = float(lines[1].strip().rstrip("%"))
            return pct < DISK_THRESHOLD_PCT, pct
    except Exception:
        pass
    return True, 0.0


def check_ram_usage() -> tuple[bool, float]:
    """Check RAM usage. Returns (is_ok, usage_pct)."""
    try:
        with open("/proc/meminfo") as f:
            info = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1])
            total = info.get("MemTotal", 1)
            available = info.get("MemAvailable", info.get("MemFree", 0))
            used_pct = ((total - available) / total) * 100
            return used_pct < RAM_THRESHOLD_PCT, used_pct
    except Exception:
        pass
    return True, 0.0


def main():
    state = load_state()
    issues = []
    restarts_done = []
    flapping = []

    # --- Check each service ---
    for service in CRITICAL_SERVICES:
        is_active = check_service(service)
        if is_active:
            continue

        restart_count = get_restart_count_last_hour(state, service)

        if restart_count >= MAX_RESTARTS_PER_HOUR:
            # Service is flapping -- alert instead of restart
            flapping.append(f"{service} (restarted {restart_count}x in last hour)")
            log(f"FLAPPING: {service} -- {restart_count} restarts in last hour, alerting instead", "WARN")
        else:
            # Restart it
            log(f"DOWN: {service} -- attempting restart ({restart_count} prior restarts this hour)")
            success = restart_service(service)
            if success:
                record_restart(state, service)
                restarts_done.append(service)
                log(f"RESTARTED: {service}")
            else:
                issues.append(f"{service} restart FAILED")
                log(f"RESTART FAILED: {service}", "ERROR")

    # --- Check container services ---
    for service in CONTAINER_SERVICES:
        is_active = check_service(service)
        if is_active:
            continue

        restart_count = get_restart_count_last_hour(state, service)
        if restart_count >= MAX_RESTARTS_PER_HOUR:
            flapping.append(f"{service} (container, restarted {restart_count}x in last hour)")
            log(f"FLAPPING: {service} container -- alerting instead", "WARN")
        else:
            log(f"DOWN: {service} container -- attempting restart")
            success = restart_service(service)
            if success:
                record_restart(state, service)
                restarts_done.append(service)
                log(f"RESTARTED: {service} container")
            else:
                issues.append(f"{service} container restart FAILED")
                log(f"RESTART FAILED: {service} container", "ERROR")

    # --- Check live tick freshness ---
    tick_fresh, tick_age = check_live_tick_freshness()
    if not tick_fresh:
        age_str = f"{tick_age:.0f}s" if tick_age < float("inf") else "missing"
        issues.append(f"xlm-ws tick stale ({age_str})")
        log(f"STALE: live_tick.json age={age_str}", "WARN")

    # --- HTTP health checks ---
    for name, url in HEALTH_CHECKS.items():
        if not check_http_health(url):
            issues.append(f"{name} HTTP not responding")
            log(f"HTTP DOWN: {name} at {url}", "WARN")

    # --- Disk usage ---
    disk_ok, disk_pct = check_disk_usage()
    if not disk_ok:
        issues.append(f"Disk at {disk_pct:.0f}%")
        log(f"DISK HIGH: {disk_pct:.0f}%", "WARN")

    # --- RAM usage ---
    ram_ok, ram_pct = check_ram_usage()
    if not ram_ok:
        issues.append(f"RAM at {ram_pct:.0f}%")
        log(f"RAM HIGH: {ram_pct:.0f}%", "WARN")

    # --- Post alerts ---
    alert_parts = []

    if flapping:
        alert_parts.append(
            f":rotating_light: *FLAPPING SERVICES* (auto-restart disabled):\n"
            + "\n".join(f"  - {s}" for s in flapping)
        )

    if issues:
        alert_parts.append(
            f":warning: *Infrastructure Issues:*\n"
            + "\n".join(f"  - {i}" for i in issues)
        )

    if restarts_done:
        alert_parts.append(
            f":arrows_counterclockwise: *Auto-Restarted:*\n"
            + "\n".join(f"  - {s}" for s in restarts_done)
        )

    if alert_parts:
        ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
        message = f"*Hive Watchdog [{ts}]*\n\n" + "\n\n".join(alert_parts)
        slack_alert(message)
        log(f"Alert sent: {len(flapping)} flapping, {len(issues)} issues, {len(restarts_done)} restarted")
    else:
        log("All services healthy")

    save_state(state)


if __name__ == "__main__":
    main()
