from __future__ import annotations

import unittest

import pandas as pd

from strategy.entries import assess_htf_breakout_continuation, htf_breakout_continuation
from strategy.lane_scoring import select_lane


def _build_df(length: int, start: float, step: float, volume_base: float = 100.0) -> pd.DataFrame:
    rows = []
    price = start
    for i in range(length):
        open_ = price
        close = price + step
        high = max(open_, close) + abs(step) * 0.35 + 0.0004
        low = min(open_, close) - abs(step) * 0.15 - 0.0002
        rows.append(
            {
                "open": round(open_, 6),
                "high": round(high, 6),
                "low": round(low, 6),
                "close": round(close, 6),
                "volume": volume_base + i * 2.0,
            }
        )
        price = close
    return pd.DataFrame(rows)


class HtfBreakoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.levels = {"resistance": 0.1620, "support": 0.1500}
        self.fibs = {"0.618": 0.1605, "0.705": 0.1610}
        self.cfg = {
            "enabled": True,
            "lane_w_enabled": True,
            "lane_w_threshold": 52,
            "lane_w_distance_bypass": True,
            "lane_w_min_signals": 6,
            "lane_w_breakout_lookback_4h": 6,
            "lane_w_breakout_lookback_1h": 12,
            "lane_w_min_breakout_pct": 0.0005,
            "lane_w_max_chase_atr": 1.2,
            "lane_w_min_volume_ratio": 1.0,
            "lane_w_min_close_strength": 0.55,
            "lane_w_zone_lookback_15m": 24,
            "lane_w_zone_lookback_1h": 18,
            "lane_w_zone_lookback_4h": 10,
            "lane_w_zone_recent_bars": 4,
            "lane_w_zone_recent_bars_1h": 3,
            "lane_w_zone_recent_bars_4h": 2,
            "lane_w_rsi_4h_long_min": 52,
            "lane_w_rsi_4h_short_max": 48,
            "lane_w_event_block_hours": 6,
        }

    def test_long_breakout_assessment_ready(self):
        df_4h = _build_df(30, 0.1580, 0.00022, volume_base=180)
        df_1h = _build_df(60, 0.1605, 0.00010, volume_base=130)
        df_15m = _build_df(80, 0.1652, 0.000025, volume_base=105)
        df_15m.loc[df_15m.index[-1], "open"] = df_15m.loc[df_15m.index[-1], "close"] - 0.00014
        df_15m.loc[df_15m.index[-1], "high"] = df_15m.loc[df_15m.index[-1], "close"] + 0.00005
        df_15m.loc[df_15m.index[-1], "low"] = df_15m.loc[df_15m.index[-1], "open"] - 0.00002
        df_15m.loc[df_15m.index[-1], "volume"] = 260.0
        price = float(df_15m["close"].iloc[-1])
        weekly_playbook = {
            "label": "BULLISH OPEN",
            "thesis": "bullish breakout pressure building",
            "top_setups": [{"setup": "breakout continuation long"}],
        }

        assessment = assess_htf_breakout_continuation(
            price,
            df_4h,
            df_1h,
            df_15m,
            self.levels,
            self.fibs,
            "long",
            weekly_playbook=weekly_playbook,
            event_calendar={"next_event": {"label": "none", "importance": "low", "hours_to_event": 24}},
            config=self.cfg,
        )
        self.assertTrue(assessment["ready"])
        self.assertGreaterEqual(assessment["pressure_score"], 60)
        self.assertIn(assessment["management_bias"], {"hold_breakout", "fade_failed_breakout"})
        entry = htf_breakout_continuation(
            price,
            df_4h,
            df_1h,
            df_15m,
            self.levels,
            self.fibs,
            "long",
            weekly_playbook=weekly_playbook,
            event_calendar={"next_event": {"label": "none", "importance": "low", "hours_to_event": 24}},
            config=self.cfg,
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["type"], "htf_breakout_continuation")

    def test_event_risk_blocks_breakout(self):
        df_4h = _build_df(30, 0.1580, 0.00022, volume_base=180)
        df_1h = _build_df(60, 0.1605, 0.00010, volume_base=130)
        df_15m = _build_df(80, 0.1652, 0.000025, volume_base=105)
        df_15m.loc[df_15m.index[-1], "open"] = df_15m.loc[df_15m.index[-1], "close"] - 0.00014
        df_15m.loc[df_15m.index[-1], "high"] = df_15m.loc[df_15m.index[-1], "close"] + 0.00005
        df_15m.loc[df_15m.index[-1], "low"] = df_15m.loc[df_15m.index[-1], "open"] - 0.00002
        df_15m.loc[df_15m.index[-1], "volume"] = 260.0
        price = float(df_15m["close"].iloc[-1])

        assessment = assess_htf_breakout_continuation(
            price,
            df_4h,
            df_1h,
            df_15m,
            self.levels,
            self.fibs,
            "long",
            weekly_playbook={"label": "bullish"},
            event_calendar={"next_event": {"label": "Fed", "importance": "high", "hours_to_event": 2}},
            config=self.cfg,
        )
        self.assertFalse(assessment["ready"])
        self.assertTrue(assessment["event_risk_blocked"])
        self.assertEqual(assessment["reason"], "event_risk_block")
        self.assertGreaterEqual(assessment["false_break_risk"], 18)

    def test_reclaim_probe_just_below_breakout_is_ready(self):
        df_4h = _build_df(30, 0.1580, 0.00020, volume_base=180)
        df_1h = _build_df(60, 0.1610, 0.00008, volume_base=135)
        df_15m = _build_df(80, 0.1640, 0.000018, volume_base=108)

        prior_4h_high = float(df_4h["high"].iloc[-(self.cfg["lane_w_breakout_lookback_4h"] + 1):-1].max())
        prior_1h_high = float(df_1h["high"].iloc[-(self.cfg["lane_w_breakout_lookback_1h"] + 1):-1].max())
        breakout_level = max(prior_4h_high, prior_1h_high)

        df_4h.loc[df_4h.index[-1], "open"] = round(prior_4h_high - 0.00022, 6)
        df_4h.loc[df_4h.index[-1], "close"] = round(prior_4h_high - 0.00008, 6)
        df_4h.loc[df_4h.index[-1], "high"] = round(prior_4h_high - 0.00003, 6)
        df_4h.loc[df_4h.index[-1], "low"] = round(prior_4h_high - 0.00028, 6)

        df_1h.loc[df_1h.index[-1], "open"] = round(prior_1h_high - 0.00018, 6)
        df_1h.loc[df_1h.index[-1], "close"] = round(prior_1h_high - 0.00006, 6)
        df_1h.loc[df_1h.index[-1], "high"] = round(prior_1h_high - 0.00002, 6)
        df_1h.loc[df_1h.index[-1], "low"] = round(prior_1h_high - 0.00024, 6)

        df_15m.loc[df_15m.index[-1], "open"] = round(breakout_level - 0.00019, 6)
        df_15m.loc[df_15m.index[-1], "close"] = round(breakout_level - 0.00002, 6)
        df_15m.loc[df_15m.index[-1], "high"] = round(breakout_level + 0.00005, 6)
        df_15m.loc[df_15m.index[-1], "low"] = round(breakout_level - 0.00021, 6)
        df_15m.loc[df_15m.index[-1], "volume"] = 330.0
        price = float(df_15m["close"].iloc[-1])

        weekly_playbook = {
            "label": "BULLISH OPEN",
            "thesis": "breakout pressure building with squeeze higher potential",
            "top_setups": [{"setup": "breakout continuation long"}],
        }

        assessment = assess_htf_breakout_continuation(
            price,
            df_4h,
            df_1h,
            df_15m,
            self.levels,
            self.fibs,
            "long",
            weekly_playbook=weekly_playbook,
            event_calendar={"next_event": {"label": "none", "importance": "low", "hours_to_event": 24}},
            config=self.cfg,
        )
        self.assertTrue(assessment["ready"])
        self.assertTrue(assessment["breakout_probe_reclaim"])
        self.assertGreaterEqual(assessment["signal_count"], 6)
        entry = htf_breakout_continuation(
            price,
            df_4h,
            df_1h,
            df_15m,
            self.levels,
            self.fibs,
            "long",
            weekly_playbook=weekly_playbook,
            event_calendar={"next_event": {"label": "none", "importance": "low", "hours_to_event": 24}},
            config=self.cfg,
        )
        self.assertIsNotNone(entry)
        self.assertTrue(entry["confluence"]["BREAKOUT_PROBE_RECLAIM"])

    def test_zone_breakout_hold_is_ready_before_full_htf_close_confirmation(self):
        df_4h = _build_df(30, 0.1580, 0.00020, volume_base=180)
        df_1h = _build_df(60, 0.1610, 0.00008, volume_base=135)
        df_15m = _build_df(90, 0.1636, 0.000012, volume_base=110)

        prior_4h_high = float(df_4h["high"].iloc[-(self.cfg["lane_w_breakout_lookback_4h"] + 1):-1].max())
        prior_1h_high = float(df_1h["high"].iloc[-(self.cfg["lane_w_breakout_lookback_1h"] + 1):-1].max())
        zone_high = float(df_15m["high"].iloc[-28:-4].max())

        df_4h.loc[df_4h.index[-1], "open"] = round(prior_4h_high - 0.00024, 6)
        df_4h.loc[df_4h.index[-1], "close"] = round(prior_4h_high - 0.00006, 6)
        df_4h.loc[df_4h.index[-1], "high"] = round(prior_4h_high - 0.00001, 6)
        df_4h.loc[df_4h.index[-1], "low"] = round(prior_4h_high - 0.00028, 6)

        df_1h.loc[df_1h.index[-1], "open"] = round(prior_1h_high - 0.00018, 6)
        df_1h.loc[df_1h.index[-1], "close"] = round(prior_1h_high - 0.00004, 6)
        df_1h.loc[df_1h.index[-1], "high"] = round(prior_1h_high - 0.00001, 6)
        df_1h.loc[df_1h.index[-1], "low"] = round(prior_1h_high - 0.00022, 6)

        recent_specs = [
            (zone_high - 0.00006, zone_high + 0.00003, zone_high + 0.00010, zone_high - 0.00007, 190.0),
            (zone_high + 0.00002, zone_high + 0.00009, zone_high + 0.00013, zone_high - 0.00001, 220.0),
            (zone_high + 0.00007, zone_high + 0.00016, zone_high + 0.00020, zone_high + 0.00003, 255.0),
            (zone_high + 0.00012, zone_high + 0.00024, zone_high + 0.00027, zone_high + 0.00006, 340.0),
        ]
        for idx, (open_, close, high, low, volume) in zip(df_15m.index[-4:], recent_specs):
            df_15m.loc[idx, "open"] = round(open_, 6)
            df_15m.loc[idx, "close"] = round(close, 6)
            df_15m.loc[idx, "high"] = round(high, 6)
            df_15m.loc[idx, "low"] = round(low, 6)
            df_15m.loc[idx, "volume"] = volume

        price = float(df_15m["close"].iloc[-1])
        weekly_playbook = {
            "label": "BULLISH OPEN",
            "thesis": "resistance shelf broke and buyers are defending the reclaim",
            "top_setups": [{"setup": "breakout continuation long"}],
        }

        assessment = assess_htf_breakout_continuation(
            price,
            df_4h,
            df_1h,
            df_15m,
            self.levels,
            self.fibs,
            "long",
            weekly_playbook=weekly_playbook,
            event_calendar={"next_event": {"label": "none", "importance": "low", "hours_to_event": 24}},
            config=self.cfg,
        )
        self.assertTrue(assessment["ready"])
        self.assertTrue(assessment["zone_breakout_hold"])
        self.assertIn("15m", assessment["zone_breakout_tfs"])
        self.assertEqual(assessment["zone_active_tf"], "15m")
        self.assertGreaterEqual(assessment["signal_count"], 6)
        self.assertAlmostEqual(float(assessment["trigger_price"]), float(assessment["zone_high"]), places=6)
        entry = htf_breakout_continuation(
            price,
            df_4h,
            df_1h,
            df_15m,
            self.levels,
            self.fibs,
            "long",
            weekly_playbook=weekly_playbook,
            event_calendar={"next_event": {"label": "none", "importance": "low", "hours_to_event": 24}},
            config=self.cfg,
        )
        self.assertIsNotNone(entry)
        self.assertTrue(entry["confluence"]["ZONE_BREAKOUT_HOLD"])
        self.assertEqual(entry["zone_active_tf"], "15m")
        self.assertAlmostEqual(float(entry["trigger_price"]), float(entry["zone_high"]), places=6)

    def test_hourly_zone_breakout_hold_is_detected(self):
        df_4h = _build_df(30, 0.1580, 0.00016, volume_base=180)
        df_1h = _build_df(70, 0.1608, 0.00005, volume_base=132)
        df_15m = _build_df(96, 0.1642, 0.00001, volume_base=108)

        prior_4h_high = float(df_4h["high"].iloc[-(self.cfg["lane_w_breakout_lookback_4h"] + 1):-1].max())
        prior_1h_high = float(df_1h["high"].iloc[-(self.cfg["lane_w_zone_lookback_1h"] + self.cfg["lane_w_zone_recent_bars_1h"]):-self.cfg["lane_w_zone_recent_bars_1h"]].max())
        zone_15m_high = float(df_15m["high"].iloc[-28:-4].max())

        df_4h.loc[df_4h.index[-1], "open"] = round(prior_4h_high - 0.00020, 6)
        df_4h.loc[df_4h.index[-1], "close"] = round(prior_4h_high - 0.00008, 6)
        df_4h.loc[df_4h.index[-1], "high"] = round(prior_4h_high - 0.00002, 6)
        df_4h.loc[df_4h.index[-1], "low"] = round(prior_4h_high - 0.00024, 6)

        hourly_specs = [
            (prior_1h_high - 0.00005, prior_1h_high + 0.00002, prior_1h_high + 0.00005, prior_1h_high - 0.00007, 185.0),
            (prior_1h_high + 0.00001, prior_1h_high + 0.00008, prior_1h_high + 0.00011, prior_1h_high - 0.00001, 205.0),
            (prior_1h_high + 0.00007, prior_1h_high + 0.00016, prior_1h_high + 0.00019, prior_1h_high + 0.00003, 235.0),
        ]
        for idx, (open_, close, high, low, volume) in zip(df_1h.index[-3:], hourly_specs):
            df_1h.loc[idx, "open"] = round(open_, 6)
            df_1h.loc[idx, "close"] = round(close, 6)
            df_1h.loc[idx, "high"] = round(high, 6)
            df_1h.loc[idx, "low"] = round(low, 6)
            df_1h.loc[idx, "volume"] = volume

        fifteen_specs = [
            (zone_15m_high - 0.00018, zone_15m_high - 0.00011, zone_15m_high - 0.00006, zone_15m_high - 0.00022, 150.0),
            (zone_15m_high - 0.00010, zone_15m_high - 0.00014, zone_15m_high - 0.00005, zone_15m_high - 0.00020, 152.0),
            (zone_15m_high - 0.00013, zone_15m_high - 0.00009, zone_15m_high - 0.00002, zone_15m_high - 0.00017, 155.0),
            (prior_1h_high + 0.00003, prior_1h_high + 0.00014, prior_1h_high + 0.00018, prior_1h_high + 0.00001, 245.0),
        ]
        for idx, (open_, close, high, low, volume) in zip(df_15m.index[-4:], fifteen_specs):
            df_15m.loc[idx, "open"] = round(open_, 6)
            df_15m.loc[idx, "close"] = round(close, 6)
            df_15m.loc[idx, "high"] = round(high, 6)
            df_15m.loc[idx, "low"] = round(low, 6)
            df_15m.loc[idx, "volume"] = volume

        price = float(df_15m["close"].iloc[-1])
        weekly_playbook = {
            "label": "BULLISH OPEN",
            "thesis": "hourly shelf broke and held while lower timeframe follows through",
            "top_setups": [{"setup": "breakout continuation long"}],
        }

        assessment = assess_htf_breakout_continuation(
            price,
            df_4h,
            df_1h,
            df_15m,
            self.levels,
            self.fibs,
            "long",
            weekly_playbook=weekly_playbook,
            event_calendar={"next_event": {"label": "none", "importance": "low", "hours_to_event": 24}},
            config=self.cfg,
        )
        self.assertTrue(assessment["ready"])
        self.assertIn("1h", assessment["zone_breakout_tfs"])
        self.assertEqual(assessment["zone_active_tf"], "1h")
        self.assertAlmostEqual(float(assessment["trigger_price"]), float(assessment["zone_high"]), places=6)
        entry = htf_breakout_continuation(
            price,
            df_4h,
            df_1h,
            df_15m,
            self.levels,
            self.fibs,
            "long",
            weekly_playbook=weekly_playbook,
            event_calendar={"next_event": {"label": "none", "importance": "low", "hours_to_event": 24}},
            config=self.cfg,
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["zone_active_tf"], "1h")
        self.assertIn("1h", entry["zone_breakout_tfs"])

    def test_lane_scoring_routes_to_w(self):
        lane = select_lane(
            entry_type="htf_breakout_continuation",
            regime="trend",
            expansion_phase="EXPANSION",
            sweep=None,
            squeeze=None,
            contract_ctx=None,
            config=self.cfg,
        )
        self.assertIsNotNone(lane)
        self.assertEqual(lane.lane, "W")
        self.assertTrue(lane.distance_gate_bypass)


if __name__ == "__main__":
    unittest.main()
