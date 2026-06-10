#!/usr/bin/env python3
"""oracle_reachability_watchdog_oracle_side.py -- Oracle-side mirror.

Author: Elias Varga (Iron Stack -- Verifier)

Why this exists
---------------
When the phone-side watchdog says "Oracle is dead," the failure is one of:
    (a) phone network         -- nothing on Oracle is wrong
    (b) Oracle VCN ingress    -- Oracle is healthy, ingress rule changed
    (c) Oracle VM             -- Oracle itself died

We can't tell (a) from (b)/(c) just from the phone. This script runs on
Oracle and proves liveness from the OTHER side. When phone-side reconnects,
both logs are diff-able and the truth is obvious.

What it does (every 60s, intended as a systemd timer when Oracle is up)
-----------------------------------------------------------------------
    1. Egress test -- Oracle's own outbound to a few canonical hosts:
         1.1.1.1:53, 8.8.8.8:53, github.com:443, slack.com:443
       If egress fails, Oracle's network is broken; restart networking
       (logged, not auto-fixed -- restarting networking can lock us out).
    2. Self-loop test -- localhost ports 22, 1111, 5678, 8504, 8080.
       Each is a service-level health check independent of the systemd
       unit's "active (running)" claim. Operator Truth: "active" is not
       proof.
    3. Service auto-restart -- if a self-loop port is dead but its
       systemd unit is "active", we have a stuck process. We restart
       the unit (only those in OUR allowlist; never blanket).
    4. Phone-side liveness flag -- writes /home/opc/.watchdog_pulse with
       UTC iso each successful run. Phone-side can SSH-cat this on
       recovery to confirm Oracle was up the whole time (= phone-side
       network was the problem).

Logs
----
JSONL at /home/opc/_logs/oracle_watchdog_local.log

Slack
-----
Same #hive-alerts, but tagged source=oracle-side so we can tell them apart
on the dashboard.

Operator Truth
--------------
Service active != service serving. We probe the actual port. We log what
the port said, not what systemd claimed. If a unit is "active" but its
port refuses, that is a stuck process and we say so by name.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── constants ────────────────────────────────────────────────────────
LOCAL_LOG_DIR = Path("/home/opc/_logs")
LOG_FILE = LOCAL_LOG_DIR / "oracle_watchdog_local.log"
PULSE_FILE = Path("/home/opc/.watchdog_pulse")
STATE_FILE = LOCAL_LOG_DIR / "oracle_watchdog_local_state.json"

# Egress: prove we can reach the internet at all
EGRESS_TARGETS = [
    ("1.1.1.1", 53),
    ("8.8.8.8", 53),
    ("github.com", 443),
    ("slack.com", 443),
]

# Self-loop: services we expect to answer locally
LOCAL_SERVICES = [
    {"port": 22,   "unit": "ssh.service",            "label": "ssh"},
    {"port": 1111, "unit": "blinko.service",         "label": "blinko"},
    {"port": 5678, "unit": "n8n.service",            "label": "n8n"},
    {"port": 8504, "unit": "hive-django.service",    "label": "django"},
    {"port": 8502, "unit": "xlm-dash-react.service", "label": "react-dash"},
    {"port": 8200, "unit": "hive-voice.service",     "label": "voice"},
    {"port": 8080, "unit": "nginx.service",          "label": "nginx"},
]

# Allowlist of units we are permitted to restart automatically
AUTORESTART_ALLOWLIST = {
    "blinko.service", "n8n.service", "hive-django.service",
    "xlm-dash-react.service", "hive-voice.service",
}

TCP_TIMEOUT_S = 4.0
SLACK_CHANNEL = "#hive-alerts"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(event: str, **fields) -> dict:
    row = {"ts": _utc_now_iso(), "event": event, "src": "oracle-side", **fields}
    LOCAL_LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    return row


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {"last_status": {}, "last_alert_at": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"last_status": {}, "last_alert_at": {}}


def _save_state(state: dict) -> None:
    LOCAL_LOG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def probe_tcp(host: str, port: int, timeout: float = TCP_TIMEOUT_S) -> dict:
    t0 = time.monotonic()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    obs = {"host": host, "port": port, "ok": False, "latency_ms": None, "error": None}
    try:
        sock.connect((host, port))
        obs["ok"] = True
        obs["latency_ms"] = round((time.monotonic() - t0) * 1000, 1)
    except socket.timeout:
        obs["error"] = f"timeout {timeout}s"
    except OSError as e:
        obs["error"] = f"{e.__class__.__name__}: {e}"
    finally:
        try:
            sock.close()
        except OSError:
            pass
    return obs


def systemctl_is_active(unit: str) -> str:
    try:
        proc = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return (proc.stdout or "").strip() or "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        return f"error:{e.__class__.__name__}"


def systemctl_restart(unit: str) -> dict:
    try:
        proc = subprocess.run(
            ["sudo", "-n", "systemctl", "restart", unit],
            capture_output=True, text=True, timeout=20, check=False,
        )
        return {"unit": unit, "rc": proc.returncode,
                "stdout": (proc.stdout or "")[:400],
                "stderr": (proc.stderr or "")[:400]}
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        return {"unit": unit, "rc": -1, "stdout": "", "stderr": str(e)}


def slack_alert(title: str, detail: str, severity: str) -> dict:
    """Post to #hive-alerts via branded_slack. Tolerate failure."""
    sys.path.insert(0, "/home/opc")
    try:
        from content_tools.branded_slack import post_branded_alert  # type: ignore
        res = post_branded_alert(
            channel=SLACK_CHANNEL,
            title=title,
            detail=detail,
            severity=severity,
            agent_name="Elias Varga (oracle-side)",
        )
        return {"ok": getattr(res, "ok", False),
                "ts": getattr(res, "ts", None),
                "error": getattr(res, "error", None)}
    except ImportError as e:
        return {"ok": False, "error": f"branded_slack import: {e}"}
    except (RuntimeError, OSError, ValueError) as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


