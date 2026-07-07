# Solano Live Desk -- Phase 1: Live Incident Map -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working live map of Solano County CHP incidents: polled from the CHP feed, stored in a per-day SQLite file, served by FastAPI, and rendered on a MapLibre page with GPS pins, dispatch-log popups, a scrub-back time slider, and a day picker.

**Architecture:** A small Python package (`sld/`) with pure, testable units (geo decode, XML parser, day-partitioned store) plus an async ingest loop and a FastAPI app that serves both the JSON API and a single static web page. The frontend is one HTML page using MapLibre GL from CDN. Everything runs on e5-mother; the phone is only a browser viewer.

**Tech Stack:** Python 3.11+, httpx, FastAPI, uvicorn, SQLite (stdlib), pytest; MapLibre GL JS (CDN) on the frontend.

## Global Constraints

- Python 3.11+ (uses `zoneinfo`, `X | None` type syntax, `list[dict]`).
- Free-first: no paid APIs, no paid dependencies. CHP + Caltrans feeds are free/no-auth.
- No em-dash character anywhere in any file (a PreToolUse guard blocks it). Use ASCII hyphens.
- Frontend builds popup DOM with `textContent`, never `innerHTML`/`setHTML` (XSS guard).
- Broadcastify audio is EMBED-ONLY (not in Phase 1; hard rule for later phases): never scrape/restream.
- Service binds `127.0.0.1` by default; expose only via tailnet or `EV_BIND` per Network Binding Doctrine.
- Archive, never delete: day DB files are never removed, only rolled over.
- All timestamps in Pacific Time (America/Los_Angeles).
- Project root: `06_DEVELOPMENT/solano_live_desk/`. Run pytest from that root.

---

## File Structure

```
06_DEVELOPMENT/solano_live_desk/
  requirements.txt
  README.md
  .gitignore
  sld/
    __init__.py
    geo.py            # decode_latlon, in_solano_bbox, SOLANO_CENTROID (pure)
    chp_parser.py     # parse_incidents, is_solano (pure)
    store.py          # day-partition SQLite: connect, upsert_event, get_events, list_days
    ingest.py         # run_once (injectable fetch), fetch_chp, poll_loop
    api.py            # FastAPI: /healthz, /api/days, /api/events, static web mount
  web/
    index.html        # MapLibre page
    app.js            # map, markers, popups, time slider, day picker, follow-me
    style.css
  tests/
    fixtures/sa_sample.xml
    test_geo.py
    test_chp_parser.py
    test_store.py
    test_ingest.py
    test_api.py
  scripts/
    run.sh            # launch ingest loop + uvicorn on e5/local
  store/              # runtime day DBs (gitignored)
```

---

### Task 1: Scaffold + geo utilities

**Files:**
- Create: `06_DEVELOPMENT/solano_live_desk/requirements.txt`
- Create: `06_DEVELOPMENT/solano_live_desk/.gitignore`
- Create: `06_DEVELOPMENT/solano_live_desk/sld/__init__.py`
- Create: `06_DEVELOPMENT/solano_live_desk/sld/geo.py`
- Test: `06_DEVELOPMENT/solano_live_desk/tests/test_geo.py`

**Interfaces:**
- Produces: `decode_latlon(raw: str) -> tuple[float|None, float|None]`, `in_solano_bbox(lat, lon) -> bool`, `SOLANO_CENTROID: tuple[float,float]`.

- [ ] **Step 1: Create requirements.txt and .gitignore**

`requirements.txt`:
```
httpx>=0.27
fastapi>=0.110
uvicorn[standard]>=0.29
pytest>=8.0
```

`.gitignore`:
```
store/
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 2: Create the package init (empty) and write the failing test**

`sld/__init__.py`: empty file.

`tests/test_geo.py`:
```python
from sld.geo import decode_latlon, in_solano_bbox, SOLANO_CENTROID


def test_decode_latlon_valid_negates_longitude():
    assert decode_latlon('"38223740:122126960"') == (38.22374, -122.12696)


def test_decode_latlon_zero_is_none():
    assert decode_latlon('"0:0"') == (None, None)


def test_decode_latlon_garbage_is_none():
    assert decode_latlon("") == (None, None)
    assert decode_latlon("nope") == (None, None)


def test_in_solano_bbox():
    assert in_solano_bbox(38.25, -122.0) is True
    assert in_solano_bbox(34.05, -118.24) is False
    assert in_solano_bbox(None, None) is False


def test_centroid_is_inside_bbox():
    assert in_solano_bbox(*SOLANO_CENTROID) is True
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_geo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sld.geo'`.

- [ ] **Step 4: Implement geo.py**

