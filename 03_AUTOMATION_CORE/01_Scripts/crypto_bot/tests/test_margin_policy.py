"""Tests for crypto_bot.utils.margin_policy — margin tier classification."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.margin_policy import (
    PolicyDecision,
    _num,
    _find_key_recursive,
    _extract_margin_metrics,
    evaluate_margin_policy,
)


class NumTests(unittest.TestCase):
    def test_float(self):
        self.assertAlmostEqual(_num(3.14), 3.14)

    def test_string_float(self):
        self.assertAlmostEqual(_num("1.5"), 1.5)

    def test_none(self):
        self.assertIsNone(_num(None))

    def test_nan(self):
        self.assertIsNone(_num(float("nan")))

    def test_inf(self):
        self.assertIsNone(_num(float("inf")))
        self.assertIsNone(_num(float("-inf")))

    def test_dict_with_value(self):
        self.assertAlmostEqual(_num({"value": "2.5"}), 2.5)

    def test_invalid_string(self):
        self.assertIsNone(_num("not_a_number"))

    def test_zero(self):
        self.assertAlmostEqual(_num(0), 0.0)
        self.assertAlmostEqual(_num("0"), 0.0)


class FindKeyRecursiveTests(unittest.TestCase):
    def test_top_level(self):
        self.assertEqual(_find_key_recursive({"a": 1}, "a"), 1)

    def test_nested(self):
        obj = {"level1": {"level2": {"target": "found"}}}
        self.assertEqual(_find_key_recursive(obj, "target"), "found")

    def test_in_list(self):
        obj = [{"a": 1}, {"b": 2}]
        self.assertEqual(_find_key_recursive(obj, "b"), 2)

    def test_not_found(self):
        self.assertIsNone(_find_key_recursive({"a": 1}, "missing"))

    def test_none_returns_none(self):
        self.assertIsNone(_find_key_recursive(None, "key"))

    def test_string_returns_none(self):
        self.assertIsNone(_find_key_recursive("string", "key"))


class ExtractMarginMetricsTests(unittest.TestCase):
    def test_empty_summary(self):
        metrics = _extract_margin_metrics({})
        self.assertIsNone(metrics["mr_intraday"])
        self.assertIsNone(metrics["mr_overnight"])
        self.assertIsNone(metrics["total_funds_for_margin"])

    def test_direct_fields(self):
        bs = {
            "balance_summary": {
                "total_funds_for_margin": "1000.0",
                "intraday_margin_ratio": "0.5",
                "overnight_margin_ratio": "0.6",
                "maintenance_margin_requirement": "500.0",
            }
        }
        metrics = _extract_margin_metrics(bs)
        self.assertAlmostEqual(metrics["total_funds_for_margin"], 1000.0)
        self.assertAlmostEqual(metrics["mr_intraday"], 0.5)
        self.assertAlmostEqual(metrics["mr_overnight"], 0.6)
        self.assertAlmostEqual(metrics["maintenance_margin_requirement"], 500.0)

    def test_computed_from_maintenance_margin(self):
        bs = {
            "balance_summary": {
                "total_funds_for_margin": "1000.0",
                "maintenance_margin_requirement": "800.0",
            }
        }
        metrics = _extract_margin_metrics(bs)
        self.assertAlmostEqual(metrics["mr_intraday"], 0.8)

    def test_nested_intraday_measure(self):
        bs = {
            "balance_summary": {
                "total_funds_for_margin": "2000.0",
                "intraday_margin_window_measure": {
                    "maintenance_margin": "600.0",
                },
            }
        }
        metrics = _extract_margin_metrics(bs)
        self.assertAlmostEqual(metrics["mr_intraday"], 0.3)


class PolicyDecisionTests(unittest.TestCase):
    def test_to_dict(self):
        pd = PolicyDecision(
            tier="SAFE",
            actions=["ALLOW_ENTRY"],
            reasons=[],
            metrics={"mr_intraday": 0.5},
        )
        d = pd.to_dict()
        self.assertEqual(d["tier"], "SAFE")
        self.assertEqual(d["actions"], ["ALLOW_ENTRY"])

    def test_frozen(self):
        pd = PolicyDecision(tier="SAFE", actions=[], reasons=[], metrics={})
        with self.assertRaises(AttributeError):
            pd.tier = "DANGER"


class EvaluateMarginPolicyTests(unittest.TestCase):
    def _make_bs(self, total_funds, mr_intraday=None, mr_overnight=None, mm_req=None):
        bs = {"balance_summary": {"total_funds_for_margin": str(total_funds)}}
        root = bs["balance_summary"]
        if mr_intraday is not None:
            root["intraday_margin_ratio"] = str(mr_intraday)
        if mr_overnight is not None:
            root["overnight_margin_ratio"] = str(mr_overnight)
        if mm_req is not None:
            root["maintenance_margin_requirement"] = str(mm_req)
        return bs

    def test_safe_tier(self):
        bs = self._make_bs(1000, mr_intraday=0.5)
        now = datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)
        result = evaluate_margin_policy(bs, now_utc=now)
        self.assertEqual(result.tier, "SAFE")
        self.assertIn("ALLOW_ENTRY", result.actions)

    def test_warning_tier(self):
        bs = self._make_bs(1000, mr_intraday=0.85)
        now = datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)
        result = evaluate_margin_policy(bs, now_utc=now)
        self.assertEqual(result.tier, "WARNING")
        self.assertIn("BLOCK_ENTRY", result.actions)

    def test_danger_tier(self):
        bs = self._make_bs(1000, mr_intraday=0.92)
        now = datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)
        result = evaluate_margin_policy(bs, now_utc=now)
        self.assertEqual(result.tier, "DANGER")
        self.assertIn("BLOCK_ENTRY", result.actions)
        self.assertIn("REDUCE_ONLY", result.actions)

    def test_liquidation_tier(self):
        bs = self._make_bs(1000, mr_intraday=1.05)
        now = datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)
        result = evaluate_margin_policy(bs, now_utc=now)
        self.assertEqual(result.tier, "LIQUIDATION")
        self.assertIn("EXIT_ALL", result.actions)
        self.assertIn("HALT_TRADING", result.actions)

    def test_unknown_when_no_margin_data(self):
        bs = {"balance_summary": {}}
        now = datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)
        result = evaluate_margin_policy(bs, now_utc=now)
        self.assertEqual(result.tier, "UNKNOWN")
        self.assertIn("ALLOW_ENTRY", result.actions)

    def test_none_balance_summary(self):
        now = datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)
        result = evaluate_margin_policy(None, now_utc=now)
        self.assertEqual(result.tier, "UNKNOWN")

    def test_metrics_in_result(self):
        bs = self._make_bs(1000, mr_intraday=0.5)
        now = datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)
        result = evaluate_margin_policy(bs, now_utc=now)
        self.assertIn("active_mr", result.metrics)
        self.assertIn("now_et", result.metrics)
        self.assertIn("mins_to_cutoff", result.metrics)


if __name__ == "__main__":
    unittest.main()
