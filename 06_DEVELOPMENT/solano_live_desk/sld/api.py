from __future__ import annotations

import json
import os
import time
from pathlib import Path

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from . import aircraft as air_mod
from . import broadcaster
from . import cameras as cams_mod
from . import camera_dvr
from . import beacon, config, correlate, decide as decide_mod, dvr, escape as escape_mod, evac, fema, news, notify, routing, spacewx, store, threat, trains as train_mod, transit as transit_mod, wayfinding, webcams
from .hub import HUB
from .feeds import feeds_for_county
from .geo_county import county_for

config.load_env()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# Alarm-queue ordering: most dangerous, then closest, first.
_LEVEL_RANK = {"EXTREME": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "LOG": 0}

app = FastAPI(title="Solano Live Desk")

# --- Private-domain gate ---------------------------------------------------
# The public Cloudflare tunnel (survival.everlightventures.io) is locked to the
# operator with a one-time magic link that sets a long-lived cookie. Any other
# Host (tailnet IP, localhost) is unaffected and stays frictionless.
_ACCESS_TOKEN = os.environ.get("SLD_ACCESS_TOKEN", "")
_PUBLIC_HOST = os.environ.get("SLD_PUBLIC_HOST", "survival.everlightventures.io")


@app.middleware("http")
async def _private_gate(request, call_next):
    host = (request.headers.get("host") or "").split(":")[0]
    if _ACCESS_TOKEN and host == _PUBLIC_HOST:
        path = request.url.path
        if not (path == "/healthz" or path.startswith("/unlock/")):
            # The background GPS poster authenticates with the token as a query
            # param (no browser, no cookie) so location stays fresh app-closed.
            if path == "/api/location" and request.query_params.get("token") == _ACCESS_TOKEN:
                return await call_next(request)
            if request.cookies.get("sld_auth") != _ACCESS_TOKEN:
                return Response("Private dashboard. Open your unlock link.", status_code=403)
    return await call_next(request)


@app.middleware("http")
async def _no_cache_html(request, call_next):
    # HTML must never be stale -- it references hashed JS/CSS. Always revalidate
    # the shell so a rebuild reaches the browser on the next load. Hashed assets
    # keep their own long cache.
    resp = await call_next(request)
    if "text/html" in resp.headers.get("content-type", ""):
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
    return resp


@app.get("/unlock/{token}")
def unlock(token: str):
    if _ACCESS_TOKEN and token == _ACCESS_TOKEN:
        r = RedirectResponse("/console/")
        r.set_cookie("sld_auth", _ACCESS_TOKEN, max_age=31_536_000, httponly=True, samesite="lax", secure=True)
        return r
    return Response("invalid unlock link", status_code=403)


def _store_dir() -> str:
    return os.environ.get("SLD_STORE", "store")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/days")
def days():
    return {"days": store.list_days(_store_dir())}


@app.get("/api/events")
def events(date: str | None = None, lat: float | None = None, lon: float | None = None):
    """Events for a day, threat-scored against the caller's live GPS if given."""
    base = _store_dir()
    day = date or store.today_pt()
    if not store.day_db_path(base, day).exists():
        return {"date": day, "events": []}
    conn = store.connect(base, day)
    try:
        rows = store.get_events(conn)
    finally:
        conn.close()
    rows = [r for r in rows if store.on_day(r.get("last_seen"), day)]  # daily reset: this day's live events only
    user = (lat, lon) if lat is not None and lon is not None else None
    scored = [threat.classify(r, user) for r in rows]
    for e in scored:  # lifecycle: derived narrative state (ACTIVE..CLEARED/CLOSED)
        e["status"] = correlate.lifecycle_status(e.get("last_seen"))
        e["lifecycle"] = correlate.lifecycle(e)
    scored.sort(
        key=lambda e: (
            _LEVEL_RANK.get(e["threat_level"], 0),
            -(e["distance_mi"] if e["distance_mi"] is not None else 9999),
        ),
        reverse=True,
    )
    return {"date": day, "user": user, "events": scored}


@app.get("/api/correlated")
def correlated(date: str | None = None, lat: float | None = None, lon: float | None = None):
    """Fused, confidence-scored incidents (the PSIM brain) for a day, GPS-scored."""
    base = _store_dir()
    day = date or store.today_pt()
    if not store.day_db_path(base, day).exists():
        return {"date": day, "incidents": []}
    conn = store.connect(base, day)
    try:
        rows = store.get_events(conn)
    finally:
        conn.close()
    rows = [r for r in rows if store.on_day(r.get("last_seen"), day)]  # daily reset: this day's live events only
    user = (lat, lon) if lat is not None and lon is not None else None
    fused = [threat.classify(i, user) for i in correlate.correlate(rows)]
    for e in fused:
        e["lifecycle"] = correlate.lifecycle(e)
    fused.sort(key=lambda e: (_LEVEL_RANK.get(e["threat_level"], 0), e.get("confidence", 0)), reverse=True)
    return {"date": day, "incidents": fused}


