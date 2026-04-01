from __future__ import annotations

import unittest
from datetime import datetime, timezone

import pandas as pd

from timing.trade_eta import estimate_next_entry


class TradeEtaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 3, 16, 12, 0, tzinfo=timezone.utc)
        self.trades = pd.DataFrame(
            [
                {"entry_time": "2026-03-15T08:00:00+00:00", "entry_type": "pullback", "time_in_trade_min": None, "result": None},
                {"entry_time": "2026-03-15T08:00:00+00:00", "entry_type": "", "time_in_trade_min": 35, "result": "win"},
                {"entry_time": "2026-03-15T10:00:00+00:00", "entry_type": "pullback", "time_in_trade_min": None, "result": None},
                {"entry_time": "2026-03-15T10:00:00+00:00", "entry_type": "", "time_in_trade_min": 42, "result": "loss"},
                {"entry_time": "2026-03-15T13:00:00+00:00", "entry_type": "pullback", "time_in_trade_min": None, "result": None},
                {"entry_time": "2026-03-15T13:00:00+00:00", "entry_type": "", "time_in_trade_min": 38, "result": "win"},
            ]
        )

    def test_forecast_uses_htf_bias_and_profit_projection(self):
        state = {"vol_state": "EXPANSION", "last_exit_time": "2026-03-16T11:20:00+00:00"}
        last_decision = {
            "price": 0.17120,
            "contract_size": 5000,
            "v4_score_long": 72,
            "v4_score_short": 38,
            "v4_threshold_long": 70,
            "v4_threshold_short": 70,
            "thought": "trend continuation long building",
            "next_play_long": {
                "trigger_price": 0.17080,
                "level_name": "fib 0.618",
                "distance_atr": 0.40,
                "readiness_pct": 88,
            },
            "next_play_short": {
                "trigger_price": 0.17240,
                "level_name": "channel upper",
                "distance_atr": 1.10,
                "readiness_pct": 35,
            },
            "weekly_research_bias": "bullish",
            "weekly_research_xlm_bias": "bullish",
            "weekly_research_confidence": 0.82,
            "htf_readiness": "LONG_BREAKOUT_WATCH",
            "market_regime": "expansion",
            "v4_regime": "expansion",
            "v4_adx_15m": 27.0,
            "long_block_reason": None,
            "short_block_reason": "distance_from_value",
            "contract_ladder": {"1": {"ready": True, "target_size": 1}, "2": {"ready": False, "target_size": 2}},
            "margin_playbook_max_new_contracts": 1,
        }

        result = estimate_next_entry(state, last_decision, self.trades, self.now)
        self.assertEqual(result["forecast_direction"], "long")
        self.assertEqual(result["forecast_contracts"], 1)
        self.assertGreater(result["forecast_profit_per_contract_usd"], 0.0)
        self.assertIn("weekly XLM bias bullish", result["htf_bias_summary"])
        self.assertIn("Higher timeframes lean up", result["timeframe_logic"])

    def test_blocking_reason_carries_into_forecast(self):
        state = {
            "_safe_mode": True,
            "vol_state": "COMPRESSION",
            "last_exit_time": "2026-03-16T11:45:00+00:00",
        }
        last_decision = {
            "price": 0.17120,
            "contract_size": 5000,
            "v4_score_long": 41,
            "v4_score_short": 46,
            "v4_threshold_long": 70,
            "v4_threshold_short": 70,
            "thought": "pullback short possible",
            "next_play_short": {
                "trigger_price": 0.17200,
                "level_name": "channel upper",
                "distance_atr": 0.80,
                "readiness_pct": 60,
            },
            "weekly_research_bias": "mixed",
            "weekly_research_xlm_bias": "mixed",
            "weekly_research_confidence": 0.25,
            "htf_readiness": "SHORT_BIAS_WATCH",
            "market_regime": "compression",
            "v4_regime": "compression",
            "v4_adx_15m": 16.0,
            "long_block_reason": "score_below_threshold",
            "short_block_reason": None,
            "margin_playbook_max_new_contracts": 1,
        }

        result = estimate_next_entry(state, last_decision, self.trades, self.now)
        self.assertEqual(result["blocking_reason"], "safe mode")
        self.assertIn("Current blocker: safe mode", result["timeframe_logic"])
        self.assertTrue(str(result["estimated_display"]).startswith("Blocked:"))


if __name__ == "__main__":
    unittest.main()
