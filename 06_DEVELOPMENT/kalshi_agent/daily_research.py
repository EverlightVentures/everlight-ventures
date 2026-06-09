#!/usr/bin/env python3
"""daily_research.py -- the AUTONOMOUS daily edge-finder.

Runs on a cron at optimal times. For the day's sports slate it derives a SHARP
win-probability from the live book line (ESPN's free API -> spread -> prob, no key,
no signup), maps each game to its Kalshi ticker, and writes a FRESH sharp number
into sharp_overrides.json. The auto_edge engine (15-min cron) then places maker bids
on any market where Kalshi diverges enough to clear the net-edge floor -- zero human
in the loop. Every run logs a slate summary + a Slack ping so Rich SEES the research
even on no-edge days.

WHY spread->prob: ESPN's scoreboard reliably carries the spread (e.g. "NY -1.5") for
every game; moneylines are spotty. NBA final margins are ~Normal(spread, 12), so
P(favorite wins) = Phi(spread/12). This is a well-validated sharp anchor and needs
exactly one free API call per sport. (A multi-book de-vig via The Odds API is a later
upgrade if we add a key.)

  python3 -m kalshi_agent.daily_research            # research + write fresh overrides
  python3 -m kalshi_agent.daily_research --quiet     # same, no Slack ping
"""
import json
import math
import re
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from kalshi_agent.dataflows.kalshi_api import best_bbo
from kalshi_agent import sharp_lines

HERE = Path(__file__).parent
OVERRIDES = HERE / "sharp_overrides.json"
RESEARCH_LOG = HERE / "data" / "daily_research.jsonl"
SIGMA = 12.0  # NBA final-margin standard deviation (points)
UA = {"User-Agent": "everlight-ventures-research/1.0"}
_MON = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# ESPN team abbreviation -> Kalshi team abbreviation (only the ones that differ +
# the full set so any NBA game maps cleanly).
ESPN_TO_KALSHI = {
    "ATL": "ATL", "BOS": "BOS", "BKN": "BKN", "CHA": "CHA", "CHI": "CHI", "CLE": "CLE",
    "DAL": "DAL", "DEN": "DEN", "DET": "DET", "GS": "GSW", "HOU": "HOU", "IND": "IND",
    "LAC": "LAC", "LAL": "LAL", "MEM": "MEM", "MIA": "MIA", "MIL": "MIL", "MIN": "MIN",
    "NO": "NOP", "NY": "NYK", "OKC": "OKC", "ORL": "ORL", "PHI": "PHI", "PHX": "PHX",
    "POR": "POR", "SA": "SAS", "SAC": "SAC", "TOR": "TOR", "UTAH": "UTA", "WSH": "WAS",
}


def _get_json(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read())


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def prob_from_spread(spread_favorite):
    """P(favorite wins) given the points they are favored by. spread_favorite > 0."""
    return _norm_cdf(spread_favorite / SIGMA)


def _ymd_to_kalshi(ymd):
    """ESPN query date 'YYYYMMDD' (the US game day) -> Kalshi token '26JUN10'.
    Kalshi NBA tickers use the US calendar date, NOT the UTC timestamp of tipoff
    (an 8:30pm ET game is already the next UTC day), so we key off the queried day."""
    return "%s%s%s" % (ymd[2:4], _MON[int(ymd[4:6])], ymd[6:8])