@app.get("/api/stats")
def stats(date: str | None = None):
    """Trader-style analytics for a day: busy hours, type mix, severity, hotspots."""
    from collections import Counter
    from datetime import datetime as _dt

    base = _store_dir()
    day = date or store.today_pt()
    empty = {"date": day, "total": 0, "by_hour": [0] * 24, "by_type": [],
             "by_severity": {}, "by_area": [], "by_source": {}, "avg_active_min": 0}
    if not store.day_db_path(base, day).exists():
        return empty
    conn = store.connect(base, day)
    try:
        rows = store.get_events(conn)
    finally:
        conn.close()
    if not rows:
        return empty
    by_hour = [0] * 24
    by_type, by_sev, by_area, by_src = Counter(), Counter(), Counter(), Counter()
    durations = []
    for r in rows:
        try:
            by_hour[_dt.fromisoformat(r.get("last_seen") or r.get("first_seen")).hour] += 1
        except Exception:  # noqa: BLE001
            pass
        by_type[(r.get("type") or "Other")[:26]] += 1
        by_sev[r.get("severity") or "LOW"] += 1
        by_area[(r.get("geo_label") or r.get("source") or "?")[:26]] += 1
        by_src[r.get("source") or "?"] += 1
        try:
            fs = _dt.fromisoformat(r.get("first_seen"))
            le = _dt.fromisoformat(r.get("last_seen"))
            durations.append((le - fs).total_seconds() / 60)
        except Exception:  # noqa: BLE001
            pass
    return {
        "date": day, "total": len(rows),
        "by_hour": by_hour,
        "by_type": by_type.most_common(8),
        "by_severity": dict(by_sev),
        "by_area": by_area.most_common(8),
        "by_source": dict(by_src),
        "avg_active_min": round(sum(durations) / len(durations), 1) if durations else 0,
    }


@app.get("/api/county")
def county(lat: float, lon: float):
    """Resolve the caller's GPS to a US county (the follow-me re-key trigger)."""
    try:
        return county_for(lat, lon)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e), "fips": None, "county": None, "state": None}


@app.post("/api/location")
def set_location(lat: float, lon: float):
    """Phone posts its live GPS so server-side alerting scores against it."""
    p = Path(_store_dir())
    p.mkdir(parents=True, exist_ok=True)
    (p / "last_location.json").write_text(json.dumps({"lat": lat, "lon": lon}))
    return {"ok": True, "lat": lat, "lon": lon}


@app.get("/api/incidents")
def incidents(limit: int = 200):
    """The DVR / case log: cross-day recorded incidents, newest first."""
    conn = dvr.connect(_store_dir())
    try:
        return {"incidents": dvr.recent(conn, limit)}
    finally:
        conn.close()


# Caltrans camera list is large and slow; cache it in-process for 5 minutes.
_CAM_CACHE: dict = {"at": 0.0, "cams": []}


def _all_cameras() -> list[dict]:
    if time.time() - _CAM_CACHE["at"] > 300 or not _CAM_CACHE["cams"]:
        try:
            _CAM_CACHE["cams"] = cams_mod.fetch_cameras()
            _CAM_CACHE["at"] = time.time()
        except Exception:  # noqa: BLE001 - serve stale on transient failure
            pass
    return _CAM_CACHE["cams"]


@app.on_event("startup")
def _warm_caches():
    # Pre-fetch the 735-camera list in a thread so the first incident click is
    # instant instead of blocking on a cold Caltrans fetch.
    import threading

    threading.Thread(target=_all_cameras, daemon=True).start()


@app.on_event("startup")
async def _start_broadcaster():
    # The WebSocket push loop: diffs the store every 2s, pushes deltas to /ws.
    asyncio.create_task(broadcaster.broadcast_loop(_store_dir()))
    # The EPIRB pulse: re-broadcasts active distress beacons on their interval.
    asyncio.create_task(_beacon_repeater(_store_dir()))


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    """Live push: an immediate snapshot, then incident deltas as they happen."""
    await websocket.accept()
    q = HUB.subscribe()
    try:
        day = store.today_pt()
        user = broadcaster.read_user(_store_dir())
        snap = await asyncio.to_thread(broadcaster.snapshot, _store_dir(), day, user)
        await websocket.send_json({"t": "snapshot", "date": day,
                                   "user": list(user) if user else None, "events": snap})
        while True:
            await websocket.send_json(await q.get())
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        HUB.unsubscribe(q)


