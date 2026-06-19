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
UPCOMING = HERE / "data" / "upcoming_edges.json"   # what the engine is about to bet (for the dashboard)
WD_STATE = HERE / "data" / "watchdog_state.json"   # the watchdog's brakes+gas (quarantines + lean-ins)

_SPORT_PREFIX = (("KXNBA", "nba"), ("KXMLB", "mlb"), ("KXNHL", "nhl"), ("KXWC", "wc"),
                 ("KXUFC", "ufc"), ("KXNFL", "nfl"), ("KXWNBA", "wnba"),
                 ("KXKBO", "kbo"), ("KXNPB", "npb"))


def sport_of(ticker):
    t = (ticker or "").upper()
    for pre, sp in _SPORT_PREFIX:
        if t.startswith(pre):
            return sp
    return "other"


def load_watchdog_state():
    """The self-healing watchdog's live decisions: {quarantine:{seg:{until,..}}, lean_in:{seg:{until,mult,..}}}.
    Expired entries drop on read so brakes/gas auto-release. Missing file = no-op (engine runs normally)."""
    try:
        st = json.loads(WD_STATE.read_text())
    except Exception:
        return {"quarantine": {}, "lean_in": {}}
    now = time.time()
    return {"quarantine": {k: v for k, v in st.get("quarantine", {}).items() if v.get("until", 0) > now},
            "lean_in": {k: v for k, v in st.get("lean_in", {}).items() if v.get("until", 0) > now}}


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


def _live_book(k):
    """Rebuild from FILLS (the only honest source -- /positions reports 0): the open
    positions we actually hold {ticker: {contracts, avg, side}} and the P&L we have
    REALIZED today. The press lane needs both: what to add to, and how much locked
    profit is available to fund it."""
    from collections import defaultdict
    fills = k._request("GET", "/portfolio/fills").get("fills", [])
    setls = {s["ticker"]: s for s in k._request("GET", "/portfolio/settlements").get("settlements", [])}
    agg = defaultdict(lambda: {"contracts": 0.0, "cost": 0.0, "side": None})
    for f in fills:
        tk, sd = f.get("ticker"), f.get("side")
        c = float(f.get("count_fp") or 0)
        px = float(f.get("yes_price_dollars") or 0) if sd == "yes" else float(f.get("no_price_dollars") or 0)
        sgn = 1 if f.get("action") == "buy" else -1
        a = agg[tk]; a["contracts"] += sgn * c; a["cost"] += sgn * c * px
        if a["side"] is None:
            a["side"] = sd
    today = _today()
    realized_today, openpos = 0.0, {}
    for tk, a in agg.items():
        if abs(a["contracts"]) < 0.01:
            continue
        if tk in setls:
            s = setls[tk]
            if (s.get("settled_time") or "")[:10] == today:
                won = s.get("market_result") == a["side"]
                realized_today += (a["contracts"] if won else 0.0) - a["cost"]
        else:
            openpos[tk] = {"contracts": a["contracts"], "side": a["side"], "cost": a["cost"],
                           "avg": a["cost"] / a["contracts"] if a["contracts"] else 0.0}
    return openpos, realized_today


def settled_record(k, n=25):
    """Win/loss over our last n SETTLED bets (our side vs the result). The realized
    hit rate the win-rate controller steers on."""
    fills = k._request("GET", "/portfolio/fills").get("fills", [])
    setls = k._request("GET", "/portfolio/settlements").get("settlements", [])
    side = {}
    for f in fills:
        side.setdefault(f.get("ticker"), f.get("side"))
    rows = [(s.get("settled_time", ""), s.get("market_result") == side[s["ticker"]])
            for s in setls if s.get("ticker") in side]
    rows.sort(reverse=True)
    recent = rows[:n]
    wins = sum(1 for _, w in recent if w)
    return wins, len(recent) - wins, (wins / len(recent) if recent else None)


