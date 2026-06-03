#!/usr/bin/env python3
"""hunt_kalshi.py -- the money machine. Around-the-clock edge hunter for Kalshi.

Every cycle: pull the ALLOWED markets (crypto now -- Sports/Elections/Entertainment
are blocked for this account), price each with the live edge model, and bet the
cheap side whenever our probability beats Kalshi's price by enough to clear the fee
AND profit. Maker-first (post_only) so the fee is ~75% lower. Sized by quarter-Kelly,
capped (growth ladder), with Kalshi balance as the source of truth.

DRY-RUN by default (prints what it WOULD trade). --live to actually place orders.
  python3 -m kalshi_agent.hunt_kalshi                 # scan + show candidates
  python3 -m kalshi_agent.hunt_kalshi --live --max-stake 5 --max-trades 3
"""
import argparse
import json
import math
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

from kalshi_agent.crypto_edge import spot_and_vol, prob_above, prob_between

K = "https://api.elections.kalshi.com/trade-api/v2"
ALLOWED_SERIES = ["KXBTC", "KXETH"]   # crypto only -- the categories CA/NV allow


def _get(path, params=None):
    u = K + path + ("?" + urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None}) if params else "")
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ev-hunt/1.0"}), timeout=15).read())


def maker_fee(price, count):
    return math.ceil(0.0175 * price * (1 - price) * count * 100) / 100   # 0.25x of taker


def _close_minutes(m):
    ct = m.get("close_time")
    if not ct:
        return None
    try:
        dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
        return (dt - datetime.now(timezone.utc)).total_seconds() / 60.0
    except Exception:
        return None


def model_prob(m, spot, sig):
    """Our probability the market resolves YES, from spot + vol + time."""
    mins = _close_minutes(m)
    if mins is None or mins <= 0:
        return None, mins
    st = m.get("strike_type"); fl = m.get("floor_strike"); cp = m.get("cap_strike")
    if st == "greater" and fl:
        return prob_above(spot, fl, sig, mins), mins
    if st == "less" and (cp or fl):
        return 1.0 - prob_above(spot, cp or fl, sig, mins), mins
    if st == "between" and fl and cp:
        return prob_between(spot, fl, cp, sig, mins), mins
    return None, mins


def scan(min_edge=0.07, stake=5.0):
    """Return ranked trade candidates across allowed crypto markets."""
    spots = {"KXBTC": spot_and_vol("BTC"), "KXETH": spot_and_vol("ETH")}
    out = []
    for series in ALLOWED_SERIES:
        spot, sig = spots[series]
        try:
            ev = _get("/events", {"series_ticker": series, "status": "open",
                                  "limit": 6, "with_nested_markets": "true"})
        except Exception:
            continue
        for e in ev.get("events", []):
            for m in (e.get("markets") or []):
                t = m.get("ticker")
                try:
                    ob = _get(f"/markets/{t}/orderbook").get("orderbook", {})
                except Exception:
                    continue
                yes, no = ob.get("yes") or [], ob.get("no") or []
                ybid = max([p for p, s in yes], default=None)
                nobid = max([p for p, s in no], default=None)
                yask = (100 - nobid) if nobid is not None else None
                if ybid is None or yask is None:
                    continue
                mid = (ybid + yask) / 200.0
                mp, mins = model_prob(m, spot, sig)
                if mp is None:
                    continue
                e_yes = mp - mid                       # >0 YES cheap, <0 NO cheap
                side = "yes" if e_yes > 0 else "no"
                # maker limit: join the cheap side's bid + 1c (still a maker)
                px_c = (ybid + 1) if side == "yes" else (nobid + 1)
                px = px_c / 100.0
                win_prob = mp if side == "yes" else (1 - mp)
                count = max(1, int(stake / max(px, 0.01)))
                fee = maker_fee(px, count)
                # net EV: win -> (1-px)*count ; lose -> -px*count ; minus fee
                ev_usd = win_prob * (1 - px) * count - (1 - win_prob) * px * count - fee
                if abs(e_yes) >= min_edge and ev_usd > 0:
                    out.append({"ticker": t, "title": (m.get("title") or "")[:34],
                                "side": side, "edge": round(e_yes, 3), "model": round(mp, 3),
                                "mid": round(mid, 3), "limit_c": px_c, "count": count,
                                "fee": fee, "net_ev": round(ev_usd, 3), "mins": round(mins, 1)})
    out.sort(key=lambda c: -c["net_ev"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--max-stake", type=float, default=5.0)
    ap.add_argument("--max-trades", type=int, default=3)
    ap.add_argument("--min-edge", type=float, default=0.07)
    args = ap.parse_args()
    print("=" * 60); print("  KALSHI EDGE HUNTER", "[LIVE]" if args.live else "[DRY-RUN]"); print("=" * 60)
    cands = scan(min_edge=args.min_edge, stake=args.max_stake)
    print(f"  tradeable edges found: {len(cands)}")
    for c in cands[:8]:
        print(f"  {c['side'].upper():3} {c['ticker'][:24]:24} edge={c['edge']:+.3f} "
              f"model={c['model']:.2f} mkt={c['mid']:.2f} @ {c['limit_c']}c x{c['count']} "
              f"netEV=${c['net_ev']} ({c['mins']:.0f}m) {c['title']}")
    if not cands:
        print("  (no edge clears fees + liquidity right now -- crypto is thin off-hours;")
        print("   the cron keeps hunting and fires when active markets misprice)")
        return 0
    if not args.live:
        print("\n  DRY-RUN -- re-run with --live to place the top trades.")
        return 0
    from kalshi_agent.execution.kalshi_exec import from_creds
    k = from_creds()
    bal = k.get_balance()
    print(f"\n  LIVE. Kalshi balance ${bal:.2f}. Placing up to {args.max_trades} maker orders...")
    placed = 0
    for c in cands[:args.max_trades]:
        if c["limit_c"] * c["count"] / 100.0 > bal:
            print(f"  skip {c['ticker']}: would exceed balance"); continue
        try:
            o = k.place_order(c["ticker"], side=c["side"], action="buy",
                              count=c["count"], price_cents=c["limit_c"], post_only=True)
            print(f"  PLACED {c['side']} {c['ticker']} x{c['count']} @ {c['limit_c']}c -> {o.get('order_id')}")
            placed += 1
        except Exception as e:
            print(f"  rejected {c['ticker']}: {str(e)[:80]}")
    print(f"  placed {placed} order(s).")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
