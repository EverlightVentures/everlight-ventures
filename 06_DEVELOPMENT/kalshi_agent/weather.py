#!/usr/bin/env python3
"""weather.py -- NWS forecast as the SHARP LINE for Kalshi daily high-temp markets.

ONE STRATEGY, MANY SHARP LINES (Rich 2026-06-25). DraftKings -> sports, Polymarket -> politics
(efficient, no edge), and the free National Weather Service forecast -> weather. Unlike politics,
weather markets are a DOCUMENTED retail inefficiency: casual traders misprice temperature buckets
while NWS publishes a sharp probabilistic forecast. We turn the NWS forecast high into a Normal
distribution over Kalshi's buckets and compare to the live orderbook price.

DISCIPLINE: weather edges live in sub-50% buckets, so they do NOT fit the sports gates (win-prob
floor / favorites-only). This runs as a SCANNER + PAPER LOG first -- it records (forecast, kalshi
price, bucket) so we can settle vs the realized high and PROVE NWS systematically beats the crowd
before any live capital. Forward days only (today's high may already be realized -> Kalshi has the
edge, not us).

  python3 -m kalshi_agent.weather            # scan + paper-log the edges
"""
import json
import math
import re
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

from kalshi_agent.execution.kalshi_exec import from_creds
from kalshi_agent.dataflows.kalshi_api import best_bbo

HERE = Path(__file__).parent
PAPER = HERE / "data" / "weather_paper.jsonl"
UA = {"User-Agent": "everlight-weather/1.0 (ops@everlightventures.io)"}
SIGMA = 3.0          # NWS daytime-high forecast error (deg F, ~1-2 days out). Tune from paper data.
MIN_EDGE = 0.06      # |fair - price| to flag (net of the ~2c maker fee)

# Kalshi high-temp series -> NWS point (the city's climate station). VERIFY station per city before
# trusting beyond NY (Central Park is the confirmed KXHIGHNY resolver).
CITIES = {
    "KXHIGHNY":  (40.78, -73.97, "NYC (Central Park)"),
    "KXHIGHLAX": (33.94, -118.41, "LA (LAX)"),
    "KXHIGHCHI": (41.96, -87.93, "Chicago (O'Hare)"),
    "KXHIGHMIA": (25.79, -80.29, "Miami (MIA)"),
    "KXHIGHAUS": (30.18, -97.68, "Austin (AUS)"),
    "KXHIGHDEN": (39.85, -104.66, "Denver (DEN)"),
    "KXHIGHPHIL": (39.87, -75.23, "Philadelphia (PHL)"),
}


def _gj(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read())


def _phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def nws_highs(lat, lon):
    """{forecast period name -> high F} for the daytime periods (forward forecast)."""
    try:
        p = _gj("https://api.weather.gov/points/%s,%s" % (lat, lon))
        fc = _gj(p["properties"]["forecast"])["properties"]["periods"]
        return [(pd["name"], pd["temperature"]) for pd in fc if pd.get("isDaytime")]
    except Exception:
        return []


def bucket_bounds(label):
    """'80 to 81' -> (79.5,81.5); '75 or below' -> (-inf,75.5); '84 or above' -> (83.5,inf)."""
    s = (label or "").replace("°", "").lower()
    m = re.search(r"(\d+)\s*to\s*(\d+)", s)
    if m:
        return float(m.group(1)) - 0.5, float(m.group(2)) + 0.5
    m = re.search(r"(\d+)\s*or below", s)
    if m:
        return float("-inf"), float(m.group(1)) + 0.5
    m = re.search(r"(\d+)\s*or above", s)
    if m:
        return float(m.group(1)) - 0.5, float("inf")
    return None


def bucket_prob(lo, hi, forecast, sigma=SIGMA):
    p_hi = 1.0 if hi == float("inf") else _phi((hi - forecast) / sigma)
    p_lo = 0.0 if lo == float("-inf") else _phi((lo - forecast) / sigma)
    return max(0.0, p_hi - p_lo)


def scan(creds=None, paper=True):
    k = from_creds(creds) if creds else from_creds()
    rows = []
    for series, (lat, lon, name) in CITIES.items():
        try:
            ms = k._request("GET", "/markets?status=open&limit=120&series_ticker=%s" % series).get("markets", [])
        except Exception:
            ms = []
        if not ms:
            continue
        highs = nws_highs(lat, lon)
        if not highs:
            continue
        # group markets by event-date token; skip the soonest (today -> realized-data trap)
        byday = defaultdict(list)
        for m in ms:
            tk = m.get("ticker", "")
            byday[tk.split("-")[1] if "-" in tk else "?"].append(m)
        forward_days = sorted(byday)[1:1 + len(highs)]    # tomorrow onward
        for i, day in enumerate(forward_days):
            fhigh = highs[i + 1][1] if i + 1 < len(highs) else highs[-1][1]   # map day->forecast
            for m in byday[day]:
                b = bucket_bounds(m.get("yes_sub_title"))
                if not b:
                    continue
                try:
                    yb, ya, nb, yc, nc = best_bbo(m.get("ticker"))
                except Exception:
                    yb = ya = yc = None
                if ya is None and yb is None:
                    continue
                price = ((yb + ya) / 2 / 100.0) if (yb is not None and ya is not None) else ((ya or yb) / 100.0)
                fair = bucket_prob(b[0], b[1], fhigh)
                edge = fair - price
                if abs(edge) >= MIN_EDGE:
                    rows.append({"city": name, "ticker": m.get("ticker"), "bucket": m.get("yes_sub_title"),
                                 "nws_high": fhigh, "fair": round(fair, 3), "price": round(price, 3),
                                 "edge": round(edge, 3), "depth": round(yc or 0)})
    rows.sort(key=lambda r: -abs(r["edge"]))
    if paper and rows:
        PAPER.parent.mkdir(parents=True, exist_ok=True)
        with open(PAPER, "a") as f:
            f.write(json.dumps({"ts": int(time.time()), "edges": rows}) + "\n")
    return rows


def main():
    rows = scan(None, paper=True)
    print("WEATHER edges (NWS sharp line vs Kalshi, forward days, paper-logged): %d" % len(rows))
    print("  %-22s %-14s nws  fair  price  edge   depth" % ("city", "bucket"))
    for r in rows[:20]:
        side = "BUY YES " if r["edge"] > 0 else "SELL/NO "
        print("  %-22s %-14s %3d  %4.0f%% %4.0f%% %s%+4.0f%% $%s" % (
            r["city"][:22], (r["bucket"] or "")[:14], r["nws_high"],
            r["fair"] * 100, r["price"] * 100, side, r["edge"] * 100, r["depth"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
