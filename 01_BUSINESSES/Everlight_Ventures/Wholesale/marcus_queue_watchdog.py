"""marcus_queue_watchdog -- Justine Gate G compliance watchdog.

Why this exists
---------------
TX deals (and any other state we route through Marcus quarterback review)
get parked in `Wholesale/marcus_queue/<deal_id>.json` by
`rex_negotiator._queue_for_marcus_review()`. If Marcus does not triage a
queued deal within 24 hours we miss the SB 1577 / DTPA window where the
seller still expects a human reply. Justine's audit (May 2026) flagged
the absence of any age-based escalation as a Gate G FAIL.

Behavior
--------
Every run (cron: */30 min on PC):
  1. Scan Wholesale/marcus_queue/*.json
  2. For each file:
     - Parse `queued_at` ISO timestamp
     - Skip if `marcus_acknowledged_at` is set (Marcus already touched it)
     - 0 <  age <= 24h: silent
     - 24h < age <= 48h: post severity='warning' to #ft-consult
     - age > 48h: post severity='critical' to #ft-consult AND #war-room
  3. Track sidecar `<deal_id>.alerted.json` so we don't re-spam every cycle.
     Re-alert only if the escalation tier crosses warning -> critical.

Idempotency
-----------
Each deal_id has at most ONE warning alert and at most ONE critical alert
across its lifetime. The sidecar records which tiers have already fired.
If a deal sits at warning for 48h then crosses into critical, the watchdog
fires the critical alert (one time) and updates the sidecar.

CLI
---
  --once    Single scan, intended for cron (default behavior).
  --status  Print queue age stats as JSON. No alerts fired.

Usage
-----
  PC crontab line (auto-installed via _ensure_pc_cron() helper):
    */30 * * * * cd /AA_MY_DRIVE && /AA_MY_DRIVE/.venv/bin/python3 \
      01_BUSINESSES/Everlight_Ventures/Wholesale/marcus_queue_watchdog.py \
      --once >> _logs/marcus_queue.log 2>&1

  Wholesale dispatcher integration:
    HANDLERS["marcus_queue_watchdog"] = handle_marcus_queue_watchdog
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("marcus_queue_watchdog")

# ── Paths ─────────────────────────────────────────────────────────
_QUEUE_CANDIDATES = [
    Path("/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/marcus_queue"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/marcus_queue"),
    Path("/home/opc/wholesale/marcus_queue"),
]


def _resolve_queue_dir() -> Path:
    for p in _QUEUE_CANDIDATES:
        if p.exists():
            return p
    # Default: phone path (creates if missing)
    fallback = _QUEUE_CANDIDATES[0]
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


_LOG_CANDIDATES = [
    Path("/AA_MY_DRIVE/_logs"),
    Path("/mnt/sdcard/AA_MY_DRIVE/_logs"),
    Path("/home/opc/_logs"),
]


def _resolve_log_dir() -> Path:
    for p in _LOG_CANDIDATES:
        if p.parent.exists():
            p.mkdir(parents=True, exist_ok=True)
            return p
    fallback = _LOG_CANDIDATES[0]
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# ── Path bootstrap for branded_slack import ────────────────────────
_CONTENT_TOOLS_PATHS = [
    "/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts",
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts",
    "/home/opc",
]
for _p in _CONTENT_TOOLS_PATHS:
    if _p not in sys.path and Path(_p).exists():
        sys.path.insert(0, _p)


# ── Thresholds ────────────────────────────────────────────────────
WARNING_AGE_HR = 24
CRITICAL_AGE_HR = 48

CHANNEL_PRIMARY = "#ft-consult"
CHANNEL_ESCALATION = "#war-room"


# ── Result types ──────────────────────────────────────────────────
@dataclass
class DealStatus:
    deal_id: str
    address: str
    state: str
    queued_at: str
    age_hr: float
    tier: str  # "ok" | "warning" | "critical"
    snippet: str
    acknowledged: bool
    alerted_warning: bool
    alerted_critical: bool


# ── Core scan ─────────────────────────────────────────────────────
def _load_sidecar(queue_dir: Path, deal_id: str) -> dict:
    sidecar = queue_dir / f"{deal_id}.alerted.json"
    if not sidecar.exists():
        return {}
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_sidecar(queue_dir: Path, deal_id: str, data: dict) -> None:
    sidecar = queue_dir / f"{deal_id}.alerted.json"
    try:
        sidecar.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    except Exception as exc:
        log.warning("sidecar write failed for %s: %s", deal_id, exc)


def _parse_queued_at(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    try:
        # Handle Z suffix and bare ISO formats
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _classify_age(age_hr: float) -> str:
    if age_hr >= CRITICAL_AGE_HR:
        return "critical"
    if age_hr >= WARNING_AGE_HR:
        return "warning"
    return "ok"


def _build_snippet(deal: dict) -> str:
    """Pull a useful preview from the deal record for the Slack alert body."""
    parts = []
    if deal.get("queued_reason"):
        parts.append(f"reason: {deal['queued_reason']}")
    if deal.get("owner_name"):
        parts.append(f"owner: {deal['owner_name']}")
    if deal.get("our_offer"):
        try:
            parts.append(f"offer: ${int(deal['our_offer']):,}")
        except Exception:
            pass
    return " | ".join(parts)[:300]


def _scan_queue(queue_dir: Path, now: Optional[datetime] = None) -> list[DealStatus]:
    if now is None:
        now = datetime.now(timezone.utc)

    rows: list[DealStatus] = []
    for path in sorted(queue_dir.glob("*.json")):
        # Skip sidecar files
        if path.name.endswith(".alerted.json"):
            continue
        try:
            deal = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("skip unparseable %s: %s", path.name, exc)
            continue

        deal_id = deal.get("deal_id") or path.stem
        queued_at = deal.get("queued_at", "")
        dt = _parse_queued_at(queued_at)
        if dt is None:
            log.warning("skip %s -- no parseable queued_at", deal_id)
            continue

        age_hr = (now - dt).total_seconds() / 3600.0
        acknowledged = bool(deal.get("marcus_acknowledged_at"))
        sidecar = _load_sidecar(queue_dir, deal_id)

        rows.append(DealStatus(
            deal_id=deal_id,
            address=str(deal.get("address", ""))[:120],
            state=str(deal.get("state", "")).upper(),
            queued_at=queued_at,
            age_hr=round(age_hr, 2),
            tier=_classify_age(age_hr),
            snippet=_build_snippet(deal),
            acknowledged=acknowledged,
            alerted_warning=bool(sidecar.get("alerted_warning")),
            alerted_critical=bool(sidecar.get("alerted_critical")),
        ))

    return rows


# ── Slack alerting ────────────────────────────────────────────────
def _post_alert(*, channel: str, severity: str, deal: DealStatus) -> bool:
    """Fire a branded Slack alert. Returns True on success."""
    title = f"Marcus queue {severity.upper()} -- {deal.deal_id}"
    detail_lines = [
        f"deal_id: {deal.deal_id}",
        f"address: {deal.address}",
        f"state: {deal.state}",
        f"queued_at: {deal.queued_at}",
        f"age: {deal.age_hr:.1f}h ({severity} threshold "
        f"{CRITICAL_AGE_HR if severity == 'critical' else WARNING_AGE_HR}h)",
    ]
    if deal.snippet:
        detail_lines.append(f"snippet: {deal.snippet}")
    detail = "\n".join(detail_lines)

    try:
        from content_tools.branded_slack import post_branded_alert  # type: ignore
    except ImportError:
        try:
            from branded_slack import post_branded_alert  # type: ignore
        except ImportError as exc:
            log.error("branded_slack unavailable: %s", exc)
            return False

    try:
        result = post_branded_alert(
            channel=channel,
            title=title,
            detail=detail,
            severity=severity,
            agent_name="Marcus Queue Watchdog",
        )
        ok = bool(getattr(result, "ok", False))
        if not ok:
            log.warning("alert failed (%s -> %s): %s",
                        deal.deal_id, channel, getattr(result, "error", ""))
        return ok
    except Exception as exc:
        log.error("alert exception (%s -> %s): %s", deal.deal_id, channel, exc)
        return False


def _emit_alerts(queue_dir: Path, deal: DealStatus) -> dict:
    """Fire warning or critical alerts for one deal as appropriate.

    Returns a result dict for the run summary. Idempotent: writes the
    sidecar so the same tier never alerts twice.
    """
    actions: list[str] = []
    sidecar = _load_sidecar(queue_dir, deal.deal_id)

    # Warning tier (24h-48h): fire once if not already.
    if deal.tier == "warning" and not deal.alerted_warning:
        if _post_alert(channel=CHANNEL_PRIMARY, severity="warning", deal=deal):
            actions.append(f"warning -> {CHANNEL_PRIMARY}")
            sidecar["alerted_warning"] = True
            sidecar["warning_at"] = datetime.now(timezone.utc).isoformat()

    # Critical tier (>=48h): fire once each into both channels.
    if deal.tier == "critical" and not deal.alerted_critical:
        if _post_alert(channel=CHANNEL_PRIMARY, severity="critical", deal=deal):
            actions.append(f"critical -> {CHANNEL_PRIMARY}")
        if _post_alert(channel=CHANNEL_ESCALATION, severity="critical", deal=deal):
            actions.append(f"critical -> {CHANNEL_ESCALATION}")
        if actions:
            sidecar["alerted_critical"] = True
            sidecar["critical_at"] = datetime.now(timezone.utc).isoformat()
            # If we hadn't fired warning yet, we still mark it -- skipping warning
            # is fine; the critical alert supersedes it.
            sidecar.setdefault("alerted_warning", True)

    if actions:
        _save_sidecar(queue_dir, deal.deal_id, sidecar)

    return {
        "deal_id": deal.deal_id,
        "tier": deal.tier,
        "age_hr": deal.age_hr,
        "actions": actions,
    }


# ── Public entry points ───────────────────────────────────────────
def scan_once(queue_dir: Optional[Path] = None) -> dict:
    """Single watchdog pass. Returns a summary dict.

    Wholesale dispatcher integration calls this directly.
    """
    qdir = queue_dir or _resolve_queue_dir()
    rows = _scan_queue(qdir)
    summary = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "queue_dir": str(qdir),
        "total_queued": len(rows),
        "ok": 0,
        "warning": 0,
        "critical": 0,
        "acknowledged_skipped": 0,
        "alerts_fired": [],
    }

    for deal in rows:
        if deal.acknowledged:
            summary["acknowledged_skipped"] += 1
            continue
        summary[deal.tier] += 1
        result = _emit_alerts(qdir, deal)
        if result["actions"]:
            summary["alerts_fired"].append(result)

    # Persist a run record for visibility.
    log_path = _resolve_log_dir() / "marcus_queue_watchdog.jsonl"
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(summary, default=str) + "\n")
    except Exception:
        pass

    return summary


def status_report(queue_dir: Optional[Path] = None) -> dict:
    """Read-only stats. No alerts fired."""
    qdir = queue_dir or _resolve_queue_dir()
    rows = _scan_queue(qdir)
    return {
        "queue_dir": str(qdir),
        "total_queued": len(rows),
        "by_tier": {
            "ok":       sum(1 for r in rows if r.tier == "ok" and not r.acknowledged),
            "warning":  sum(1 for r in rows if r.tier == "warning" and not r.acknowledged),
            "critical": sum(1 for r in rows if r.tier == "critical" and not r.acknowledged),
            "acknowledged": sum(1 for r in rows if r.acknowledged),
        },
        "deals": [
            {
                "deal_id": r.deal_id,
                "address": r.address,
                "state": r.state,
                "age_hr": r.age_hr,
                "tier": r.tier,
                "acknowledged": r.acknowledged,
            }
            for r in rows
        ],
    }


# ── CLI ───────────────────────────────────────────────────────────
def _cli(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Marcus queue watchdog")
    ap.add_argument("--once", action="store_true", default=True,
                    help="Single scan + alert (default)")
    ap.add_argument("--status", action="store_true",
                    help="Print queue stats, do not fire alerts")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] marcus_queue_watchdog: %(message)s",
    )

    if args.status:
        out = status_report()
        print(json.dumps(out, indent=2, default=str))
        return 0

    summary = scan_once()
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