`sld/geo.py`:
```python
from __future__ import annotations

# Approx county centroid, kept inside the bbox below.
SOLANO_CENTROID: tuple[float, float] = (38.25, -121.98)
# min_lat, min_lon, max_lat, max_lon
SOLANO_BBOX: tuple[float, float, float, float] = (38.0, -122.35, 38.55, -121.55)


def decode_latlon(raw: str | None) -> tuple[float | None, float | None]:
    """Decode a CHP sa.xml LATLON micro-degree pair.

    Values arrive as '"lat:lon"' integers in millionths of a degree, often
    wrapped in literal quotes. Longitude magnitude is returned as West (negative).
    '0:0', empty, or unparseable input returns (None, None).
    """
    if raw is None:
        return (None, None)
    s = raw.strip().strip('"').strip()
    if ":" not in s:
        return (None, None)
    a, b = s.split(":", 1)
    try:
        lat_i = int(a)
        lon_i = int(b)
    except ValueError:
        return (None, None)
    if lat_i == 0 and lon_i == 0:
        return (None, None)
    return (lat_i / 1_000_000, -abs(lon_i) / 1_000_000)


def in_solano_bbox(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    mn_lat, mn_lon, mx_lat, mx_lon = SOLANO_BBOX
    return mn_lat <= lat <= mx_lat and mn_lon <= lon <= mx_lon
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_geo.py -v`
Expected: PASS (5 passed).

- [ ] **Step 6: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 06_DEVELOPMENT/solano_live_desk/requirements.txt \
        06_DEVELOPMENT/solano_live_desk/.gitignore \
        06_DEVELOPMENT/solano_live_desk/sld/__init__.py \
        06_DEVELOPMENT/solano_live_desk/sld/geo.py \
        06_DEVELOPMENT/solano_live_desk/tests/test_geo.py
git commit -m "feat(sld): geo decode + Solano bbox utilities"
```

---

### Task 2: CHP XML parser

**Files:**
- Create: `06_DEVELOPMENT/solano_live_desk/sld/chp_parser.py`
- Create: `06_DEVELOPMENT/solano_live_desk/tests/fixtures/sa_sample.xml`
- Test: `06_DEVELOPMENT/solano_live_desk/tests/test_chp_parser.py`

**Interfaces:**
- Consumes: `sld.geo.decode_latlon`.
- Produces: `parse_incidents(xml_str: str, dispatch_id: str = "GGCC") -> list[dict]` where each dict has keys `id, source, type, title, lat, lon, geo_label, log_time, area, body, details`. `is_solano(area: str, location: str) -> bool`.

> Note: the fixture is modeled on the documented CHP sa.xml schema (Center/Dispatch/Log/LogDetails/details, values wrapped in literal quotes). Task 7 validates the parser against live bytes and the executor adjusts tag names if the live feed differs.

- [ ] **Step 1: Write the fixture**

`tests/fixtures/sa_sample.xml`:
```xml
<State>
  <Center ID="GGHB">
    <Dispatch ID="GGCC">
      <Log ID="0042">
        <LogTime>"7:34AM"</LogTime>
        <LogType>"Trfc Collision-No Inj"</LogType>
        <Location>"I80 E / SUISUN VALLEY RD"</Location>
        <LocationDesc>"Fairfield"</LocationDesc>
        <Area>"Solano"</Area>
        <LATLON>"38223740:122126960"</LATLON>
        <LogDetails>
          <details><DetailTime>"7:35AM"</DetailTime><IncidentDetail>"veh in center divide"</IncidentDetail></details>
          <details><DetailTime>"7:36AM"</DetailTime><IncidentDetail>"units en route"</IncidentDetail></details>
        </LogDetails>
      </Log>
      <Log ID="0043">
        <LogTime>"7:40AM"</LogTime>
        <LogType>"Traffic Hazard"</LogType>
        <Location>"SR1 / OCEAN AVE"</Location>
        <LocationDesc>"San Francisco"</LocationDesc>
        <Area>"San Francisco"</Area>
        <LATLON>"0:0"</LATLON>
        <LogDetails></LogDetails>
      </Log>
    </Dispatch>
    <Dispatch ID="SFCC">
      <Log ID="9001">
        <LogType>"x"</LogType>
        <Location>"FAIRFIELD ST"</Location>
        <Area>"San Francisco"</Area>
        <LATLON>"0:0"</LATLON>
      </Log>
    </Dispatch>
  </Center>
</State>
```

- [ ] **Step 2: Write the failing test**

`tests/test_chp_parser.py`:
```python
from pathlib import Path
from sld.chp_parser import parse_incidents, is_solano

FIX = Path(__file__).parent / "fixtures" / "sa_sample.xml"


