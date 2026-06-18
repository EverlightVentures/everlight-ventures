#!/usr/bin/env python3
"""daily_research.py -- the AUTONOMOUS multi-sport daily edge-finder.

Cron'd at 30-min intervals. For every game on the day's slate it derives a SHARP
win-probability from the live book line (ESPN's free API, no key) and writes a FRESH
sharp number into sharp_overrides.json. auto_edge (15-min cron) then places bets on
any market where Kalshi lags the book enough to clear the net-edge floor -- and, per
Rich (2026-06-09), a FRESH big gap is treated as opportunity (more gap = more margin),
not dismissed as a bug.

Handles three market shapes off ESPN's `details`/`drawOdds`:
  * spread2  (NBA): "NY -1.5" -> P(fav)=Phi(spread/12).
  * ml2 (MLB/NHL/tennis): "SEA -122" -> de-vig one line by the assumed 2-way hold.
  * soccer3  (World Cup): home ML ("MEX -235") + draw ML -> de-vig the full W/D/L,
    writing fair for the team tickets AND the Kalshi `-TIE` outcome.

Matching is by Kalshi market DISCOVERY: pull the open series, match on date token +
both competitor codes present in the ticker + the outcome suffix. Unmatched games are
safely skipped, never mis-bet. Tennis Kalshi codes == player surname[:3].

  python3 -m kalshi_agent.daily_research [--quiet]
"""
import json
import math
import re
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from kalshi_agent.dataflows.kalshi_api import best_bbo
from kalshi_agent.dataflows import odds_api
from kalshi_agent.hunt_kalshi import _markets_by_series

HERE = Path(__file__).parent
OVERRIDES = HERE / "sharp_overrides.json"
RESEARCH_LOG = HERE / "data" / "daily_research.jsonl"
UA = {"User-Agent": "everlight-ventures-research/1.0"}
_MON = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
HOLD2 = 1.045   # assumed 2-way book overround
HOLD3 = 1.07    # assumed 3-way (W/D/L) overround

# ESPN abbreviation -> Kalshi abbreviation; identity is the fallback.
ABBR_FIX = {"GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA",
            "CHW": "CWS", "AZ": "ARI", "TB": "TBL", "LA": "LAK", "NJ": "NJD", "SJ": "SJS"}

SPORTS = {
    "nba": {"espn": "basketball/nba", "series": "KXNBAGAME", "kind": "spread2", "sigma": 12.0, "odds": "basketball_nba"},
    "wnba": {"espn": "basketball/wnba", "series": "KXWNBAGAME", "kind": "spread2", "sigma": 11.0, "odds": "basketball_wnba"},
    "mlb": {"espn": "baseball/mlb", "series": "KXMLBGAME", "kind": "ml2", "odds": "baseball_mlb"},
    "nhl": {"espn": "hockey/nhl", "series": "KXNHLGAME", "kind": "ml2", "odds": "icehockey_nhl"},
    "wc":  {"espn": "soccer/fifa.world", "series": "KXWCGAME", "kind": "soccer3", "odds": "soccer_fifa_world_cup"},
    "atp": {"espn": "tennis/atp", "series": "KXATPMATCH", "kind": "tennis2"},
    "wta": {"espn": "tennis/wta", "series": "KXWTAMATCH", "kind": "tennis2"},
}


def _get_json(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read())


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def american_to_prob(odds):
    o = float(odds)
    return (-o) / ((-o) + 100.0) if o < 0 else 100.0 / (o + 100.0)


def _ymd_to_kalshi(ymd):
    return "%s%s%s" % (ymd[2:4], _MON[int(ymd[4:6])], ymd[6:8])


def fix(a):
    return ABBR_FIX.get(a, a) if a else a


def _surname_code(athlete):
    """Kalshi tennis code == first 3 letters of the surname (Safiullin -> SAF)."""
    a = athlete or {}
    ln = a.get("lastName") or (a.get("displayName") or "").split(" ")[-1]
    ln = re.sub(r"[^A-Za-z]", "", ln or "")
    return ln[:3].upper() if len(ln) >= 3 else None


def _parse_line(s):
    """'NY -1.5' -> ('NY', -1.5); 'SEA -122' -> ('SEA', -122). Returns (team, num)."""
    if not s:
        return None, None
    s = s.strip().upper()
    if s in ("EVEN", "PK", "PICK"):
        return None, 0.0
    m = re.match(r"^([A-Z]{2,4})\s*([+-]?\d+(?:\.\d+)?)$", s)
    return (m.group(1), float(m.group(2))) if m else (None, None)