@app.get("/api/cameras")
def cameras(lat: float, lon: float, n: int = 3):
    """The n public traffic cameras nearest a point (visual support for an incident)."""
    return {"cameras": cams_mod.nearest(_all_cameras(), lat, lon, n)}


@app.get("/api/where")
def where(lat: float, lon: float):
    """Human wayfinding for a point: nearest landmark + cross street + city."""
    return wayfinding.where(lat, lon)


@app.get("/api/feeds")
def feeds(lat: float, lon: float):
    """Live-listen scanner feeds for the county containing a point."""
    try:
        fips = county_for(lat, lon).get("fips")
    except Exception:  # noqa: BLE001
        fips = None
    return {"fips": fips, "feeds": feeds_for_county(fips)}


_AIR_CACHE: dict = {}   # keyed by rounded (lat,lon,dist) -> (ts, data)
_TRAIN_CACHE: dict = {"at": 0.0, "trains": []}
_FLIGHT_CACHE: dict = {}   # callsign -> route (routes are static; cache forever)
# ICAO airline prefix -> name, so we can name the carrier even with no route.
_ICAO_AIRLINE = {
    "UAL": "United", "SWA": "Southwest", "AAL": "American", "DAL": "Delta",
    "JBU": "JetBlue", "ASA": "Alaska", "NKS": "Spirit", "FFT": "Frontier",
    "SKW": "SkyWest", "FDX": "FedEx", "UPS": "UPS", "AAY": "Allegiant",
    "HAL": "Hawaiian", "ACA": "Air Canada", "VOI": "Volaris", "AMX": "Aeromexico",
    "QXE": "Horizon", "GJS": "GoJet", "EDV": "Endeavor", "RPA": "Republic",
    "ENY": "Envoy", "JIA": "PSA", "AWI": "Air Wisconsin", "CPZ": "Compass",
}
# Aircraft type -> typical passenger seats (occupancy is NOT broadcast; this is
# the type's usual capacity, the closest honest number available).
_TYPE_SEATS = {
    "B738": 176, "B739": 189, "B737": 143, "B38M": 178, "B39M": 189,
    "A320": 180, "A321": 200, "A319": 140, "A20N": 180, "A21N": 200, "A319neo": 140,
    "B752": 200, "B763": 245, "B764": 245, "B77W": 396, "B772": 314, "B788": 242,
    "B789": 290, "B744": 416, "A332": 268, "A333": 295, "A359": 325, "A388": 555,
    "E75L": 76, "E170": 76, "E145": 50, "CRJ2": 50, "CRJ7": 70, "CRJ9": 90,
    "DH8D": 78, "AT76": 70, "C208": 9, "PC12": 9,
}


# US industry average passenger load factor (BTS ~83%); estimate occupancy from
# the type's seats since actual counts are never broadcast.
_LOAD_FACTOR = 0.83


def _pax(seats):
    return round(seats * _LOAD_FACTOR) if seats else None


@app.get("/api/flight")
def flight(callsign: str, type: str = ""):
    """Enrich a live flight: origin->destination + airline (adsbdb, or airline
    from the callsign prefix) + typical seat capacity + estimated occupancy."""
    cs = callsign.strip().upper()
    seats = _TYPE_SEATS.get(type.strip().upper()) if type else None
    if not cs:
        return {"callsign": cs, "origin": None, "dest": None, "seats": seats, "est_pax": _pax(seats)}
    if cs in _FLIGHT_CACHE:
        return {**_FLIGHT_CACHE[cs], "seats": seats, "est_pax": _pax(seats)}
    airline = _ICAO_AIRLINE.get(cs[:3])
    out = {"callsign": cs, "origin": None, "dest": None, "airline": airline}
    try:
        import httpx

        r = httpx.get(f"https://api.adsbdb.com/v0/callsign/{cs}", timeout=10,
                      headers={"User-Agent": "solano-live-desk/0.1"})
        if r.status_code == 200:
            fr = (r.json().get("response") or {}).get("flightroute") or {}
            o, d = fr.get("origin") or {}, fr.get("destination") or {}
            if o or d:
                out = {
                    "callsign": cs,
                    "origin": {"code": o.get("iata_code") or o.get("icao_code"), "city": o.get("municipality"), "name": o.get("name")},
                    "dest": {"code": d.get("iata_code") or d.get("icao_code"), "city": d.get("municipality"), "name": d.get("name")},
                    "airline": (fr.get("airline") or {}).get("name") or airline,
                }
    except Exception:  # noqa: BLE001
        pass
    _FLIGHT_CACHE[cs] = out
    return {**out, "seats": seats, "est_pax": _pax(seats)}