def test_is_solano_by_area():
    assert is_solano("Solano", "anything") is True


def test_is_solano_by_location_token():
    assert is_solano("San Francisco", "I80 E / SUISUN VALLEY RD") is True
    assert is_solano("San Francisco", "SR1 / OCEAN AVE") is False


def test_parse_keeps_only_ggcc_solano():
    events = parse_incidents(FIX.read_text())
    # GGCC 0043 is SF (filtered), SFCC 9001 is wrong dispatch (skipped),
    # only GGCC 0042 (Solano) survives.
    assert len(events) == 1
    ev = events[0]
    assert ev["id"] == "chp:GGCC:0042"
    assert ev["source"] == "chp"
    assert ev["type"] == "Trfc Collision-No Inj"
    assert ev["lat"] == 38.22374
    assert ev["lon"] == -122.12696
    assert ev["geo_label"] == "I80 E / SUISUN VALLEY RD"
    assert ev["body"] == "7:35AM  veh in center divide\n7:36AM  units en route"
    assert ev["details"] == [
        "7:35AM  veh in center divide",
        "7:36AM  units en route",
    ]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_chp_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sld.chp_parser'`.

- [ ] **Step 4: Implement chp_parser.py**

`sld/chp_parser.py`:
```python
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .geo import decode_latlon

SOLANO_TOKENS = re.compile(
    r"\b(FAIRFIELD|VACAVILLE|VALLEJO|BENICIA|SUISUN|DIXON|RIO VISTA|"
    r"CORDELIA|GREEN VALLEY|ELMIRA|"
    r"I80|I-80|I680|I-680|I505|I-505|SR12|SR-12|SR37|SR-37|SR113|SR-113)\b",
    re.IGNORECASE,
)


def _clean(text: str | None) -> str:
    if text is None:
        return ""
    return text.strip().strip('"').strip()


def is_solano(area: str, location: str) -> bool:
    if _clean(area).lower() == "solano":
        return True
    return bool(SOLANO_TOKENS.search(location or ""))


def parse_incidents(xml_str: str, dispatch_id: str = "GGCC") -> list[dict]:
    """Parse CHP sa.xml and return normalized Solano incident dicts."""
    out: list[dict] = []
    root = ET.fromstring(xml_str)
    for dispatch in root.iter("Dispatch"):
        if dispatch.get("ID") != dispatch_id:
            continue
        for log in dispatch.findall("Log"):
            log_id = log.get("ID") or ""
            logtype = _clean(log.findtext("LogType"))
            location = _clean(log.findtext("Location"))
            location_desc = _clean(log.findtext("LocationDesc"))
            area = _clean(log.findtext("Area"))
            logtime = _clean(log.findtext("LogTime"))
            latlon = _clean(log.findtext("LATLON"))
            if not is_solano(area, f"{location} {location_desc}"):
                continue
            lat, lon = decode_latlon(latlon)
            details: list[str] = []
            for d in log.findall("./LogDetails/details"):
                dt = _clean(d.findtext("DetailTime"))
                txt = _clean(d.findtext("IncidentDetail"))
                if txt:
                    details.append(f"{dt}  {txt}".strip())
            title = f"{logtype} - {location}".strip(" -")
            out.append(
                {
                    "id": f"chp:{dispatch_id}:{log_id}",
                    "source": "chp",
                    "type": logtype,
                    "title": title,
                    "lat": lat,
                    "lon": lon,
                    "geo_label": location or location_desc,
                    "log_time": logtime,
                    "area": area,
                    "body": "\n".join(details),
                    "details": details,
                }
            )
    return out
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_chp_parser.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 06_DEVELOPMENT/solano_live_desk/sld/chp_parser.py \
        06_DEVELOPMENT/solano_live_desk/tests/fixtures/sa_sample.xml \
        06_DEVELOPMENT/solano_live_desk/tests/test_chp_parser.py
git commit -m "feat(sld): CHP sa.xml parser filtered to Solano/GGCC"
```

---

### Task 3: Day-partitioned SQLite store

**Files:**
- Create: `06_DEVELOPMENT/solano_live_desk/sld/store.py`
- Test: `06_DEVELOPMENT/solano_live_desk/tests/test_store.py`

**Interfaces:**
- Produces: `PT` (ZoneInfo), `today_pt() -> str`, `day_db_path(base, day) -> Path`, `connect(base, day) -> sqlite3.Connection`, `upsert_event(conn, ev: dict, now_iso: str) -> None`, `get_events(conn) -> list[dict]`, `list_days(base) -> list[str]`.

- [ ] **Step 1: Write the failing test**

