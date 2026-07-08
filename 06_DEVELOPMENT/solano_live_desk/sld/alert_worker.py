from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from . import alerts, dvr, notify, store, threat

# Threat levels that trigger an active push/email (vs. dashboard-only logging).
ALERT_LEVELS = {"EXTREME", "HIGH"}
# Proximity-first rule: ANYTHING this close pings you, whatever its level -- the
# whole point of a life-safety app is what is happening in your zone right now.
NEAR_MI = 1.5
_NEAR_NOISE = re.compile(r"construction|roadwork|road work|closure|maintenance", re.I)


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
        dist = ev.get("distance_mi")
        text = f"{ev.get('type', '')} {ev.get('body', '')}"
        is_blocklog = (ev.get("type") or "").startswith("Scanner log")
        near = dist is not None and dist <= NEAR_MI and not is_blocklog and not _NEAR_NOISE.search(text)
        if (ev["threat_level"] in ALERT_LEVELS or near) and ev["id"] not in seen:
            seen.add(ev["id"])
            # Proximity forces a push: route a near-but-lower incident as HIGH/EXTREME
            # so it reaches the phone, even if its raw threat level is only MEDIUM.
            route_as = None
            if near:
                route_as = "EXTREME" if (dist is not None and dist <= 0.5) else "HIGH"
            fired.append(
                {
                    "id": ev["id"],
                    "threat_level": ev["threat_level"],
                    "type": ev.get("type"),
                    "distance_mi": dist,
                    "near": near,
                    "receipts": alerts.dispatch(ev, senders, route_as=route_as),
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