@app.get("/api/aircraft")
def aircraft(lat: float, lon: float, dist: int = 100):
    """Live aircraft (commercial + military) within dist nm of a point."""
    key = (round(lat, 1), round(lon, 1), dist)
    hit = _AIR_CACHE.get(key)
    if hit and time.time() - hit[0] < 8:   # short cache; adsb.lol throttles (420)
        return {"aircraft": hit[1]}
    try:
        acs = air_mod.fetch(lat, lon, dist)
        _AIR_CACHE[key] = (time.time(), acs)
        return {"aircraft": acs}
    except Exception as e:  # noqa: BLE001
        return {"aircraft": hit[1] if hit else [], "error": str(e)}


@app.get("/api/trains")
def trains(lat: float, lon: float, radius: float = 60):
    """Live Amtrak trains within radius miles of a point."""
    if time.time() - _TRAIN_CACHE["at"] > 30 or not _TRAIN_CACHE["trains"]:
        try:
            _TRAIN_CACHE["trains"] = train_mod.fetch()
            _TRAIN_CACHE["at"] = time.time()
        except Exception:  # noqa: BLE001
            pass
    return {"trains": train_mod.near(_TRAIN_CACHE["trains"], lat, lon, radius)}


_EVAC_CACHE: dict = {"at": 0.0, "gj": {"type": "FeatureCollection", "features": []}}


@app.get("/api/evac")
def evac_zones():
    """Active CA evacuation zones (GeoJSON + a flat summary). Empty in blue-sky."""
    if time.time() - _EVAC_CACHE["at"] > 120:
        try:
            _EVAC_CACHE["gj"] = evac.fetch_active_zones()
            _EVAC_CACHE["at"] = time.time()
        except Exception:  # noqa: BLE001
            pass
    gj = _EVAC_CACHE["gj"]
    return {"geojson": gj, "zones": evac.summarize(gj)}


@app.get("/api/safepoints")
def safe_points(lat: float, lon: float):
    """Nearest hospitals / police / fire stations / shelters (where to go)."""
    return {"safe_points": evac.fetch_safe_points(lat, lon)}


@app.get("/api/webcams")
def webcams_near(lat: float, lon: float, radius_km: int = 50):
    """Public webcams near a point (the legal 'look around' layer)."""
    return {"webcams": webcams.fetch_near(lat, lon, radius_km)}


_TRANSIT_CACHE: dict = {"at": 0.0, "vehicles": []}


@app.get("/api/transit")
def transit_near(lat: float, lon: float, radius: float = 30):
    """Live buses / BART / regional transit near a point (511, Bay Area)."""
    if time.time() - _TRANSIT_CACHE["at"] > 20 or not _TRANSIT_CACHE["vehicles"]:
        try:
            _TRANSIT_CACHE["vehicles"] = transit_mod.fetch("RG")
            _TRANSIT_CACHE["at"] = time.time()
        except Exception:  # noqa: BLE001
            pass
    near = transit_mod.near(_TRANSIT_CACHE["vehicles"], lat, lon, radius)
    return {"transit": near[:150]}  # cap markers so the map stays smooth


_NEWS_CACHE: dict = {}   # place -> (ts, articles)


@app.get("/api/scanner_near")
def scanner_near(lat: float | None = None, lon: float | None = None, limit: int = 8):
    """Recent radio transcripts (timestamped, code-named) for the Transcript tab.
    Returns each scanner block/call with its transcript + replayable audio."""
    base = _store_dir()
    day = store.today_pt()
    if not store.day_db_path(base, day).exists():
        return {"transcripts": []}
    conn = store.connect(base, day)
    try:
        rows = store.get_events(conn)
    finally:
        conn.close()
    sc = [r for r in rows if r.get("source") == "scanner"]
    sc.sort(key=lambda r: r.get("last_seen") or "", reverse=True)
    return {"transcripts": [
        {"type": r.get("type"), "geo_label": r.get("geo_label"), "log_time": r.get("log_time"),
         "body": r.get("body"), "audio_url": r.get("audio_url"), "block": r.get("archive_block")}
        for r in sc[:limit]
    ]}


