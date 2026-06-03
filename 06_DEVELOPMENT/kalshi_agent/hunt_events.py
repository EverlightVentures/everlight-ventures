#!/usr/bin/env python3
"""hunt_events.py -- deep-liquidity hunter for EVENT markets (sports/elections/etc).

Crypto = math (hunt_kalshi.py). Events = research: Perplexity reads the matchup/race,
Claude estimates the probability (research_edge.py), we bet the edge vs Kalshi's price.
Runs on e5 (California IP) so the full board is tradeable. Research is CACHED + capped
per cycle to control Claude/Perplexity cost (a race's odds don't move every 5 min).

DRY-RUN by default. --live places maker orders (post_only). MUST run from e5.
"""
import argparse
import json
import time
from pathlib import Path

from kalshi_agent.research_edge import estimate
from kalshi_agent.hunt_kalshi import _get, maker_fee
from kalshi_agent.dataflows.kalshi_api import best_bbo

CACHE = Path(__file__).parent / "data" / "research_cache.json"
CRYPTO_PREFIX = ("KXBTC", "KXETH", "KXSOL", "KXXRP")   # crypto is the other hunter's job


def _active_event_markets(limit=200):
    """Tickers that RECENTLY TRADED (= liquid/active), minus crypto. Recency order."""
    tr = _get("/markets/trades", {"limit": limit}).get("trades", [])
    out = []
    for t in tr:
        tk = t.get("ticker", "")
        if tk and tk not in out and not tk.upper().startswith(CRYPTO_PREFIX):
            out.append(tk)
    return out


def _cache():
    try:
        return json.loads(CACHE.read_text())
    except Exception:
        return {}


def scan(min_edge=0.07, min_conf=0.6, stake=5.0, max_research=6, ttl=1800, model="claude-sonnet-4-6"):
    """Ranked event-market candidates. Researches only markets with a live two-sided
    book (tradeable now), capped at max_research fresh Claude/Perplexity calls/cycle."""
    cache = _cache()
    now_ish = max((c.get("ts", 0) for c in cache.values()), default=0) + 1  # monotonic-ish stamp
    out, researched = [], 0
    for tk in _active_event_markets():
        try:
            ybid, yask, nobid, _yc, _nc = best_bbo(tk)
        except Exception:
            continue
        if ybid is None or yask is None:
            continue                                   # need a two-sided book to trade
        mid = (ybid + yask) / 200.0
        c = cache.get(tk)
        if c and (now_ish - c["ts"]) < ttl:
            prob, conf, reason = c["prob"], c["conf"], c.get("reason", "")
        else:
            if researched >= max_research:
                continue
            try:
                m = _get(f"/markets/{tk}")["market"]
                r = estimate(m.get("title", ""), m.get("yes_sub_title") or m.get("subtitle") or "YES", model=model)
            except Exception:
                continue
            if r.get("prob") is None:
                continue
            prob, conf, reason = r["prob"], r["confidence"], r["reasoning"]
            cache[tk] = {"prob": prob, "conf": conf, "reason": reason, "ts": now_ish}
            researched += 1
        if prob is None or conf < min_conf:
            continue
        e_yes = prob - mid
        side = "yes" if e_yes > 0 else "no"
        px_c = (ybid + 1) if side == "yes" else (nobid + 1)
        px = px_c / 100.0
        win = prob if side == "yes" else (1 - prob)
        count = max(1, int(stake / max(px, 0.01)))
        fee = maker_fee(px, count)
        ev = win * (1 - px) * count - (1 - win) * px * count - fee
        if abs(e_yes) >= min_edge and ev > 0:
            out.append({"ticker": tk, "side": side, "edge": round(e_yes, 3),
                        "model_prob": round(prob, 3), "mid": round(mid, 3), "conf": conf,
                        "limit_c": px_c, "count": count, "net_ev": round(ev, 3),
                        "reason": reason[:70]})
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache))
    except Exception:
        pass
    out.sort(key=lambda c: -c["net_ev"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--max-stake", type=float, default=5.0)
    ap.add_argument("--max-trades", type=int, default=3)
    ap.add_argument("--min-edge", type=float, default=0.07)
    ap.add_argument("--min-conf", type=float, default=0.6)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    args = ap.parse_args()
    print("=" * 60); print("  KALSHI EVENT HUNTER", "[LIVE]" if args.live else "[DRY-RUN]"); print("=" * 60)
    cands = scan(min_edge=args.min_edge, min_conf=args.min_conf, stake=args.max_stake, model=args.model)
    print(f"  researched-edge candidates: {len(cands)}")
    for c in cands[:8]:
        print(f"  {c['side'].upper():3} {c['ticker'][:26]:26} edge={c['edge']:+.3f} "
              f"prob={c['model_prob']:.2f} mkt={c['mid']:.2f} conf={c['conf']:.2f} "
              f"@{c['limit_c']}c x{c['count']} netEV=${c['net_ev']} | {c['reason']}")
    if not cands:
        print("  (no researched edge clears fees + a live book right now)")
        return 0
    if not args.live:
        print("\n  DRY-RUN -- --live to place the top trades (from e5 only).")
        return 0
    from kalshi_agent.execution.kalshi_exec import from_creds
    k = from_creds(); bal = k.get_balance()
    print(f"\n  LIVE. balance ${bal:.2f}. placing up to {args.max_trades}...")
    placed = 0
    for c in cands[:args.max_trades]:
        if c["limit_c"] * c["count"] / 100.0 > bal:
            continue
        try:
            o = k.place_order(c["ticker"], side=c["side"], action="buy",
                              count=c["count"], price_cents=c["limit_c"], post_only=True)
            print(f"  PLACED {c['side']} {c['ticker']} x{c['count']} @ {c['limit_c']}c -> {o.get('order_id')}")
            placed += 1
        except Exception as e:
            print(f"  rejected {c['ticker']}: {str(e)[:70]}")
    print(f"  placed {placed}.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