def win_prob_floor(cfg, winrate):
    """THE MAINTENANCE FORMULA. Effective sharp-lane win-prob floor:
        floor = base + gain * (target - realized_hit_rate),  clamped to [base, max].
    Below target -> floor rises -> only stronger favorites clear -> hit rate recovers.
    Above target -> floor eases to base -> more volume. Self-correcting toward target."""
    base = cfg.get("win_floor_base", 0.60)
    if winrate is None:
        return base
    f = base + cfg.get("win_floor_gain", 1.5) * (cfg.get("target_win_rate", 0.72) - winrate)
    return max(base, min(cfg.get("win_floor_max", 0.86), f))


def conviction_stake(cfg, fair, our_cents, books, is_fresh=False):
    """CONVICTION-WEIGHTED stake (Rich 2026-06-15: "if the logic supports it, place a bigger
    bet -- be adaptive in a good way too, don't limit yourself"). Flat $8-on-everything
    over-bets a marginal edge and under-bets a monster one. Conviction blends three evidence
    signals -- edge size, multi-book CONSENSUS strength, and favorite safety -- into a dollar
    stake in [conviction_min_usd, conviction_max_usd]. The hard caps (daily / exposure /
    balance floor) still bound it; this only decides WHERE in the envelope a bet sits."""
    if not cfg.get("conviction_sizing", True):
        return cfg["per_bet_max_usd"]
    raw_edge = max(0.0, fair - our_cents / 100.0)
    edge_s = min(1.0, raw_edge / cfg.get("conviction_full_edge", 0.10))            # 10pt gap = full marks
    span = max(1, cfg.get("sharp_min_books", 5) - 2)
    books_s = min(1.0, max(0.0, (books - 2) / float(span)))                        # 2bk=0 .. 5+bk=full
    safe_s = min(1.0, max(0.0, (fair - 0.50) / 0.40))                              # 50%=0 .. 90%+=full
    w = cfg.get("conviction_weights", {"edge": 0.40, "books": 0.35, "safety": 0.25})
    conv = w["edge"] * edge_s + w["books"] * books_s + w["safety"] * safe_s
    if is_fresh:
        conv = min(1.0, conv + cfg.get("conviction_fresh_bonus", 0.10))
    lo, hi = cfg.get("conviction_min_usd", 3.0), cfg.get("conviction_max_usd", 12.0)
    return round(lo + conv * (hi - lo), 2)


