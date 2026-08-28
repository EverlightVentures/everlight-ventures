"""Tests for crypto_bot.utils.market_filters — trading hours and event filters."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.market_filters import FilterResult, TradingHoursFilter


class FilterResultTests(unittest.TestCase):
    def test_defaults(self):
        fr = FilterResult(passed=True, reason="OK")
        self.assertTrue(fr.passed)
        self.assertEqual(fr.reason, "OK")
        self.assertEqual(fr.details, {})

    def test_custom_details(self):
        fr = FilterResult(passed=False, reason="Blocked", details={"key": "val"})
        self.assertEqual(fr.details["key"], "val")


class TradingHoursFilterTests(unittest.TestCase):
    def test_disabled_filter_always_passes(self):
        f = TradingHoursFilter({"trading_hours_filter": {"enabled": False}})
        result = f.check(datetime(2026, 1, 1, 3, 0))
        self.assertTrue(result.passed)
        self.assertIn("disabled", result.reason)

    def test_optimal_window_passes(self):
        f = TradingHoursFilter({})
        result = f.check(datetime(2026, 1, 1, 9, 0))
        self.assertTrue(result.passed)
        self.assertIn("Optimal", result.reason)

    def test_another_optimal_window(self):
        f = TradingHoursFilter({})
        result = f.check(datetime(2026, 1, 1, 14, 0))
        self.assertTrue(result.passed)

    def test_avoid_window_blocked(self):
        f = TradingHoursFilter({})
        result = f.check(datetime(2026, 1, 1, 3, 0))
        self.assertFalse(result.passed)
        self.assertIn("Low volume", result.reason)

    def test_acceptable_window_non_strict(self):
        f = TradingHoursFilter({})
        result = f.check(datetime(2026, 1, 1, 12, 0))
        self.assertTrue(result.passed)
        self.assertIn("Acceptable", result.reason)

    def test_strict_mode_blocks_non_optimal(self):
        f = TradingHoursFilter({"trading_hours_filter": {"strict_mode": True}})
        result = f.check(datetime(2026, 1, 1, 12, 0))
        self.assertFalse(result.passed)
        self.assertIn("Strict mode", result.reason)

    def test_strict_mode_allows_optimal(self):
        f = TradingHoursFilter({"trading_hours_filter": {"strict_mode": True}})
        result = f.check(datetime(2026, 1, 1, 9, 0))
        self.assertTrue(result.passed)

    def test_custom_optimal_windows(self):
        f = TradingHoursFilter({
            "trading_hours_filter": {
                "optimal_hours_utc": [[10, 12]],
            }
        })
        result = f.check(datetime(2026, 1, 1, 11, 0))
        self.assertTrue(result.passed)
        self.assertIn("Optimal", result.reason)

    def test_custom_avoid_windows(self):
        f = TradingHoursFilter({
            "trading_hours_filter": {
                "avoid_hours_utc": [[20, 23]],
            }
        })
        result = f.check(datetime(2026, 1, 1, 21, 0))
        self.assertFalse(result.passed)

    def test_get_status(self):
        f = TradingHoursFilter({})
        status = f.get_status()
        self.assertIn("enabled", status)
        self.assertIn("can_trade", status)
        self.assertIn("reason", status)
        self.assertIn("optimal_windows", status)


class TimeInRangeTests(unittest.TestCase):
    def setUp(self):
        self.f = TradingHoursFilter({})

    def test_normal_range(self):
        self.assertTrue(self.f._time_in_range(time(9, 0), time(8, 0), time(10, 0)))

    def test_outside_range(self):
        self.assertFalse(self.f._time_in_range(time(7, 0), time(8, 0), time(10, 0)))

    def test_midnight_crossing(self):
        self.assertTrue(self.f._time_in_range(time(23, 0), time(22, 0), time(2, 0)))
        self.assertTrue(self.f._time_in_range(time(1, 0), time(22, 0), time(2, 0)))
        self.assertFalse(self.f._time_in_range(time(12, 0), time(22, 0), time(2, 0)))

    def test_boundary(self):
        self.assertTrue(self.f._time_in_range(time(8, 0), time(8, 0), time(10, 0)))
        self.assertTrue(self.f._time_in_range(time(10, 0), time(8, 0), time(10, 0)))


class NextOptimalWindowTests(unittest.TestCase):
    def test_before_first_window(self):
        f = TradingHoursFilter({})
        result = f._next_optimal_window(datetime(2026, 1, 1, 7, 0))
        self.assertIn("08:00", result)
        self.assertIn("today", result)

    def test_between_windows(self):
        f = TradingHoursFilter({})
        result = f._next_optimal_window(datetime(2026, 1, 1, 11, 0))
        self.assertIn("13:00", result)
        self.assertIn("today", result)

    def test_after_all_windows(self):
        f = TradingHoursFilter({})
        result = f._next_optimal_window(datetime(2026, 1, 1, 17, 0))
        self.assertIn("tomorrow", result)


if __name__ == "__main__":
    unittest.main()
