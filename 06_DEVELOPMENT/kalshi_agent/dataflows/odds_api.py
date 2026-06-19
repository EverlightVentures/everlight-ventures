"""odds_api.py -- The Odds API multi-book consensus (the sharp "fair").

ESPN gives ONE book's line, which is noisy at +/-2pts, so the engine needs a fat
3pt gap to trust it. This pulls 8-10 books, de-vigs EACH, and AVERAGES the no-vig
shares -> a consensus fair that is sharp enough to trust 1.5-2pt edges. That is the
whole point: more REAL edges become bettable without lowering the standard.

Free tier: 500 req/day, ~1 credit per sport per call. Pure stdlib (runs on e5 cron).
Key read straight from the gitignored env file (cron has no exported env).
"""
import json
import re
import urllib.request
from pathlib import Path

BASE = "https://api.the-odds-api.com/v4"
_KEY_FILES = [
    "/home/ubuntu/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/odds_api.env",
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/odds_api.env",
]

# our sport -> Odds API sport key (only the ones Kalshi actually lists game markets for)
SPORT_KEYS = {
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "wc": "soccer_fifa_world_cup",
    "wnba": "basketball_wnba",
    "kbo": "baseball_kbo",      # Korea -- fills US overnight (name-matched slate)
    "npb": "baseball_npb",      # Japan -- fills US overnight (name-matched slate)
}


def key():
    import os
    for p in _KEY_FILES:
        try:
            for line in Path(p).read_text().splitlines():
                if line.startswith("ODDS_API_KEY="):
                    return line.split("=", 1)[1].strip()
        except Exception:
            continue
    return os.environ.get("ODDS_API_KEY")


def _american_to_prob(o):
    o = float(o)
    return (-o) / ((-o) + 100.0) if o < 0 else 100.0 / (o + 100.0)


def _norm(name):
    return re.sub(r"[^a-z]", "", (name or "").lower())


CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "odds_cache"
CACHE_TTL = 7200          # re-fetch a sport at most every 2h (free tier = 500 credits/day)
STALE_MAX = 6 * 3600      # on quota/error, serve cache up to 6h old rather than starve the engine


def _cache_path(sport_key, regions):
    return CACHE_DIR / ("%s_%s.json" % (sport_key, regions.replace(",", "-")))


def consensus(sport_key, regions="us"):
    """Cached multi-book no-vig consensus. Returns cached games when fresh (< CACHE_TTL),
    re-fetches otherwise, and on a quota/API error serves recent stale cache instead of []
    so a credit blip doesn't starve the engine. The whole reason the bot went dark: the free
    500/day Odds-API budget was being burned by 30-min x many-sport polling; this caps it."""
    import time
    p, now = _cache_path(sport_key, regions), time.time()
    try:
        cached = json.loads(p.read_text())
    except Exception:
        cached = None
    if cached and (now - cached.get("ts", 0) < CACHE_TTL):
        return cached.get("games", [])
    games = _fetch_consensus(sport_key, regions)
    if games is not None:                                  # legit response (maybe empty) -- cache it
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"ts": int(now), "games": games}))
        except Exception:
            pass
        return games
    if cached and (now - cached.get("ts", 0) < STALE_MAX):  # quota/error -> recent stale, don't starve
        return cached.get("games", [])
    return []


def _fetch_consensus(sport_key, regions="us"):
    """Raw fetch + de-vig. Returns the games list, or None on API/quota error (so the cache
    layer falls back to stale). An empty list [] is a legit 'no games right now'."""
    k = key()
    if not k:
        return None
    url = "%s/sports/%s/odds/?apiKey=%s&regions=%s&markets=h2h&oddsFormat=american" % (
        BASE, sport_key, k, regions)
    try:
        data = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "ev-sharp/1.0"}), timeout=20).read())
    except Exception:
        return None
    if not isinstance(data, list):     # quota message / error object -> signal error to the cache layer
        return None
    out = []
    for g in data:
        acc, nbk = {}, 0
        for bk in g.get("bookmakers", []):
            mk = next((m for m in bk.get("markets", []) if m.get("key") == "h2h"), None)
            if not mk:
                continue
            imps = {o["name"]: _american_to_prob(o["price"]) for o in mk.get("outcomes", []) if o.get("price")}
            tot = sum(imps.values())
            if tot <= 0:
                continue
            for nm, p in imps.items():
                acc[nm] = acc.get(nm, 0.0) + p / tot     # de-vig this book, accumulate share
            nbk += 1
        if nbk == 0:
            continue
        out.append({"home": g.get("home_team"), "away": g.get("away_team"),
                    "home_n": _norm(g.get("home_team")), "away_n": _norm(g.get("away_team")),
                    "probs": {nm: v / nbk for nm, v in acc.items()}, "books": nbk})
    return out


def match(games, home_name, away_name):
    """Find the consensus game for these full team names. Returns (probs, books) or (None, 0)."""
    hn, an = _norm(home_name), _norm(away_name)
    if not hn or not an:
        return None, 0
    for g in games:
        if {g["home_n"], g["away_n"]} == {hn, an}:
            return g["probs"], g["books"]
    for g in games:                                       # looser containment fallback
        names = g["home_n"] + "|" + g["away_n"]
        if (hn in names or g["home_n"] in hn or g["away_n"] in hn) and \
           (an in names or g["home_n"] in an or g["away_n"] in an):
            return g["probs"], g["books"]
    return None, 0


def prob_for(probs, full_name):
    """Consensus prob for one team/outcome by (fuzzy) full name; None if absent."""
    n = _norm(full_name)
    if not n:
        return None
    for nm, p in probs.items():
        if _norm(nm) == n:
            return p
    for nm, p in probs.items():
        a = _norm(nm)
        if n and (n in a or a in n):
            return p
    return None
