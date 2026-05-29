"""Tests for the compound-growth ladder: tiered max-bet ceilings + harvest plan."""
from decimal import Decimal
from polymarket_agent import growth


def test_tier_ceilings_scale_with_bankroll():
    assert growth.max_bet_for(250) == Decimal("1000")     # < $10k
    assert growth.max_bet_for(5000) == Decimal("1000")
    assert growth.max_bet_for(10000) == Decimal("2000")   # $10k-20k
    assert growth.max_bet_for(20000) == Decimal("4000")   # $20k-30k
    assert growth.max_bet_for(30000) == Decimal("5000")   # >= $30k
    assert growth.max_bet_for(100000) == Decimal("5000")


def test_compound_phase_below_30k_withdraws_nothing():
    plan = growth.harvest_plan(1000)
    assert plan["phase"] == "compound"
    assert plan["withdraw_today"] == Decimal("0")
    plan2 = growth.harvest_plan(29999)
    assert plan2["withdraw_today"] == Decimal("0")


def test_harvest_phase_at_30k_pays_daily():
    # at exactly $30k, no excess yet -> 0; at $30,100 -> pay up to $100
    assert growth.harvest_plan(30000)["withdraw_today"] == Decimal("0")
    plan = growth.harvest_plan(30100)
    assert plan["phase"] == "harvest"
    assert plan["withdraw_today"] == Decimal("100")
    assert plan["working_capital"] == Decimal("30000")


def test_harvest_caps_at_payout_per_day():
    # big excess still only pays the daily amount (rest keeps compounding)
    plan = growth.harvest_plan(35000)
    assert plan["withdraw_today"] == Decimal("100")


def test_ladder_caps_risk_manager_size():
    """The growth ceiling is one of the 3 sizing caps (min wins)."""
    from polymarket_agent.agents.risk_manager import RiskManager
    rm = RiskManager(max_bet_pct=Decimal("5.0"), max_daily_loss_pct=Decimal("15"),
                     max_open_positions=10, max_bet_abs=Decimal("5"))
    # quarter-Kelly/% would allow more, but abs cap $5 binds
    sized = rm._quarter_kelly_size(bankroll=Decimal("250"), edge=0.20, odds=0.5)
    assert sized <= Decimal("5")