def main() -> int:
    state = _load_state()

    # 1) egress
    egress_results = [probe_tcp(h, p) for h, p in EGRESS_TARGETS]
    egress_ok_count = sum(1 for r in egress_results if r["ok"])
    egress_healthy = egress_ok_count >= 2  # require >=2 of 4 to count as ok
    _log("egress_probe", ok_count=egress_ok_count, total=len(egress_results),
         results=egress_results)

    if not egress_healthy:
        _log("egress_unhealthy", note="Oracle cannot reach the internet -- "
             "skipping local restarts to avoid making it worse")
        prev = state["last_status"].get("egress", "ok")
        if prev != "down":
            slack_alert(
                title="Oracle EGRESS down",
                detail=f"Oracle ({ORACLE_PUBLIC()}) cannot reach the internet. "
                       f"Egress probes: {egress_results}",
                severity="critical",
            )
            state["last_status"]["egress"] = "down"
            _save_state(state)
        return 0
    else:
        if state["last_status"].get("egress") == "down":
            slack_alert(
                title="Oracle EGRESS recovered",
                detail=f"Oracle internet egress restored. "
                       f"{egress_ok_count}/{len(egress_results)} targets ok.",
                severity="info",
            )
        state["last_status"]["egress"] = "ok"

    # 2) self-loop
    actions: list[dict] = []
    for svc in LOCAL_SERVICES:
        port = svc["port"]
        unit = svc["unit"]
        label = svc["label"]
        port_obs = probe_tcp("127.0.0.1", port)
        unit_active = systemctl_is_active(unit)
        _log("local_probe", label=label, unit=unit,
             port=port, port_ok=port_obs["ok"],
             port_latency_ms=port_obs["latency_ms"],
             port_error=port_obs["error"], unit_active=unit_active)

        prev = state["last_status"].get(label, "unknown")
        cur = "ok" if port_obs["ok"] else "down"

        # 3) auto-restart only if (a) port dead, (b) unit "active" = stuck process,
        #    (c) unit on the allowlist
        if not port_obs["ok"] and unit_active == "active" and unit in AUTORESTART_ALLOWLIST:
            restart = systemctl_restart(unit)
            actions.append({"label": label, "action": "restart_stuck_active",
                            "result": restart})
            _log("autorestart", label=label, unit=unit, result=restart)
            # alert only on first dead, not every cycle
            if prev != "down":
                slack_alert(
                    title=f"Oracle service {label} stuck -- restarted",
                    detail=f"Unit {unit} reported active but port {port} did not "
                           f"answer. Issued systemctl restart "
                           f"(rc={restart['rc']}).",
                    severity="warning",
                )
        elif not port_obs["ok"] and unit_active != "active":
            _log("unit_not_active", unit=unit, status=unit_active)
            if prev != "down":
                slack_alert(
                    title=f"Oracle service {label} DOWN",
                    detail=f"Unit {unit} status={unit_active}. Port {port} "
                           f"did not answer. NOT auto-restarting (unit is not "
                           f"in active state -- needs human eyes).",
                    severity="warning",
                )

        if port_obs["ok"] and prev == "down":
            slack_alert(
                title=f"Oracle service {label} RECOVERED",
                detail=f"Port {port} responding ({port_obs['latency_ms']}ms).",
                severity="info",
            )

        state["last_status"][label] = cur

    # 4) write pulse so phone-side can prove Oracle was alive
    PULSE_FILE.write_text(_utc_now_iso() + "\n", encoding="utf-8")

    _save_state(state)
    _log("cycle_done", actions=actions)
    return 0


def ORACLE_PUBLIC() -> str:
    """Best-effort lookup of Oracle's public IP for log readability."""
    try:
        proc = subprocess.run(
            ["curl", "-sS", "--max-time", "3", "https://api.ipify.org"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return (proc.stdout or "").strip() or "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "unknown"


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
