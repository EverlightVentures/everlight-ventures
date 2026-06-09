#!/usr/bin/env python3
"""daily_research.py -- the AUTONOMOUS multi-sport daily edge-finder.

Runs on a cron at optimal times. For every game on the day's slate (NBA, MLB, NHL...)
it derives a SHARP win-probability from the live book line (ESPN's free API, no key,
no signup), maps the game to its Kalshi ticker, and writes a FRESH sharp number into
sharp_overrides.json. The auto_edge engine (15-min cron) then places maker bids on any
market where Kalshi diverges enough to clear the net-edge floor -- zero human in loop.

ESPN's `details` field is sport-dependent and we read both shapes:
  * basketball -> point spread ("NY -1.5"). NBA final margin ~Normal(spread, 12),
    so P(fav) = Phi(spread/12).
  * baseball/hockey -> favorite moneyline ("SEA -122"). raw = implied(ML); we de-vig
    with an assumed 2-way hold: fair_fav = raw / 1.045.

Matching is by Kalshi market DISCOVERY (pull the open series, match on date token +
both team abbrevs + the team suffix) so we never have to guess the time component some
tickers carry. Unmatched games are safely skipped, never mis-bet.

  python3 -m kalshi_agent.daily_research            # research all sports + write overrides
  python3 -m kalshi_agent.daily_research --quiet     # no Slack ping
"""
import json
import math
import re
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from kalshi_agent.dataflows.kalshi_api import best_bbo
from kalshi_agent.hunt_kalshi import _markets_by_series

HERE = Path(__file__).parent
OVERRIDES = HERE / "sharp_overrides.json"
RESEARCH_LOG = HERE / "data" / "daily_research.jsonl"
UA = {"User-Agent": "everlight-ventures-research/1.0"}
_MON = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
HOLD = 1.045   # assumed 2-way book overround, for single-line moneyline de-vig

# ESPN abbreviation -> Kalshi abbreviation. Identity is the fallback (most match);
# only the known mismatches need an entry. Unmatched teams just get skipped safely.
ABBR_FIX = {
    # NBA
    "GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA", "WSH_NBA": "WAS",
    # MLB
    "CHW": "CWS", "AZ": "ARI",
    # NHL (ESPN short -> Kalshi standard)
    "TB": "TBL", "LA": "LAK", "NJ": "NJD", "SJ": "SJS",
}

SPORTS = {
    "nba": {"espn": "basketball/nba", "series": "KXNBAGAME", "method": "spread", "sigma": 12.0},
    "mlb": {"espn": "baseball/mlb", "series": "KXMLBGAME", "method": "moneyline"},
    "nhl": {"espn": "hockey/nhl", "series": "KXNHLGAME", "method": "moneyline"},
}


def _get_json(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read())


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def american_to_prob(odds):
    o = float(odds)
    return (-o) / ((-o) + 100.0) if o < 0 else 100.0 / (o + 100.0)


def _ymd_to_kalshi(ymd):
    """ESPN query date 'YYYYMMDD' (US game day) -> Kalshi token '26JUN10'."""
    return "%s%s%s" % (ymd[2:4], _MON[int(ymd[4:6])], ymd[6:8])


def _kalshi_abbr(espn_abbr):
    return ABBR_FIX.get(espn_abbr, espn_abbr)


def _parse_details(s):
    """'NY -1.5' -> ('NY','spread',1.5); 'SEA -122' -> ('SEA','ml',-122);
    'EVEN'/'PK' -> (None,'spread',0.0); junk -> (None,None,None)."""
    if not s:
        return None, None, None
    s = s.strip().upper()
    if s in ("EVEN", "PK", "PICK"):
        return None, "spread", 0.0
    m = re.match(r"^([A-Z]{2,4})\s*([+-]?\d+(?:\.\d+)?)$", s)
    if not m:
        return None, None, None
    team, num = m.group(1), float(m.group(2))
    kind = "ml" if abs(num) >= 100 else "spread"
    return team, kind, num


def _fair_favorite(method, kind, num, sigma):
    """Favorite's de-vigged win prob from the parsed book line."""
    if kind == "spread":
        return _norm_cdf(abs(num) / (sigma or 12.0))
    # moneyline: favorite is the negative line; de-vig by the assumed hold
    return min(0.97, max(0.50, american_to_prob(num) / HOLD))