@app.get("/api/event_transcript")
def event_transcript(lat: float, lon: float, id: str | None = None,
                     radius_mi: float = 0.75, limit: int = 6):
    """The radio traffic for THIS event. If the incident IS a scanner call (id
    given), return ONLY its own conversation -- exact. Otherwise the geocoded
    calls within radius, each split into speaker turns + tagged by service."""
    from .radio import speaker_segments, classify_service, summarize, extract_entities
    from .geo_county import distance_mi
    from datetime import datetime as _dt

    base = _store_dir()
    day = store.today_pt()
    if not store.day_db_path(base, day).exists():
        return {"conversations": [], "sources": 0}
    conn = store.connect(base, day)
    try:
        rows = store.get_events(conn)
    finally:
        conn.close()

    def _fmt(iso):
        try:
            return _dt.fromisoformat(iso).strftime("%-I:%M %p")
        except Exception:  # noqa: BLE001
            return ""

    def _conv(r, d=0.0):
        body = r.get("body") or ""
        segs = speaker_segments(body)
        svc = classify_service(body)
        return {
            "service": svc, "call": r.get("geo_label"),
            "start": _fmt(r.get("log_time") or ""), "distance_mi": round(d, 1),
            "audio_url": r.get("audio_url"), "segments": segs,
            "summary": summarize(segs, svc, r.get("geo_label")),
            "entities": extract_entities(body),
        }

    # Exact: this incident is itself a scanner call -> only its own conversation.
    if id:
        own = next((r for r in rows if r.get("id") == id
                    and (r.get("type") or "").startswith("Scanner call")), None)
        if own:
            return {"conversations": [_conv(own)], "sources": 1}

    calls = []
    for r in rows:
        if r.get("source") != "scanner" or r.get("lat") is None:
            continue
        if not (r.get("type") or "").startswith("Scanner call"):  # skip block-log dumps
            continue
        d = distance_mi((lat, lon), (r["lat"], r["lon"]))
        if d <= radius_mi:
            calls.append((d, r))
    calls.sort(key=lambda x: (x[1].get("log_time") or ""), reverse=True)  # most recent first
    return {"conversations": [_conv(r, d) for d, r in calls[:limit]], "sources": len(calls)}


@app.get("/api/intel")
def intel(lat: float, lon: float, radius_mi: float = 2.0, days: int = 7):
    """Temporal intel for an area: precursors (nearby incidents over the past
    `days`) + how active the area is today. 'Was this signaled yesterday?'"""
    from .geo_county import distance_mi
    from datetime import datetime as _dt, timedelta

    base = _store_dir()
    today = store.today_pt()
    try:
        base_date = _dt.strptime(today, "%Y_%m_%d")
    except Exception:  # noqa: BLE001
        base_date = None
    precursors = []
    if base_date:
        for i in range(1, days + 1):
            dk = (base_date - timedelta(days=i)).strftime("%Y_%m_%d")
            if not store.day_db_path(base, dk).exists():
                continue
            conn = store.connect(base, dk)
            try:
                rows = store.get_events(conn)
            finally:
                conn.close()
            for r in rows:
                if r.get("lat") is None:
                    continue
                d = distance_mi((lat, lon), (r["lat"], r["lon"]))
                if d <= radius_mi:
                    precursors.append({"date": dk.replace("_", "-"), "type": r.get("type"),
                                       "severity": r.get("severity"), "dist": round(d, 1)})
    area_today = 0
    if store.day_db_path(base, today).exists():
        conn = store.connect(base, today)
        try:
            for r in store.get_events(conn):
                if r.get("lat") is not None and distance_mi((lat, lon), (r["lat"], r["lon"])) <= radius_mi:
                    area_today += 1
        finally:
            conn.close()
    precursors.sort(key=lambda x: x["date"], reverse=True)
    # Predictive risk from OUR OWN history: density (7d) + activity now, weighted
    # up if a CRITICAL/HIGH precursor sits here. A real risk-terrain-lite score.
    prior = len(precursors)
    hi_prior = sum(1 for p in precursors if p.get("severity") in ("CRITICAL", "HIGH"))
    risk = min(100, prior * 7 + area_today * 15 + hi_prior * 6)
    level = "HIGH" if risk >= 50 else "MEDIUM" if risk >= 20 else "LOW"
    factors = []
    if prior >= 3:
        factors.append(f"{prior} incidents here in 7 days")
    if hi_prior:
        factors.append(f"{hi_prior} were high-severity")
    if area_today >= 2:
        factors.append(f"{area_today} active in this spot today")
    if not factors:
        factors.append("quiet area, little recent history")
    return {"precursors": precursors[:30], "prior_count": prior, "area_today": area_today,
            "radius_mi": radius_mi, "risk_score": risk, "risk_level": level, "risk_factors": factors}


