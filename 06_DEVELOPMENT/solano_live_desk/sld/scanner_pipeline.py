from __future__ import annotations

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

# Street address or intersection mentioned in a dispatch line.
_LOC = re.compile(
    r"\b(\d{1,5}\s+[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+){0,2}\s+"
    r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|Court|"
    r"Pkwy|Parkway|Hwy|Highway|Pl|Place|Cir|Circle)"
    r"|[A-Z][A-Za-z]+\s+(?:and|&|at)\s+[A-Z][A-Za-z]+)\b"
)


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


def latest_completed_block(session, feed_id: str, date: str) -> dict | None:
    # The archive API can list blocks newest-first, so pick by endTs explicitly
    # instead of trusting order (else we re-transcribe the 12am block forever).
    now = time.time()
    done = [b for b in bc.list_blocks(session, feed_id, date) if b.get("endTs", 0) < now]
    return max(done, key=lambda b: b.get("endTs", 0)) if done else None


def run(base: str, feed_ids=None, model: str = "base.en", now_iso: str | None = None,
        max_geocode: int = 8) -> int:
    """Transcribe the latest completed archive block per feed, geocode notable
    located calls, and store them as mapped, replayable scanner incidents.
    """
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    date = store.today_pt().replace("_", "-")
    session = bc.client()
    total = 0
    for fid in (feed_ids or list(FEEDS)):
        blk = latest_completed_block(session, fid, date)
        if not blk:
            continue
        bid = blk["id"]
        adir = os.path.join(base, "audio")
        os.makedirs(adir, exist_ok=True)
        path = os.path.join(adir, f"{bid}.mp3")
        if not os.path.exists(path):
            bc.download_block(session, bid, path)
        segs = tr.transcribe_file(path, size=model)
        start_ts = blk.get("startTs", 0)
        events, geocoded = [], 0

        def stamp(offset):
            return datetime.fromtimestamp(start_ts + offset, store.PT).strftime("%-I:%M:%S %p")

        # Timestamped, code-named, event-coded transcript lines.
        for s in segs:
            s["line"] = radio.annotate_line(stamp(s["start"]), s["text"], base)

        # Always store the whole block as a readable + replayable scanner log,
        # pinned to the feed's coverage area, severity = the loudest thing heard.
        if segs:
            sevs = [threat.severity(s["text"]) for s in segs]
            block_sev = max(sevs, key=lambda x: _RANK[x])
            clat, clon = FEED_CENTROIDS.get(fid, (38.25, -122.0))
            events.append(
                {
                    "id": f"scanner:{bid}:log",
                    "source": "scanner",
                    "type": f"Scanner log: {FEEDS.get(fid, fid)}",
                    "title": f"{FEEDS.get(fid, fid)} {blk.get('start', '')}-{blk.get('end', '')}",
                    "lat": clat,
                    "lon": clon,
                    "geo_label": FEEDS.get(fid, fid),
                    "log_time": datetime.fromtimestamp(start_ts, store.PT).isoformat(),
                    "body": "\n".join(s["line"] for s in segs)[:6000],
                    "details": [],
                    "severity": block_sev,
                    "audio_url": f"/api/scanner_audio/{bid}",
                    "archive_block": bid,
                }
            )
        for i, seg in enumerate(segs):
            loc = _LOC.search(seg["text"])
            sev = threat.severity(seg["text"])
            if not loc:  # can only map a call we can place
                continue
            if sev == "LOW" and geocoded >= max_geocode:
                continue
            if geocoded >= max_geocode:
                break
            lat, lon = _geocode(loc.group(0))
            geocoded += 1
            time.sleep(1.1)  # Nominatim 1 req/s
            if lat is None:
                continue
            ev_time = datetime.fromtimestamp(start_ts + seg["start"], store.PT).isoformat()
            # Correlate: which units/operators are on this call (spoken within 90s).
            responders: set = set()
            for s2 in segs:
                if 0 <= (s2["start"] - seg["start"]) <= 90:
                    responders.update(radio.line_ids(s2["text"], base))
            body = seg["line"]
            if responders:
                body += "\n\nUnits on this call: " + ", ".join(sorted(responders))
            events.append(
                {
                    "id": f"scanner:{bid}:{i}",
                    "source": "scanner",
                    "type": f"Scanner call ({loc.group(0)[:22]})",
                    "title": seg["text"][:70],
                    "lat": lat,
                    "lon": lon,
                    "geo_label": loc.group(0),
                    "log_time": ev_time,
                    "body": body,
                    "details": [],
                    "severity": sev,
                    "audio_url": f"/api/scanner_audio/{bid}",
                    "archive_block": bid,
                }
            )
        conn = store.connect(base, store.today_pt())
        try:
            for ev in events:
                store.upsert_event(conn, ev, now_iso)
        finally:
            conn.close()
        total += len(events)
    return total
