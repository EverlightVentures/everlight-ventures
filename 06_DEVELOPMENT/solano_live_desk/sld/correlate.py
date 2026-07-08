from __future__ import annotations

import re
from datetime import datetime, timedelta

from . import store, threat
from .geo_county import distance_mi
from .radio import extract as radio_extract

WINDOW = timedelta(minutes=30)   # two signals inside this window can be one event
TIGHT_MI = 0.3                   # very close in space + time = same event
RADIUS_MI = 1.5                  # within this + shared meaning = same event
LIVE_MIN = 15                    # lifecycle: LIVE if updated within 15 min, else REPORT

_RANK = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
_TIER = {1: "UNCONFIRMED", 2: "PROBABLE", 3: "CONFIRMED", 4: "CONFIRMED"}
_SHOTS = re.compile(r"shots?\s*fired|gunshot|11-?99|\bshooting\b", re.I)
_GSW = re.compile(r"\bgsw\b|gunshot wound|shot victim|shooting victim", re.I)


def _parse_dt(s):
    try:
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=store.PT) if dt.tzinfo is None else dt
    except Exception:  # noqa: BLE001
        return None


def lifecycle_status(last_seen: str | None, now=None) -> str:
    """LIVE while an incident is still updating, REPORT once it goes quiet."""
    now = now or datetime.now(store.PT)
    dt = _parse_dt(last_seen or "")
    if dt is None:
        return "REPORT"
    return "LIVE" if (now - dt) <= timedelta(minutes=LIVE_MIN) else "REPORT"


class _UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def _signal(ev: dict) -> dict:
    text = " ".join(str(v) for v in (ev.get("type"), ev.get("title"), ev.get("body")) if v)
    units, codes = radio_extract(text)
    tags = set()
    if _SHOTS.search(text):
        tags.add("gunshot")
    if _GSW.search(text):
        tags.add("gsw")
    return {
        "id": ev["id"], "source": ev.get("source"), "lat": ev.get("lat"), "lon": ev.get("lon"),
        "t": _parse_dt(ev.get("last_seen") or ev.get("first_seen") or ""),
        "units": set(units), "codes": {c for c, _ in codes}, "tags": tags,
        "sev": threat.severity(text), "ev": ev,
    }


def _linked(a: dict, b: dict) -> bool:
    if a["t"] is None or b["t"] is None:
        return False
    if abs((a["t"] - b["t"]).total_seconds()) > WINDOW.total_seconds():
        return False
    if a["units"] & b["units"]:                       # same responding unit = same call
        return True
    if a["lat"] is None or b["lat"] is None:
        return False
    d = distance_mi((a["lat"], a["lon"]), (b["lat"], b["lon"]))
    if d <= TIGHT_MI:
        return True
    shared = bool(a["codes"] & b["codes"]) or bool(a["tags"] & b["tags"])
    return d <= RADIUS_MI and shared


def _cluster(sigs: list[dict]) -> list[list[dict]]:
    n = len(sigs)
    uf = _UF(n)
    for i in range(n):
        for j in range(i + 1, n):
            if _linked(sigs[i], sigs[j]):
                uf.union(i, j)
    groups: dict[int, list[dict]] = {}
    for i, s in enumerate(sigs):
        groups.setdefault(uf.find(i), []).append(s)
    return list(groups.values())


def _infer_gunshot(members: list[dict]) -> bool:
    """Shots-fired + INDEPENDENT corroboration (a GSW patient, a 3+ unit surge, or a
    second source also reporting shots) = a gunshot incident, no ShotSpotter needed."""
    shots = [m for m in members if "gunshot" in m["tags"]]
    if not shots:
        return False
    gsw = {m["source"] for m in members if "gsw" in m["tags"]}
    units = set().union(*[m["units"] for m in members]) if members else set()
    shot_sources = {m["source"] for m in shots}
    return bool(gsw) or len(units) >= 3 or len(shot_sources) >= 2


def _confidence(sources: set, units: set, inferred: bool) -> float:
    n = len(sources)
    base = {1: 0.30, 2: 0.62, 3: 0.80}.get(n, 0.90 if n >= 4 else 0.30)
    if len(units) >= 3:
        base += 0.05
    if inferred:
        base = max(base, 0.85)
    return round(min(0.99, base), 2)


def correlate(events: list[dict], now=None) -> list[dict]:
    """Fuse raw events into confidence-scored incidents. Surfaces only the ones
    worth a command-center's attention (multi-source, inferred, or high-severity)."""
    now = now or datetime.now(store.PT)
    sigs = [_signal(e) for e in events if e.get("lat") is not None]
    out: list[dict] = []
    for c in _cluster(sigs):
        sources = {s["source"] for s in c}
        units = set().union(*[s["units"] for s in c]) if c else set()
        inferred = _infer_gunshot(c)
        sev = max((s["sev"] for s in c), key=lambda x: _RANK[x])
        if inferred:
            sev = "CRITICAL"
        lat = sum(s["lat"] for s in c) / len(c)
        lon = sum(s["lon"] for s in c) / len(c)
        anchor = min(c, key=lambda s: (s["t"] or now))
        last = max((s["t"] for s in c if s["t"]), default=now)
        timeline = []
        for s in sorted(c, key=lambda s: (s["t"] or now)):
            ts = s["t"].strftime("%-I:%M %p") if s["t"] else "?"
            timeline.append(f"[{ts}] ({s['source']}) {(s['ev'].get('type') or '')[:44]}")
        out.append({
            "id": f"corr:{anchor['id']}",
            "source": "correlated",
            "type": "GUNSHOT (inferred)" if inferred else (anchor["ev"].get("type") or "Incident"),
            "title": f"{'GUNSHOT ' if inferred else ''}{len(c)}-source incident",
            "lat": lat, "lon": lon,
            "geo_label": anchor["ev"].get("geo_label"),
            "severity": sev,
            "confidence": _confidence(sources, units, inferred),
            "tier": _TIER[min(len(sources), 4)],
            "sources": sorted(sources),
            "members": [s["id"] for s in c],
            "units": sorted(units),
            "inferred": inferred,
            "status": lifecycle_status(last.isoformat(), now),
            "body": "\n".join(timeline),
            "last_seen": last.isoformat(),
        })
    return [i for i in out
            if len(i["sources"]) >= 2 or i["inferred"] or i["severity"] in ("CRITICAL", "HIGH")]
