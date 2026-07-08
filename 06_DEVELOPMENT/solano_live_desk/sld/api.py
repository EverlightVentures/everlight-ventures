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
from . import config, correlate, dvr, evac, fema, news, routing, spacewx, store, threat, trains as train_mod, transit as transit_mod, wayfinding, webcams
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
    user = (lat, lon) if lat is not None and lon is not None else None
    scored = [threat.classify(r, user) for r in rows]
    for e in scored:  # lifecycle: LIVE while updating, REPORT once quiet
        e["status"] = correlate.lifecycle_status(e.get("last_seen"))
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
    user = (lat, lon) if lat is not None and lon is not None else None
    fused = [threat.classify(i, user) for i in correlate.correlate(rows)]
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


@app.get("/api/flight")
def flight(callsign: str):
    """Enrich a live flight with its origin -> destination + airline (adsbdb)."""
    cs = callsign.strip().upper()
    if not cs:
        return {"callsign": cs, "origin": None, "dest": None}
    if cs in _FLIGHT_CACHE:
        return _FLIGHT_CACHE[cs]
    out = {"callsign": cs, "origin": None, "dest": None, "airline": None}
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
                    "airline": (fr.get("airline") or {}).get("name"),
                }
    except Exception:  # noqa: BLE001
        pass
    _FLIGHT_CACHE[cs] = out
    return out


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
    from .radio import speaker_segments, classify_service, summarize
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
