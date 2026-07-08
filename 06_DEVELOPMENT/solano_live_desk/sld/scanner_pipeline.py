from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime

from . import broadcastify as bc
from . import radio, store, threat
from . import transcribe as tr

# Solano scanner feeds to transcribe (feed_id -> label + coverage centroid).
FEEDS = {
    "45149": "Solano PD/Fire/CHP",
    "20773": "Solano Sheriff / Rio Vista / Dixon",
}
FEED_CENTROIDS = {
    "45149": (38.2494, -122.0400),   # Fairfield / Vacaville / Suisun
    "20773": (38.20, -121.85),        # Sheriff countywide / Rio Vista / Dixon
}
_RANK = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}

# Street address, highway, "block of", or intersection mentioned in a dispatch line.
_LOC = re.compile(
    r"\b(?:"
    r"\d{1,5}\s+[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+){0,2}\s+"
    r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|Court|"
    r"Pkwy|Parkway|Hwy|Highway|Pl|Place|Cir|Circle|Ter|Terrace|Trail|Trl)"
    r"|(?:I-?80|I-?680|I-?505|SR-?\d{1,3}|Highway\s?\d{1,3}|Hwy\s?\d{1,3})"
    r"|\d{1,4}\s+[Bb]lock\s+of\s+[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+){0,2}"
    r"|[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?\s+(?:and|&|at)\s+[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?"
    r")\b"
)


def _load_geocache(base: str) -> dict:
    p = os.path.join(base, "geocode_cache.json")
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _save_geocache(base: str, gc: dict) -> None:
    try:
        json.dump(gc, open(os.path.join(base, "geocode_cache.json"), "w"))
    except Exception:  # noqa: BLE001
        pass


def _geocode(text: str) -> tuple[float | None, float | None]:
    import httpx

    try:
        r = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{text}, Solano County, California", "format": "json", "limit": 1},
            headers={"User-Agent": "solano-live-desk/0.1 (personal safety)"},
            timeout=12,
        )
        d = r.json()
        if d:
            return (float(d[0]["lat"]), float(d[0]["lon"]))
    except Exception:  # noqa: BLE001
        pass
    return (None, None)


def latest_blocks(session, feed_id: str, date: str, n: int = 2) -> list[dict]:
    """The most recent N completed blocks (chronological), chosen by endTs -- the
    archive can list newest-first, so never trust order."""
    now = time.time()
    done = sorted(
        (b for b in bc.list_blocks(session, feed_id, date) if b.get("endTs", 0) < now),
        key=lambda b: b.get("endTs", 0),
    )
    return done[-n:] if done else []


def latest_completed_block(session, feed_id: str, date: str) -> dict | None:
    blks = latest_blocks(session, feed_id, date, 1)
    return blks[-1] if blks else None


def _process_block(session, base, fid, blk, model, now_iso, gc, budget) -> int:
    """Transcribe one block; store its log + geocoded calls. `gc` is the shared
    geocode cache (recurring locations are instant + free); `budget` is a shared
    [remaining_new_geocodes] list so NEW lookups are capped across the whole run."""
    bid = blk["id"]
    adir = os.path.join(base, "audio")
    os.makedirs(adir, exist_ok=True)
    path = os.path.join(adir, f"{bid}.mp3")
    if not os.path.exists(path):
        bc.download_block(session, bid, path)
    segs = tr.transcribe_file(path, size=model)
    if not segs:
        return 0
    start_ts = blk.get("startTs", 0)

    def stamp(offset):
        return datetime.fromtimestamp(start_ts + offset, store.PT).strftime("%-I:%M:%S %p")

    for s in segs:
        s["line"] = radio.annotate_line(stamp(s["start"]), s["text"], base)

    events = []
    block_sev = max((threat.severity(s["text"]) for s in segs), key=lambda x: _RANK[x])
    clat, clon = FEED_CENTROIDS.get(fid, (38.25, -122.0))
    events.append({
        "id": f"scanner:{bid}:log", "source": "scanner",
        "type": f"Scanner log: {FEEDS.get(fid, fid)}",
        "title": f"{FEEDS.get(fid, fid)} {blk.get('start', '')}-{blk.get('end', '')}",
        "lat": clat, "lon": clon, "geo_label": FEEDS.get(fid, fid),
        "log_time": datetime.fromtimestamp(start_ts, store.PT).isoformat(),
        "body": "\n".join(s["line"] for s in segs)[:6000], "details": [],
        "severity": block_sev, "audio_url": f"/api/scanner_audio/{bid}", "archive_block": bid,
    })

    for i, seg in enumerate(segs):
        loc = _LOC.search(seg["text"])
        if not loc:
            continue
        place = loc.group(0)
        key = place.strip().lower()
        if key in gc:                          # cached -> instant, free, uncapped
            v = gc[key]
            lat, lon = (v[0], v[1]) if v else (None, None)
        else:
            if budget[0] <= 0:
                continue                       # out of NEW-geocode budget this run
            lat, lon = _geocode(place)
            budget[0] -= 1
            gc[key] = [lat, lon] if lat is not None else None
            time.sleep(1.1)                    # Nominatim 1 req/s -- new locations only
        if lat is None:
            continue
        ev_time = datetime.fromtimestamp(start_ts + seg["start"], store.PT).isoformat()
        # The whole exchange around this call (~30s before to ~2.5min after), so
        # the transcript reads as a real conversation AND the service classifies
        # from the call type + the units' talk, not just the dispatch address line.
        window = [s2 for s2 in segs if -30 <= (s2["start"] - seg["start"]) <= 150]
        body = "\n".join(s2["line"] for s2 in window)
        responders: set = set()
        for s2 in window:
            responders.update(radio.line_ids(s2["text"], base))
        if responders:
            body += "\n\nUnits on this call: " + ", ".join(sorted(responders))
        sev = max((threat.severity(s2["text"]) for s2 in window), key=lambda x: _RANK[x])
        events.append({
            "id": f"scanner:{bid}:{i}", "source": "scanner",
            "type": f"Scanner call ({place[:22]})", "title": seg["text"][:70],
            "lat": lat, "lon": lon, "geo_label": place, "log_time": ev_time,
            "body": body, "details": [], "severity": sev,
            "audio_url": f"/api/scanner_audio/{bid}", "archive_block": bid,
        })

    conn = store.connect(base, store.today_pt())
    try:
        for ev in events:
            store.upsert_event(conn, ev, now_iso)
    finally:
        conn.close()
    return len(events)


def run(base: str, feed_ids=None, model: str = "base.en", now_iso: str | None = None,
        max_geocode: int = 24, blocks: int = 1) -> int:
    """Transcribe the latest `blocks` completed blocks per feed, geocode located
    calls (cached across runs so tabs fill faster), store as mapped incidents."""
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    date = store.today_pt().replace("_", "-")
    session = bc.client()
    gc = _load_geocache(base)
    budget = [max_geocode]  # NEW geocodes across the whole run; cached hits are free
    total = 0
    for fid in (feed_ids or list(FEEDS)):
        for blk in latest_blocks(session, fid, date, blocks):
            try:
                total += _process_block(session, base, fid, blk, model, now_iso, gc, budget)
            except Exception as e:  # noqa: BLE001 - one bad block never kills the run
                print(f"scanner block {blk.get('id')} failed: {e}", flush=True)
    _save_geocache(base, gc)
    return total