`tests/test_store.py`:
```python
from sld import store


def test_upsert_creates_then_updates(tmp_path):
    conn = store.connect(tmp_path, "2026_07_07")
    ev = {
        "id": "chp:GGCC:1", "source": "chp", "type": "x", "title": "t",
        "lat": 38.2, "lon": -122.0, "geo_label": "L", "body": "line1",
        "details": ["line1"],
    }
    store.upsert_event(conn, ev, "2026-07-07T07:35:00-07:00")
    ev["body"] = "line1\nline2"
    store.upsert_event(conn, ev, "2026-07-07T07:36:00-07:00")
    rows = store.get_events(conn)
    assert len(rows) == 1
    assert rows[0]["body"] == "line1\nline2"
    assert rows[0]["first_seen"] == "2026-07-07T07:35:00-07:00"
    assert rows[0]["last_seen"] == "2026-07-07T07:36:00-07:00"


def test_upsert_preserves_coords_when_later_none(tmp_path):
    conn = store.connect(tmp_path, "2026_07_07")
    base = {"id": "chp:GGCC:2", "source": "chp", "type": "x", "title": "t",
            "geo_label": "L", "body": "b", "details": []}
    store.upsert_event(conn, {**base, "lat": 38.2, "lon": -122.0}, "t1")
    store.upsert_event(conn, {**base, "lat": None, "lon": None}, "t2")
    rows = store.get_events(conn)
    assert rows[0]["lat"] == 38.2  # COALESCE keeps the known fix


def test_list_days(tmp_path):
    store.connect(tmp_path, "2026_07_06").close()
    store.connect(tmp_path, "2026_07_07").close()
    assert store.list_days(tmp_path) == ["2026_07_06", "2026_07_07"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sld.store'`.

- [ ] **Step 3: Implement store.py**

`sld/store.py`:
```python
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PT = ZoneInfo("America/Los_Angeles")
DAY_FMT = "%Y_%m_%d"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    source TEXT, type TEXT, title TEXT,
    lat REAL, lon REAL, geo_label TEXT,
    first_seen TEXT, last_seen TEXT,
    body TEXT, entities TEXT, raw TEXT
);
"""


def today_pt() -> str:
    return datetime.now(PT).strftime(DAY_FMT)


def day_db_path(base: str | Path, day: str) -> Path:
    return Path(base) / f"events_{day}.db"


def connect(base: str | Path, day: str) -> sqlite3.Connection:
    Path(base).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(day_db_path(base, day))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def upsert_event(conn: sqlite3.Connection, ev: dict, now_iso: str) -> None:
    row = conn.execute(
        "SELECT first_seen FROM events WHERE id=?", (ev["id"],)
    ).fetchone()
    entities = json.dumps(ev.get("entities") or {})
    raw = json.dumps(ev.get("details") or [])
    if row is None:
        conn.execute(
            "INSERT INTO events "
            "(id,source,type,title,lat,lon,geo_label,first_seen,last_seen,body,entities,raw) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (ev["id"], ev.get("source"), ev.get("type"), ev.get("title"),
             ev.get("lat"), ev.get("lon"), ev.get("geo_label"),
             now_iso, now_iso, ev.get("body"), entities, raw),
        )
    else:
        conn.execute(
            "UPDATE events SET last_seen=?, body=?, "
            "lat=COALESCE(?,lat), lon=COALESCE(?,lon), raw=? WHERE id=?",
            (now_iso, ev.get("body"), ev.get("lat"), ev.get("lon"), raw, ev["id"]),
        )
    conn.commit()


def get_events(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM events ORDER BY last_seen").fetchall()
    return [dict(r) for r in rows]


def list_days(base: str | Path) -> list[str]:
    base = Path(base)
    if not base.exists():
        return []
    found = list(base.glob("events_*.db")) + list((base / "archive").glob("events_*.db"))
    days = {p.stem.replace("events_", "") for p in found}
    return sorted(days)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_store.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 06_DEVELOPMENT/solano_live_desk/sld/store.py \
        06_DEVELOPMENT/solano_live_desk/tests/test_store.py
git commit -m "feat(sld): day-partitioned SQLite event store"
```

---

### Task 4: Ingest cycle

**Files:**
- Create: `06_DEVELOPMENT/solano_live_desk/sld/ingest.py`
- Test: `06_DEVELOPMENT/solano_live_desk/tests/test_ingest.py`

**Interfaces:**
- Consumes: `sld.chp_parser.parse_incidents`, `sld.store.{connect,upsert_event,today_pt,PT}`.
- Produces: `run_once(fetch_fn, base, day=None, now_iso=None) -> int`, `fetch_chp(timeout=20.0) -> str`, `async poll_loop(base, interval=60) -> None`, `CHP_URL`.