@app.get("/api/links")
def links(id: str, days: int = 3):
    """Link analysis: incidents connected to this one by shared plate, vehicle,
    suspect description, responding unit, or exact location (today + recent days)."""
    from .radio import extract_entities, line_ids
    from datetime import datetime as _dt, timedelta

    base = _store_dir()
    rows: list[dict] = []
    try:
        bd = _dt.strptime(store.today_pt(), "%Y_%m_%d")
    except Exception:  # noqa: BLE001
        return {"links": [], "entities": {}}
    for i in range(days):
        dk = (bd - timedelta(days=i)).strftime("%Y_%m_%d")
        if not store.day_db_path(base, dk).exists():
            continue
        conn = store.connect(base, dk)
        try:
            for r in store.get_events(conn):
                r["_day"] = dk.replace("_", "-")
                rows.append(r)
        finally:
            conn.close()
    target = next((r for r in rows if r.get("id") == id), None)
    if not target:
        return {"links": [], "entities": {}}
    tb = target.get("body") or ""
    te = extract_entities(tb)
    t_plate, t_veh, t_person = set(te.get("plate", [])), set(te.get("vehicle", [])), set(te.get("person", []))
    t_units = set(line_ids(tb, base))
    t_loc = (target.get("geo_label") or "").strip().lower()
    out = []
    for r in rows:
        if r.get("id") == id or r.get("lat") is None:
            continue
        if (r.get("type") or "").startswith("Scanner log"):  # skip block-log dumps (match everything)
            continue
        rb = r.get("body") or ""
        re_ = extract_entities(rb)
        reasons = []
        if t_plate & set(re_.get("plate", [])):
            reasons.append("same plate")
        if t_veh & set(re_.get("vehicle", [])):
            reasons.append("same vehicle")
        if t_person & set(re_.get("person", [])):
            reasons.append("same description")
        su = t_units & set(line_ids(rb, base))
        if su:
            reasons.append("unit " + ", ".join(sorted(su)[:2]))
        if t_loc and t_loc == (r.get("geo_label") or "").strip().lower():
            reasons.append("same location")
        if reasons:
            out.append({"id": r.get("id"), "type": r.get("type"), "day": r.get("_day"),
                        "geo_label": r.get("geo_label"), "lat": r.get("lat"), "lon": r.get("lon"),
                        "reasons": list(dict.fromkeys(reasons))})
    return {"links": out[:20], "entities": te}


@app.get("/api/social")
def social(place: str = "Solano County"):
    """Local safety chatter (Reddit RSS), collected + geo-tagged by the ingest loop."""
    import json as _json

    p = os.path.join(_store_dir(), "social.json")
    if os.path.exists(p):
        try:
            return {"place": place, "posts": _json.load(open(p)).get("posts", [])}
        except Exception:  # noqa: BLE001
            pass
    from . import social as social_mod

    return {"place": place, "posts": social_mod.safety_posts(place)}


@app.get("/api/social_hotspots")
def social_hotspots():
    """Geo-tagged social heat: cities with clustered safety chatter (for the map)."""
    import json as _json

    p = os.path.join(_store_dir(), "social.json")
    if os.path.exists(p):
        try:
            d = _json.load(open(p))
            return {"hotspots": d.get("hotspots", []), "updated": d.get("updated", 0)}
        except Exception:  # noqa: BLE001
            pass
    return {"hotspots": [], "updated": 0}


@app.get("/api/mesh")
def mesh():
    """Meshtastic nodes + messages in the bubble (collected off the public MQTT)."""
    import json as _json

    p = os.path.join(_store_dir(), "mesh.json")
    if os.path.exists(p):
        try:
            return _json.load(open(p))
        except Exception:  # noqa: BLE001
            pass
    return {"nodes": [], "messages": [], "updated": 0}


@app.get("/api/cam_dvr")
def cam_dvr(lat: float, lon: float, t: int | None = None):
    """Recorded camera frames around an event time (5 min before -> after)."""
    return camera_dvr.window(_store_dir(), lat, lon, t or int(time.time()))


@app.get("/api/camframe/{safe_id}/{ts}")
def camframe(safe_id: str, ts: str):
    from fastapi import HTTPException

    p = camera_dvr.frame_path(_store_dir(), safe_id, ts)
    if os.path.exists(p):
        return FileResponse(p, media_type="image/jpeg")
    raise HTTPException(status_code=404)


