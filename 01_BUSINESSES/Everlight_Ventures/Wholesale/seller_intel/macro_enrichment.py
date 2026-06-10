"""
macro_enrichment.py -- the puller that fills parser's macro_context slots.

Walks Wholesale/owner_downloads/parsed/*.json. For each parcel, queries
free public APIs for catalysts in the property's county and date range,
populates the parcel's macro_context dict, and appends pitch hooks loaded
from macro_pitch_copy.yaml. Writes back to the JSON in place.

Sources (network-first per feedback_network_first_not_clone_first):
  - NOAA NWS alerts archive (api.weather.gov)
  - USGS earthquake feed (earthquake.usgs.gov)
  - InciWeb (wildfires, GeoJSON feed)
  - GDELT GKG (gdeltproject.org -- ToS-safe public news catalog at scale,
    chosen instead of Google News scrape per Priya compliance memo)

Usage:
    python3 macro_enrichment.py              # process all parsed JSONs
    python3 macro_enrichment.py --parcel ID  # one parcel
    python3 macro_enrichment.py --dry-run    # show would-change, no write

Idempotent: re-running on a parcel that's been enriched in the last 7
days skips it. Force re-enrich with --force.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen, Request


WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
PARSED_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/parsed"
PITCH_COPY = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/seller_intel/macro_pitch_copy.yaml"

UA = "EverlightIntel/1.0 (macro_enrichment)"
TIMEOUT = 10
ENRICHMENT_TTL_DAYS = 7


# ---------------------------------------------------------------------------
# Simple HTTP helper (sync, stdlib only -- module runs from cron)
# ---------------------------------------------------------------------------
def _http_get(url: str, accept: str = "application/json") -> tuple[int, str]:
    req = Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"err:{e}"


# ---------------------------------------------------------------------------
# Pitch copy loader (network-first inline -- the YAML lives on disk but
# this is a thin parser; full YAML loader is optional dep)
# ---------------------------------------------------------------------------
def _load_pitch_copy() -> dict:
    """Read macro_pitch_copy.yaml. If pyyaml is installed use it; else
    fall back to a minimal hardcoded copy set."""
    if not PITCH_COPY.exists():
        return _hardcoded_pitch_copy()
    try:
        import yaml  # type: ignore
        with open(PITCH_COPY) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return _hardcoded_pitch_copy()


def _hardcoded_pitch_copy() -> dict:
    """Minimal fallback so the puller works without pyyaml installed."""
    return {
        "weather_event": {"piper": ["FALLBACK: storm-affected county pitch -- generic"]},
        "earthquake": {"piper": ["FALLBACK: seismic-area pitch -- generic"]},
        "wildfire": {"piper": ["FALLBACK: wildfire-area pitch -- generic"]},
        "news_catalyst": {"piper": ["FALLBACK: local-news catalyst pitch -- generic"]},
        "infrastructure_event": {"piper": ["FALLBACK: infrastructure-change pitch -- generic"]},
    }


def _pick_phrasing(copy: dict, category: str, persona: str = "piper") -> str | None:
    """Random phrasing for category x persona. Returns None if no copy available."""
    cat = copy.get(category, {})
    if not isinstance(cat, dict):
        return None
    persona_list = cat.get(persona) or cat.get("piper") or next(iter(cat.values()), [])
    if not persona_list:
        return None
    return random.choice(persona_list)


# ---------------------------------------------------------------------------
# Source queries
# ---------------------------------------------------------------------------
def _noaa_weather_alerts(state: str) -> dict | None:
    """NOAA NWS active alerts for a state. Returns the most-severe recent alert.
    state = 2-letter postal code (e.g. 'TN', 'TX')."""
    if not state or len(state) != 2:
        return None
    url = f"https://api.weather.gov/alerts/active/area/{state.upper()}"
    status, body = _http_get(url)
    if status != 200:
        return None
    try:
        data = json.loads(body)
        features = data.get("features", [])
        if not features:
            return None
        # Pick highest severity by NWS rank
        severity_rank = {"Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1, "Unknown": 0}
        ranked = sorted(features, key=lambda f: severity_rank.get(
            f.get("properties", {}).get("severity", "Unknown"), 0), reverse=True)
        top = ranked[0].get("properties", {})
        return {
            "event": top.get("event", ""),
            "severity": top.get("severity", ""),
            "headline": top.get("headline", "")[:200],
            "effective": top.get("effective", "")[:10],
            "areas": top.get("areaDesc", "")[:120],
        }
    except (ValueError, KeyError):
        return None


def _usgs_earthquakes(lat: float | None, lon: float | None, radius_km: int = 50) -> dict | None:
    """USGS quakes within radius_km of (lat, lon), M3+, last 90 days.
    Returns most recent significant quake or None."""
    if lat is None or lon is None:
        return None
    start = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
    url = (f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
           f"&starttime={start}&minmagnitude=3"
           f"&latitude={lat}&longitude={lon}&maxradiuskm={radius_km}")
    status, body = _http_get(url)
    if status != 200:
        return None
    try:
        data = json.loads(body)
        features = data.get("features", [])
        if not features:
            return None
        top = features[0].get("properties", {})
        return {
            "magnitude": top.get("mag"),
            "place": top.get("place", ""),
            "time": datetime.fromtimestamp(top.get("time", 0) / 1000, timezone.utc).isoformat()[:10] if top.get("time") else "",
            "url": top.get("url", ""),
        }
    except (ValueError, KeyError):
        return None


def _inciweb_wildfire(state: str) -> dict | None:
    """InciWeb active fires in a state. InciWeb's GeoJSON feed is at
    inciweb.nwcg.gov; we filter by state name in the incident data."""
    if not state:
        return None
    url = "https://inciweb.nwcg.gov/incidents/rss.xml"  # RSS is more stable than the JSON API
    status, body = _http_get(url, accept="application/rss+xml")
    if status != 200:
        return None
    import re as _re
    # State names from postal codes (subset of our 8 markets)
    state_full = {
        "TN": "Tennessee", "TX": "Texas", "FL": "Florida", "GA": "Georgia",
        "OH": "Ohio", "AZ": "Arizona", "MO": "Missouri", "NV": "Nevada",
        "CA": "California", "MS": "Mississippi",
    }.get(state.upper())
    if not state_full:
        return None
    items = _re.findall(r"<item>(.*?)</item>", body, _re.S)
    for item in items[:20]:
        if state_full in item:
            title_m = _re.search(r"<title>([^<]+)</title>", item)
            link_m = _re.search(r"<link>([^<]+)</link>", item)
            if title_m:
                return {
                    "incident": title_m.group(1).strip(),
                    "state": state_full,
                    "url": link_m.group(1).strip() if link_m else "",
                }
    return None


def _gdelt_news(county_query: str) -> dict | None:
    """GDELT GKG (Global Knowledge Graph) -- county-level news catalyst search.
    Uses the GDELT DOC 2.0 API which is free and ToS-safe.

    Phone-side observation 2026-05-15: GDELT sometimes returns HTTP 200 with
    an empty body (likely rate limit / CDN ghosting). We log that distinctly
    so the enrichment doesn't silently zero out -- operator sees the
    degraded source instead of assuming "no news catalysts exist."
    """
    if not county_query:
        return None
    url = (f"https://api.gdeltproject.org/api/v2/doc/doc?"
           f"query={quote(county_query)}%20sourcecountry:US&mode=ArtList&maxrecords=5&format=json")
    status, body = _http_get(url)
    if status != 200:
        return {"_degraded": f"gdelt_http_{status}"}
    if not body or not body.strip():
        return {"_degraded": "gdelt_empty_body"}
    try:
        data = json.loads(body)
        articles = data.get("articles", [])
        if not articles:
            return None
        # Filter to last 30 days
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y%m%d")
        recent = [a for a in articles if a.get("seendate", "0")[:8] >= cutoff]
        if not recent:
            return None
        top = recent[0]
        return {
            "title": top.get("title", "")[:200],
            "url": top.get("url", ""),
            "domain": top.get("domain", ""),
            "seendate": top.get("seendate", "")[:8],
        }
    except ValueError:
        return {"_degraded": "gdelt_json_parse"}


def _county_from_property(lead: dict) -> str:
    """Best-effort county derivation from parcel data. Shelby County for our
    Memphis core; otherwise derive from owner_mailing_state + property city
    text. Returns 'Shelby County TN' style for GDELT queries."""
    state = lead.get("owner_mailing_state") or "TN"
    city = "Memphis"  # Shelby Assessor records are all Shelby County
    if state.upper() == "TN":
        return f"Shelby County Tennessee"
    return f"{city} {state}"


# ---------------------------------------------------------------------------
# Main enrichment pass
# ---------------------------------------------------------------------------
def _is_stale(lead: dict, force: bool = False) -> bool:
    if force:
        return True
    macro = lead.get("macro_context", {}) or {}
    enriched_at = macro.get("enriched_at")
    if not enriched_at:
        return True
    try:
        enriched_dt = datetime.fromisoformat(enriched_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - enriched_dt) > timedelta(days=ENRICHMENT_TTL_DAYS)
    except (ValueError, AttributeError):
        return True


def enrich_parcel(path: Path, pitch_copy: dict, dry_run: bool = False,
                  force: bool = False) -> dict:
    """Enrich one parsed parcel JSON. Returns summary of what changed."""
    try:
        lead = json.loads(path.read_text())
    except Exception as e:
        return {"path": str(path), "ok": False, "error": str(e)[:120]}

    if not _is_stale(lead, force=force):
        return {"path": path.name, "ok": True, "skipped": "recent", "changes": []}

    # Default macro_context if missing (parser may not have written it for old JSONs)
    macro = lead.setdefault("macro_context", {
        "weather_event": None, "earthquake": None, "wildfire": None,
        "news_catalyst": None, "infrastructure_event": None,
        "enrichment_status": "pending", "enriched_at": None,
    })

    state = (lead.get("owner_mailing_state") or "TN").upper()
    changes: list[str] = []
    new_hooks: list[str] = []

    # Weather (state-level NOAA)
    weather = _noaa_weather_alerts(state)
    if weather:
        macro["weather_event"] = weather
        changes.append(f"weather_event: {weather['event']} ({weather['severity']})")
        phrasing = _pick_phrasing(pitch_copy, "weather_event")
        if phrasing:
            new_hooks.append(phrasing)

    # Earthquake (lat/lon if we had it; assessor doesn't give us geo
    # directly, so we fall back to Shelby County centroid for TN parcels)
    # TODO: geocode property_address_full once we wire a Nominatim cache.
    lat, lon = None, None
    if state == "TN":  # Shelby County centroid
        lat, lon = 35.1175, -89.9714
    elif state == "TX":  # Dallas-Fort Worth centroid
        lat, lon = 32.7767, -96.7970
    if lat is not None:
        quake = _usgs_earthquakes(lat, lon)
        if quake and quake.get("magnitude", 0) and quake["magnitude"] >= 3:
            macro["earthquake"] = quake
            changes.append(f"earthquake: M{quake['magnitude']} at {quake.get('place','')}")
            phrasing = _pick_phrasing(pitch_copy, "earthquake")
            if phrasing:
                new_hooks.append(phrasing)

    # Wildfire (state-level InciWeb)
    fire = _inciweb_wildfire(state)
    if fire:
        macro["wildfire"] = fire
        changes.append(f"wildfire: {fire['incident']}")
        phrasing = _pick_phrasing(pitch_copy, "wildfire")
        if phrasing:
            new_hooks.append(phrasing)

    # News catalyst (county-level via GDELT)
    county_query = _county_from_property(lead)
    news = _gdelt_news(county_query)
    if news and not news.get("_degraded"):
        macro["news_catalyst"] = news
        changes.append(f"news_catalyst: {news['title'][:60]}...")
        phrasing = _pick_phrasing(pitch_copy, "news_catalyst")
        if phrasing:
            new_hooks.append(phrasing)
    elif news and news.get("_degraded"):
        # Source-degraded: record in macro_context so operator sees it,
        # but don't treat as a hit
        macro.setdefault("_source_status", {})["gdelt"] = news["_degraded"]

    # Infrastructure: no clean free API; placeholder slot (FHWA + city planning
    # require state-specific scrapers, queued as separate build).
    # macro["infrastructure_event"] stays None for now.

    macro["enrichment_status"] = "enriched"
    macro["enriched_at"] = datetime.now(timezone.utc).isoformat()

    # Merge new hooks into pitch_hooks (dedup; preserve order)
    existing_hooks = lead.get("pitch_hooks", []) or []
    for h in new_hooks:
        if h not in existing_hooks:
            existing_hooks.append(h)
    lead["pitch_hooks"] = existing_hooks
    lead["signal_count"] = len(lead.get("distress_signals", []) or []) + len(new_hooks)

    # Recompute outreach_priority including macro hits
    macro_hits = sum(1 for k in ("weather_event", "earthquake", "wildfire", "news_catalyst")
                     if macro.get(k))
    total_signals = len(lead.get("distress_signals", []) or []) + macro_hits
    lead["outreach_priority"] = (
        "high" if total_signals >= 3
        else "medium" if total_signals >= 1
        else "low"
    )

    if not dry_run:
        path.write_text(json.dumps(lead, indent=2, default=str))

    return {"path": path.name, "ok": True, "changes": changes,
            "new_hooks": len(new_hooks), "macro_hits": macro_hits}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parcel", help="Process one parcel ID (matches filename)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true", help="Re-enrich even if recent")
    args = p.parse_args()

    if not PARSED_DIR.exists():
        print(f"PARSED_DIR not found: {PARSED_DIR}", file=sys.stderr)
        sys.exit(1)

    pitch_copy = _load_pitch_copy()

    if args.parcel:
        targets = [PARSED_DIR / f"{args.parcel}.json"]
        if not targets[0].exists():
            print(f"Parcel not found: {targets[0]}", file=sys.stderr)
            sys.exit(1)
    else:
        targets = sorted(PARSED_DIR.glob("*.json"))

    print(f"Enriching {len(targets)} parcels (dry_run={args.dry_run}, force={args.force})")
    results = []
    for t in targets:
        r = enrich_parcel(t, pitch_copy, dry_run=args.dry_run, force=args.force)
        results.append(r)
        if r.get("changes"):
            print(f"  {r['path']}: {len(r['changes'])} hits, +{r.get('new_hooks', 0)} hooks")
            for c in r["changes"]:
                print(f"    - {c}")
        elif r.get("skipped"):
            pass  # quiet on no-change
        elif not r.get("ok"):
            print(f"  ERR {r['path']}: {r.get('error')}")

        # Polite delay between parcels -- public APIs prefer ~1 RPS
        time.sleep(0.5)

    enriched = sum(1 for r in results if r.get("ok") and r.get("changes"))
    skipped = sum(1 for r in results if r.get("skipped"))
    errs = sum(1 for r in results if not r.get("ok"))
    print(f"\nDone. {enriched} enriched, {skipped} skipped (recent), {errs} errors")


if __name__ == "__main__":
    main()
