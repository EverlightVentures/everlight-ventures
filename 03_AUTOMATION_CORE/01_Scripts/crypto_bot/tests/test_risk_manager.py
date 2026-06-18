"""Tests for crypto_bot.utils.risk_manager — trade validation and position sizing."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.risk_manager import RiskManager


class ValidateTradeTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "max_daily_loss_usd": 150,
            "max_open_positions": 2,
            "min_reward_risk_ratio": 2.0,
        }
        self.rm = RiskManager(self.config)

    def test_trade_approved_basic(self):
        allowed, reason = self.rm.validate_trade({})
        self.assertTrue(allowed)
        self.assertEqual(reason, "Trade approved")

    def test_emergency_stop(self):
        self.config["emergency_stop"] = True
        rm = RiskManager(self.config)
        allowed, reason = rm.validate_trade({})
        self.assertFalse(allowed)
        self.assertIn("Emergency stop", reason)

    def test_daily_loss_limit(self):
        self.rm.daily_pnl = -150.0
        allowed, reason = self.rm.validate_trade({})
        self.assertFalse(allowed)
        self.assertIn("Daily loss limit", reason)

    def test_max_positions_reached(self):
        self.rm.open_positions = [{"id": "1"}, {"id": "2"}]
        allowed, reason = self.rm.validate_trade({})
        self.assertFalse(allowed)
        self.assertIn("Max positions", reason)

    def test_rr_ratio_too_low(self):
        signal = {
            "price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 107.0,
        }
        allowed, reason = self.rm.validate_trade(signal)
        self.assertFalse(allowed)
        self.assertIn("R:R too low", reason)

    def test_rr_ratio_acceptable(self):
        signal = {
            "price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 115.0,
        }
        allowed, reason = self.rm.validate_trade(signal)
        self.assertTrue(allowed)

    def test_rr_with_zero_risk(self):
        signal = {
            "price": 100.0,
            "stop_loss": 100.0,
            "take_profit": 110.0,
        }
        allowed, reason = self.rm.validate_trade(signal)
        self.assertTrue(allowed)

    def test_signal_with_current_price(self):
        signal = {
            "current_price": 50.0,
            "stop_loss": 45.0,
            "take_profit": 60.0,
        }
        allowed, reason = self.rm.validate_trade(signal)
        self.assertTrue(allowed)


class CalculatePositionSizeTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "max_risk_per_trade_percent": 1.0,
            "max_lot_size_usd": 1000,
        }
        self.rm = RiskManager(self.config)

    def test_basic_calculation(self):
        size = self.rm.calculate_position_size(
            entry=100.0, stop_loss=95.0, account_balance=10000.0
        )
        # Risk = 1% of 10000 = $100, price_risk = $5
        # position_size = 100/5 = 20 units, * 100 = $2000
        # Capped at $1000
        self.assertAlmostEqual(size, 1000.0)

    def test_small_account(self):
        size = self.rm.calculate_position_size(
            entry=1.0, stop_loss=0.95, account_balance=500.0
        )
        # Risk = 1% of 500 = $5, price_risk = $0.05
        # position_size = 5/0.05 = 100, * 1.0 = $100
        self.assertAlmostEqual(size, 100.0)

    def test_zero_price_risk(self):
        size = self.rm.calculate_position_size(
            entry=100.0, stop_loss=100.0, account_balance=10000.0
        )
        self.assertEqual(size, 0)


class RecordTradeResultTests(unittest.TestCase):
    def setUp(self):
        self.rm = RiskManager({})

    def test_winning_trade(self):
        self.rm.record_trade_result(50.0, "trend")
        self.assertEqual(self.rm.wins, 1)
        self.assertEqual(self.rm.losses, 0)
        self.assertAlmostEqual(self.rm.daily_pnl, 50.0)
        self.assertAlmostEqual(self.rm.total_pnl, 50.0)
        self.assertEqual(self.rm.daily_trades, 1)

    def test_losing_trade(self):
        self.rm.record_trade_result(-25.0, "scalp")
        self.assertEqual(self.rm.losses, 1)
        self.assertEqual(self.rm.wins, 0)
        self.assertAlmostEqual(self.rm.daily_pnl, -25.0)

    def test_multiple_trades(self):
        self.rm.record_trade_result(30.0, "a")
        self.rm.record_trade_result(-10.0, "b")
        self.rm.record_trade_result(20.0, "c")
        self.assertEqual(self.rm.wins, 2)
        self.assertEqual(self.rm.losses, 1)
        self.assertAlmostEqual(self.rm.total_pnl, 40.0)
        self.assertEqual(self.rm.daily_trades, 3)


class PositionTrackingTests(unittest.TestCase):
    def setUp(self):
        self.rm = RiskManager({})

    def test_add_position(self):
        self.rm.add_position({"id": "p1", "side": "buy"})
        self.assertEqual(len(self.rm.open_positions), 1)

    def test_remove_position(self):
        self.rm.add_position({"id": "p1", "side": "buy"})
        self.rm.add_position({"id": "p2", "side": "sell"})
        self.rm.remove_position("p1")
        self.assertEqual(len(self.rm.open_positions), 1)
        self.assertEqual(self.rm.open_positions[0]["id"], "p2")

    def test_remove_nonexistent(self):
        self.rm.add_position({"id": "p1"})
        self.rm.remove_position("nonexistent")
        self.assertEqual(len(self.rm.open_positions), 1)


class BreakevenAndTrailingTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "break_even_at_percent": 1.5,
            "use_trailing_stops": True,
            "trailing_stop_percent": 1.0,
        }
        self.rm = RiskManager(self.config)

    def test_should_move_to_breakeven_buy(self):
        self.assertTrue(self.rm.should_move_to_breakeven(100.0, 102.0, "buy"))

    def test_should_not_move_to_breakeven_buy(self):
        self.assertFalse(self.rm.should_move_to_breakeven(100.0, 100.5, "buy"))

    def test_should_move_to_breakeven_sell(self):
        self.assertTrue(self.rm.should_move_to_breakeven(100.0, 98.0, "sell"))

    def test_trailing_stop_buy(self):
        new_stop = self.rm.calculate_trailing_stop(
            entry=100.0, current=110.0, side="buy", current_stop=105.0
        )
        expected = 110.0 * (1 - 1.0 / 100)  # 108.9
        self.assertAlmostEqual(new_stop, max(105.0, expected, 100.0))

    def test_trailing_stop_never_moves_down(self):
        new_stop = self.rm.calculate_trailing_stop(
            entry=100.0, current=101.0, side="buy", current_stop=100.5
        )
        # new_stop = 101*(1-0.01) = 99.99, max(100.5, 99.99, 100) = 100.5
        self.assertGreaterEqual(new_stop, 100.5)

    def test_trailing_stop_disabled(self):
        self.config["use_trailing_stops"] = False
        rm = RiskManager(self.config)
        new_stop = rm.calculate_trailing_stop(100.0, 110.0, "buy", 95.0)
        self.assertEqual(new_stop, 95.0)


class GetStatsTests(unittest.TestCase):
    def test_stats_structure(self):
        rm = RiskManager({})
        rm.record_trade_result(50.0, "a")
        rm.record_trade_result(-20.0, "b")
        stats = rm.get_stats()
        self.assertIn("total_pnl", stats)
        self.assertIn("win_rate", stats)
        self.assertIn("open_positions", stats)
        self.assertAlmostEqual(stats["total_pnl"], 30.0)
        self.assertAlmostEqual(stats["win_rate"], 50.0)

    def test_get_status(self):
        rm = RiskManager({})
        status = rm.get_status()
        self.assertIn("can_trade", status)
        self.assertIn("daily_pnl", status)
        self.assertTrue(status["can_trade"])


if __name__ == "__main__":
    unittest.main()