- [ ] **Step 1: Write the failing test**

`tests/test_ingest.py`:
```python
from pathlib import Path
from sld import ingest, store

FIX = Path(__file__).parent / "fixtures" / "sa_sample.xml"


def test_run_once_stores_solano_events(tmp_path):
    xml = FIX.read_text()
    n = ingest.run_once(
        lambda: xml, tmp_path, day="2026_07_07",
        now_iso="2026-07-07T07:35:00-07:00",
    )
    assert n == 1
    conn = store.connect(tmp_path, "2026_07_07")
    rows = store.get_events(conn)
    assert len(rows) == 1
    assert rows[0]["id"] == "chp:GGCC:0042"


def test_run_once_is_idempotent(tmp_path):
    xml = FIX.read_text()
    ingest.run_once(lambda: xml, tmp_path, day="2026_07_07", now_iso="t1")
    ingest.run_once(lambda: xml, tmp_path, day="2026_07_07", now_iso="t2")
    conn = store.connect(tmp_path, "2026_07_07")
    assert len(store.get_events(conn)) == 1  # same log id, no duplicate row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sld.ingest'`.

- [ ] **Step 3: Implement ingest.py**

`sld/ingest.py`:
```python
from __future__ import annotations

import asyncio
from datetime import datetime

from . import store
from .chp_parser import parse_incidents

CHP_URL = "http://media.chp.ca.gov/sa_xml/sa.xml"


def run_once(fetch_fn, base, day: str | None = None, now_iso: str | None = None) -> int:
    """Fetch, parse, and upsert one cycle. fetch_fn is injectable for tests."""
    day = day or store.today_pt()
    now_iso = now_iso or datetime.now(store.PT).isoformat()
    events = parse_incidents(fetch_fn())
    conn = store.connect(base, day)
    try:
        for ev in events:
            store.upsert_event(conn, ev, now_iso)
    finally:
        conn.close()
    return len(events)


def fetch_chp(timeout: float = 20.0) -> str:
    """GET the CHP statewide XML with retries (old IIS host is flaky)."""
    import httpx

    headers = {"User-Agent": "solano-live-desk/0.1 (personal)"}
    last: Exception | None = None
    for _ in range(3):
        try:
            r = httpx.get(CHP_URL, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.text
        except Exception as e:  # noqa: BLE001 - retry any transport error
            last = e
    raise RuntimeError(f"CHP fetch failed after 3 tries: {last}")


async def poll_loop(base: str, interval: int = 60) -> None:
    while True:
        try:
            n = run_once(fetch_chp, base)
            print(f"[ingest] {store.today_pt()} upserted {n} Solano events", flush=True)
        except Exception as e:  # noqa: BLE001 - keep the loop alive
            print(f"[ingest] error: {e}", flush=True)
        await asyncio.sleep(interval)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_ingest.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 06_DEVELOPMENT/solano_live_desk/sld/ingest.py \
        06_DEVELOPMENT/solano_live_desk/tests/test_ingest.py
git commit -m "feat(sld): CHP ingest cycle with injectable fetch"
```

---

### Task 5: FastAPI app

**Files:**
- Create: `06_DEVELOPMENT/solano_live_desk/sld/api.py`
- Test: `06_DEVELOPMENT/solano_live_desk/tests/test_api.py`

**Interfaces:**
- Consumes: `sld.store.{today_pt,day_db_path,connect,get_events,list_days}`.
- Produces: FastAPI `app`; routes `GET /healthz`, `GET /api/days -> {"days":[...]}`, `GET /api/events?date= -> {"date":..., "events":[...]}`. Reads store dir from env `SLD_STORE` at call time (default `store`).

- [ ] **Step 1: Write the failing test**

`tests/test_api.py`:
```python
from fastapi.testclient import TestClient
from sld import api, store


def _seed(tmp_path):
    conn = store.connect(tmp_path, store.today_pt())
    store.upsert_event(
        conn,
        {"id": "chp:GGCC:1", "source": "chp", "type": "x", "title": "t",
         "lat": 38.2, "lon": -122.0, "geo_label": "L", "body": "b", "details": []},
        "2026-07-07T07:35:00-07:00",
    )
    conn.close()


def test_healthz():
    client = TestClient(api.app)
    assert client.get("/healthz").json() == {"ok": True}


def test_events_endpoint_returns_seeded(tmp_path, monkeypatch):
    monkeypatch.setenv("SLD_STORE", str(tmp_path))
    _seed(tmp_path)
    client = TestClient(api.app)
    body = client.get("/api/events").json()
    assert body["events"][0]["id"] == "chp:GGCC:1"


def test_events_missing_day_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("SLD_STORE", str(tmp_path))
    client = TestClient(api.app)
    body = client.get("/api/events?date=1999_01_01").json()
    assert body == {"date": "1999_01_01", "events": []}


def test_days_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("SLD_STORE", str(tmp_path))
    _seed(tmp_path)
    client = TestClient(api.app)
    assert store.today_pt() in client.get("/api/days").json()["days"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sld.api'`.