def size_bet(cfg, price, balance, spent_today, total_exposure, stake_usd=None):
    """Largest contract count that fits every cap. price in dollars. stake_usd = the
    conviction-chosen target stake (defaults to the flat per-bet max); the hard daily /
    exposure / balance-floor caps still clamp it -- the ruin-prevention governor."""
    cap = stake_usd if stake_usd is not None else cfg["per_bet_max_usd"]
    room = min(cap,
               cfg["daily_max_usd"] - spent_today,
               cfg["total_exposure_max_usd"] - total_exposure,
               max(0.0, balance - cfg["min_balance_floor_usd"]))
    if room <= 0 or price <= 0:
        return 0
    return int(room // price)


def gate(cfg, count, our_cents, fair, depth, spread_cents, books=1, lane=None):
    """Every guardrail in one place. Returns (ok, reason)."""
    # NO-COVERAGE GUARD (Rich 2026-06-15: "if we don't have coverage it's betting blind").
    # The sharp lane's whole trust comes from a MULTI-BOOK consensus -- one bookmaker's number
    # is a rumor, not a signal. When the odds service has no coverage for a market (the entire
    # World Cup slate -> 0 games -> ESPN single-book fallback -> books=1), we'd be betting BLIND
    # on one book -- exactly the soccer bleed. Require >= require_consensus_books independent
    # books on the sharp lane. (favorite_longshot is a Kalshi-internal screen, not book-backed,
    # so it's exempt -- this only fences the consensus-dependent sharp lane.)
    if lane == "sharp_sports" and books < cfg.get("require_consensus_books", 2):
        return False, "no multi-book coverage (%d book) -- betting blind, skip" % books
    # DUST floor: a 1-contract bet is noise -- it clutters the record/dashboard with
    # extra reds (and meaningless greens) without moving money. Keep small bets, kill dust.
    if count < cfg.get("min_bet_contracts", 1):
        return False, "size %d < %d-contract min (dust/caps)" % (count, cfg.get("min_bet_contracts", 1))
    price = our_cents / 100.0
    raw_edge = fair - price
    if abs(raw_edge) > cfg["sanity_max_raw_edge"]:
        return False, "edge %.0f%% > sanity cap (likely a bug/stale)" % (raw_edge * 100)
    # ABSOLUTE-edge floor: a 1-2 point gap vs a SINGLE book is de-vig NOISE. But a
    # multi-book CONSENSUS (>= sharp_min_books via The Odds API) is sharp enough to
    # trust a smaller gap -- that is the whole point of the consensus: more real edges
    # become bettable without lowering the standard. The net-EV floor still applies.
    sharp = books >= cfg.get("sharp_min_books", 4)
    floor = cfg.get("min_abs_edge_prob_sharp", cfg.get("min_abs_edge_prob", 0.0)) if sharp \
        else cfg.get("min_abs_edge_prob", 0.0)
    if raw_edge < floor:
        return False, "abs gap %.1fpts < %.1fpt floor (%s)" % (
            raw_edge * 100, floor * 100, ("sharp %dbk" % books) if sharp else "single-book noise")
    # SINGLE-BOOK STALE CAP (2026-06-15): one book claiming a huge edge is almost always
    # STALE/WRONG, not gold -- it cuts both ways (a lone book at 13% made South Africa look
    # +31% EV; a lone book at 56% made Australia look +210% EV). Only a multi-book CONSENSUS
    # earns trust for a big gap; a single book gets a hard ceiling. The whole World Cup slate
    # is single-book right now (Odds API has 0 WC games), so this is where the bleed lived.
    if not sharp and raw_edge > cfg.get("single_book_max_edge", 0.15):
        return False, "single-book edge %.0fpt > %.0fpt cap (stale -- need consensus)" % (
            raw_edge * 100, cfg.get("single_book_max_edge", 0.15) * 100)
    # WIN-RATE GUARD (Rich 2026-06-10, BYPASS FIXED 2026-06-15): skip sub-floor win-prob
    # longshots -- great EV but they lose most of the time and drag the hit rate Rich cares
    # about. This now protects EVERY sharp-lane bet, not just multi-book ones -- the old
    # `if sharp and` clause let single-book longshots (the entire WC slate) skip it, which
    # is exactly what flipped the record green->red. The controller sets the floor each run.
    if fair < cfg.get("min_fair_prob_sharp", 0.0):
        return False, "fair %.0f%% < %.0f%% win-prob floor (protects hit rate)" % (
            fair * 100, cfg.get("min_fair_prob_sharp", 0.0) * 100)
    # PAYOUT-RATIO CEILING (Rich 2026-06-15: "$8 to win $16 is cool, $6.15 to win $7 is
    # ridiculous"). Never overpay for a favorite -- a win must be WORTH taking. Buying at
    # `our_cents` risks that to win (100-our_cents); above max_buy_price_c the payout/risk is
    # too thin to support the 2:1 profit-factor target (one loss eats many wins). This is the
    # geometry fix that lets a 75% win rate actually MAKE money. Operator bets bypass gate().
    maxc = cfg.get("max_buy_price_c", 100)
    if our_cents > maxc:
        return False, "buy %dc > %dc ceiling -- win only %dc per %dc risked (payout too thin)" % (
            our_cents, maxc, 100 - our_cents, our_cents)
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
        mid = (yb + ya) / 2.0
        div = abs(fair * 100 - mid)
        # FRESHNESS-AWARE GUARD (2026-06-09, Rich: "the more inaccurate, the more
        # margin... don't let the misprice fool you -- it could be opportunity").
        # A big gap means one of two things: (a) the sharp number is STALE -> skip;
        # or (b) the number is FRESH (daily_research just pulled the book) and Kalshi
        # is LAGGING -> that's the opportunity, and the bigger the gap the fatter the
        # margin. Tell them apart by the override's freshness, not by gap size alone.
        fresh_ts = sf.get("fresh_ts")
        is_fresh = bool(fresh_ts) and (time.time() - fresh_ts) < cfg.get("fresh_window_sec", 7200)
        stale_gap = cfg.get("override_stale_divergence_cents", 8)
        if div > stale_gap and not is_fresh:
            print("  STALE %-30s sharp %.0f%% vs mid %.0fc (gap %.0fc, line not fresh) -- skip" % (
                tk[:30], fair * 100, mid, div))
            continue
        # Grab a FAT FRESH mispricing by TAKING the offer (lock the margin before it
        # corrects); rest a maker for ordinary thin edges.
        net_at_ask = kalshi_net(10, ya / 100.0, fair)["net_pct"]
        if is_fresh and div > stale_gap and net_at_ask >= 2 * cfg["min_net_edge_pct"]:
            our_cents, post_only = ya, False
            print("  OPPORTUNITY %-30s FRESH %.0f%% vs Kalshi %.0fc (gap %.0fc, +%.1f%% net at ask) -- TAKING IT" % (
                tk[:30], fair * 100, mid, div, net_at_ask * 100))
        else:
            our_cents, post_only = best_maker_cents(cfg, fair, ya), True
        cands.append({"lane": "sharp_sports", "ticker": tk, "side": "yes",
                      "our_cents": our_cents, "fair": fair, "ask": ya, "bid": yb,
                      "depth": yc or 0, "spread": spread, "source": sf["source"],
                      "post_only": post_only, "books": sf.get("books", 1)})
    return cands


def lane_favorite_longshot(cfg):
    try:
        from kalshi_agent.hunt_favorites import scan
    except Exception:
        return []
    out = []
    cap = cfg.get("favorite_longshot_max_buy_c", 92)   # avoid 95c+ dust (one upset wipes ~19 wins)
    picks = [c for c in scan(stake=cfg["per_bet_max_usd"], max_markets=80) if c["buy_c"] <= cap]
    for c in picks[: cfg.get("favorite_longshot_max_picks", 3)]:
        out.append({"lane": "favorite_longshot", "ticker": c["ticker"], "side": c["side"],
                    "our_cents": c["buy_c"], "fair": c["our_prob"], "ask": c["buy_c"],
                    "bid": None, "depth": c.get("depth", 0), "spread": None, "post_only": True,
                    "source": "favorite-longshot +%.0f%% hypothesis" % ((c["our_prob"] - c["implied"]) * 100)})
    return out


def lane_press_winners(cfg, open_book, realized_today):
    """Profit-funded double-down. Add to an OPEN position ONLY when every test holds:
      * we are already net-green for the day (realized_today >= press_min_daily_profit);
      * the position's sharp number is FRESH; and the live ask STILL shows real edge
        (>= the absolute-edge floor) -- never press just because price moved our way;
      * the price has NOT collapsed below our entry (a falling knife = our pre-game
        number is stale, the Astros trap) -- press_max_adverse_cents;
      * the edge isn't too-good-to-be-true (a huge gap at press time = stale live
        number, not a gift) -- press_max_trusted_edge.
    Sized from a fraction of LOCKED profit, capped so the night stays net-green."""
    out = []
    floor_profit = cfg.get("press_min_daily_profit_usd", 15.0)
    if realized_today < floor_profit:
        return out
    bankroll = min(cfg.get("press_fraction", 0.5) * realized_today,
                   realized_today - cfg.get("press_keep_min_profit_usd", 12.0))
    if bankroll <= 0:
        return out
    for tk, pos in open_book.items():
        if pos["side"] != "yes":          # v1 presses the yes-side sharp positions only
            continue
        sf = sharp_lines.sharp_fair(tk)
        if not sf:
            continue
        fresh_ts = sf.get("fresh_ts")
        if not (bool(fresh_ts) and (time.time() - fresh_ts) < cfg.get("fresh_window_sec", 7200)):
            continue
        try:
            yb, ya, nb, yc, nc = best_bbo(tk)
        except Exception:
            continue
        if ya is None:
            continue
        fair, avg_c = sf["fair_prob"], pos["avg"] * 100
        add_edge = fair - ya / 100.0
        if fair < cfg.get("min_fair_prob_sharp", 0.0):
            continue                      # never PRESS a longshot -- it pressed South Africa
                                          # at 13% on 2026-06-11; same win-rate floor as the gate
        if ya < avg_c - cfg.get("press_max_adverse_cents", 6):
            continue                      # falling knife -- stale model vs a live drop
        if add_edge > cfg.get("press_max_trusted_edge", 0.12):
            continue                      # too good to be true at press time = stale
        if add_edge < cfg.get("min_abs_edge_prob", 0.03):
            continue                      # not enough fresh edge left to add
        out.append({"lane": "press_winners", "ticker": tk, "side": "yes",
                    "our_cents": ya, "fair": fair, "ask": ya, "bid": yb,
                    "depth": yc or 0, "spread": (ya - yb) if yb else None,
                    "post_only": False, "bankroll": bankroll, "avg": pos["avg"],
                    "source": "press locked-profit: +%.1fpt fresh edge at %dc (entry %.0fc)" % (
                        add_edge * 100, ya, avg_c)})
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
    wd_state = load_watchdog_state()      # the watchdog's brakes (quarantine) + gas (lean-in)
    live = live and cfg.get("live", False)
    print("=" * 64)
    print("  AUTO-EDGE ENGINE", "[LIVE]" if live else "[DRY-RUN]", time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()))
    print("=" * 64)

    if halted():
        print("  HALTED by kill switch (AUTO_EDGE_HALT present). Nothing runs.")
        return 0

    balance, positions = None, []
    open_book, realized_today = {}, 0.0
    if live:
        from kalshi_agent.execution.kalshi_exec import from_creds
        k = from_creds()
        balance = k.get_balance()
        positions = k.get_positions()
        if balance < cfg["min_balance_floor_usd"]:
            print("  balance $%.2f < floor $%.2f -- HALT." % (balance, cfg["min_balance_floor_usd"]))
            return 0
        try:
            open_book, realized_today = _live_book(k)
        except Exception as e:
            print("  (press book unavailable: %s)" % str(e)[:60])
    else:
        try:
            from kalshi_agent.execution.kalshi_exec import from_creds as _fc
            open_book, realized_today = _live_book(_fc())
        except Exception:
            pass
    # WIN-RATE MAINTENANCE CONTROLLER: steer the sharp-lane win-prob floor off the
    # realized hit rate so the system holds the target instead of drifting down.
    try:
        from kalshi_agent.execution.kalshi_exec import from_creds as _fcw
        _w, _l, _wr = settled_record(_fcw())
        cfg["min_fair_prob_sharp"] = win_prob_floor(cfg, _wr)
        print("  win-rate %s (%d-%d) -> sharp win-prob floor %.0f%% (target %.0f%%)" % (
            ("%.0f%%" % (_wr * 100)) if _wr is not None else "n/a", _w, _l,
            cfg["min_fair_prob_sharp"] * 100, cfg.get("target_win_rate", 0.72) * 100))
    except Exception:
        pass
    # idempotency for the normal lanes: never re-bet anything we already hold (open_book
    # is reliable; /positions is not). The press lane targets these on purpose, below.
    held = held_tickers(positions) | set(open_book.keys())
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

    # ---- PRESS WINNERS (profit-funded double-down, Rich 2026-06-10): add to an OPEN
    # position only where it STILL shows fresh real edge at the live ask, funded by a
    # slice of LOCKED daily profit, capped so the night stays net-green. 'log' proves
    # it flags the right spots without spending; 'bet' makes it live.
    press_mode = modes.get("press_winners", "off")
    if press_mode in ("bet", "log"):
        print("  press: realized today $%.2f (need >$%.0f to arm)" % (
            realized_today, cfg.get("press_min_daily_profit_usd", 15.0)))
        prior = [r for r in _ledger_rows() if r.get("lane") == "press_winners"
                 and r.get("day") == _today() and r.get("placed")]
        pressed_ct, press_spent = {}, 0.0
        for r in prior:
            pressed_ct[r["ticker"]] = pressed_ct.get(r["ticker"], 0) + 1
            press_spent += r.get("cost", 0.0)
        for c in lane_press_winners(cfg, open_book, realized_today):
            tk = c["ticker"]
            if sport_of(tk) in wd_state["quarantine"]:
                print("  PRESS skip %-28s (watchdog quarantine)" % tk[:28]); continue
            if pressed_ct.get(tk, 0) >= cfg.get("press_max_adds_per_ticker", 1):
                print("  PRESS skip %-28s (already pressed today)" % tk[:28]); continue
            room = min(cfg.get("press_per_add_max_usd", 6.0), c["bankroll"] - press_spent)
            if live:
                room = min(room, cfg["daily_max_usd"] - spent_today,
                           cfg["total_exposure_max_usd"] - total_exposure,
                           max(0.0, (balance or 0) - cfg["min_balance_floor_usd"]))
            count = int(room // (c["our_cents"] / 100.0)) if c["our_cents"] else 0
            print("  PRESS %-28s [%s] add x%d @ %dc (fair %.0f%%) -- %s" % (
                tk[:28], press_mode, count, c["our_cents"], c["fair"] * 100, c["source"]))
            scorecard.record("press_winners", tk, "yes", c["fair"], c["our_cents"] / 100.0,
                             reasoning=c["source"][:110])
            if press_mode != "bet" or not live or count < 1:
                continue
            from kalshi_agent.execution.kalshi_exec import from_creds
            kp = from_creds()
            try:
                o = kp.place_order(tk, side="yes", action="buy", count=count,
                                   price_cents=c["our_cents"], post_only=False)
                cost = count * c["our_cents"] / 100.0
                spent_today += cost; total_exposure += cost; press_spent += cost
                pressed_ct[tk] = pressed_ct.get(tk, 0) + 1
                log_ledger({"ts": int(time.time()), "day": _today(), "lane": "press_winners",
                            "ticker": tk, "side": "yes", "count": count, "price_c": c["our_cents"],
                            "cost": round(cost, 2), "fair": c["fair"], "placed": True,
                            "order_id": o.get("order_id"), "source": c["source"]})
                notify("auto-edge PRESS (locked-profit add) YES %s x%d @ %dc -> %s" % (
                    tk, count, c["our_cents"], o.get("order_id")))
            except Exception as e:
                log_ledger({"ts": int(time.time()), "day": _today(), "lane": "press_winners",
                            "ticker": tk, "placed": False, "error": str(e)[:140]})
                print("    PRESS rejected: %s" % str(e)[:90])

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

    # ONE BET PER GAME (Rich 2026-06-15: "the bot bets both teams on opposite sides"). That is
    # NOT a hedge -- it pays the vig twice and one side always loses (France+Senegal netted
    # -$2.72). Take only the SINGLE best-edge outcome per game. (TRUE arbitrage -- all outcomes
    # priced < 100c combined -- is the separate arb lane, off by default.) Sort best-edge-first
    # so the kept outcome is the strongest, then dedupe by game.
    candidates.sort(key=lambda c: -(((c.get("fair") or 0) - (c.get("our_cents") or 100) / 100.0)))
    def _game_key(t):
        return (t or "").rsplit("-", 1)[0]
    held_games = {_game_key(t) for t in held}
    bet_games = set()

    placed = 0
    flagged = []          # every gate-passing edge this run (for the dashboard's "coming up")
    cap_reached = False
    for c in candidates:
        if live and placed >= cfg.get("max_new_bets_per_run", 2) and not cap_reached:
            print("  (per-run bet cap %d reached -- still flagging the rest for the dashboard)" % cfg.get("max_new_bets_per_run", 2))
            cap_reached = True
        mode = modes.get(c["lane"], "off")
        tk = c["ticker"]
        if tk in held or tk in recent_placed:
            print("  skip %-32s (already held / bid placed)" % tk[:32])
            continue
        gk = _game_key(tk)
        if gk in held_games or gk in bet_games:
            print("  skip %-32s (one-bet-per-game: already betting this game)" % tk[:32])
            continue
        if c["our_cents"] is None or c["our_cents"] < 1:
            print("  skip %-32s (no maker price)" % tk[:32])
            continue
        sp = sport_of(tk)
        q = wd_state["quarantine"].get(sp) or wd_state["quarantine"].get(c["lane"])
        if q:                                 # BRAKES: watchdog quarantined this segment for a cooldown
            print("  skip %-32s (watchdog quarantine: %s)" % (tk[:32], (q.get("reason") or "")[:28]))
            continue
        if mode == "bet" and live:
            stake = conviction_stake(cfg, c["fair"], c["our_cents"], c.get("books", 1), not c.get("post_only", True))
            li = wd_state["lean_in"].get(sp) or wd_state["lean_in"].get(c["lane"])
            if li and li.get("mult"):         # GAS: watchdog leaning into a proven hot segment
                stake = min(stake * li["mult"], cfg.get("conviction_max_usd", 12.0))
            count = size_bet(cfg, c["our_cents"] / 100.0, balance or 0.0, spent_today, total_exposure, stake)
        else:
            count = max(1, int(cfg["per_bet_max_usd"] // (c["our_cents"] / 100.0)))
        ok, info = gate(cfg, count, c["our_cents"], c["fair"], c["depth"], c["spread"], c.get("books", 1), c.get("lane"))
        edge_pct = c["fair"] - c["our_cents"] / 100.0
        tag = "[%s/%s]" % (c["lane"], mode)
        if not ok:
            print("  PASS %-30s %s  buy %dc fair %.0f%%  -- %s" % (tk[:30], tag, c["our_cents"], c["fair"] * 100, info))
            continue
        ev = info
        bet_games.add(gk)     # claim this game -- no second outcome of it gets bet this run
        print("  EDGE %-30s %s  buy %dc fair %.0f%% (+%.1f%% raw, +%.1f%% net) x%d depth$%d" % (
            tk[:30], tag, c["our_cents"], c["fair"] * 100, edge_pct * 100, ev["net_pct"] * 100, count, int(c["depth"])))
        flagged.append({"ticker": tk, "lane": c["lane"], "side": c["side"],
                        "our_cents": c["our_cents"], "fair": c["fair"],
                        "net_pct": ev["net_pct"], "source": c["source"]})

        # log to scorecard (measurement) for bet+log lanes
        scorecard.record(c["lane"], tk, c["side"], c["fair"], c["our_cents"] / 100.0,
                         reasoning=c["source"][:110])

        if mode != "bet" or not live or cap_reached:
            continue
        # ---- place the maker bid ----
        from kalshi_agent.execution.kalshi_exec import from_creds
        k = from_creds()
        try:
            o = k.place_order(tk, side=c["side"], action="buy", count=count,
                              price_cents=c["our_cents"], post_only=c.get("post_only", True))
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
    # publish what the engine is about to bet so the dashboard can show "coming up"
    try:
        UPCOMING.parent.mkdir(parents=True, exist_ok=True)
        flagged.sort(key=lambda x: -x.get("net_pct", 0))
        UPCOMING.write_text(json.dumps({"ts": int(time.time()), "edges": flagged[:8]}, indent=2))
    except Exception:
        pass
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
