#!/usr/bin/env python3
"""
blinko_queue_audit.py -- self-auditing, self-healing health gate for the
Blinko offline-first log queue.

THE WORKFLOW (audit -> heal -> verify -> journal -> report). Idempotent and
safe to run on a cron:

  1. AUDIT   read-only checks on the queue dir, the local Blinko server(s),
             the blinko log files, and the crontab. Nothing is mutated.
  2. HEAL    safe, idempotent repairs ONLY:
               - start a local Blinko server if :1111 is down
               - drain the queue (reuses blinko_queue_drain.drain())
             Never deletes or rewrites logs (Comms Doctrine: no deletion
             without a memory-pipeline pass). Skip heals with --no-heal.
  3. VERIFY  end-to-end proof: enqueue a uniquely-marked probe note, drain it,
             search Blinko for the marker, confirm the round-trip, then delete
             the probe row from the local DB so the RAG stays clean.
  4. JOURNAL append one row to blinko_audit_history.jsonl AND a human-readable
             entry to blinko_audit_history.md, so the next person/agent who
             looks at the queue sees what was checked, found, and fixed.
  5. REPORT  print a concise summary; exit 0 if healthy, 1 if issues remain.

Born 2026-06-03 from a live audit that found: duplicated log lines (cron stdout
double-write), BrokenPipeError tracebacks from the health endpoint, a zombie
ingest cron pointed at the dead old-mother host (129.159.38.250), per-drain
'#hive/probe' RAG pollution, and BOTH local Blinko instances down. Source fixes
for those shipped the same day; this tool is the standing guard so they -- or
similar regressions -- do not silently come back.

Usage:
  python3 blinko_queue_audit.py             # audit + heal + verify + journal
  python3 blinko_queue_audit.py --no-heal   # audit + verify only (read-mostly)
  python3 blinko_queue_audit.py --json      # also emit machine report to stdout
  python3 blinko_queue_audit.py --purge-probes  # additionally delete accumulated
                                                # #hive/probe / audit-probe notes
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOGS = WORKSPACE / "_logs"
QUEUE = LOGS / "blinko_log_queue"
PROCESSED = QUEUE / "processed"
# Canonical phone brain unified to _state on 2026-06-03 (was _logs).
DB_PATH = WORKSPACE / "_state" / "blinko_lite.db"
BLINKO_LITE_PY = WORKSPACE / "06_DEVELOPMENT" / "everlight_os" / "blinko" / "blinko_lite.py"
INGEST_SH = WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts" / "blinko_log_ingest.sh"
SCRIPTS = WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts"
HISTORY_JSONL = LOGS / "blinko_audit_history.jsonl"
HISTORY_MD = LOGS / "blinko_audit_history.md"

# Logs to inspect for tracebacks / duplicate lines / bloat.
BLINKO_LOG_FILES = [
    "blinko_lite.log",
    "blinko_queue_drain.log",
    "blinko_log_ingest.log",
    "blinko_watchdog.log",
]

STUCK_MINUTES = 60          # a pending note older than this is treated as stuck
LOG_SIZE_WARN_MB = 5        # logs larger than this are flagged for rotation
DEAD_HOSTS = ("129.159.38.250", "163.192.19.196")  # old mother + xlm-bot (no Blinko)
HEALTH_PORTS = (1111, 2700)  # local mirror + local write-buffer

# Reuse the canonical drainer rather than re-implementing queue logic.
sys.path.insert(0, str(SCRIPTS))
try:
    import blinko_queue_drain as drainer  # noqa: E402
except Exception as e:  # pragma: no cover - import guard
    drainer = None
    _IMPORT_ERR = repr(e)
else:
    _IMPORT_ERR = None


# -- small helpers ------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _http_get(url: str, timeout: float = 3.0) -> tuple[int, str]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception:
        return 0, ""


def _http_post(url: str, payload: dict, timeout: float = 4.0) -> tuple[int, str]:
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception:
        return 0, ""


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False


# -- 1. AUDIT -----------------------------------------------------------------

def audit_queue() -> dict:
    """Pending/processed counts, oldest-pending age, malformed + stuck notes."""
    QUEUE.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    pending = sorted(p for p in QUEUE.glob("*.md") if p.is_file())
    processed = sum(1 for _ in PROCESSED.glob("*.md"))
    now = _now().timestamp()
    oldest_min = 0.0
    malformed, stuck = [], []
    for p in pending:
        try:
            age_min = (now - p.stat().st_mtime) / 60.0
            oldest_min = max(oldest_min, age_min)
            if age_min > STUCK_MINUTES:
                stuck.append(p.name)
            if not p.read_text(encoding="utf-8", errors="replace").strip():
                malformed.append(p.name)
        except Exception:
            malformed.append(p.name)
    return {
        "pending": len(pending),
        "processed": processed,
        "oldest_pending_min": round(oldest_min, 1),
        "malformed": malformed,
        "stuck": stuck,
    }


def audit_blinko() -> dict:
    """Local Blinko server liveness on each known port."""
    status = {}
    for port in HEALTH_PORTS:
        code, body = _http_get(f"http://127.0.0.1:{port}/health")
        status[f"port_{port}"] = (code == 200 and '"ok"' in body)
    return status


def _tail_lines(path: Path, max_lines: int = 4000) -> list[str]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.readlines()[-max_lines:]
    except Exception:
        return []


def audit_logs() -> dict:
    """Per-log traceback count, duplicate-consecutive-line count, size."""
    out = {}
    for name in BLINKO_LOG_FILES:
        path = LOGS / name
        if not path.exists():
            out[name] = {"exists": False}
            continue
        lines = _tail_lines(path)
        tracebacks = sum(
            1 for ln in lines
            if "Traceback (most recent call" in ln
            or "BrokenPipeError" in ln
            or "ConnectionResetError" in ln
        )
        dups = sum(
            1 for i in range(1, len(lines))
            if lines[i] == lines[i - 1] and lines[i].strip()
        )
        try:
            size_mb = round(path.stat().st_size / 1_048_576, 2)
        except Exception:
            size_mb = 0.0
        out[name] = {
            "exists": True,
            "tracebacks": tracebacks,
            "dup_lines": dups,
            "size_mb": size_mb,
            "oversize": size_mb > LOG_SIZE_WARN_MB,
        }
    return out


def audit_crontab() -> dict:
    """Detect the zombie ingest cron pointed at a dead host."""
    try:
        res = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
        cron = res.stdout if res.returncode == 0 else ""
    except Exception:
        cron = ""
    zombie = False
    detail = ""
    if "blinko_log_ingest" in cron and INGEST_SH.exists():
        script = INGEST_SH.read_text(encoding="utf-8", errors="replace")
        for host in DEAD_HOSTS:
            if host in script:
                zombie = True
                detail = f"blinko_log_ingest.sh targets dead host {host}; superseded by blinko_queue_drain.py"
                break
    return {"zombie_ingest_cron": zombie, "detail": detail}


def audit_probe_pollution() -> int:
    """Count accumulated reachability-probe notes in the local RAG."""
    if not DB_PATH.exists():
        return 0
    try:
        con = sqlite3.connect(str(DB_PATH), timeout=5)
        try:
            cur = con.execute(
                "SELECT COUNT(*) FROM notes WHERE content LIKE ? OR content LIKE ?",
                ("%blinko reachability probe%", "%#hive/audit-probe%"),
            )
            return int(cur.fetchone()[0])
        finally:
            con.close()
    except Exception:
        return -1  # could not read


# -- 2. HEAL ------------------------------------------------------------------

def heal_start_blinko() -> bool:
    """Start a local blinko_lite on :1111 if it is down. Returns True if started."""
    if _port_open(1111):
        return False
    if not BLINKO_LITE_PY.exists():
        return False
    log_path = LOGS / "blinko_lite.log"
    env = {**os.environ, "BLINKO_PORT": "1111", "BLINKO_HOST": "127.0.0.1"}
    try:
        logf = open(log_path, "a")
        subprocess.Popen(
            [sys.executable, str(BLINKO_LITE_PY)],
            stdout=logf, stderr=logf, start_new_session=True, env=env,
        )
    except Exception:
        return False
    # Wait (condition-based) up to ~12s for it to answer /health.
    for _ in range(24):
        if _port_open(1111):
            code, body = _http_get("http://127.0.0.1:1111/health")
            if code == 200 and '"ok"' in body:
                return True
        time.sleep(0.5)
    return _port_open(1111)


def heal_drain() -> dict:
    if drainer is None:
        return {"error": _IMPORT_ERR or "drainer unavailable"}
    try:
        return drainer.drain()
    except Exception as e:
        return {"error": repr(e)}


def heal_purge_probes() -> int:
    """Delete accumulated probe notes from the LOCAL db. Opt-in only."""
    if not DB_PATH.exists():
        return 0
    try:
        con = sqlite3.connect(str(DB_PATH), timeout=5)
        try:
            cur = con.execute(
                "DELETE FROM notes WHERE content LIKE ? OR content LIKE ?",
                ("%blinko reachability probe%", "%#hive/audit-probe%"),
            )
            con.commit()
            return cur.rowcount
        finally:
            con.close()
    except Exception:
        return -1


# -- 3. VERIFY (end-to-end) ---------------------------------------------------

def verify_end_to_end() -> dict:
    """Enqueue a marked probe -> drain -> search it back -> clean up."""
    if drainer is None:
        return {"ok": False, "reason": _IMPORT_ERR or "drainer unavailable"}
    stamp = _now().strftime("%Y%m%d%H%M%S")
    marker = f"auditprobe{stamp}{os.getpid()}"  # single FTS token, no separators
    note = (
        f"# Blinko audit probe {marker}\n#hive/audit-probe\n\n"
        "End-to-end queue verification by blinko_queue_audit.py. "
        "Safe to ignore; auto-removed after the round-trip check."
    )
    result = {"marker": marker, "ok": False}
    try:
        path = drainer.enqueue(note)
        result["enqueued"] = path.name
    except Exception as e:
        result["reason"] = f"enqueue failed: {e!r}"
        return result

    drain_res = heal_drain()
    result["drain"] = drain_res
    target = drain_res.get("target") if isinstance(drain_res, dict) else None

    # Search the marker back through the HTTP API (proves the search path).
    api_found = False
    if target:
        code, body = _http_post(f"{target}/api/v1/note/list", {"searchText": marker, "size": 5})
        api_found = (code == 200 and marker in body)
    result["api_found"] = api_found

    # Authoritative storage check + cleanup against the LOCAL db.
    db_found, cleaned = False, 0
    if DB_PATH.exists():
        try:
            con = sqlite3.connect(str(DB_PATH), timeout=5)
            try:
                cur = con.execute("SELECT COUNT(*) FROM notes WHERE content LIKE ?", (f"%{marker}%",))
                db_found = int(cur.fetchone()[0]) > 0
                cur = con.execute("DELETE FROM notes WHERE content LIKE ?", (f"%{marker}%",))
                con.commit()
                cleaned = cur.rowcount
            finally:
                con.close()
        except Exception as e:
            # Surface, never swallow: a silently-failing DELETE is exactly how
            # the FTS-trigger 'SQL logic error' bug hid for so long.
            result["cleanup_error"] = repr(e)
    result["db_found"] = db_found
    result["cleaned_rows"] = cleaned

    # Remove the drained probe file from processed/ so it doesn't linger.
    try:
        for leftover in PROCESSED.glob("*.md"):
            if marker in leftover.read_text(encoding="utf-8", errors="replace"):
                leftover.unlink()
    except Exception:
        pass

    result["ok"] = bool(api_found or db_found)
    if not result["ok"]:
        result["reason"] = "probe did not round-trip (enqueue->drain->retrieve)"
    return result


# -- assessment ---------------------------------------------------------------

def assess(report: dict) -> tuple[bool, list[str], list[str]]:
    """Return (healthy, issues, recommendations) from the gathered report."""
    issues, recs = [], []
    q = report["queue"]
    if q["stuck"]:
        issues.append(f"{len(q['stuck'])} note(s) stuck >{STUCK_MINUTES}min in queue")
    if q["malformed"]:
        issues.append(f"{len(q['malformed'])} malformed/empty note(s) in queue")
    b = report["blinko"]
    if not b.get("port_1111"):
        issues.append("local Blinko :1111 not answering /health")
    if not b.get("port_2700"):
        recs.append("local Blinko :2700 (write-buffer) down -- no keepalive guards it")
    for name, lg in report["logs"].items():
        if lg.get("tracebacks"):
            issues.append(f"{name}: {lg['tracebacks']} traceback line(s) present")
        if lg.get("dup_lines", 0) > 5:
            issues.append(f"{name}: {lg['dup_lines']} duplicated line(s) (double-logging)")
        if lg.get("oversize"):
            recs.append(f"{name}: {lg['size_mb']}MB -- rotate")
    if report["crontab"].get("zombie_ingest_cron"):
        recs.append("retire zombie cron: " + report["crontab"]["detail"])
    pol = report.get("probe_pollution", 0)
    if isinstance(pol, int) and pol > 50:
        recs.append(f"{pol} reachability-probe notes polluting RAG -- run --purge-probes")
    if not report["verify"].get("ok"):
        issues.append("end-to-end verify FAILED: " + report["verify"].get("reason", "unknown"))
    if report["verify"].get("cleanup_error"):
        issues.append("verify probe cleanup errored: " + report["verify"]["cleanup_error"])
    healthy = not issues
    return healthy, issues, recs


# -- 4. JOURNAL ---------------------------------------------------------------

def journal(report: dict, healthy: bool, issues: list[str], recs: list[str],
            actions: list[str]) -> None:
    ts = report["ts"]
    row = {
        "ts": ts,
        "healthy": healthy,
        "queue": report["queue"],
        "blinko": report["blinko"],
        "logs": report["logs"],
        "crontab": report["crontab"],
        "probe_pollution": report.get("probe_pollution"),
        "verify": report["verify"],
        "actions": actions,
        "issues": issues,
        "recommendations": recs,
    }
    try:
        with HISTORY_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass

    # Human-readable history: newest entry first.
    q = report["queue"]
    v = report["verify"]
    status = "HEALTHY" if healthy else "ISSUES"
    block = [
        f"## {ts} -- {status}",
        "",
        f"- Queue: {q['pending']} pending / {q['processed']} processed"
        f" (oldest pending {q['oldest_pending_min']}min)",
        f"- Blinko: :1111 {'UP' if report['blinko'].get('port_1111') else 'DOWN'},"
        f" :2700 {'UP' if report['blinko'].get('port_2700') else 'DOWN'}",
        f"- Verify (end-to-end): {'PASS' if v.get('ok') else 'FAIL'}"
        f" (api_found={v.get('api_found')}, db_found={v.get('db_found')},"
        f" cleaned={v.get('cleaned_rows')})",
        f"- Actions taken: {', '.join(actions) if actions else 'none'}",
        f"- Issues: {'; '.join(issues) if issues else 'none'}",
        f"- Recommendations: {'; '.join(recs) if recs else 'none'}",
        "",
    ]
    new_entry = "\n".join(block)
    header = (
        "# Blinko Queue Audit History\n\n"
        "Running journal written by `blinko_queue_audit.py`. Newest first. Each\n"
        "entry records what was checked, what was found, and what was fixed so the\n"
        "next person/agent who opens the queue has the full history.\n\n"
    )
    try:
        existing = HISTORY_MD.read_text(encoding="utf-8") if HISTORY_MD.exists() else ""
        body = existing[len(header):] if existing.startswith(header) else existing
        HISTORY_MD.write_text(header + new_entry + body, encoding="utf-8")
    except Exception:
        pass


# -- 5. REPORT / main ---------------------------------------------------------

def run(do_heal: bool = True, purge_probes: bool = False) -> dict:
    report = {"ts": _now().isoformat()}
    actions: list[str] = []

    # 1. AUDIT
    report["queue"] = audit_queue()
    report["blinko"] = audit_blinko()
    report["logs"] = audit_logs()
    report["crontab"] = audit_crontab()
    report["probe_pollution"] = audit_probe_pollution()

    # 2. HEAL
    if do_heal:
        if heal_start_blinko():
            actions.append("started local Blinko :1111")
            report["blinko"] = audit_blinko()  # refresh after start
        if purge_probes:
            n = heal_purge_probes()
            if n > 0:
                actions.append(f"purged {n} probe note(s)")
            report["probe_pollution"] = audit_probe_pollution()

    # 3. VERIFY (also drains the queue as a side effect)
    report["verify"] = verify_end_to_end() if do_heal else {"ok": None, "reason": "skipped (--no-heal)"}
    if do_heal:
        actions.append("drained queue + ran end-to-end probe")
        report["queue"] = audit_queue()  # refresh after drain

    healthy, issues, recs = assess(report)

    # 4. JOURNAL
    journal(report, healthy, issues, recs, actions)

    report["_healthy"] = healthy
    report["_issues"] = issues
    report["_recommendations"] = recs
    report["_actions"] = actions
    return report


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Blinko queue audit + self-heal + verify.")
    ap.add_argument("--no-heal", action="store_true", help="audit + journal only, no repairs/drain")
    ap.add_argument("--json", action="store_true", help="print machine-readable report")
    ap.add_argument("--purge-probes", action="store_true", help="delete accumulated probe notes")
    args = ap.parse_args(argv)

    report = run(do_heal=not args.no_heal, purge_probes=args.purge_probes)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"BLINKO QUEUE AUDIT  {report['ts']}")
        print(f"  status   : {'HEALTHY' if report['_healthy'] else 'ISSUES FOUND'}")
        q = report["queue"]
        print(f"  queue    : {q['pending']} pending / {q['processed']} processed")
        b = report["blinko"]
        print(f"  blinko   : :1111 {'UP' if b.get('port_1111') else 'DOWN'} | "
              f":2700 {'UP' if b.get('port_2700') else 'DOWN'}")
        v = report["verify"]
        print(f"  verify   : {'PASS' if v.get('ok') else ('SKIPPED' if v.get('ok') is None else 'FAIL')}")
        if report["_actions"]:
            print(f"  actions  : {'; '.join(report['_actions'])}")
        if report["_issues"]:
            print("  issues   :")
            for i in report["_issues"]:
                print(f"    - {i}")
        if report["_recommendations"]:
            print("  recommend:")
            for r in report["_recommendations"]:
                print(f"    - {r}")
        print(f"  history  : {HISTORY_MD}")
    return 0 if report["_healthy"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
