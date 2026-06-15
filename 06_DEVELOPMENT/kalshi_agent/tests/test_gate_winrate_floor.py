"""Regression test for the win-rate-floor bypass that bled the record 2026-06-11..14.

Bug: the win-prob floor (min_fair_prob_sharp) only fired for multi-book (>=5)
"sharp" bets. The World Cup slate had ZERO Odds-API coverage -> every soccer bet
was single-book (books=1) -> sharp=False -> the floor was skipped -> we bet 10-25c
longshots that lose ~80% of the time and dragged the win rate from ~75% to ~44%.

These assert the floor now protects EVERY sharp-lane bet, and that a single book
can't claim a giant (stale) edge. Pure logic, no network.

    python3 -m kalshi_agent.tests.test_gate_winrate_floor
"""
from kalshi_agent.auto_edge import gate, conviction_stake

# simulate the controller having set a 60% win-prob floor (a calm, mid-range value)
CFG = {
    "sanity_max_raw_edge": 0.40,
    "min_abs_edge_prob": 0.03,
    "min_abs_edge_prob_sharp": 0.02,
    "sharp_min_books": 5,
    "min_fair_prob_sharp": 0.60,
    "single_book_max_edge": 0.15,
    "min_bet_contracts": 2,
    "require_consensus_books": 2,
    "min_depth_dollars": 2000,
    "max_spread_cents": 6,
    "min_net_edge_pct": 0.03,
}
DEEP, SPREAD = 99999, 2


def _rej(**kw):
    ok, info = gate(CFG, kw["count"], kw["our_cents"], kw["fair"], DEEP, SPREAD,
                    kw["books"], kw.get("lane"))
    return ok, info


def main():
    fails = []

    # 1) single-book longshot (South Africa 10c, fair 13%) -- MUST be blocked by the
    #    win-prob floor now (before the fix it slipped through because books<5).
    ok, why = _rej(count=79, our_cents=10, fair=0.1331, books=1)
    if ok or "win-prob floor" not in str(why):
        fails.append("single-book longshot should hit win-prob floor, got ok=%s why=%s" % (ok, why))

    # 2) single-book FAKE favorite (Australia "56%" vs 18c market, +38pt edge) -- MUST be
    #    blocked as a stale single-book edge (only a consensus earns trust for a big gap).
    ok, why = _rej(count=44, our_cents=18, fair=0.5607, books=1)
    if ok or "single-book edge" not in str(why):
        fails.append("single-book fake favorite should hit single-book edge cap, got ok=%s why=%s" % (ok, why))

    # 3) 1-contract dust -- MUST be blocked by the contract floor.
    ok, why = _rej(count=1, our_cents=75, fair=0.78, books=9)
    if ok or "min" not in str(why):
        fails.append("1-contract dust should hit contract floor, got ok=%s why=%s" % (ok, why))

    # 4) a real CONSENSUS favorite (9 books, fair 78%, 75c) must NOT be rejected for any of
    #    the new reasons (it can still fail net-EV after fee -- that's fine, just not these).
    ok, why = _rej(count=10, our_cents=75, fair=0.7837, books=9)
    bad = any(s in str(why) for s in ("win-prob floor", "single-book edge", "contract min"))
    if bad:
        fails.append("consensus favorite wrongly blocked by a new guard: %s" % (why,))

    # 5) a single-book pick that IS above the floor with a modest edge stays bettable
    #    (variety preserved -- not every soccer bet dies, just the longshots).
    ok, why = _rej(count=10, our_cents=62, fair=0.66, books=1)
    if "win-prob floor" in str(why) or "single-book edge" in str(why):
        fails.append("reasonable single-book favorite wrongly blocked: %s" % (why,))

    # 6) NO-COVERAGE on the sharp lane: a single-book bet (the whole WC slate) is BLIND and
    #    must be skipped outright, even a reasonable-looking favorite. This is the soccer fix.
    ok, why = _rej(count=10, our_cents=62, fair=0.66, books=1, lane="sharp_sports")
    if ok or "betting blind" not in str(why):
        fails.append("single-book sharp bet should be skipped as betting blind, got ok=%s why=%s" % (ok, why))

    # 7) ...but a 2+ book CONSENSUS clears the coverage gate (still subject to the other guards).
    ok, why = _rej(count=10, our_cents=75, fair=0.78, books=6, lane="sharp_sports")
    if "betting blind" in str(why):
        fails.append("a 6-book consensus should clear the coverage gate, got why=%s" % (why,))

    # ---- CONVICTION SIZING (Rich: bigger bet when the logic supports it) ----
    CONV = {"conviction_sizing": True, "conviction_min_usd": 3.0, "conviction_max_usd": 12.0,
            "conviction_full_edge": 0.10, "conviction_fresh_bonus": 0.10, "sharp_min_books": 5,
            "conviction_weights": {"edge": 0.40, "books": 0.35, "safety": 0.25}, "per_bet_max_usd": 8.0}
    # monster: +9pt edge, 9-book consensus, 85% favorite -> near the top of the envelope
    strong = conviction_stake(CONV, fair=0.85, our_cents=76, books=9)
    # marginal: +3pt edge, 2-book, near coin-flip -> near the floor
    weak = conviction_stake(CONV, fair=0.55, our_cents=52, books=2)
    if not (strong > weak):
        fails.append("conviction: strong (%.2f) should stake more than weak (%.2f)" % (strong, weak))
    if not (strong > CONV["per_bet_max_usd"]):
        fails.append("conviction: a monster edge (%.2f) should be able to exceed the old flat $%.0f" % (
            strong, CONV["per_bet_max_usd"]))
    if not (CONV["conviction_min_usd"] <= weak <= strong <= CONV["conviction_max_usd"]):
        fails.append("conviction: stakes must stay within [min,max], got weak=%.2f strong=%.2f" % (weak, strong))

    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        raise SystemExit(1)
    print("OK: win-rate floor now protects every sharp bet; single-book stale edges capped; dust blocked.")


if __name__ == "__main__":
    main()