@app.get("/api/scanner_audio/{block_id}")
def scanner_audio(block_id: str):
    """Serve a downloaded Broadcastify archive block for DVR replay."""
    from fastapi import HTTPException

    safe = block_id.replace("/", "").replace("..", "")
    path = Path(_store_dir()) / "audio" / f"{safe}.mp3"
    if not path.exists():
        raise HTTPException(status_code=404, detail="audio not available")
    return FileResponse(str(path), media_type="audio/mpeg")


_SWX_CACHE: dict = {"at": 0.0, "v": None}
_FEMA_CACHE: dict = {}


@app.get("/api/danger")
def danger():
    """GeoJSON of everything to avoid: evac ORDER zones + fire + CRITICAL/HIGH incidents."""
    return routing.danger_features(_store_dir())


@app.get("/api/route")
def route(lat: float, lon: float):
    """Route to the nearest safe destination (with alternates)."""
    return routing.route_to_safety(lat, lon)


_EVAC_CACHE: dict = {"at": 0.0, "gj": None}


@app.get("/api/decision")
def decision(lat: float, lon: float):
    """Shelter-in-place vs Evacuate vs Clear, fused from classified incidents +
    active evac zones. The 'what do I actually do' layer."""
    base = _store_dir()
    day = store.today_pt()
    incidents: list[dict] = []
    if store.day_db_path(base, day).exists():
        conn = store.connect(base, day)
        try:
            rows = [r for r in store.get_events(conn) if store.on_day(r.get("last_seen"), day)]
        finally:
            conn.close()
        incidents = [threat.classify(r, (lat, lon)) for r in rows]  # same daily-reset as the map
    if time.time() - _EVAC_CACHE["at"] > 300 or _EVAC_CACHE["gj"] is None:
        try:
            _EVAC_CACHE["gj"] = evac.fetch_active_zones()
            _EVAC_CACHE["at"] = time.time()
        except Exception:  # noqa: BLE001 - serve stale/empty on transient failure
            _EVAC_CACHE["gj"] = _EVAC_CACHE["gj"] or {"features": []}
    zones = decide_mod.enrich_zones(_EVAC_CACHE["gj"], lat, lon)
    return decide_mod.decide(incidents, zones, user=(lat, lon))


@app.get("/api/escape")
def escape_route(lat: float, lon: float):
    """Dispersed Egress: several ranked escape routes to safety, scored by real
    free-flow time (road speed limits + a penalty per traffic light and stop sign)
    and steered around incident-blocked roads, so you take the clearest way out
    instead of the jammed artery. Advisory only -- follow official orders + 911."""
    hazard = None
    try:
        d = decision(lat, lon)  # flee AWAY from the decide-engine's hazard
        if d.get("hazard_lat") is not None:
            hazard = {"lat": d["hazard_lat"], "lon": d["hazard_lon"]}
    except Exception:  # noqa: BLE001
        pass
    return escape_mod.plan_escape(lat, lon, _store_dir(), hazard=hazard)


@app.post("/api/sos")
def sos(lat: float | None = None, lon: float | None = None, kind: str = "manual", where: str = ""):
    """Personal SOS / crash alert. Fires a max-priority ntfy push (breaks Do Not
    Disturb) with the location + a maps link, so a trusted phone gets it even when
    the operator can't act. Advisory: the app also offers to dial 911 client-side."""
    maps = f"https://maps.google.com/?q={lat},{lon}" if lat is not None and lon is not None else ""
    label = "CRASH DETECTED" if kind == "crash" else "SOS"
    ev = {
        "threat_level": "EXTREME",
        "type": label,
        "geo_label": where or maps,
        "distance_mi": None,
        "body": f"{label} from AroundMe.\n{where}\n{maps}".strip(),
    }
    ok = notify.ntfy_sender(ev, 5)  # priority 5 = breaks Do Not Disturb
    return {"ok": ok, "maps": maps, "label": label}


@app.post("/api/report")
def post_report(kind: str, lat: float, lon: float, detail: str = "", heading: float | None = None):
    """One-tap community hazard / reckless-driver report. Warns other drivers, not
    police. Time-decaying (reckless fades fast, static hazards linger)."""
    from . import reports
    return reports.add_report(_store_dir(), kind, lat, lon, detail, heading)


