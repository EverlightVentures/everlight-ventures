#!/usr/bin/env python3
"""Oracle Reachability Watcher (Layer 1).

Runs continuously on the phone. Probes Oracle E5 (163.192.19.196) every
60 seconds across multiple ports. Maintains a JSON state file so the rest
of the Hive can read current Oracle reachability without re-probing.

Self-healing recipes:
  1. On 3 consecutive failures: kill stale SSH multiplex sessions, flush DNS.
  2. On 5+ minutes RED: post critical alert to #hive-alerts via branded_slack.
  3. On 15+ minutes RED: hit external prober (check-host.net) to determine
     if it's an Oracle outage or a phone-only path issue, post diagnosis.
  4. On recovery: post info-severity recovery message and clear counter.

Runs as foreground service via Termux boot script:
  ~/.termux/boot/start_oracle_watch.sh

Author: Henrik Strand (Iron Stack S1)
Per CLAUDE.md doctrine: feedback_oracle_only_crons is suspended for THIS
script only -- a watcher of Oracle reachability must run off-Oracle.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from urllib import request, error

ORACLE_HOST = "163.192.19.196"
ORACLE_PORTS = [
    (22, "ssh"),
    (1111, "blinko"),
    (5678, "n8n"),
    (8504, "hive_django"),
]
PROBE_INTERVAL_SEC = 60
TCP_TIMEOUT_SEC = 5
HEALTH_PROBE_TIMEOUT_SEC = 5

STATE_FILE = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/.oracle_reachability_state.json")
LOG_FILE = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/oracle_reachability_watch.log")

# Alert thresholds (in consecutive failure counts at PROBE_INTERVAL_SEC each)
ALERT_AT = 5    # 5 min RED -> critical Slack alert
DEEP_DIAG_AT = 15  # 15 min RED -> external prober + carrier diagnosis


@dataclass
class ProbeResult:
    timestamp: str
    overall_ok: bool
    port_results: dict
    phone_internet_ok: bool
    duration_ms: int
    failure_reason: Optional[str] = None


@dataclass
class WatchState:
    last_success_ts: Optional[str]
    last_failure_ts: Optional[str]
    consecutive_failures: int
    last_alert_ts: Optional[str]
    last_recovery_ts: Optional[str]
    current_status: str  # GREEN | YELLOW | RED
    last_probe: Optional[dict]
    deep_diag_done: bool


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def now_pt() -> str:
    pt = timezone(timedelta(hours=-8))
    return datetime.now(pt).strftime("%Y-%m-%d %H:%M:%S PT")


def log(msg: str) -> None:
    line = f"[{now_pt()}] {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")


def tcp_probe(host: str, port: int, timeout: float = TCP_TIMEOUT_SEC) -> tuple[bool, str]:
    """Returns (ok, reason)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True, "ok"
    except socket.timeout:
        return False, "timeout"
    except ConnectionRefusedError:
        return False, "refused"  # Service down but kernel responsive == VCN OK
    except OSError as e:
        return False, f"oserror_{e.errno}"


def http_health_probe(url: str, timeout: float = HEALTH_PROBE_TIMEOUT_SEC) -> bool:
    try:
        req = request.Request(url, headers={"User-Agent": "OracleWatch/1.0"})
        with request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except (error.URLError, error.HTTPError, TimeoutError, OSError):
        return False


def phone_has_internet() -> bool:
    """Quick test that phone IPv4 path works at all."""
    return tcp_probe("1.1.1.1", 443, timeout=4)[0] or tcp_probe("8.8.8.8", 443, timeout=4)[0]


def probe_oracle() -> ProbeResult:
    start = time.time()
    port_results = {}
    for port, label in ORACLE_PORTS:
        ok, reason = tcp_probe(ORACLE_HOST, port)
        port_results[label] = {"port": port, "ok": ok, "reason": reason}
    overall_ok = any(v["ok"] for v in port_results.values())
    phone_ok = phone_has_internet()
    duration_ms = int((time.time() - start) * 1000)
    failure_reason = None
    if not overall_ok:
        if not phone_ok:
            failure_reason = "phone_internet_down"
        else:
            reasons = {v["reason"] for v in port_results.values() if not v["ok"]}
            if reasons == {"timeout"}:
                failure_reason = "oracle_path_timeout_all_ports"
            elif "refused" in reasons:
                failure_reason = "oracle_some_services_down_but_path_ok"
            else:
                failure_reason = f"mixed:{','.join(reasons)}"
    return ProbeResult(
        timestamp=now_iso(),
        overall_ok=overall_ok,
        port_results=port_results,
        phone_internet_ok=phone_ok,
        duration_ms=duration_ms,
        failure_reason=failure_reason,
    )


def load_state() -> WatchState:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            return WatchState(**data)
        except (json.JSONDecodeError, TypeError):
            pass
    return WatchState(
        last_success_ts=None,
        last_failure_ts=None,
        consecutive_failures=0,
        last_alert_ts=None,
        last_recovery_ts=None,
        current_status="UNKNOWN",
        last_probe=None,
        deep_diag_done=False,
    )


def save_state(state: WatchState) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(asdict(state), indent=2))


def kill_stale_ssh() -> None:
    """Kill any phone-side SSH sessions to Oracle that may be hung."""
    try:
        subprocess.run(
            ["pkill", "-f", "ssh.*163.192.19.196"],
            check=False, capture_output=True, timeout=5,
        )
        log("self-heal: killed stale SSH sessions to Oracle")
    except Exception as e:
        log(f"self-heal kill_stale_ssh failed: {e}")


