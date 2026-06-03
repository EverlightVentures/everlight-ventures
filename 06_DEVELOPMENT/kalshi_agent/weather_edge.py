"""Weather edge -- the data edge where an AI/data pipeline genuinely beats the crowd.

The National Weather Service publishes authoritative forecast highs for free; Kalshi's
high-temp markets ("will the high in CITY be < X degrees") are priced by a sparse crowd.
We turn the NWS forecast high into P(high < threshold) using forecast-error sigma, and
compare to Kalshi's price. Divergence = a real, automatable edge (better information,
not a model hallucination). Pure stdlib; runs on e5.
"""
import json
import math
import urllib.request
from datetime import datetime, timedelta

# Kalshi high-temp series -> (lat, lon) of the NWS station Kalshi settles on
STATIONS = {
    "KXHIGHNY":   (40.7790, -73.9693),   # Central Park
    "KXHIGHLAX":  (33.9381, -118.3889),  # LAX
    "KXHIGHCHI":  (41.9603, -87.9316),   # O'Hare
    "KXHIGHMIA":  (25.7905, -80.3164),   # Miami Intl
    "KXHIGHAUS":  (30.1975, -97.6664),   # Austin-Bergstrom
    "KXHIGHDEN":  (39.8466, -104.6562),  # Denver Intl
    "KXHIGHPHIL": (39.8729, -75.2437),   # Philadelphia Intl
}
UA = {"User-Agent": "everlight-ventures-weather/1.0 (1m.rich.gee@gmail.com)"}
# same-day/next-day NWS high-temp forecast error ~ 2-4 F; use a slightly conservative sigma
DEFAULT_SIGMA = 3.5


def _get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read())


def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def forecast_high(series, target_date):
    """NWS forecast high (deg F) for a series' station on target_date 'YYYY-MM-DD'."""
    lat, lon = STATIONS[series]
    furl = _get(f"https://api.weather.gov/points/{lat},{lon}")["properties"]["forecast"]
    periods = _get(furl)["properties"]["periods"]
    for p in periods:
        if p.get("isDaytime") and p.get("startTime", "").startswith(target_date):
            return p["temperature"]
    # fallback: nearest daytime period
    days = [p for p in periods if p.get("isDaytime")]
    return days[0]["temperature"] if days else None


def prob_below(cap, fhigh, sigma=DEFAULT_SIGMA):
    """P(actual high < cap) given the forecast high (YES side of a 'high < cap' market)."""
    return _norm_cdf((cap - fhigh) / sigma)


def target_date_from_close(close_time):
    """The local high-temp day for a market that CLOSES early-AM-UTC = prior local day."""
    dt = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
    return (dt - timedelta(days=1)).strftime("%Y-%m-%d")


_MON = {"JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
        "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"}


def date_from_ticker(ticker):
    """KXHIGHDEN-26JUN04-B92.5 -> '2026-06-04' (the day being measured)."""
    import re
    m = re.search(r"-(\d{2})([A-Z]{3})(\d{2})-", ticker)
    if not m:
        return None
    yy, mon, dd = m.groups()
    return f"20{yy}-{_MON.get(mon, '01')}-{dd}"


def market_yes_prob(strike_type, floor, cap, fhigh, sigma=DEFAULT_SIGMA):
    """P(YES) for a high-temp market, reading the ACTUAL market type:
      less    -> YES = high < cap
      greater -> YES = high > floor
      between -> YES = floor < high < cap   (the narrow B buckets)
    Returns None if the type/strikes are unusable."""
    below = lambda x: prob_below(x, fhigh, sigma)
    if strike_type == "less" and cap is not None:
        return below(cap)
    if strike_type == "greater" and floor is not None:
        return 1.0 - below(floor)
    if strike_type == "between" and floor is not None and cap is not None:
        return max(0.0, below(cap) - below(floor))
    return None
