from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import alerts, dvr, notify, store, threat

# Threat levels that trigger an active push/email (vs. dashboard-only logging).
ALERT_LEVELS = {"EXTREME", "HIGH"}


def process(
    events: list[dict],
    user_latlon: tuple[float, float] | None,
    seen: set,
    dvr_conn,
    senders: dict,
    now_iso: str | None = None,
) -> list[dict]:
    """Classify events vs the user, record every one to the DVR, and dispatch
    alerts for NEW incidents at ALERT_LEVELS. `seen` (mutated) prevents re-alerting.
    Returns the list of dispatched incidents with their delivery receipts.
    """
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    fired: list[dict] = []
    for ev in (threat.classify(e, user_latlon) for e in events):
        dvr.record(dvr_conn, ev, now_iso)
        if ev["threat_level"] in ALERT_LEVELS and ev["id"] not in seen:
            seen.add(ev["id"])
            fired.append(
                {
                    "id": ev["id"],
                    "threat_level": ev["threat_level"],
                    "type": ev.get("type"),
                    "receipts": alerts.dispatch(ev, senders),
                }
            )
    return fired


def _default_senders() -> dict:
    return {
        "push": notify.ntfy_sender,
        "email": notify.email_sender,
        "dashboard": lambda e, p: True,   # already in the store; nothing to send
        "digest": lambda e, p: True,      # queued for the periodic digest
    }


def read_user_location(base: str) -> tuple[float, float] | None:
    p = Path(base) / "last_location.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
        return (float(d["lat"]), float(d["lon"]))
    except Exception:  # noqa: BLE001
        return None


_SEEN: set = set()


def run_alerts(base: str, senders: dict | None = None) -> list[dict]:
    """Poll-loop entry point: score today's stored events vs the phone's last-known
    GPS, record to the DVR, and fire alerts for new EXTREME/HIGH incidents.
    """
    senders = senders or _default_senders()
    user = read_user_location(base)
    conn = store.connect(base, store.today_pt())
    try:
        events = store.get_events(conn)
    finally:
        conn.close()
    dvr_conn = dvr.connect(base)
    try:
        return process(events, user, _SEEN, dvr_conn, senders)
    finally:
        dvr_conn.close()
