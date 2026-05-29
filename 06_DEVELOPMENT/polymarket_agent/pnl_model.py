#!/usr/bin/env python3
"""Polymarket P&L projection model -- honest expected value, not a promise.

Answers: at a $250 bankroll, what is the expected daily/monthly profit, the
target profit, the target (max) loss, and the 30-day balance path -- and WHY.

The model is deterministic expected-value (the median path), bounded by the
real risk rules already coded in risk_manager.py + executor (quarter-Kelly,
5% max bet, 15% daily-loss circuit breaker). Three scenarios bracket the one
variable we cannot know until calibration: the bot's real win rate on the
+EV bets it selects.

Run: python3 pnl_model.py
"""
from dataclasses import dataclass


@dataclass
class Assumptions:
    bankroll: float = 250.0
    avg_stake_pct: float = 0.04      # quarter-Kelly at ~8% edge, price ~0.5 -> ~4%
    max_bet_pct: float = 0.05        # hard cap (executor check 5)
    bets_per_day: int = 3            # qualifying bets after edge>=5% + confidence gates
    spread_cost: float = 0.04        # 3-10% round-trip on thin markets; ~4% typical
    fee_drag: float = 0.02           # 2026 taker fee (peaks at 50c, less at extremes)
    daily_loss_breaker: float = 0.15  # halt the day at -15% (executor check 7)
    days: int = 30


SCENARIOS = {
    # win_rate = fraction of the bot's SELECTED bets that resolve in its favor.
    # Calibrated to the RESEARCH: ~84% of traders lose; honest retail edge is thin.
    # The longshot-fade gives a HIGH raw win rate but small net edge per trade.
    # 0.50 = no edge. Below it the bot bleeds -- the calibration gate catches that.
    "conservative": 0.52,
    "base":         0.55,
    "optimistic":   0.58,
}


def per_bet_return(win_rate: float, spread: float, fee: float = 0.02) -> float:
    """Expected return per $1 staked on a ~even-money outcome, NET of the 2026
    Polymarket taker fee + spread/slippage. EV = (2*wr - 1) - spread - fee."""
    return (2.0 * win_rate - 1.0) - spread - fee


def project(a: Assumptions, win_rate: float):
    daily_ret = a.bets_per_day * a.avg_stake_pct * per_bet_return(
        win_rate, a.spread_cost, a.fee_drag)
    # Floor the daily loss at the circuit breaker.
    daily_ret = max(daily_ret, -a.daily_loss_breaker)
    bal = a.bankroll
    path = [bal]
    for _ in range(a.days):
        bal *= (1.0 + daily_ret)
        path.append(bal)
    return daily_ret, path


def main():
    a = Assumptions()
    print("=" * 70)
    print("  POLYMARKET P&L PROJECTION  --  honest expected value, not a promise")
    print("=" * 70)
    print(f"  Starting bankroll      ${a.bankroll:,.2f}")
    print(f"  Avg stake per bet      {a.avg_stake_pct*100:.0f}% of bankroll  "
          f"(~${a.bankroll*a.avg_stake_pct:.2f}); hard cap {a.max_bet_pct*100:.0f}%")
    print(f"  Bets per day           {a.bets_per_day} (only edge>=5% + confidence-passing)")
    print(f"  Spread/slippage drag   {a.spread_cost*100:.1f}% per bet")
    print(f"  Daily-loss circuit     halts the day at -{a.daily_loss_breaker*100:.0f}% "
          f"(-${a.bankroll*a.daily_loss_breaker:.2f})")
    print()
    print("  PER-DAY TARGETS")
    print(f"  Target profit (good day, base win rate): "
          f"~+${a.bankroll * project(a, SCENARIOS['base'])[0]:.2f}/day")
    print(f"  Target MAX loss (circuit breaker):       "
          f"-${a.bankroll*a.daily_loss_breaker:.2f}/day  (hard stop, then halt to next day)")
    print()
    print(f"  {a.days}-DAY PROJECTION (compounding the median daily EV)")
    print(f"  {'scenario':<14}{'win rate':>9}{'daily EV':>10}{'day 0':>9}"
          f"{'day 10':>9}{'day 20':>9}{'day 30':>10}{'P/L':>11}")
    for name, wr in SCENARIOS.items():
        daily_ret, path = project(a, wr)
        pl = path[-1] - a.bankroll
        print(f"  {name:<14}{wr*100:>7.0f}%{daily_ret*100:>9.2f}%"
              f"{path[0]:>9.0f}{path[10]:>9.0f}{path[20]:>9.0f}{path[30]:>10.2f}"
              f"{pl:>+11.2f}")
    print()
    print("  WHY THESE NUMBERS")
    print("  - The ONLY unknown is win rate on the bot's SELECTED bets. Everything")
    print("    else (stake size, bet count, fees, the loss breaker) is fixed by the")
    print("    risk rules already coded + tested.")
    print("  - At 50% win rate the bot is a coin flip and the spread bleeds it slowly.")
    print("    Edge selection (only bet when predicted prob beats market by >=5%) is")
    print("    what pushes win rate above 50%. That edge is UNPROVEN until the 20-")
    print("    resolved-trade paper calibration gate clears (Brier<0.25, win>52%).")
    print("  - With real 2026 fees + spread, ~52% win rate LOSES money, ~55% makes")
    print("    ~+15%/mo, ~58% makes ~+40%/mo. The break-even is ~53-54% -- you need")
    print("    GENUINE edge, not a coin flip. Research: ~84% of traders lose; honest")
    print("    target is mid-single-digit monthly ROI. The 20-trade calibration gate")
    print("    (Brier<0.25, win>52%) must clear before real money -- it catches a")
    print("    losing edge before it costs us.")
    print("  - Downside is hard-capped: worst real day is -15% ($37.50), then the bot")
    print("    halts to the next day. A full wipe requires many breaker days in a row,")
    print("    which the bankroll-floor halt (-40% -> operator) stops first.")
    print("=" * 70)


if __name__ == "__main__":
    main()
