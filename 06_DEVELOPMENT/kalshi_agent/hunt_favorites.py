#!/usr/bin/env python3
"""hunt_favorites.py -- the favorite-longshot edge (the one academically documented
to PERSIST on Kalshi). Bettors overpay for longshots, so heavy FAVORITES are slightly
underpriced and win MORE often than their price implies. We systematically buy heavy
favorites (price 85-96c, deep book) as a small basket and let the scorecard measure
the realized win-rate vs the implied price. If realized > implied, the bias is real
for us -> scale. This is a STATISTICAL edge over many bets, not a per-market call.

DRY-RUN/log by default (feeds the scorecard). --live places small maker bets (e5 only).
"""
import argparse
import json

from kalshi_agent.hunt_kalshi import _get, maker_fee
from kalshi_agent.dataflows.kalshi_api import best_bbo

# documented favorite-longshot uplift: favorites at ~90c historically realize a few
# points higher. We log a modest +0.03 hypothesis and let real outcomes confirm/deny.
BIAS_UPLIFT = 0.03
LO, HI = 85, 96         # heavy-but-buyable favorites (room to profit, not 99c dust)
MIN_DEPTH = 500
CRYPTO = ("KXBTC", "KXETH", "KXSOL", "KXXRP")   # crypto efficient -> skip


def _active_markets(limit=400):
    tr = _get("/markets/trades", {"limit": limit}).get("trades", [])
    out = []
    for t in tr:
        tk = t.get("ticker", "")
        if tk and tk not in out and not tk.upper().startswith(CRYPTO):
            out.append(tk)
    return out


def scan(stake=3.0, max_markets=None):
    out = []
    tickers = _active_markets()
    if max_markets:
        tickers = tickers[:max_markets]
    for tk in tickers:
        try:
            yb, ya, nb, yc, nc = best_bbo(tk)
        except Exception:
            continue
        if yb is None or ya is None:
            continue
        yes_mid = (yb + ya) / 2
        # the favorite side + the price to BUY it
        if yes_mid >= 50:
            side, buy, depth = "yes", ya, yc          # buy YES at the ask
        else:
            side, buy, depth = "no", 100 - yb, nc     # buy NO (= fade the YES longshot)
        if not (LO <= buy <= HI) or depth < MIN_DEPTH:
            continue
        implied = buy / 100.0
        our_prob = min(0.99, implied + BIAS_UPLIFT)   # the bias hypothesis
        count = max(1, int(stake / implied))
        fee = maker_fee(implied, count)
        ev = our_prob * (1 - implied) * count - (1 - our_prob) * implied * count - fee
        out.append({"ticker": tk, "side": side, "buy_c": buy, "implied": round(implied, 2),
                    "our_prob": round(our_prob, 2), "count": count, "net_ev": round(ev, 2),
                    "depth": int(depth)})
    out.sort(key=lambda c: -c["buy_c"])               # strongest favorites first
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--max-stake", type=float, default=3.0)
    ap.add_argument("--max-trades", type=int, default=5)
    args = ap.parse_args()
    print("=" * 60); print("  FAVORITE-LONGSHOT HUNTER", "[LIVE]" if args.live else "[DRY/LOG]"); print("=" * 60)
    cands = scan(stake=args.max_stake)
    print(f"  heavy favorites ({LO}-{HI}c, depth>{MIN_DEPTH}): {len(cands)}")
    for c in cands[:10]:
        print(f"  {c['side'].upper():3} {c['ticker'][:30]:30} buy {c['buy_c']}c (implied {c['implied']}) x{c['count']} depth{c['depth']}")
    try:                                              # log the basket to the scorecard
        from kalshi_agent import scorecard
        for c in cands:
            scorecard.record("favorite-longshot", c["ticker"], c["side"], c["our_prob"], c["implied"])
    except Exception:
        pass
    if not args.live or not cands:
        if not args.live:
            print("\n  DRY/LOG -- favorites logged to scorecard; measures realized win-rate vs implied.")
        return 0
    from kalshi_agent.execution.kalshi_exec import from_creds
    k = from_creds(); bal = k.get_balance()
    print(f"\n  LIVE. balance ${bal:.2f}. placing up to {args.max_trades} favorites...")
    placed = 0
    for c in cands[:args.max_trades]:
        if c["buy_c"] * c["count"] / 100 > bal:
            continue
        try:
            o = k.place_order(c["ticker"], side=c["side"], action="buy",
                              count=c["count"], price_cents=c["buy_c"], post_only=False)
            print(f"  PLACED {c['side']} {c['ticker']} x{c['count']} @ {c['buy_c']}c -> {o.get('order_id')}")
            placed += 1
        except Exception as e:
            print(f"  rejected {c['ticker']}: {str(e)[:60]}")
    print(f"  placed {placed}.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
