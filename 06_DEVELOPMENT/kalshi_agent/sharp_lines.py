"""Sharp-line provider -- the external reference the edge engine de-vigs against.

The ONLY edge that has actually worked for us is Kalshi-vs-sharp-sportsbook
divergence (proven 2026-06-04 on the Knicks title: Kalshi 54c to BUY vs FanDuel
-134/+114 -> de-vig 55.1% fair). Model edges (crypto vol, weather sigma, research
LLM) were all bugs. So this module is the heart of the autonomous engine: it
returns a hand-verified or live "fair YES probability" for a Kalshi ticker, and
auto_edge bets the side where Kalshi is cheaper than fair (net of the maker fee).

Two sources, same output:
  1. manual override (sharp_overrides.json) -- a de-vigged number dropped in by
     hand. Zero external dependency, acts immediately, durable. PRIMARY in v1.
  2. live API (The Odds API, free tier, ODDS_API_KEY) -- auto-refreshes the
     override. Wired but optional; the override path is the proven route.
Pure stdlib so it runs on e5.
"""
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

OVERRIDES = Path(__file__).parent / "sharp_overrides.json"


def american_to_prob(odds) -> float:
    """American moneyline -> raw implied probability (still carries the vig)."""
    o = float(odds)
    return (-o) / ((-o) + 100.0) if o < 0 else 100.0 / (o + 100.0)


def devig_two_way(prob_a_raw: float, prob_b_raw: float):
    """Strip the vig from a two-outcome market. Returns (fair_a, fair_b) summing 1.
    This is the step that turns -134/+114 into a true 55.1% / 44.9%."""
    tot = prob_a_raw + prob_b_raw
    if tot <= 0:
        return None, None
    return prob_a_raw / tot, prob_b_raw / tot


def fair_from_american(odds_yes, odds_no) -> float:
    """Fair YES probability from the two American moneylines of a 2-way market."""
    fa, _ = devig_two_way(american_to_prob(odds_yes), american_to_prob(odds_no))
    return fa


def from_overrides(ticker: str):
    """Hand-verified de-vig number for a ticker, if present and not expired."""
    if not OVERRIDES.exists():
        return None
    try:
        data = json.loads(OVERRIDES.read_text())
    except Exception:
        return None
    row = data.get(ticker)
    if not isinstance(row, dict):
        return None
    exp = row.get("expires_ts")
    if exp and time.time() > float(exp):
        return None
    fp = row.get("fair_prob")
    if fp is None:
        return None
    return {"fair_prob": float(fp), "source": row.get("source", "override"),
            "fresh_ts": row.get("fresh_ts"), "books": row.get("books", 1)}


def _odds_api(sport_key: str):
    """The Odds API h2h pull (free tier). Returns list of events or None.
    Left minimal in v1 -- the override path is what the engine actually runs on;
    this is the hook to automate the refresh later (set ODDS_API_KEY)."""
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        return None
    url = ("https://api.the-odds-api.com/v4/sports/%s/odds?" % sport_key) + urllib.parse.urlencode(
        {"apiKey": key, "regions": "us", "markets": "h2h", "oddsFormat": "american"})
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(
            url, headers={"User-Agent": "ev-sharp/1.0"}), timeout=15).read())
    except Exception:
        return None


def sharp_fair(ticker: str):
    """Best available sharp fair YES-prob for a Kalshi ticker.
    Override first (durable, hand-verified); live API is a future auto-refresh.
    Returns {'fair_prob': float, 'source': str} or None."""
    ov = from_overrides(ticker)
    if ov:
        return ov
    # live API hook: needs a ticker->event mapping per series; intentionally not
    # auto-mapped in v1 so the engine never acts on an unverified guess.
    return None


def overridden_tickers():
    """All tickers with a live (non-expired) hand-verified sharp number."""
    if not OVERRIDES.exists():
        return []
    try:
        data = json.loads(OVERRIDES.read_text())
    except Exception:
        return []
    return [t for t in data if not t.startswith("_") and from_overrides(t)]
