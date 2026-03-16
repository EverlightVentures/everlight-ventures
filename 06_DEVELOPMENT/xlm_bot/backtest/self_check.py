from __future__ import annotations

import json
from pathlib import Path

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from strategy.exits import tp_prices
from strategy.risk import sl_distance_ok
from strategy.confluence import confluence_passes


def test_tp1_move():
    entry = 1.0
    plan = tp_prices(entry, 4, "long", 0.20, 0.40, 0.60)
    expected = 1.0 * (1 + 0.20 / 4)
    assert abs(plan.tp1 - expected) < 1e-8


def test_sl_distance():
    assert sl_distance_ok(1.0, 0.98, 0.03) is True
    assert sl_distance_ok(1.0, 0.95, 0.03) is False


def test_two_confluences_fail():
    conf = {"STRUCTURE_ZONE": True, "RSI_VALID": True, "MACD_EXPAND": False, "FIB_ZONE": False}
    assert confluence_passes(conf) is False


def run():
    test_tp1_move()
    test_sl_distance()
    test_two_confluences_fail()
    print("self_check: ok")


if __name__ == "__main__":
    run()