def espn_slate(cfg, days=2):
    out = []
    base = datetime.now(timezone.utc)
    for d in range(days):
        ymd = (base + timedelta(days=d)).strftime("%Y%m%d")
        ktoken = _ymd_to_kalshi(ymd)
        try:
            data = _get_json("https://site.api.espn.com/apis/site/v2/sports/%s/scoreboard?dates=%s" % (cfg["espn"], ymd))
        except Exception:
            continue
        for e in data.get("events", []):
            comp = (e.get("competitions") or [{}])[0]
            cs = comp.get("competitors", [])
            home = next((c for c in cs if c.get("homeAway") == "home"), None)
            away = next((c for c in cs if c.get("homeAway") == "away"), None)
            odds = comp.get("odds") or []
            if not home or not away or not odds:
                continue
            ha = _kalshi_abbr((home.get("team") or {}).get("abbreviation") or "")
            aa = _kalshi_abbr((away.get("team") or {}).get("abbreviation") or "")
            fav_espn, kind, num = _parse_details(odds[0].get("details"))
            if kind is None:
                continue
            fav_p = _fair_favorite(cfg["method"], kind, num, cfg.get("sigma"))
            fav_k = _kalshi_abbr(fav_espn) if fav_espn else None
            home_p = fav_p if fav_k == ha else (1 - fav_p if fav_k == aa else 0.5)
            out.append({"date": ktoken, "home": ha, "away": aa, "name": e.get("name"),
                        "fair_home": round(home_p, 4), "fair_away": round(1 - home_p, 4),
                        "book": (odds[0].get("provider") or {}).get("name", "book")})
    return out


def _find_ticker(markets, date_tok, away_k, home_k, team_k):
    for m in markets:
        t = m.get("ticker", "")
        parts = t.split("-")
        if len(parts) < 3:
            continue
        mid, suf = parts[1], parts[-1]
        if mid.startswith(date_tok) and away_k in mid and home_k in mid and suf == team_k:
            return t
    return None


def research(write=True):
    existing = {}
    if OVERRIDES.exists():
        try:
            existing = json.loads(OVERRIDES.read_text())
        except Exception:
            existing = {}
    rows, ngames = [], 0
    for sport, cfg in SPORTS.items():
        slate = espn_slate(cfg)
        if not slate:
            continue
        try:
            kmkts = _markets_by_series(cfg["series"])
        except Exception:
            kmkts = []
        for g in slate:
            ngames += 1
            for team, p in ((g["home"], g["fair_home"]), (g["away"], g["fair_away"])):
                tk = _find_ticker(kmkts, g["date"], g["away"], g["home"], team)
                if not tk:
                    continue
                try:
                    yb, ya, nb, yc, nc = best_bbo(tk)
                except Exception:
                    yb = ya = None
                row = {"sport": sport, "ticker": tk, "team": team, "fair_prob": round(p, 4),
                       "kalshi_ask": ya, "game": g["name"], "book": g["book"]}
                if ya is not None:
                    row["edge_buy"] = round(p - ya / 100.0, 4)
                rows.append(row)
                if write and ya is not None:
                    existing[tk] = {"fair_prob": round(p, 4),
                                    "source": "%s %s->prob (daily_research)" % (g["book"], sport),
                                    "expires_ts": int(time.time()) + 18 * 3600,
                                    "fresh_ts": int(time.time())}
    if write:
        OVERRIDES.write_text(json.dumps(existing, indent=2))
        RESEARCH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(RESEARCH_LOG, "a") as f:
            f.write(json.dumps({"ts": int(time.time()), "games": ngames, "rows": rows}) + "\n")
    return {"games": ngames, "rows": rows}


def main():
    import sys
    quiet = "--quiet" in sys.argv
    r = research(write=True)
    print("=" * 64)
    print("  DAILY RESEARCH", time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "-- games:", r["games"])
    print("=" * 64)
    edges = []
    for row in sorted(r["rows"], key=lambda x: -(x.get("edge_buy") or -9)):
        eb = row.get("edge_buy")
        mark = ""
        if eb is not None and eb >= 0.025:
            mark = "  <== EDGE +%.1f%%" % (eb * 100)
            edges.append(row)
        if eb is not None and (eb >= 0.0 or mark):
            print("  %-4s %-30s fair %.0f%% ask %sc edge %+.1f%%%s" % (
                row["sport"].upper(), row["ticker"][:30], row["fair_prob"] * 100,
                row.get("kalshi_ask"), (eb or 0) * 100, mark))
    msg = "Daily research: %d games across %d sports, %d edge(s)%s. auto_edge places any that clear the floor." % (
        r["games"], len(SPORTS), len(edges),
        (" -> " + ", ".join(e["ticker"] for e in edges)) if edges else " (efficient slate, sitting out)")
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
