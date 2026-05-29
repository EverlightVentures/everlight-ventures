"""Trade economics: a bet must clear fees+gas AND grow the book."""
from polymarket_agent.costs import net_ev, clears_costs, trade_fee


def test_coinflip_on_50c_market_loses_after_costs():
    # 50/50 true prob on a 50c market: gross EV ~0, costs make it NEGATIVE -> reject
    assert not clears_costs(stake=2.0, price=0.50, pred_prob=0.50,
                            fee_rate=0.02, gas_usd=0.01, min_net_ev_pct=0.05)


def test_thin_edge_fails_cost_gate():
    # 53% true vs 50c: small gross edge, costs eat most -> below 5% net growth bar
    assert not clears_costs(stake=2.0, price=0.50, pred_prob=0.53, min_net_ev_pct=0.05)


def test_strong_edge_clears_costs():
    # 65% true vs 50c: real edge -> net EV well above the cost+growth bar
    assert clears_costs(stake=2.0, price=0.50, pred_prob=0.65, min_net_ev_pct=0.05)


def test_net_ev_is_below_gross_due_to_costs():
    ev = net_ev(stake=2.0, price=0.50, pred_prob=0.65)
    assert ev["net_ev"] < ev["gross_ev"]     # costs always reduce EV
    assert ev["cost"] > 0


def test_fee_peaks_near_50c():
    # fee is higher at 0.5 than at the extremes for the same stake
    f_mid = trade_fee(100, 0.50, 0.02)
    f_edge = trade_fee(100, 0.05, 0.02)
    assert f_mid > f_edge
