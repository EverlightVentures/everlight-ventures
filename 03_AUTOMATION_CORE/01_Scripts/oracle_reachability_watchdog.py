#!/usr/bin/env python3
"""oracle_reachability_watchdog.py -- phone-side Oracle E5 watchdog.

Author: Elias Varga (Iron Stack -- Verifier)
Catchphrase enforced: "Green dashboard, red assumptions."

Purpose
-------
Phone (Termux/PRoot) has NO systemd. This script runs from cron every 5 min
and verifies Oracle E5 (163.192.19.196) is reachable on the three sockets
that matter for ops:

    22   -- SSH        (deploys, voice, manual ops)
    1111 -- Blinko     (RAG knowledge base)
    8504 -- Django     (hive_dashboard, reports, taskboard)

State machine
-------------
    UNKNOWN -> ALIVE  -> ALIVE  -> ALIVE  ...
                  |        |
                  v        v
                FAIL_1 -> FAIL_2 -> FAIL_3 = DEAD (alert + recovery)
                                       |
                                       +-> ALIVE again = recovered (alert)

Three CONSECUTIVE failures trip the dead state. We do not panic on a single
flap (mobile data, NAT churn, VCN ARP timeout). Three in a row across 15
minutes is a real outage.

Recovery sequence (when we go DEAD)
-----------------------------------
    1. log every stuck process targeting 163.192.19.196 (ss, ps, lsof)
    2. SIGTERM those processes; SIGKILL if still alive after 3s
    3. flush DNS resolver caches we can reach (resolvectl, dscacheutil
       are absent on Termux -- we no-op gracefully and log it)
    4. attempt one curl to https://163.192.19.196:8504 with 5s timeout
       to seed the routing table after kill
    5. record everything we DID, not what we ASSUMED happened

Slack
-----
We post to #hive-alerts on transition events ONLY. Post storms are noise.
    ALIVE -> DEAD: severity=critical, "Oracle unreachable for 15 minutes"
    DEAD  -> ALIVE: severity=info, "Oracle recovered after Xmin"
We tolerate a Slack post failing -- the local log is the source of truth.

Operator Truth doctrine
-----------------------
Every log line records what the watchdog OBSERVED, not what it expects.
A port timing out is logged as "timeout 5.0s", not "down". A connection
refused is logged as "ECONNREFUSED", not "down". Marquise reads these
logs to make real-money decisions; vague is a lie.

Idempotent
----------
- Single state file at _logs/oracle_watchdog_state.json with last status
- Lock file at _logs/oracle_watchdog.lock (PID + start time)
- A cron-launched copy that finds an existing live lock <2 min old exits
  immediately. This makes the cron entry safe at any frequency.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_DIR = WORKSPACE / "_logs"
LOG_FILE = LOG_DIR / "oracle_watchdog.log"          # JSONL, append-only
STATE_FILE = LOG_DIR / "oracle_watchdog_state.json"
LOCK_FILE = LOG_DIR / "oracle_watchdog.lock"

# ── target ───────────────────────────────────────────────────────────
ORACLE_IP = "163.192.19.196"
ORACLE_PORTS = [22, 1111, 8504]
TCP_TIMEOUT_S = 5.0
DEAD_AFTER_N_FAILS = 3
SLACK_CHANNEL = "#hive-alerts"
LOCK_STALE_S = 120

# ── content_tools import (best-effort) ───────────────────────────────
sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(event: str, **fields) -> dict:
    """Append one JSONL row. Returns the row for caller side-use."""
    row = {"ts": _utc_now_iso(), "event": event, **fields}
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    return row


# ── lock ─────────────────────────────────────────────────────────────
def _acquire_lock() -> bool:
    """Return True if we got the lock; False if another live copy holds it."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            age = time.time() - LOCK_FILE.stat().st_mtime
            if age < LOCK_STALE_S:
                return False
        except OSError:
            pass
    LOCK_FILE.write_text(f"{os.getpid()} {_utc_now_iso()}\n", encoding="utf-8")
    return True


def _release_lock() -> None:
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass


# ── state ────────────────────────────────────────────────────────────
def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {"status": "UNKNOWN", "consecutive_fails": 0,
                "last_alive_iso": None, "last_dead_iso": None,
                "last_alert_status": None}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "UNKNOWN", "consecutive_fails": 0,
                "last_alive_iso": None, "last_dead_iso": None,
                "last_alert_status": None}