def _game_outcomes(cfg, comp, home, away):
    """Return (code_a, code_b, [(code, prob), ...]) for a game, or None."""
    odds = comp.get("odds") or []
    if not odds:
        return None
    o = odds[0]
    if not isinstance(o, dict):     # ESPN sometimes returns [null] -- skip, don't crash the run
        return None
    kind = cfg["kind"]
    if kind == "tennis2":
        ca = _surname_code((away.get("athlete") if away else None))
        cb = _surname_code((home.get("athlete") if home else None))
        team, num = _parse_line(o.get("details"))
        if not ca or not cb or num is None or num == 0.0:
            return None
        raw = american_to_prob(num)            # the listed player's implied
        p_listed = min(0.97, max(0.03, raw / HOLD2))
        # the listed player is whichever code the ML team matches; default to home
        listed = cb if (team and team[:3] == cb) else (ca if (team and team[:3] == ca) else cb)
        other = ca if listed == cb else cb
        return ca, cb, [(listed, p_listed), (other, 1 - p_listed)]

    ha = fix((home.get("team") or {}).get("abbreviation")) if home else None
    aa = fix((away.get("team") or {}).get("abbreviation")) if away else None
    if not ha or not aa:
        return None

    if kind == "soccer3":
        home_team, home_num = _parse_line(o.get("details"))      # details = HOME ml
        draw = (o.get("drawOdds") or {}).get("moneyLine")
        if home_num is None or draw is None:
            return None
        rh = american_to_prob(home_num)
        rd = american_to_prob(draw)
        ra = max(0.02, HOLD3 - rh - rd)
        t = rh + rd + ra
        return aa, ha, [(ha, rh / t), (aa, ra / t), ("TIE", rd / t)]

    # spread2 / ml2
    team, num = _parse_line(o.get("details"))
    if num is None:
        return None
    if kind == "spread2":
        fav_p = _norm_cdf(abs(num) / (cfg.get("sigma") or 12.0))
    else:  # ml2 -- de-vig the single listed line
        fav_p = min(0.97, max(0.03, american_to_prob(num) / HOLD2))
    fav = fix(team)
    home_p = fav_p if fav == ha else (1 - fav_p if fav == aa else 0.5)
    return aa, ha, [(ha, home_p), (aa, 1 - home_p)]


def espn_slate(cfg, days=3):
    out = []
    cons = []
    if cfg.get("odds"):
        try:
            cons = odds_api.consensus(cfg["odds"])   # one Odds API call per sport (multi-book)
        except Exception:
            cons = []
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
            home = next((c for c in cs if c.get("homeAway") == "home"), cs[0] if cs else None)
            away = next((c for c in cs if c.get("homeAway") == "away"), cs[1] if len(cs) > 1 else None)
            if not home or not away:
                continue
            res = _game_outcomes(cfg, comp, home, away)
            if not res:
                continue
            ca, cb, outcomes = res
            books = 1
            book = ((comp.get("odds") or [{}])[0].get("provider") or {}).get("name", "book")
            # SHARPEN: replace the single-book ESPN prob with the multi-book consensus
            # where we can match the game by team name. More books -> trust smaller edges.
            if cons:
                hn = (home.get("team") or {}).get("displayName")
                an = (away.get("team") or {}).get("displayName")
                probs, nbk = odds_api.match(cons, hn, an)
                if probs and nbk:
                    namemap = {fix((home.get("team") or {}).get("abbreviation")): hn,
                               fix((away.get("team") or {}).get("abbreviation")): an,
                               "TIE": "Draw"}
                    sharp = []
                    for c, p in outcomes:
                        cp = odds_api.prob_for(probs, namemap.get(c))
                        sharp.append((c, cp if cp is not None else p))
                    outcomes, books, book = sharp, nbk, "consensus/%dbk" % nbk
            out.append({"date": ktoken, "code_a": ca, "code_b": cb,
                        "outcomes": [{"code": c, "prob": round(p, 4)} for c, p in outcomes],
                        "name": e.get("name"), "book": book, "books": books})
    return out


def _find_ticker(markets, date_tok, code_a, code_b, outcome):
    for m in markets:
        t = m.get("ticker", "")
        parts = t.split("-")
        if len(parts) < 3:
            continue
        mid, suf = parts[1], parts[-1]
        if mid.startswith(date_tok) and code_a in mid and code_b in mid and suf == outcome:
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
        try:
            slate = espn_slate(cfg)        # isolate each sport -- one bad feed can't abort the rest
        except Exception as e:
            print("  (%s slate failed: %s -- skipping)" % (sport, str(e)[:70]))
            continue
        if not slate:
            continue
        try:
            kmkts = _markets_by_series(cfg["series"])
        except Exception:
            kmkts = []
        for g in slate:
            ngames += 1
            for oc in g["outcomes"]:
                tk = _find_ticker(kmkts, g["date"], g["code_a"], g["code_b"], oc["code"])
                if not tk:
                    continue
                try:
                    yb, ya, nb, yc, nc = best_bbo(tk)
                except Exception:
                    yb = ya = None
                row = {"sport": sport, "ticker": tk, "outcome": oc["code"], "fair_prob": oc["prob"],
                       "kalshi_ask": ya, "game": g["name"], "book": g["book"]}
                if ya is not None:
                    row["edge_buy"] = round(oc["prob"] - ya / 100.0, 4)
                rows.append(row)
                if write and ya is not None:
                    existing[tk] = {"fair_prob": oc["prob"],
                                    "source": "%s %s->prob (daily_research)" % (g["book"], sport),
                                    "books": g.get("books", 1),
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
    print("=" * 66)
    print("  DAILY RESEARCH", time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "-- games:", r["games"])
    print("=" * 66)
    edges = []
    for row in sorted(r["rows"], key=lambda x: -(x.get("edge_buy") or -9)):
        eb = row.get("edge_buy")
        if eb is None:
            continue
        mark = "  <== EDGE +%.1f%%" % (eb * 100) if eb >= 0.025 else ""
        if mark:
            edges.append(row)
        if eb >= 0.0 or mark:
            print("  %-4s %-32s fair %.0f%% ask %sc edge %+.1f%%%s" % (
                row["sport"].upper(), row["ticker"][:32], row["fair_prob"] * 100,
                row.get("kalshi_ask"), eb * 100, mark))
    msg = "Daily research: %d games / %d sports, %d edge(s)%s. auto_edge takes any that clear the floor." % (
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