- [ ] **Step 3: Implement api.py**

`sld/api.py`:
```python
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import store

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Solano Live Desk")


def _store_dir() -> str:
    return os.environ.get("SLD_STORE", "store")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/days")
def days():
    return {"days": store.list_days(_store_dir())}


@app.get("/api/events")
def events(date: str | None = None):
    base = _store_dir()
    day = date or store.today_pt()
    if not store.day_db_path(base, day).exists():
        return {"date": day, "events": []}
    conn = store.connect(base, day)
    try:
        return {"date": day, "events": store.get_events(conn)}
    finally:
        conn.close()


# Serve the static web page at "/" (index.html). Mounted last so /api and
# /healthz win. Guard so the app imports even before web/ exists (Task 6).
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_api.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 06_DEVELOPMENT/solano_live_desk/sld/api.py \
        06_DEVELOPMENT/solano_live_desk/tests/test_api.py
git commit -m "feat(sld): FastAPI events/days API + static mount"
```

---

### Task 6: Frontend map page

**Files:**
- Create: `06_DEVELOPMENT/solano_live_desk/web/index.html`
- Create: `06_DEVELOPMENT/solano_live_desk/web/app.js`
- Create: `06_DEVELOPMENT/solano_live_desk/web/style.css`
- Test: add `test_serves_index_html` to `06_DEVELOPMENT/solano_live_desk/tests/test_api.py`

**Interfaces:**
- Consumes: `GET /api/days`, `GET /api/events?date=`.
- Produces: a static page. The API's existing static mount serves it at `/`.

> Security constraint: build popup content with DOM nodes + `textContent`. Do NOT use `innerHTML` or `setHTML` (blocked by the XSS guard and unsafe for feed text).

- [ ] **Step 1: Write the failing test (append to test_api.py)**

Add to `tests/test_api.py`:
```python
def test_serves_index_html():
    client = TestClient(api.app)
    r = client.get("/")
    assert r.status_code == 200
    assert "maplibre" in r.text.lower()
    assert 'id="map"' in r.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_api.py::test_serves_index_html -v`
Expected: FAIL (404, since `web/` does not exist yet so the mount was skipped).

- [ ] **Step 3: Create index.html**

`web/index.html`:
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Solano Live Desk</title>
  <link href="https://unpkg.com/maplibre-gl@4.5.0/dist/maplibre-gl.css" rel="stylesheet" />
  <link href="style.css" rel="stylesheet" />
</head>
<body>
  <header id="bar">
    <strong>Solano Live Desk</strong>
    <select id="day"></select>
    <span id="count">0 incidents</span>
    <label id="scrub">
      <input type="range" id="time" min="0" max="100" value="100" />
      <span id="clock">live</span>
    </label>
  </header>
  <div id="map"></div>
  <script src="https://unpkg.com/maplibre-gl@4.5.0/dist/maplibre-gl.js"></script>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 4: Create style.css**

`web/style.css`:
```css
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; font-family: system-ui, sans-serif; }
#bar {
  position: fixed; top: 0; left: 0; right: 0; height: 48px; z-index: 5;
  display: flex; align-items: center; gap: 12px; padding: 0 12px;
  background: #0A0A0A; color: #E8E8E8; border-bottom: 2px solid #D4AF37;
}
#bar strong { color: #D4AF37; }
#map { position: absolute; top: 48px; bottom: 0; left: 0; right: 0; }
#scrub { display: flex; align-items: center; gap: 6px; margin-left: auto; }
#time { width: 200px; }
.maplibregl-popup-content { max-width: 280px; font-size: 13px; }
.popup-body { white-space: pre-wrap; margin-top: 6px; color: #333; }
```

- [ ] **Step 5: Create app.js**