def _save_state(state: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── probes ───────────────────────────────────────────────────────────
def probe_port(host: str, port: int, timeout: float = TCP_TIMEOUT_S) -> dict:
    """Single TCP connect test. Returns observation dict."""
    t0 = time.monotonic()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    obs = {"host": host, "port": port, "ok": False,
           "latency_ms": None, "error": None}
    try:
        sock.connect((host, port))
        obs["ok"] = True
        obs["latency_ms"] = round((time.monotonic() - t0) * 1000, 1)
    except socket.timeout:
        obs["error"] = f"timeout {timeout}s"
    except OSError as e:
        # ECONNREFUSED / EHOSTUNREACH / ENETUNREACH all land here
        obs["error"] = f"{e.__class__.__name__}: {e}"
    finally:
        try:
            sock.close()
        except OSError:
            pass
    return obs


def probe_oracle() -> dict:
    """Probe all configured ports. Returns aggregate observation."""
    results = [probe_port(ORACLE_IP, p) for p in ORACLE_PORTS]
    any_ok = any(r["ok"] for r in results)
    all_ok = all(r["ok"] for r in results)
    return {"any_ok": any_ok, "all_ok": all_ok, "ports": results}


# ── recovery actions ─────────────────────────────────────────────────
def _run(cmd: list[str], timeout: float = 10.0) -> dict:
    """Run a command, capture output. Never raises."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, check=False)
        return {"cmd": cmd, "rc": proc.returncode,
                "stdout": (proc.stdout or "")[:1000],
                "stderr": (proc.stderr or "")[:1000]}
    except FileNotFoundError:
        return {"cmd": cmd, "rc": -1, "stdout": "", "stderr": "binary not found"}
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "rc": -2, "stdout": "", "stderr": f"timeout {timeout}s"}
    except OSError as e:
        return {"cmd": cmd, "rc": -3, "stdout": "", "stderr": str(e)}


def find_stuck_processes() -> list[dict]:
    """Return PIDs whose cmdline references the Oracle IP."""
    suspects: list[dict] = []
    proc_root = Path("/proc")
    if not proc_root.exists():
        return suspects
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace")
        except (OSError, UnicodeDecodeError):
            continue
        if ORACLE_IP in cmdline or "oracle-bot" in cmdline or "oracle-mcp" in cmdline:
            # filter out self
            try:
                if int(entry.name) == os.getpid():
                    continue
            except ValueError:
                continue
            suspects.append({"pid": int(entry.name), "cmdline": cmdline.strip()[:300]})
    return suspects


def kill_stuck_processes(suspects: list[dict]) -> list[dict]:
    """SIGTERM, then SIGKILL after grace. Log each step."""
    actions = []
    for s in suspects:
        pid = s["pid"]
        # SIGTERM
        try:
            os.kill(pid, signal.SIGTERM)
            actions.append({"pid": pid, "signal": "SIGTERM", "ok": True})
        except OSError as e:
            actions.append({"pid": pid, "signal": "SIGTERM", "ok": False, "error": str(e)})
            continue
    if actions:
        time.sleep(3)
    # SIGKILL stragglers
    for s in suspects:
        pid = s["pid"]
        try:
            os.kill(pid, 0)  # alive check
        except OSError:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
            actions.append({"pid": pid, "signal": "SIGKILL", "ok": True})
        except OSError as e:
            actions.append({"pid": pid, "signal": "SIGKILL", "ok": False, "error": str(e)})
    return actions


def flush_dns_caches() -> list[dict]:
    """Best-effort DNS cache flush. Termux has none of these by default --
    we still try so log records what's actually present on this device."""
    attempts = []
    candidates = [
        ["resolvectl", "flush-caches"],
        ["systemd-resolve", "--flush-caches"],
        ["nscd", "-i", "hosts"],
        ["dscacheutil", "-flushcache"],
    ]
    for cmd in candidates:
        attempts.append(_run(cmd, timeout=5))
    return attempts


def seed_route() -> dict:
    """Single curl to seed the route table after kills. Use --max-time
    so cron does not hang."""
    return _run(
        ["curl", "-sS", "-o", "/dev/null", "-w", "http=%{http_code} t=%{time_total}",
         "--max-time", "8", "--connect-timeout", "5",
         f"https://{ORACLE_IP}:8504", "-k"],
        timeout=12,
    )


# ── slack ────────────────────────────────────────────────────────────
def slack_alert(title: str, detail: str, severity: str = "critical") -> dict:
    """Post via branded_slack. Tolerate failure."""
    try:
        from content_tools.branded_slack import post_branded_alert  # type: ignore
        res = post_branded_alert(
            channel=SLACK_CHANNEL,
            title=title,
            detail=detail,
            severity=severity,
            agent_name="Elias Varga",
        )
        return {"ok": getattr(res, "ok", False),
                "ts": getattr(res, "ts", None),
                "error": getattr(res, "error", None)}
    except ImportError as e:
        return {"ok": False, "error": f"branded_slack import: {e}"}
    except (RuntimeError, OSError, ValueError) as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


# ── main loop ────────────────────────────────────────────────────────
def main() -> int:
    if not _acquire_lock():
        # another copy is running -- safe to exit
        sys.stdout.write("watchdog: another copy holds the lock; exiting\n")
        return 0
    try:
        state = _load_state()
        prev_status = state.get("status", "UNKNOWN")

        observation = probe_oracle()
        any_ok = observation["any_ok"]
        all_ok = observation["all_ok"]

        _log("probe", any_ok=any_ok, all_ok=all_ok, ports=observation["ports"])

        if any_ok:
            # at least one port answered = the host is up; treat as ALIVE
            state["consecutive_fails"] = 0
            new_status = "ALIVE"
            state["last_alive_iso"] = _utc_now_iso()
        else:
            state["consecutive_fails"] = int(state.get("consecutive_fails", 0)) + 1
            if state["consecutive_fails"] >= DEAD_AFTER_N_FAILS:
                new_status = "DEAD"
                state["last_dead_iso"] = _utc_now_iso()
            else:
                # not yet considered dead; hold previous status (or UNKNOWN)
                new_status = "DEGRADED"

        state["status"] = new_status

        # transition events drive recovery + slack
        transition = (prev_status, new_status)

        if new_status == "DEAD" and state.get("last_alert_status") != "DEAD":
            # 1) snapshot stuck processes
            suspects = find_stuck_processes()
            _log("recovery_suspects", count=len(suspects), suspects=suspects)
            # 2) kill them
            kill_actions = kill_stuck_processes(suspects)
            _log("recovery_kills", actions=kill_actions)
            # 3) DNS flush (best-effort)
            dns = flush_dns_caches()
            _log("recovery_dns", attempts=dns)
            # 4) seed route
            seed = seed_route()
            _log("recovery_seed", **seed)
            # 5) slack alert
            detail = (
                f"Oracle E5 ({ORACLE_IP}) unreachable on ports "
                f"{ORACLE_PORTS} for {DEAD_AFTER_N_FAILS} consecutive 5-min checks. "
                f"Killed {len(kill_actions)} stuck process(es). Seed-curl: "
                f"rc={seed.get('rc')} stderr={(seed.get('stderr') or '')[:120]}"
            )
            slack_res = slack_alert(
                title="Oracle E5 UNREACHABLE -- recovery sequence ran",
                detail=detail,
                severity="critical",
            )
            _log("alert_posted", status="DEAD", slack=slack_res)
            state["last_alert_status"] = "DEAD"

        elif new_status == "ALIVE" and prev_status == "DEAD":
            # recovered
            detail = (
                f"Oracle E5 ({ORACLE_IP}) is reachable again. "
                f"Ports up: {[p['port'] for p in observation['ports'] if p['ok']]} "
                f"(latency: {[(p['port'], p['latency_ms']) for p in observation['ports'] if p['ok']]})"
            )
            slack_res = slack_alert(
                title="Oracle E5 RECOVERED",
                detail=detail,
                severity="info",
            )
            _log("alert_posted", status="ALIVE", slack=slack_res)
            state["last_alert_status"] = "ALIVE"

            # auto-fire post-recovery redeploy (idempotent, runs in background)
            try:
                import subprocess
                redeploy = subprocess.Popen(
                    ["bash", "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/post_recovery_redeploy.sh"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                _log("post_recovery_redeploy_launched", pid=redeploy.pid)
            except Exception as e:
                _log("post_recovery_redeploy_launch_failed", error=str(e))

        _log("transition", from_=prev_status, to=new_status,
             consecutive_fails=state["consecutive_fails"])
        _save_state(state)
        return 0
    finally:
        _release_lock()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _release_lock()
        sys.exit(130)
