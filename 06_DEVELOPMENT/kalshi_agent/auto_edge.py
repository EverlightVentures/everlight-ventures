#!/usr/bin/env python3
"""auto_edge.py -- the AUTONOMOUS edge engine.

Operator mandate (2026-06-04, Rich): "figure out a way to automate this... you
don't ask me, you just start jumping in when you see edges." This is the loop we
ran by hand on the Knicks, now self-driving on e5 every 15 minutes:

    scan Kalshi -> sharp de-vig fair prob -> net-EV AFTER the maker fee ->
    guardrails -> size small -> post a MAKER bid -> log (scorecard + ledger) -> ping.

HARD GUARDRAILS (every one fail-closed):
  * live ONLY when config live=true (default false) AND creds resolve (e5 only).
  * kill switch: a file named AUTO_EDGE_HALT next to this script halts everything.
  * Kalshi balance is the source of truth (XLM lesson); never trade below the floor.
  * per-bet / daily / total-exposure caps; min net edge after fee.
  * SANITY cap: a raw edge bigger than sanity_max_raw_edge in a liquid market is a
    BUG/stale data, not gold (the whole lesson of 2026-06-03) -- reject it.
  * depth + spread filters (wide-spread props are a tax, skip them).
  * idempotent: never double-bet a ticker already held or already open.
  * MAKER ONLY (post_only) -- thin edges only survive the maker fee, never taker.

Lane modes (config): 'bet' = real maker orders, 'log' = scorecard only (measure,
no money), 'alert' = notify only.

DRY-RUN by default. --live places real maker orders (e5 only).
  python3 -m kalshi_agent.auto_edge            # show what it WOULD do
  python3 -m kalshi_agent.auto_edge --live     # act (respects config caps)
"""
import argparse
import json
import math
import time
from pathlib import Path

from kalshi_agent.hunt_kalshi import _get, maker_fee
from kalshi_agent.dataflows.kalshi_api import best_bbo
from kalshi_agent import scorecard, sharp_lines

HERE = Path(__file__).parent
CONFIG = HERE / "auto_edge_config.json"
HALT_FILE = HERE / "AUTO_EDGE_HALT"
LEDGER = HERE / "data" / "auto_edge_ledger.jsonl"


def load_config():
    cfg = json.loads(CONFIG.read_text())
    return cfg


def halted():
    return HALT_FILE.exists()


def _ledger_rows():
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]


def _today():
    return time.strftime("%Y-%m-%d", time.gmtime())


def daily_spent():
    today = _today()
    return sum(r.get("cost", 0.0) for r in _ledger_rows() if r.get("day") == today and r.get("placed"))


def log_ledger(row):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")


OPERATOR_BETS = HERE / "operator_bets.json"