`web/app.js`:
```javascript
const map = new maplibregl.Map({
  container: "map",
  style: "https://demotiles.maplibre.org/style.json",
  center: [-121.98, 38.25], // Solano
  zoom: 9,
});
map.addControl(new maplibregl.NavigationControl());
map.addControl(
  new maplibregl.GeolocateControl({
    positionOptions: { enableHighAccuracy: true },
    trackUserLocation: true,
  })
); // "follow-me"

let markers = [];
let events = [];

function clearMarkers() {
  markers.forEach((m) => m.remove());
  markers = [];
}

function tsMillis(ev) {
  return Date.parse(ev.last_seen) || 0;
}

// Build popup content as DOM nodes with textContent (no innerHTML: XSS-safe).
function buildPopupNode(ev) {
  const wrap = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = ev.type || "Incident";
  const meta = document.createElement("small");
  meta.textContent = `${ev.geo_label || ""} · ${ev.log_time || ""}`;
  const body = document.createElement("div");
  body.className = "popup-body";
  body.textContent = ev.body || "";
  wrap.appendChild(title);
  wrap.appendChild(document.createElement("br"));
  wrap.appendChild(meta);
  wrap.appendChild(body);
  return wrap;
}

function render(cutoffMillis) {
  clearMarkers();
  let shown = 0;
  for (const ev of events) {
    if (ev.lat == null || ev.lon == null) continue;
    if (cutoffMillis && tsMillis(ev) > cutoffMillis) continue;
    const el = document.createElement("div");
    el.textContent = "!";
    el.style.cssText =
      "background:#D4AF37;color:#0A0A0A;font-weight:700;border-radius:50%;" +
      "width:22px;height:22px;display:flex;align-items:center;justify-content:center;" +
      "border:2px solid #0A0A0A;cursor:pointer;";
    const popup = new maplibregl.Popup({ offset: 14 }).setDOMContent(
      buildPopupNode(ev)
    );
    markers.push(
      new maplibregl.Marker({ element: el })
        .setLngLat([ev.lon, ev.lat])
        .setPopup(popup)
        .addTo(map)
    );
    shown++;
  }
  document.getElementById("count").textContent = shown + " incidents";
}

async function loadDays() {
  const sel = document.getElementById("day");
  const { days } = await (await fetch("/api/days")).json();
  sel.replaceChildren();
  for (const d of days.slice().reverse()) {
    const o = document.createElement("option");
    o.value = d;
    o.textContent = d.replace(/_/g, "-");
    sel.appendChild(o);
  }
  sel.onchange = () => loadEvents(sel.value);
  await loadEvents(sel.value);
}

async function loadEvents(date) {
  const url = date ? `/api/events?date=${date}` : "/api/events";
  const data = await (await fetch(url)).json();
  events = data.events || [];
  const withGeo = events.filter((e) => e.lat != null);
  if (withGeo.length) {
    const b = new maplibregl.LngLatBounds();
    withGeo.forEach((e) => b.extend([e.lon, e.lat]));
    if (!b.isEmpty()) map.fitBounds(b, { padding: 60, maxZoom: 12 });
  }
  wireSlider();
  render(null);
}

function wireSlider() {
  const slider = document.getElementById("time");
  const clock = document.getElementById("clock");
  const stamps = events.map(tsMillis).filter(Boolean);
  if (!stamps.length) {
    clock.textContent = "live";
    return;
  }
  const min = Math.min(...stamps);
  const max = Math.max(...stamps);
  slider.oninput = () => {
    const frac = slider.value / 100;
    const cutoff = min + (max - min) * frac;
    clock.textContent =
      slider.value === "100"
        ? "live"
        : new Date(cutoff).toLocaleTimeString("en-US", {
            timeZone: "America/Los_Angeles",
            hour: "2-digit",
            minute: "2-digit",
          });
    render(slider.value === "100" ? null : cutoff);
  };
}

map.on("load", loadDays);
setInterval(() => {
  const sel = document.getElementById("day");
  if (!sel.value || sel.selectedIndex === 0) loadEvents(sel.value);
}, 60000); // refresh the live day each minute
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest tests/test_api.py -v`
Expected: PASS (all, including `test_serves_index_html`).

- [ ] **Step 7: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 06_DEVELOPMENT/solano_live_desk/web/
git add 06_DEVELOPMENT/solano_live_desk/tests/test_api.py
git commit -m "feat(web): MapLibre incident map with time slider + day picker"
```

---

### Task 7: Run script, README, and live end-to-end verification

**Files:**
- Create: `06_DEVELOPMENT/solano_live_desk/scripts/run.sh`
- Create: `06_DEVELOPMENT/solano_live_desk/README.md`

**Interfaces:**
- Consumes everything above.
- Produces: a runnable service and a proof that real Solano data flows end to end.

- [ ] **Step 1: Create run.sh**

`scripts/run.sh`:
```bash
#!/usr/bin/env bash
# Launch Solano Live Desk: background ingest loop + API server.
# Binds 127.0.0.1 by default; set EV_BIND=0.0.0.0 to expose on tailnet.
set -euo pipefail
cd "$(dirname "$0")/.."
export SLD_STORE="${SLD_STORE:-$PWD/store}"
BIND="${EV_BIND:-127.0.0.1}"
PORT="${PORT:-2600}"