@app.post("/api/presence")
def post_presence(client: str, lat: float, lon: float, active: bool = True):
    """Gig-driver 'on delivery' self-marker, so a vehicle idling on a street reads
    as a delivery, not a prowler. Refreshed while working; active=false clears it."""
    from . import reports
    if not active:
        return reports.clear_presence(_store_dir(), client)
    return reports.mark_presence(_store_dir(), client, lat, lon)


@app.get("/api/reports")
def get_reports():
    """Active community reports + gig-driver presence markers (non-expired)."""
    from . import reports
    return {"reports": reports.active(_store_dir())}


def _broadcast_beacon(base, client, lat, lon, note):
    """Fire a distress pulse on every channel we have (ntfy now, mesh best-effort)."""
    maps = f"https://maps.google.com/?q={lat},{lon}" if lat is not None and lon is not None else ""
    notify.ntfy_sender({
        "threat_level": "EXTREME", "type": "DISTRESS BEACON", "geo_label": maps,
        "distance_mi": None, "body": f"DISTRESS BEACON ACTIVE. {note}\nPosition: {maps}".strip(),
    }, 5)
    try:  # off-grid channel, best-effort (no-op until mesh send is wired to hardware)
        from . import meshtastic_mesh
        sender = getattr(meshtastic_mesh, "send_text", None)
        if sender:
            sender(f"SOS DISTRESS {lat},{lon} {note}"[:200])
    except Exception:  # noqa: BLE001 - a beacon must never crash on a dead channel
        pass


async def _beacon_repeater(base):
    """Autonomous EPIRB pulse: re-broadcast every active beacon on its interval, so
    it keeps transmitting even if the operator's screen is off or the app is closed."""
    while True:
        try:
            for b in beacon.due_for_broadcast(base):
                _broadcast_beacon(base, b["client"], b.get("lat"), b.get("lon"), b.get("note", ""))
                beacon.mark_broadcast(base, b["client"])
        except Exception as e:  # noqa: BLE001
            print(f"[beacon] repeater error: {e}", flush=True)
        await asyncio.sleep(60)


@app.post("/api/beacon")
def beacon_ctl(client: str, lat: float | None = None, lon: float | None = None, note: str = "", active: bool = True):
    """EPIRB-style distress beacon. Activating broadcasts your position on repeat
    until you cancel. NOT a certified 406 MHz EPIRB (does not reach Coast Guard /
    SARSAT); it pulses ntfy + the local mesh. active=false cancels + sends all-clear."""
    base = _store_dir()
    if not active:
        beacon.cancel(base, client)
        notify.ntfy_sender({"threat_level": "LOW", "type": "DISTRESS CANCELLED",
                            "geo_label": "", "distance_mi": None, "body": "Distress beacon cancelled."}, 3)
        return {"active": False}
    st = beacon.activate(base, client, lat, lon, note)
    _broadcast_beacon(base, client, lat, lon, note)  # first pulse now
    beacon.mark_broadcast(base, client)
    return st


@app.get("/api/beacon")
def beacon_get():
    """All active distress beacons (for the map + the active-beacon banner)."""
    return {"beacons": beacon.get(_store_dir())}


@app.get("/api/spacewx")
def space_weather():
    """Geomagnetic (Kp) status -> GPS/comms reliability (10-min cache)."""
    if time.time() - _SWX_CACHE["at"] > 600 or _SWX_CACHE["v"] is None:
        _SWX_CACHE["v"] = spacewx.fetch()
        _SWX_CACHE["at"] = time.time()
    return _SWX_CACHE["v"]


@app.get("/api/disasters")
def disasters(state: str = "CA"):
    """Recent FEMA disaster declarations for a state (1-hour cache)."""
    hit = _FEMA_CACHE.get(state)
    if hit and time.time() - hit[0] < 3600:
        return {"state": state, "disasters": hit[1]}
    d = fema.fetch(state=state)
    _FEMA_CACHE[state] = (time.time(), d)
    return {"state": state, "disasters": d}


@app.get("/api/news")
def local_news(place: str):
    """Recent news about a place (the survival-OS news outlet). 10-min cache."""
    hit = _NEWS_CACHE.get(place)
    if hit and time.time() - hit[0] < 600:
        return {"place": place, "news": hit[1]}
    try:
        arts = news.fetch_news(place)
        _NEWS_CACHE[place] = (time.time(), arts)
        return {"place": place, "news": arts}
    except Exception as e:  # noqa: BLE001
        return {"place": place, "news": hit[1] if hit else [], "error": str(e)}


# Serve the static web page at "/" (index.html). Mounted last so /api and
# /healthz win. Guard so the app imports even before web/ exists.
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
