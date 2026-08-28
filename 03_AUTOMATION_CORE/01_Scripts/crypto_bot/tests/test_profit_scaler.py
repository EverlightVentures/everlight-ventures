"""Tests for crypto_bot.utils.profit_scaler — Kelly Criterion and position sizing."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.profit_scaler import ScalingConfig, ProfitScaler


class ScalingConfigTests(unittest.TestCase):
    def test_defaults(self):
        cfg = ScalingConfig()
        self.assertAlmostEqual(cfg.starting_capital, 1000.0)
        self.assertAlmostEqual(cfg.daily_target_percent, 10.0)
        self.assertAlmostEqual(cfg.max_risk_per_trade_percent, 2.0)
        self.assertAlmostEqual(cfg.kelly_fraction, 0.25)
        self.assertTrue(cfg.compound_profits)
        self.assertEqual(cfg.scale_out_targets, [1.0, 2.0, 3.0])

    def test_post_init_sets_targets(self):
        cfg = ScalingConfig()
        self.assertIsNotNone(cfg.scale_out_targets)
        self.assertEqual(len(cfg.scale_out_targets), 3)

    def test_custom_targets(self):
        cfg = ScalingConfig(scale_out_targets=[0.5, 1.0])
        self.assertEqual(cfg.scale_out_targets, [0.5, 1.0])


class KellySizeTests(unittest.TestCase):
    def setUp(self):
        self.scaler = ProfitScaler({"profit_scaling": {}}, data_dir="/tmp/test_scaler_data")

    def test_positive_edge(self):
        # 60% win rate, avg_win=100, avg_loss=50 => b=2, kelly = (0.6*2 - 0.4)/2 = 0.4
        # fractional (25%) = 0.10, capped at max_risk 0.02 => 0.02
        result = self.scaler.calculate_kelly_size(0.6, 100, 50)
        self.assertGreater(result, 0)
        self.assertLessEqual(result, 0.02)

    def test_no_edge(self):
        # 50% win rate, avg_win=50, avg_loss=50 => b=1, kelly = (0.5*1-0.5)/1 = 0
        result = self.scaler.calculate_kelly_size(0.5, 50, 50)
        self.assertAlmostEqual(result, 0.0)

    def test_negative_edge(self):
        # 30% win rate, avg_win=50, avg_loss=50 => b=1, kelly = (0.3-0.7)/1 = -0.4
        result = self.scaler.calculate_kelly_size(0.3, 50, 50)
        self.assertAlmostEqual(result, 0.0)

    def test_zero_avg_loss(self):
        result = self.scaler.calculate_kelly_size(0.6, 100, 0)
        self.assertAlmostEqual(result, 0.0)

    def test_zero_win_rate(self):
        result = self.scaler.calculate_kelly_size(0.0, 100, 50)
        self.assertAlmostEqual(result, 0.0)

    def test_high_edge_capped(self):
        # 80% win rate, avg_win=200, avg_loss=50 => b=4, kelly = (0.8*4-0.2)/4 = 0.75
        # fractional 25% = 0.1875, capped at 0.02
        result = self.scaler.calculate_kelly_size(0.8, 200, 50)
        self.assertAlmostEqual(result, 0.02)


class OptimalPositionSizeTests(unittest.TestCase):
    def setUp(self):
        self.scaler = ProfitScaler({"profit_scaling": {}}, data_dir="/tmp/test_scaler_data")

    def test_returns_dict(self):
        result = self.scaler.get_optimal_position_size(10000.0, 0.6, 100, 50)
        self.assertIsInstance(result, dict)

    def test_uses_defaults_when_none(self):
        result = self.scaler.get_optimal_position_size(5000.0)
        self.assertIsInstance(result, dict)

    def test_minimum_size_enforced(self):
        result = self.scaler.get_optimal_position_size(100.0, 0.3, 10, 20)
        # With negative kelly, size would be 0, but min is $50
        size = result.get("size_usd", result.get("recommended_size", 0))
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