python -c "import asyncio; from sld.ingest import poll_loop; asyncio.run(poll_loop('$SLD_STORE'))" &
INGEST_PID=$!
trap 'kill $INGEST_PID 2>/dev/null || true' EXIT

exec uvicorn sld.api:app --host "$BIND" --port "$PORT"
```

- [ ] **Step 2: Create README.md**

`README.md`:
```markdown
# Solano Live Desk (Phase 1)

Personal live map of Solano County CHP incidents. Free, public data only.

## Run
    pip install -r requirements.txt
    bash scripts/run.sh          # ingest loop + API on 127.0.0.1:2600
    # open http://127.0.0.1:2600

Env: `SLD_STORE` (day-DB dir, default ./store), `PORT` (default 2600),
`EV_BIND=0.0.0.0` to expose on tailnet for the phone.

## Test
    python -m pytest -q

## Sources
- CHP incidents: http://media.chp.ca.gov/sa_xml/sa.xml (public, no auth)

See docs/2026-07-07-solano-live-desk-design.md for the full design.
```

- [ ] **Step 3: Run the full test suite**

Run: `cd 06_DEVELOPMENT/solano_live_desk && python -m pytest -q`
Expected: PASS (all tests green, ~16 passed).

- [ ] **Step 4: Live smoke test against the real CHP feed**

Run:
```bash
cd 06_DEVELOPMENT/solano_live_desk
python -c "
from sld import ingest, store
n = ingest.run_once(ingest.fetch_chp, 'store')
print('Solano events pulled from LIVE CHP feed:', n)
conn = store.connect('store', store.today_pt())
for r in store.get_events(conn)[:5]:
    print(' -', r['type'], '|', r['geo_label'], '|', r['lat'], r['lon'])
"
```
Expected: prints a non-negative count. If Solano is quiet, `0` is a VALID result
(verify by checking https://cad.chp.ca.gov/traffic.aspx GGCC in a browser). If the
count is > 0, confirm at least one row has a real `geo_label` and coordinates.
If the parser returns 0 while the browser shows Solano incidents, the live tag names
differ from the fixture: dump the raw XML
(`python -c "from sld.ingest import fetch_chp; print(fetch_chp()[:3000])"`),
compare element names, and adjust `chp_parser.py` + fixture, then re-run Task 2 tests.

- [ ] **Step 5: Serve and eyeball the map**

Run: `cd 06_DEVELOPMENT/solano_live_desk && SLD_STORE=$PWD/store PORT=2600 uvicorn sld.api:app --host 127.0.0.1 --port 2600`
Then open `http://127.0.0.1:2600` in a browser.
Expected: the map loads centered on Solano, incident pins appear (if any today),
clicking a pin shows the dispatch log text, the day picker lists today, and dragging
the time slider left hides later incidents (scrub-back works).

- [ ] **Step 6: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
chmod +x 06_DEVELOPMENT/solano_live_desk/scripts/run.sh
git add 06_DEVELOPMENT/solano_live_desk/scripts/run.sh \
        06_DEVELOPMENT/solano_live_desk/README.md
git commit -m "feat(sld): run script, README, live CHP verification"
```

---

## Self-Review

**Spec coverage (Phase 1 scope):**
- CHP ingest -> Tasks 2, 4. Day-partition store + archive-never-delete -> Task 3 (list_days reads archive/; no delete path exists). FastAPI /events -> Task 5. MapLibre pins + dispatch-log popups -> Task 6. Time-slider scrub-back -> Task 6 (wireSlider/render cutoff). Daily reset -> Task 3 (today_pt selects the day DB; ingest writes to the current PT day). Follow-me GPS -> Task 6 (GeolocateControl). Private bind -> Task 7 (127.0.0.1 default, EV_BIND to expose). Live proof -> Task 7.
- Deferred by design (not Phase 1): cameras, Broadcastify embeds, webcams (Phase 2); yarn linker + AI digest (Phase 3); whisper transcription (Phase 4). Each gets its own plan.

**Placeholder scan:** No TBD/TODO; every code step ships complete code; every test step shows real assertions and the exact run command + expected result.

**Type consistency:** `run_once(fetch_fn, base, day, now_iso)` signature matches Task 4 tests and Task 7 usage. `connect/upsert_event/get_events/list_days/today_pt/day_db_path` names are identical across store.py, ingest.py, api.py, and all tests. Event dict keys (`id, source, type, title, lat, lon, geo_label, body, details`) are produced in Task 2 and consumed unchanged in Tasks 3-6. Frontend reads `last_seen, lat, lon, type, geo_label, log_time, body` which the API returns verbatim from the store rows.
