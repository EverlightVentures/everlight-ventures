#!/usr/bin/env python3
"""current_events.py -- Polymarket cross-market edge feed for Kalshi current-events markets.

ONE STRATEGY, MANY SHARP LINES (Rich 2026-06-25). DraftKings is the sharp line for sports;
Polymarket is the sharp line for politics/economy/world. Reuses dataflows/polymarket_clob
(READ only) as the consensus, matches each Polymarket question to a LIQUID Kalshi current-events
market by question text (strict), and writes the Polymarket price as a sharp_override so the
SAME auto_edge gates bet it. The gates also catch a bad match (absurd edge -> blocked).

Two fixes over v1 (both were bugs that made it look "dormant"):
  * Kalshi liquidity is read from the real ORDERBOOK (best_bbo), NOT the list endpoint (which
    shows yes_ask=None even when the book is deep -- the recurring Kalshi trap).
  * Polymarket is PAGINATED (the top-100-by-volume are novelty markets; the serious
    recession/econ/politics markets are deeper in the list).

  python3 -m kalshi_agent.current_events            # radar (print divergences, write nothing)
  python3 -m kalshi_agent.current_events --write     # write overrides -> the engine bets them (gated)
"""
import argparse
import json
import re
import time
from pathlib import Path

from kalshi_agent.dataflows.polymarket_clob import PolymarketCLOB
from kalshi_agent.dataflows.kalshi_api import best_bbo
from kalshi_agent.execution.kalshi_exec import from_creds

HERE = Path(__file__).parent
OVERRIDES = HERE / "sharp_overrides.json"
LOG = HERE / "data" / "current_events.jsonl"

# liquid Kalshi current-events series worth scanning (deep books verified via best_bbo).
# Polymarket overlaps a SUBSET (recession/politics/shutdown/crypto-ish); Fed/CPI/weather need
# other sharp sources (futures/forecast) -- future lanes. We bet only where a Polymarket match exists.
KALSHI_SERIES = ["KXRECSSNBER", "KXGOVSHUTDOWN", "KXGOVSHUT", "KXPRESPARTYWINNER", "KXHOUSECONTROL",
                 "KXSENATECONTROL", "KXBTCMAXY", "KXETHMAXY", "KXGOVSHUT26", "KXUSRECESSION",
                 "KXNATObreakup", "KXTIKTOKBAN", "KXGOOGLEBREAKUP", "KXTRUMPDEAL"]
MIN_VOL = 4000           # Polymarket 24h liquidity floor
MIN_TOKENS = 2
MIN_JACCARD = 0.42
STOP = set(("will the a an of in on by to is are be win wins won out as at for and or not no yes "
            "2025 2026 2027 2028 this year next before after end above below reach hit there").split())


def _toks(s):
    return set(w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in STOP and len(w) > 2)


def _polymarket_all(pages=10, per=100):
    """Paginated Polymarket scan (the serious markets are past the top-100-by-volume)."""
    pc, out, seen = PolymarketCLOB(), [], set()
    for p in range(pages):
        try:
            ms = pc.scan_markets(limit=per, offset=p * per)
        except Exception:
            break
        if not ms:
            break
        for m in ms:
            if m.id not in seen:
                seen.add(m.id); out.append(m)
    return out


def _kalshi_current(k):
    """Liquid Kalshi current-events markets with REAL orderbook prices (best_bbo)."""
    out = []
    for s in KALSHI_SERIES:
        try:
            ms = k._request("GET", "/markets?status=open&limit=40&series_ticker=%s" % s).get("markets", [])
        except Exception:
            continue
        for m in ms:
            tk, title = m.get("ticker"), m.get("title")
            if not tk or not title:
                continue
            try:
                yb, ya, nb, yc, nc = best_bbo(tk)
            except Exception:
                yb = ya = yc = None
            if yb is None and ya is None:
                continue
            mid = ((yb + ya) / 2.0 / 100.0) if (yb is not None and ya is not None) else \
                  ((ya / 100.0) if ya is not None else (yb / 100.0))
            out.append({"ticker": tk, "title": title, "kp": mid, "ask": ya, "depth": yc or 0})
    return out


def scan(creds=None, write=False):
    k = from_creds(creds) if creds else from_creds()
    pm = [m for m in _polymarket_all()
          if m.volume_24h >= MIN_VOL and "Yes" in m.prices and "world cup" not in (m.question or "").lower()]
    kc = _kalshi_current(k)
    existing = {}
    if OVERRIDES.exists():
        try:
            existing = json.loads(OVERRIDES.read_text())
        except Exception:
            existing = {}
    diverge = []
    for km in kc:
        kt = _toks(km["title"])
        best, bn, bj = None, 0, 0.0
        for pmm in pm:
            inter = kt & _toks(pmm.question)
            if not inter:
                continue
            jac = len(inter) / len(kt | _toks(pmm.question))
            if (len(inter), jac) > (bn, bj):
                bn, bj, best = len(inter), jac, pmm
        if not best or bn < MIN_TOKENS or bj < MIN_JACCARD:
            continue
        pmyes = best.prices.get("Yes")
        diverge.append({"kalshi_tk": km["ticker"], "kalshi_title": km["title"], "kalshi_yes": round(km["kp"], 3),
                        "poly_q": best.question, "poly_yes": round(pmyes, 3),
                        "edge": round(pmyes - km["kp"], 3), "tokens": bn, "jaccard": round(bj, 2),
                        "depth": round(km["depth"], 0), "poly_vol": int(best.volume_24h)})
        if write and pmyes is not None:
            existing[km["ticker"]] = {"fair_prob": round(pmyes, 4),
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
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--creds", default=None)
    args = ap.parse_args()
    d = sorted(scan(args.creds, args.write), key=lambda r: -abs(r.get("edge") or 0))
    print("CURRENT-EVENTS cross-market: %d matches%s" % (len(d), " (WROTE overrides)" if args.write else " (radar)"))
    for r in d[:18]:
        print("  edge %+5.0f%% | kalshi %3.0f%% vs poly %3.0f%% | depth$%-8.0f | %-26s | %s" % (
            r["edge"] * 100, r["kalshi_yes"] * 100, r["poly_yes"] * 100, r["depth"],
            r["kalshi_tk"][:26], r["poly_q"][:38]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
