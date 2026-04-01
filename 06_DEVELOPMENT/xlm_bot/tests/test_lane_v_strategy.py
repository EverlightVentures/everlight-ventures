from __future__ import annotations

import unittest

import pandas as pd

from strategy.entries import liquidity_sweep


def _df(seed: float = 0.165) -> pd.DataFrame:
    rows = []
    for i in range(24):
        base = seed + (i * 0.0001)
        rows.append(
            {
                "open": base,
                "high": base + 0.0006,
                "low": base - 0.0006,
                "close": base + 0.0002,
                "volume": 1000 + i * 10,
            }
        )
    return pd.DataFrame(rows)


def _df_down(seed: float = 0.165) -> pd.DataFrame:
    rows = []
    for i in range(24):
        base = seed - (i * 0.0001)
        rows.append(
            {
                "open": base,
                "high": base + 0.0006,
                "low": base - 0.0006,
                "close": base - 0.0002,
                "volume": 1000 + i * 10,
            }
        )
    return pd.DataFrame(rows)


class LaneVStrategyTests(unittest.TestCase):
    def setUp(self):
        self.df_15m = _df()
        self.df_1h = _df(0.164)
        self.cfg = {
            "lane_v_enabled": True,
            "lane_v_min_signals": 4,
            "lane_v_wick_min_ratio": 0.35,
            "lane_v_wick_score_min": 55,
            "lane_v_continuation_enabled": True,
            "lane_v_reversal_enabled": True,
            "lane_v_max_reversal_chase_atr": 1.2,
            "lane_v_continuation_tp_buffer_atr": 0.15,
            "lane_v_fail_fast_bars": 3,
            "lane_v_skip_balanced_clusters": True,
            "lane_v_min_cluster_strength": 30,
            "lane_v_require_volume_spike_for_reversal": False,
            "lane_v_require_fib_or_ema_stretch": True,
        }

    def test_continuation_long(self):
        intel = {
            "sweep_status": "none",
            "magnet_side": "above",
            "magnet_score": 68,
            "cluster_strength": 55,
            "cluster_side": "above",
            "distance_to_cluster_atr": 1.1,
            "continuation_ok": True,
            "failed_reclaim": False,
            "failed_rejection": False,
            "target_cluster_price": 0.1705,
        }
        entry = liquidity_sweep(0.1670, self.df_15m, self.df_1h, "long", {}, {}, intel, self.cfg)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["mode"], "continuation")
        self.assertEqual(entry["entry_profile_key"], "liquidity_sweep_continuation")

    def test_continuation_short(self):
        df_15m = _df_down()
        df_1h = _df_down(0.166)
        intel = {
            "sweep_status": "none",
            "magnet_side": "below",
            "magnet_score": 72,
            "cluster_strength": 52,
            "cluster_side": "below",
            "distance_to_cluster_atr": 1.0,
            "continuation_ok": True,
            "failed_reclaim": False,
            "failed_rejection": False,
            "target_cluster_price": 0.1620,
        }
        entry = liquidity_sweep(0.1660, df_15m, df_1h, "short", {}, {}, intel, self.cfg)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["mode"], "continuation")
        self.assertEqual(entry["entry_profile_key"], "liquidity_sweep_continuation")

    def test_reversal_long(self):
        intel = {
            "sweep_status": "completed",
            "sweep_side": "long",
            "wick_score": 74,
            "wick_ratio": 0.49,
            "cluster_strength": 60,
            "cluster_side": "below",
            "distance_to_cluster_atr": 0.45,
            "reclaim_confirmed": True,
            "followthrough_confirmed": True,
            "fib_hit": True,
            "ema_stretch": True,
            "reversal_ok": True,
            "failed_reclaim": False,
            "failed_rejection": False,
            "volume_spike": True,
            "sweep_level": 0.1635,
            "target_cluster_price": 0.1690,
            "sweep_depth_atr": 0.35,
        }
        entry = liquidity_sweep(0.1648, self.df_15m, self.df_1h, "long", {}, {}, intel, self.cfg)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["mode"], "reversal")
        self.assertEqual(entry["entry_profile_key"], "liquidity_sweep_reversal")

    def test_reversal_short(self):
        intel = {
            "sweep_status": "completed",
            "sweep_side": "short",
            "wick_score": 77,
            "wick_ratio": 0.52,
            "cluster_strength": 61,
            "cluster_side": "above",
            "distance_to_cluster_atr": 0.40,
            "rejection_confirmed": True,
            "followthrough_confirmed": True,
            "fib_hit": True,
            "ema_stretch": True,
            "reversal_ok": True,
            "failed_reclaim": False,
            "failed_rejection": False,
            "volume_spike": True,
            "sweep_level": 0.1685,
            "target_cluster_price": 0.1625,
            "sweep_depth_atr": 0.38,
        }
        entry = liquidity_sweep(0.1671, self.df_15m, self.df_1h, "short", {}, {}, intel, self.cfg)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["mode"], "reversal")
        self.assertEqual(entry["entry_profile_key"], "liquidity_sweep_reversal")

    def test_balanced_clusters_skip_trade(self):
        intel = {
            "sweep_status": "none",
            "cluster_side": "balanced",
            "magnet_side": "balanced",
            "magnet_score": 49,
            "cluster_strength": 45,
            "distance_to_cluster_atr": 1.4,
            "continuation_ok": False,
        }
        entry = liquidity_sweep(0.1664, self.df_15m, self.df_1h, "long", {}, {}, intel, self.cfg)
        self.assertIsNone(entry)


if __name__ == "__main__":
    unittest.main()
