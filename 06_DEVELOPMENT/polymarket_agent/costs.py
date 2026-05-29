"""Trade economics gate -- a trade must clear fees + gas AND grow the bankroll.

Operator law (2026-05-29): "our trades must be more than enough to cover our gas
fees and grow our portfolio at the same time." On near-50/50 markets (the 5-min
candle lane), Polymarket's crypto fee PEAKS at p=0.5 and gas is real on small
stakes -- so a coin-flip bet LOSES after costs. This computes net expected value
AFTER costs and only greenlights trades whose net EV meaningfully grows the book.

Polymarket fee model (taker): fee approx = fee_rate * shares * min(p, 1-p),
peaks at p=0.5, shrinks toward the extremes. Polymarket trades are largely
gasless (relayer), so gas is small but non-zero on tiny stakes.
"""
from decimal import Decimal


def trade_fee(stake: float, price: float, fee_rate: float) -> float:
    """Approx Polymarket taker fee for buying `stake` USDC at `price`.
    Per Polymarket docs the fee scales with p*(1-p) -- it PEAKS at p=0.5 and
    shrinks toward the extremes. Normalized so fee == fee_rate*stake at p=0.5:
        fee = fee_rate * stake * 4 * p * (1-p)."""
    if price <= 0 or price >= 1:
        return 0.0
    return fee_rate * stake * 4.0 * price * (1.0 - price)


def net_ev(stake: float, price: float, pred_prob: float,
           fee_rate: float = 0.02, gas_usd: float = 0.01,
           round_trip: bool = True) -> dict:
    """Expected $ profit of the bet AFTER fees + gas.

    Win (prob=pred_prob): payout = stake/price ($1/share); profit = stake*(1-price)/price.
    Loss (prob=1-pred_prob): -stake.
    Costs: entry fee (+ exit fee if we trade out) + gas per on-chain step.
    """
    p = price
    if p <= 0 or p >= 1:
        return {"net_ev": -stake, "gross_ev": -stake, "cost": stake, "net_ev_pct": -1.0}
    q = max(0.0, min(1.0, pred_prob))
    win_profit = stake * (1.0 - p) / p
    gross_ev = q * win_profit - (1.0 - q) * stake
    fee = trade_fee(stake, p, fee_rate)
    cost = fee * (2 if round_trip else 1) + gas_usd
    net = gross_ev - cost
    return {"net_ev": round(net, 4), "gross_ev": round(gross_ev, 4),
            "cost": round(cost, 4), "net_ev_pct": round(net / stake, 4) if stake else 0.0}


def clears_costs(stake: float, price: float, pred_prob: float,
                 fee_rate: float = 0.02, gas_usd: float = 0.01,
                 min_net_ev_pct: float = 0.05) -> bool:
    """True only if the bet's net EV (after fees+gas) grows the book by at least
    min_net_ev_pct of the stake. This is the 'more than enough to cover gas AND
    grow' gate -- a coin-flip on a 50c market fails it."""
    return net_ev(stake, price, pred_prob, fee_rate, gas_usd)["net_ev_pct"] >= min_net_ev_pct
