# tests/test_pricing.py
import pytest
from render.pricing import MAX_VARIATIONS, cost_per_cover, clears_costs


def test_standard_5dollar_cover_clears_90pct_margin():
    assert clears_costs(5.0, "standard", variations=4)


def test_variations_capped_at_max():
    assert cost_per_cover("standard", 100) == cost_per_cover("standard", MAX_VARIATIONS)


def test_unknown_tier_raises():
    with pytest.raises(ValueError):
        cost_per_cover("ultra", 1)


def test_underpriced_cover_fails_gate():
    assert not clears_costs(1.0, "standard", variations=4)


def test_premium_costs_more_than_standard():
    assert cost_per_cover("premium") > cost_per_cover("standard")
