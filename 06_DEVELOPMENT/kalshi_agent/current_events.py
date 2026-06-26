#!/usr/bin/env python3
"""current_events.py -- Polymarket cross-market edge feed for Kalshi current-events markets.

ONE STRATEGY, MANY SHARP LINES (Rich 2026-06-25: "don't differentiate, it's all one strategy").
DraftKings is the sharp line for sports; Polymarket is the sharp line for politics/economy/world.
This reuses the existing Polymarket reader (dataflows/polymarket_clob) -- no new trading, just
READING its consensus price -- matches each liquid Polymarket question to the equivalent Kalshi
market by question text (STRICT), and writes the Polymarket price as a sharp_override. The ONE
auto_edge engine + the SAME gates then bet it like any other edge.

SAFETY: the matcher is strict, AND the existing gates protect against a bad text-match -- a
mismatch (or a flipped-polarity match) shows an absurd edge and gets blocked by single_book_max_edge
(15pt cap) / the sanity cap / the win-prob floor. Run --no-write first as a RADAR to eyeball matches.

  python3 -m kalshi_agent.current_events            # radar only (print divergences, write nothing)
  python3 -m kalshi_agent.current_events --write     # also write overrides -> the engine bets them (gated)
"""
import argparse
import json
import re
import time
from pathlib import Path

from kalshi_agent.dataflows.polymarket_clob import PolymarketCLOB
from kalshi_agent.execution.kalshi_exec import from_creds

HERE = Path(__file__).parent
OVERRIDES = HERE / "sharp_overrides.json"
LOG = HERE / "data" / "current_events.jsonl"

MIN_VOL = 5000           # Polymarket 24h liquidity floor (skip dead markets)
MIN_TOKENS = 2           # >= this many distinctive shared tokens to call it a match
MIN_JACCARD = 0.45       # and this much overall word overlap
STOP = set(("will the a an of of in on by to is are be win wins won out as at for and or not no yes "
            "2025 2026 2027 2028 this year next be reach above below before after end").split())
SPORT_PREFIXES = ("KXNBA", "KXMLB", "KXNHL", "KXWC", "KXUFC", "KXWNBA", "KXKBO", "KXNPB", "KXATP",
                  "KXWTA", "KXITF", "KXMENWORLDCUP", "KXMLS", "KXTENNIS", "KXNCAA", "KXNFL",
                  "KXTABLETENNIS", "KXODI", "KXBOX", "KXPGA", "KXLPGA", "KXMVE", "KXF1")


def _toks(s):
    return set(w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOP and len(w) > 2)


def _is_sports(ticker):
    t = (ticker or "").upper()
    return any(t.startswith(p) for p in SPORT_PREFIXES)


def _fetch_kalshi_current(k, max_pages=8):
    """Open Kalshi markets that are NOT sports -- the current-events universe (title + price)."""
    out, cur = [], None
    for _ in range(max_pages):
        try:
            q = "/markets?status=open&limit=1000" + (("&cursor=%s" % cur) if cur else "")
            d = k._request("GET", q)
        except Exception:
            break
        for m in d.get("markets", []):
            if m.get("ticker") and m.get("title") and not _is_sports(m.get("ticker")):
                out.append(m)
        cur = d.get("cursor")
        if not cur:
            break
    return out


def scan(creds=None, write=False):
    k = from_creds(creds) if creds else from_creds()
    pm = [m for m in PolymarketCLOB().scan_markets(limit=400)
          if m.volume_24h >= MIN_VOL and "Yes" in m.prices and "world cup" not in (m.question or "").lower()]
    kmk = _fetch_kalshi_current(k)
    existing = {}
    if OVERRIDES.exists():
        try:
            existing = json.loads(OVERRIDES.read_text())
        except Exception:
            existing = {}
    diverge = []
    for pmm in pm:
        best, bn, bj = None, 0, 0.0
        pq = _toks(pmm.question)
        for km in kmk:
            kt = _toks(km.get("title"))
            inter = pq & kt
            if not inter:
                continue
            jac = len(inter) / len(pq | kt)
            if (len(inter), jac) > (bn, bj):
                bn, bj, best = len(inter), jac, km
        if not best or bn < MIN_TOKENS or bj < MIN_JACCARD:
            continue
        tk = best.get("ticker")
        ya, yb = best.get("yes_ask"), best.get("yes_bid")
        kp = (ya / 100.0) if ya else ((yb / 100.0) if yb else None)
        pmyes = pmm.prices.get("Yes")
        diverge.append({"poly_q": pmm.question, "kalshi_tk": tk, "kalshi_title": best.get("title"),
                        "poly_yes": round(pmyes, 3), "kalshi_yes": round(kp, 3) if kp is not None else None,
                        "edge": round(pmyes - kp, 3) if kp is not None else None,
                        "tokens": bn, "jaccard": round(bj, 2), "poly_vol": int(pmm.volume_24h)})
        if write and pmyes is not None:
            existing[tk] = {"fair_prob": round(pmyes, 4),
                            "source": "polymarket cross-market (current_events)",
                            "books": 1, "expires_ts": int(time.time()) + 6 * 3600,
                            "fresh_ts": int(time.time())}
    if write:
        OVERRIDES.write_text(json.dumps(existing, indent=2))
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps({"ts": int(time.time()), "diverge": diverge}) + "\n")
    return diverge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write overrides so the engine bets matches (gated)")
    ap.add_argument("--creds", default=None)
    args = ap.parse_args()
    d = sorted(scan(args.creds, args.write), key=lambda r: -abs(r.get("edge") or 0))
    print("CURRENT-EVENTS cross-market radar: %d strict matches%s" % (len(d), " (WROTE overrides)" if args.write else " (radar only)"))
    for r in d[:18]:
        e = ("%+.0f%%" % (r["edge"] * 100)) if r["edge"] is not None else " n/a"
        kp = ("%.0f%%" % (r["kalshi_yes"] * 100)) if r["kalshi_yes"] is not None else "no-px"
        print("  edge %5s | poly %3.0f%% vs kalshi %5s | tok%d j%.2f | %-26s | %s" % (
            e, r["poly_yes"] * 100, kp, r["tokens"], r["jaccard"], r["kalshi_tk"][:26], r["poly_q"][:42]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