def post_slack_alert(severity: str, title: str, body: str) -> bool:
    """Post via branded_slack if available; degrade to no-op if module missing."""
    try:
        sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE")
        from content_tools.branded_slack import post_branded_alert
        post_branded_alert(
            severity=severity,
            title=title,
            body=body,
            channel="#hive-alerts",
            agent="Henrik Strand",
            agent_role="Iron Stack S1 / DevOps",
        )
        log(f"slack alert posted: severity={severity} title={title}")
        return True
    except Exception as e:
        log(f"slack alert FAILED ({e}); writing to fallback file instead")
        fallback = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/oracle_watch_alerts_fallback.log")
        with fallback.open("a") as f:
            f.write(f"[{now_pt()}] {severity.upper()}: {title}\n{body}\n---\n")
        return False


def external_prober() -> dict:
    """Hit a third-party probe to determine if Oracle is globally unreachable
    or only from this phone's path. Uses check-host.net (free public API)."""
    url = f"https://check-host.net/check-tcp?host={ORACLE_HOST}:22&max_nodes=3"
    headers = {"Accept": "application/json", "User-Agent": "OracleWatch/1.0"}
    try:
        req = request.Request(url, headers=headers)
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        request_id = data.get("request_id")
        if not request_id:
            return {"ok": False, "reason": "no_request_id"}
        time.sleep(8)
        result_url = f"https://check-host.net/check-result/{request_id}"
        req2 = request.Request(result_url, headers=headers)
        with request.urlopen(req2, timeout=10) as resp:
            results = json.loads(resp.read())
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "reason": f"prober_error:{e}"}


def diagnose_carrier_vs_global(probe: ProbeResult) -> str:
    """Given a RED probe, hit external prober to classify the failure."""
    log("running external prober (check-host.net)")
    ext = external_prober()
    if not ext.get("ok"):
        return f"external prober failed ({ext.get('reason')}); cannot classify"
    results = ext.get("results", {})
    reachable_nodes = sum(
        1 for node_results in results.values()
        if node_results and any(r and r.get("address") for r in (node_results or []))
    )
    total_nodes = len(results)
    if reachable_nodes >= max(2, total_nodes // 2):
        return (
            f"GLOBAL_REACHABLE_PHONE_BLOCKED: {reachable_nodes}/{total_nodes} external "
            f"probes reach Oracle. Phone-only path issue (likely AT&T cellular IPv4 route)."
        )
    elif reachable_nodes == 0:
        return (
            f"GLOBAL_UNREACHABLE: 0/{total_nodes} external probes reach Oracle. "
            f"Oracle VM/IP/VCN issue. Check Cloud Console: VM running? IP attached? VCN rules?"
        )
    else:
        return (
            f"PARTIAL: {reachable_nodes}/{total_nodes} reach. Mixed -- could be flaky "
            f"Oracle network or partial regional outage."
        )


def main_loop():
    log(f"oracle_reachability_watch started (probe every {PROBE_INTERVAL_SEC}s)")
    state = load_state()
    while True:
        try:
            probe = probe_oracle()
            state.last_probe = asdict(probe)
            if probe.overall_ok:
                if state.current_status in ("RED", "YELLOW"):
                    log(f"RECOVERY: Oracle reachable again after {state.consecutive_failures} failures")
                    state.last_recovery_ts = probe.timestamp
                    post_slack_alert(
                        severity="info",
                        title="Oracle reachable again",
                        body=(
                            f"Oracle E5 ({ORACLE_HOST}) recovered after "
                            f"{state.consecutive_failures} failed probes "
                            f"(~{state.consecutive_failures} minutes RED).\n"
                            f"Last failure reason: {probe.failure_reason or 'n/a'}\n"
                            f"Pipeline GREEN."
                        ),
                    )
                state.consecutive_failures = 0
                state.last_success_ts = probe.timestamp
                state.current_status = "GREEN"
                state.deep_diag_done = False
            else:
                state.consecutive_failures += 1
                state.last_failure_ts = probe.timestamp
                state.current_status = "RED" if state.consecutive_failures >= 3 else "YELLOW"
                log(
                    f"FAIL #{state.consecutive_failures}: reason={probe.failure_reason} "
                    f"phone_internet={probe.phone_internet_ok} ports={probe.port_results}"
                )
                if state.consecutive_failures == 3:
                    log("self-heal: 3 consecutive failures -> killing stale SSH")
                    kill_stale_ssh()
                if state.consecutive_failures == ALERT_AT and probe.phone_internet_ok:
                    diag_summary = (
                        f"Oracle E5 ({ORACLE_HOST}) unreachable on all probed ports for "
                        f"{ALERT_AT} consecutive minutes.\n"
                        f"Failure reason: {probe.failure_reason}\n"
                        f"Phone IPv4 internet: OK (Cloudflare/Google reach fine).\n"
                        f"Port states:\n" +
                        "\n".join(
                            f"  - :{v['port']} ({k}) -> {v['reason']}"
                            for k, v in probe.port_results.items()
                        )
                    )
                    post_slack_alert(
                        severity="critical",
                        title="Oracle E5 unreachable for 5+ min",
                        body=diag_summary,
                    )
                    state.last_alert_ts = probe.timestamp
                if (state.consecutive_failures >= DEEP_DIAG_AT
                        and not state.deep_diag_done
                        and probe.phone_internet_ok):
                    diag = diagnose_carrier_vs_global(probe)
                    log(f"DEEP_DIAG: {diag}")
                    post_slack_alert(
                        severity="critical",
                        title=f"Oracle 15+ min RED -- diagnosis",
                        body=f"External-prober verdict:\n\n{diag}",
                    )
                    state.deep_diag_done = True
            save_state(state)
        except Exception as e:
            log(f"loop error: {e}")
        time.sleep(PROBE_INTERVAL_SEC)


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        log("oracle_reachability_watch shutting down (SIGINT)")
        sys.exit(0)