def load_operator_bets():
    if not OPERATOR_BETS.exists():
        return []
    try:
        data = json.loads(OPERATOR_BETS.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def enqueue_operator_bet(ticker, side, stake_usd, max_price_c=None, note=""):
    """Rich says a bet -> drop it in the queue. The next engine run (or an
    immediate --live run) PLACES it, bypassing the edge gate -- the operator's
    call IS the signal -- but still inside the risk caps."""
    q = load_operator_bets()
    q.append({"id": "%s-%d" % (ticker, int(time.time())), "ticker": ticker,
              "side": side, "stake_usd": float(stake_usd),
              "max_price_c": int(max_price_c) if max_price_c else None,
              "note": note, "ts": int(time.time())})
    OPERATOR_BETS.write_text(json.dumps(q, indent=2))
    return q[-1]


def notify(msg):
    """Best-effort ping so Rich sees autonomous action without being asked.
    Never blocks a trade -- Slack is a courtesy, the ledger is the record."""
    print(msg)
    try:
        from content_tools import branded_slack  # type: ignore
        branded_slack.post_branded_alert("auto-edge", msg, severity="info")
        return
    except Exception:
        pass
    try:
        from kalshi_agent import notify as _n  # type: ignore
        _n.send(msg)
    except Exception:
        pass


def kalshi_net(count, price, fair):
    """Net EV of buying `count` YES at `price` (dollars) when true prob = `fair`.
    On a Kalshi binary, per-contract gross EV = (fair - price); fee is the maker fee.
        net = count*(fair - price) - fee ;  cost = count*price + fee."""
    fee = maker_fee(price, count)
    gross = count * (fair - price)
    net = gross - fee
    cost = count * price + fee
    return {"net": net, "gross": gross, "fee": fee, "cost": cost,
            "net_pct": (net / (count * price)) if count * price else 0.0}


def best_maker_cents(cfg, fair, yes_ask, ref_count=10):
    """Highest integer-cent BUY price that still clears min_net_edge_pct after the
    maker fee, kept strictly below the ask (so it rests as a maker, never a taker).
    net_pct is ~count-independent, so a nominal ref_count is fine for the search.
    Returns the cents (1..98) or None if no edge-clearing maker price exists."""
    ceil_ask = (yes_ask - 1) if yes_ask is not None else int(round(fair * 100))
    hi = min(int(round(fair * 100)), ceil_ask)        # never bid at/above fair
    for cents in range(hi, 0, -1):
        ev = kalshi_net(ref_count, cents / 100.0, fair)
        if ev["net"] > 0 and ev["net_pct"] >= cfg["min_net_edge_pct"]:
            return cents
    return None


def held_tickers(positions):
    out = set()
    for p in positions or []:
        if isinstance(p, dict) and (p.get("position") or p.get("total_traded")):
            out.add(p.get("ticker"))
    return out


def size_bet(cfg, price, balance, spent_today, total_exposure):
    """Largest contract count that fits every cap. price in dollars."""
    room = min(cfg["per_bet_max_usd"],
               cfg["daily_max_usd"] - spent_today,
               cfg["total_exposure_max_usd"] - total_exposure,
               max(0.0, balance - cfg["min_balance_floor_usd"]))
    if room <= 0 or price <= 0:
        return 0
    return int(room // price)


def gate(cfg, count, our_cents, fair, depth, spread_cents):
    """Every guardrail in one place. Returns (ok, reason)."""
    if count < 1:
        return False, "size=0 (caps/balance)"
    price = our_cents / 100.0
    raw_edge = fair - price
    if abs(raw_edge) > cfg["sanity_max_raw_edge"]:
        return False, "edge %.0f%% > sanity cap (likely a bug/stale)" % (raw_edge * 100)
    if depth < cfg["min_depth_dollars"]:
        return False, "depth $%d < min" % int(depth)
    if spread_cents is not None and spread_cents > cfg["max_spread_cents"]:
        return False, "spread %dc > max (untradeable)" % spread_cents
    ev = kalshi_net(count, price, fair)
    if ev["net"] <= 0 or ev["net_pct"] < cfg["min_net_edge_pct"]:
        return False, "net edge %.1f%% < %.0f%% after fee" % (ev["net_pct"] * 100, cfg["min_net_edge_pct"] * 100)
    return True, ev


# ---------------- lanes ----------------

def lane_sharp_sports(cfg):
    """The proven lane: a hand-verified/live sharp fair prob vs Kalshi's ask."""
    cands = []
    for tk in sharp_lines.overridden_tickers():
        sf = sharp_lines.sharp_fair(tk)
        if not sf:
            continue
        try:
            yb, ya, nb, yc, nc = best_bbo(tk)
        except Exception:
            continue
        if yb is None or ya is None:
            continue
        fair = sf["fair_prob"]
        spread = ya - yb
        # STALENESS GUARD ("get with the times", 2026-06-06): a hand/cached sharp
        # number goes stale the instant the game state moves. If our sharp fair is
        # far from where the liquid market actually sits, the OVERRIDE is stale --
        # never bet on it. (Caught a Game-1 55% number trying to trade a 2-0, 80%
        # market.) Refresh the line instead.
        mid = (yb + ya) / 2.0
        div = abs(fair * 100 - mid)
        if div > cfg.get("override_stale_divergence_cents", 8):
            print("  STALE %-30s sharp %.0f%% vs market mid %.0fc (gap %.0fc) -- skip, refresh the line" % (
                tk[:30], fair * 100, mid, div))
            continue
        # MAKER bid at the highest price that still clears our net-edge floor,
        # always below the ask (rests as a maker; fills on a dip/seller).
        our_cents = best_maker_cents(cfg, fair, ya)
        cands.append({"lane": "sharp_sports", "ticker": tk, "side": "yes",
                      "our_cents": our_cents, "fair": fair, "ask": ya, "bid": yb,
                      "depth": yc or 0, "spread": spread, "source": sf["source"]})
    return cands


def lane_favorite_longshot(cfg):
    try:
        from kalshi_agent.hunt_favorites import scan
    except Exception:
        return []
    out = []
    for c in scan(stake=cfg["per_bet_max_usd"], max_markets=80)[: cfg.get("favorite_longshot_max_picks", 3)]:
        out.append({"lane": "favorite_longshot", "ticker": c["ticker"], "side": c["side"],
                    "our_cents": c["buy_c"], "fair": c["our_prob"], "ask": c["buy_c"],
                    "bid": None, "depth": c.get("depth", 0), "spread": None,
                    "source": "favorite-longshot +%.0f%% hypothesis" % ((c["our_prob"] - c["implied"]) * 100)})
    return out


def lane_arbitrage(cfg):
    """Locked-profit detector: yes_ask + no_ask < 100 (minus a fee buffer).
    v1 ALERTS only -- two-leg execution has fill risk; we verify by hand first."""
    hits = []
    for tk in sharp_lines.overridden_tickers():
        try:
            yb, ya, nb, yc, nc = best_bbo(tk)
        except Exception:
            continue
        if ya is None:
            continue
        na = (100 - nb) if nb is not None else None
        if na is not None and (ya + na) < 98:
            hits.append({"ticker": tk, "yes_ask": ya, "no_ask": na, "lock_c": 100 - (ya + na)})
    return hits


# ---------------- run ----------------

def run(live=False):
    cfg = load_config()
    live = live and cfg.get("live", False)
    print("=" * 64)
    print("  AUTO-EDGE ENGINE", "[LIVE]" if live else "[DRY-RUN]", time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()))
    print("=" * 64)

    if halted():
        print("  HALTED by kill switch (AUTO_EDGE_HALT present). Nothing runs.")
        return 0

    balance, positions = None, []
    if live:
        from kalshi_agent.execution.kalshi_exec import from_creds
        k = from_creds()
        balance = k.get_balance()
        positions = k.get_positions()
        if balance < cfg["min_balance_floor_usd"]:
            print("  balance $%.2f < floor $%.2f -- HALT." % (balance, cfg["min_balance_floor_usd"]))
            return 0
    held = held_tickers(positions)
    # money-idempotency: a real position, or a maker bid we already placed in the
    # last 3 days (so the cron doesn't re-post the same resting bid every cycle).
    # A logged scorecard prediction does NOT block a bet -- that's measurement only.
    recent_placed = {r["ticker"] for r in _ledger_rows()
                     if r.get("placed") and (time.time() - r.get("ts", 0) < 3 * 86400)}
    spent_today = daily_spent()
    total_exposure = sum(float(p.get("market_exposure", 0) or 0) / 100.0 for p in positions) if live else 0.0
    print("  balance=%s  spent_today=$%.2f  exposure=$%.2f  held=%d" % (
        ("$%.2f" % balance) if balance is not None else "n/a", spent_today, total_exposure, len(held)))

    # ---- OPERATOR BETS (highest priority): Rich's explicit calls. They BYPASS the
    # edge gate -- his read IS the signal -- but still respect caps + balance floor +
    # idempotency. TAKER fills (post_only=False) so the position actually goes on,
    # unlike a resting maker that can miss. Added 2026-06-08 after we failed to act
    # on a directly-stated Spurs bet. Automation that ignores the operator isn't.
    already = {r.get("op_id") for r in _ledger_rows() if r.get("op_id")}
    for b in load_operator_bets():
        opid = str(b.get("id") or (b.get("ticker", "") + "-" + str(b.get("ts", ""))))
        if opid in already:
            continue
        tk, side = b.get("ticker"), b.get("side", "yes")
        stake = float(b.get("stake_usd") or cfg["per_bet_max_usd"])
        if not tk or tk in held:
            print("  OP-BET skip %s (no ticker / already held)" % (tk or "?")); continue
        try:
            yb, ya, nb, yc, nc = best_bbo(tk)
        except Exception:
            ya = None
        maxp = int(b.get("max_price_c") or (ya if ya else 99))
        price_c = min(int(ya) if ya else maxp, maxp)
        if not (1 <= price_c <= 99):
            print("  OP-BET skip %s (no usable price)" % tk); continue
        room = min(stake, cfg["daily_max_usd"] - spent_today,
                   cfg["total_exposure_max_usd"] - total_exposure,
                   (max(0.0, balance - cfg["min_balance_floor_usd"]) if live else stake))
        count = int(room // (price_c / 100.0))
        print("  OP-BET %s %s x%d @ %dc  (stake $%.0f -- %s)" % (
            side.upper(), tk, count, price_c, stake, (b.get("note") or "operator call")[:45]))
        scorecard.record("operator", tk, side, price_c / 100.0, price_c / 100.0,
                         reasoning=(b.get("note") or "operator")[:110])
        if not live:
            continue
        if count < 1:
            notify("OP-BET %s could NOT place: caps/balance left no room (raise caps or free exposure)." % tk)
            continue
        from kalshi_agent.execution.kalshi_exec import from_creds
        k = from_creds()
        try:
            o = k.place_order(tk, side=side, action="buy", count=count, price_cents=price_c, post_only=False)
            cost = count * price_c / 100.0
            spent_today += cost; total_exposure += cost
            log_ledger({"ts": int(time.time()), "day": _today(), "lane": "operator", "ticker": tk,
                        "side": side, "count": count, "price_c": price_c, "cost": round(cost, 2),
                        "placed": True, "op_id": opid, "order_id": o.get("order_id"),
                        "source": "operator: " + (b.get("note") or "")})
            notify("OPERATOR BET FILLED-ORDER %s %s x%d @ %dc -> %s" % (side.upper(), tk, count, price_c, o.get("order_id")))
        except Exception as e:
            log_ledger({"ts": int(time.time()), "day": _today(), "lane": "operator", "ticker": tk,
                        "placed": False, "op_id": opid, "error": str(e)[:140]})
            print("    OP-BET rejected: %s" % str(e)[:90])

    modes = cfg["lanes"]
    candidates = []
    if modes.get("sharp_sports") in ("bet", "log"):
        candidates += lane_sharp_sports(cfg)
    if modes.get("favorite_longshot") in ("bet", "log"):
        candidates += lane_favorite_longshot(cfg)

    # arbitrage: alert-only
    if modes.get("arbitrage") in ("alert", "bet"):
        for a in lane_arbitrage(cfg):
            notify("auto-edge ARB watch: %s yes_ask %dc + no_ask %dc -> lock %dc" % (
                a["ticker"], a["yes_ask"], a["no_ask"], a["lock_c"]))

    placed = 0
    for c in candidates:
        mode = modes.get(c["lane"], "off")
        tk = c["ticker"]
        if tk in held or tk in recent_placed:
            print("  skip %-32s (already held / bid placed)" % tk[:32])
            continue
        if c["our_cents"] is None or c["our_cents"] < 1:
            print("  skip %-32s (no maker price)" % tk[:32])
            continue
        count = size_bet(cfg, c["our_cents"] / 100.0, balance or 0.0, spent_today, total_exposure) if mode == "bet" and live else max(1, int(cfg["per_bet_max_usd"] // (c["our_cents"] / 100.0)))
        ok, info = gate(cfg, count, c["our_cents"], c["fair"], c["depth"], c["spread"])
        edge_pct = c["fair"] - c["our_cents"] / 100.0
        tag = "[%s/%s]" % (c["lane"], mode)
        if not ok:
            print("  PASS %-30s %s  buy %dc fair %.0f%%  -- %s" % (tk[:30], tag, c["our_cents"], c["fair"] * 100, info))
            continue
        ev = info
        print("  EDGE %-30s %s  buy %dc fair %.0f%% (+%.1f%% raw, +%.1f%% net) x%d depth$%d" % (
            tk[:30], tag, c["our_cents"], c["fair"] * 100, edge_pct * 100, ev["net_pct"] * 100, count, int(c["depth"])))

        # log to scorecard (measurement) for bet+log lanes
        scorecard.record(c["lane"], tk, c["side"], c["fair"], c["our_cents"] / 100.0,
                         reasoning=c["source"][:110])

        if mode != "bet" or not live:
            continue
        # ---- place the maker bid ----
        from kalshi_agent.execution.kalshi_exec import from_creds
        k = from_creds()
        try:
            o = k.place_order(tk, side=c["side"], action="buy", count=count,
                              price_cents=c["our_cents"], post_only=True)
            cost = count * c["our_cents"] / 100.0
            spent_today += cost
            total_exposure += cost
            placed += 1
            row = {"ts": int(time.time()), "day": _today(), "lane": c["lane"], "ticker": tk,
                   "side": c["side"], "count": count, "price_c": c["our_cents"], "cost": round(cost, 2),
                   "fair": c["fair"], "net_pct": round(ev["net_pct"], 4), "placed": True,
                   "order_id": o.get("order_id"), "source": c["source"]}
            log_ledger(row)
            notify("auto-edge BET %s %s x%d @ %dc (fair %.0f%%, +%.1f%% net) -> %s" % (
                c["side"].upper(), tk, count, c["our_cents"], c["fair"] * 100, ev["net_pct"] * 100, o.get("order_id")))
        except Exception as e:
            log_ledger({"ts": int(time.time()), "day": _today(), "lane": c["lane"], "ticker": tk,
                        "price_c": c["our_cents"], "placed": False, "error": str(e)[:140]})
            print("    rejected: %s" % str(e)[:90])
    print("  placed %d maker bid(s)." % placed)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="place real orders (respects config caps; e5 only)")
    ap.add_argument("--op-add", nargs="+", metavar="ARG",
                    help="enqueue an operator bet then run: TICKER SIDE STAKE [MAXPRICE_C] [note words...]")
    args = ap.parse_args()
    if args.op_add:
        a = args.op_add
        ticker, side, stake = a[0], a[1], float(a[2])
        maxp = int(a[3]) if len(a) > 3 and a[3].isdigit() else None
        note = " ".join(a[4:]) if len(a) > 4 else (" ".join(a[3:]) if (len(a) > 3 and maxp is None) else "")
        b = enqueue_operator_bet(ticker, side, stake, maxp, note)
        print("ENQUEUED operator bet:", json.dumps(b))
    return run(live=args.live)


if __name__ == "__main__":
    import sys
    sys.exit(main())