def espn_slate(sport_path="basketball/nba", days=2):
    """The day's games with a parsed sharp spread. Returns list of dicts with the
    home/away Kalshi abbrevs, the favorite, and the favorite's spread."""
    out = []
    base = datetime.now(timezone.utc)
    for d in range(days):
        ymd = (base + timedelta(days=d)).strftime("%Y%m%d")
        ktoken = _ymd_to_kalshi(ymd)
        try:
            data = _get_json("https://site.api.espn.com/apis/site/v2/sports/%s/scoreboard?dates=%s" % (sport_path, ymd))
        except Exception:
            continue
        for e in data.get("events", []):
            comp = (e.get("competitions") or [{}])[0]
            cs = comp.get("competitors", [])
            home = next((c for c in cs if c.get("homeAway") == "home"), None)
            away = next((c for c in cs if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            ha = ESPN_TO_KALSHI.get((home.get("team") or {}).get("abbreviation"))
            aa = ESPN_TO_KALSHI.get((away.get("team") or {}).get("abbreviation"))
            if not ha or not aa:
                continue
            odds = comp.get("odds") or []
            if not odds:
                continue
            details = odds[0].get("details")  # e.g. "NY -1.5" or "EVEN"
            fav_espn, spread = _parse_spread(details)
            if spread is None:
                continue
            fav_kalshi = ESPN_TO_KALSHI.get(fav_espn) if fav_espn else None
            out.append({"date": ktoken, "home": ha, "away": aa,
                        "name": e.get("name"), "fav": fav_kalshi, "spread": spread,
                        "book": (odds[0].get("provider") or {}).get("name", "book")})
    return out


def _parse_spread(details):
    """'NY -1.5' -> ('NY', 1.5); 'EVEN'/'PK' -> (None, 0.0); else (None, None)."""
    if not details:
        return None, None
    s = details.strip().upper()
    if s in ("EVEN", "PK", "PICK"):
        return None, 0.0
    m = re.match(r"^([A-Z]{2,4})\s*-?\s*(\d+(?:\.\d+)?)$", s)
    if not m:
        return None, None
    return m.group(1), float(m.group(2))


def research(write=True):
    """Derive sharp probs for the slate, write fresh overrides, return the summary."""
    slate = espn_slate()
    fresh = {"_note": sharp_lines.from_overrides and "auto-written by daily_research"}
    # preserve the human note + any still-valid manual overrides
    existing = {}
    if OVERRIDES.exists():
        try:
            existing = json.loads(OVERRIDES.read_text())
        except Exception:
            existing = {}
    rows = []
    for g in slate:
        if g["fav"]:
            fav_p = prob_from_spread(g["spread"])
        else:
            fav_p = 0.5
        # per-side fair prob
        home_p = fav_p if g["fav"] == g["home"] else (1 - fav_p)
        for team, p in ((g["home"], home_p), (g["away"], 1 - home_p)):
            tk = "KXNBAGAME-%s%s%s-%s" % (g["date"], g["away"], g["home"], team)
            try:
                yb, ya, nb, yc, nc = best_bbo(tk)
            except Exception:
                yb = ya = None
            row = {"ticker": tk, "team": team, "fair_prob": round(p, 4),
                   "kalshi_bid": yb, "kalshi_ask": ya, "game": g["name"], "book": g["book"],
                   "spread": g["spread"], "fav": g["fav"]}
            if ya is not None:
                row["edge_buy"] = round(p - ya / 100.0, 4)
            rows.append(row)
            if write and ya is not None:
                existing[tk] = {"fair_prob": round(p, 4),
                                "source": "%s spread->prob (daily_research)" % g["book"],
                                "expires_ts": int(time.time()) + 18 * 3600,
                                "fresh_ts": int(time.time())}
    if write:
        OVERRIDES.write_text(json.dumps(existing, indent=2))
        RESEARCH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(RESEARCH_LOG, "a") as f:
            f.write(json.dumps({"ts": int(time.time()), "games": len(slate), "rows": rows}) + "\n")
    return {"games": len(slate), "rows": rows}


def main():
    import sys
    quiet = "--quiet" in sys.argv
    r = research(write=True)
    print("=" * 60)
    print("  DAILY RESEARCH", time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "-- games:", r["games"])
    print("=" * 60)
    edges = []
    for row in r["rows"]:
        eb = row.get("edge_buy")
        mark = ""
        if eb is not None and eb >= 0.025:
            mark = "  <== EDGE +%.1f%%" % (eb * 100)
            edges.append(row)
        print("  %-30s fair %.0f%%  kalshi_ask %sc%s" % (
            row["ticker"][:30], row["fair_prob"] * 100, row.get("kalshi_ask"), mark))
    msg = "Daily research: %d games, %d edge(s) found%s. auto_edge will place any that clear the floor." % (
        r["games"], len(edges), (" -> " + ", ".join(e["ticker"] for e in edges)) if edges else "")
    print("\n  " + msg)
    if not quiet:
        try:
            from kalshi_agent.auto_edge import notify
            notify(msg)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
