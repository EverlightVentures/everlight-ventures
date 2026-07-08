from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from . import store, threat
from .hub import HUB

# Server-side change detector that feeds the WebSocket push layer.
#
# The ingest loop runs in its own OS process (scripts/run.sh) and writes the
# per-day SQLite store. This task runs INSIDE the API process, reads that same
# day-DB on a short tick, classifies every event against the phone's last-known
# GPS (identical to /api/events), diffs the result against an in-memory
# fingerprint, and publishes only the new/changed events to HUB. Connected /ws
# clients then receive those deltas immediately.
#
# Why a decoupled tick instead of an in-ingest callback: it keeps ingest (and
# the flaky C-extension GTFS-RT path it can reach) fully isolated in its own
# process, so nothing here can add a crash surface to the web server. Every DB
# read is offloaded to a worker thread so the event loop stays responsive for
# HTTP and WebSocket traffic. The whole body is exception-guarded; a bad tick
# logs and retries, it never kills the loop or the API.

TICK = float(os.environ.get("SLD_WS_TICK", "2.0"))
# Force a full resnapshot every N ticks even with no diff, as a self-heal so a
# client that missed a delta reconverges within a minute.
RESNAPSHOT_EVERY = int(os.environ.get("SLD_WS_RESNAPSHOT_TICKS", "30"))


def read_user(base: str) -> tuple[float, float] | None:
    """The phone's last posted GPS, or None if it has not posted yet."""
    p = Path(base) / "last_location.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
        return (float(d["lat"]), float(d["lon"]))
    except Exception:  # noqa: BLE001
        return None


def snapshot(base: str, day: str, user: tuple[float, float] | None) -> list[dict]:
    """The full classified event list for a day (same shape as /api/events)."""
    if not store.day_db_path(base, day).exists():
        return []
    conn = store.connect(base, day)
    try:
        rows = store.get_events(conn)
    finally:
        conn.close()
    return [threat.classify(r, user) for r in rows]


def _fingerprint(ev: dict) -> tuple:
    """What counts as a material change worth pushing: a new id, a severity or
    threat-level shift, a moved/updated fix, fresh dispatch text, or new audio."""
    return (
        ev.get("last_seen"), ev.get("severity"), ev.get("threat_level"),
        ev.get("lat"), ev.get("lon"), ev.get("audio_url"),
    )


async def broadcast_loop(base: str, interval: float = TICK) -> None:
    """Started once at API startup. Never returns; self-guards every tick."""
    seen: dict[str, tuple] = {}
    last_day = store.today_pt()
    last_user: tuple[float, float] | None = None
    ticks = 0
    while True:
        try:
            day = store.today_pt()
            user = read_user(base)
            # Read + classify off the event loop so a slow disk never stalls
            # HTTP or the WebSocket writers.
            scored = await asyncio.to_thread(snapshot, base, day, user)
            by_id = {e["id"]: e for e in scored}

            day_rolled = day != last_day
            user_moved = user != last_user
            force = day_rolled or user_moved or (ticks % RESNAPSHOT_EVERY == 0)

            if force:
                seen = {eid: _fingerprint(e) for eid, e in by_id.items()}
                if HUB.count:
                    HUB.publish({
                        "t": "snapshot", "date": day,
                        "user": list(user) if user else None,
                        "events": scored,
                    })
            else:
                changed = []
                for eid, e in by_id.items():
                    fp = _fingerprint(e)
                    if seen.get(eid) != fp:
                        seen[eid] = fp
                        changed.append(e)
                if changed and HUB.count:
                    HUB.publish({"t": "delta", "date": day, "events": changed})

            last_day, last_user = day, user
            ticks += 1
        except Exception as e:  # noqa: BLE001 - keep the loop alive, always
            print(f"[broadcast] tick error: {e}", flush=True)
        await asyncio.sleep(interval)
