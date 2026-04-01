from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.perplexity_advisor import _weekly_research_needs_retry
from market_intel_service import refresh_market_intel_state


class MarketIntelServiceTests(unittest.TestCase):
    def test_refresh_market_intel_state_writes_structured_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            logs_dir = root / "logs"
            now = datetime(2026, 3, 16, 3, 0, tzinfo=timezone.utc)
            state = refresh_market_intel_state(
                config={},
                data_dir=data_dir,
                logs_dir=logs_dir,
                market_intel={
                    "fetched_at": now.isoformat(),
                    "summary": "BTC firm, XLM lagging, liquidation headlines active.",
                    "risk_flags": ["Liquidation headlines active"],
                    "prices": {"xlm_24h_pct": -1.7},
                    "futures_relativity": {"composite": {"bias": "BEARISH"}},
                    "headlines": [
                        {
                            "topic": "crypto",
                            "title": "XLM futures positioning stays defensive",
                            "link": "https://example.com/xlm",
                            "source": "Reuters",
                            "published_at": now.isoformat(),
                        }
                    ],
                },
                market_brief={"risk_modifier": "risk_off", "confidence": 0.62},
                weekly_research={
                    "generated_from": "websearch_proxy",
                    "macro_regime": "risk_off",
                    "directional_bias": "bearish",
                    "xlm_bias": "bearish",
                    "confidence": 0.71,
                    "key_themes": ["Macro pressure is still defensive."],
                    "trade_playbook": ["Favor shorter-duration shorts until risk improves."],
                    "sources": ["Reuters", "CoinDesk"],
                    "updated_at": now.isoformat(),
                    "window_label": "SUNDAY_RESEARCH",
                },
                now_utc=now,
            )

            self.assertIn("intraday", state)
            self.assertIn("weekly", state)
            self.assertEqual(state["intraday"]["macro_regime"], "risk_off")
            self.assertEqual(state["weekly"]["directional_bias"], "bearish")
            self.assertTrue((data_dir / "market_intel_state.json").exists())
            self.assertTrue((data_dir / "market_event_calendar.json").exists())
            self.assertTrue((data_dir / "source_scoreboard.json").exists())
            self.assertTrue((data_dir / "weekly_playbook.json").exists())
            self.assertTrue((logs_dir / "market_intel_runs.jsonl").exists())
            self.assertTrue((logs_dir / "market_intel_documents.jsonl").exists())
            self.assertTrue((logs_dir / "market_intel_claims.jsonl").exists())

            persisted = json.loads((data_dir / "market_intel_state.json").read_text())
            self.assertEqual(persisted["weekly"]["window_label"], "SUNDAY_RESEARCH")
            self.assertIn("event_calendar", persisted)
            self.assertIn("source_scoreboard", persisted)
            self.assertIn("weekly_playbook", persisted)
            self.assertGreaterEqual(int(persisted["event_calendar"]["event_count"]), 2)
            self.assertEqual(persisted["weekly_playbook"]["monday_ready"], False)
            self.assertTrue(persisted["weekly_playbook"]["top_setups"])

    def test_weekly_research_retry_flags_fallback_during_window(self):
        needs_retry = _weekly_research_needs_retry(
            {"generated_from": "market_intel_fallback", "confidence": 0.4, "sources": ["market_intel_cache"]},
            window={"in_window": True},
        )
        self.assertTrue(needs_retry)


if __name__ == "__main__":
    unittest.main()
