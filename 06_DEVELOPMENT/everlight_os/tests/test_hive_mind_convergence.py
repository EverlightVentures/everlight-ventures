"""Tests for everlight_os.hive_mind.convergence — cross-agent synthesis helpers."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hive_mind.contracts import ManagerResult, HiveSession
from hive_mind.convergence import (
    _count_active_specialists,
    _extract_recommendations,
    _extract_risks,
    _build_cross_agent_synthesis,
    build_combined_summary,
)


class CountActiveSpecialistsTests(unittest.TestCase):
    def test_empty_text(self):
        self.assertEqual(_count_active_specialists(""), (0, 0))
        self.assertEqual(_count_active_specialists(None), (0, 0))

    def test_single_active(self):
        text = "**data_analyst** | STATUS: ACTIVE\n- Finding 1: something"
        active, standby = _count_active_specialists(text)
        self.assertEqual(active, 1)

    def test_multiple(self):
        text = (
            "**analyst** | STATUS: ACTIVE\n"
            "**architect** | STATUS: ACTIVE\n"
            "**monitor** | STANDBY\n"
        )
        active, standby = _count_active_specialists(text)
        self.assertEqual(active, 2)
        self.assertEqual(standby, 1)

    def test_no_specialists(self):
        text = "Just some normal text without specialist markers"
        active, standby = _count_active_specialists(text)
        self.assertEqual(active, 0)
        self.assertEqual(standby, 0)


class ExtractRecommendationsTests(unittest.TestCase):
    def test_empty_text(self):
        self.assertEqual(_extract_recommendations(""), [])
        self.assertEqual(_extract_recommendations(None), [])

    def test_numbered_with_backtick(self):
        text = "1. `data_analyst` -> Implement daily monitoring\n2. `architect` -> Refactor the pipeline"
        recs = _extract_recommendations(text)
        self.assertEqual(len(recs), 2)
        self.assertIn("data_analyst", recs[0])

    def test_recommendation_bullet(self):
        text = "- Recommendation: Add more logging to the system"
        recs = _extract_recommendations(text)
        self.assertEqual(len(recs), 1)

    def test_substantive_bullet_points(self):
        text = "- This is a short one\n- This is a much longer substantive point about improving performance"
        recs = _extract_recommendations(text)
        # Both are >20 chars after "- "
        self.assertTrue(len(recs) >= 1)

    def test_short_bullets_filtered(self):
        text = "- Short item\n- OK"
        recs = _extract_recommendations(text)
        self.assertEqual(len(recs), 0)


class ExtractRisksTests(unittest.TestCase):
    def test_empty_text(self):
        self.assertEqual(_extract_risks(""), [])
        self.assertEqual(_extract_risks(None), [])

    def test_risk_section(self):
        text = (
            "### Risk Assessment\n"
            "- API rate limiting could cause missed signals during high volatility\n"
            "- Network latency might exceed acceptable thresholds\n"
            "### Next Steps\n"
            "- Implement fallback logic\n"
        )
        risks = _extract_risks(text)
        self.assertEqual(len(risks), 2)
        self.assertIn("rate limiting", risks[0])

    def test_inline_risk_flag(self):
        text = "- Risk flag: Margin utilization approaching danger threshold"
        risks = _extract_risks(text)
        self.assertEqual(len(risks), 1)

    def test_risk_in_bold_section(self):
        text = (
            "**Risk Factors**\n"
            "- Potential for cascading failures in trading pipeline\n"
            "## Summary\n"
        )
        risks = _extract_risks(text)
        self.assertEqual(len(risks), 1)


class BuildCrossAgentSynthesisTests(unittest.TestCase):
    def _make_session(self, managers):
        return HiveSession(
            prompt="Test",
            managers=[ManagerResult(**m) for m in managers],
        )

    def test_needs_two_agents(self):
        session = self._make_session([
            {"manager": "claude", "status": "done", "response_text": "Some text"},
        ])
        lines = _build_cross_agent_synthesis(session)
        self.assertEqual(lines, [])

    def test_two_agents_produce_synthesis(self):
        session = self._make_session([
            {
                "manager": "claude",
                "status": "done",
                "response_text": "1. `analyst` -> Improve monitoring\n- Recommendation: Add alerts",
            },
            {
                "manager": "gemini",
                "status": "done",
                "response_text": "1. `architect` -> Refactor pipeline\n- Risk flag: High latency",
            },
        ])
        lines = _build_cross_agent_synthesis(session)
        text = "\n".join(lines)
        self.assertIn("CROSS-AGENT SYNTHESIS", text)
        self.assertIn("Agents contributing: 2", text)

    def test_perplexity_excluded_from_synthesis(self):
        session = self._make_session([
            {"manager": "claude", "status": "done", "response_text": "Analysis"},
            {"manager": "perplexity", "status": "done", "response_text": "Intel data"},
        ])
        lines = _build_cross_agent_synthesis(session)
        self.assertEqual(lines, [])

    def test_failed_agent_not_counted(self):
        session = self._make_session([
            {"manager": "claude", "status": "done", "response_text": "OK"},
            {"manager": "gemini", "status": "failed", "response_text": ""},
        ])
        lines = _build_cross_agent_synthesis(session)
        self.assertEqual(lines, [])

    def test_synthesis_shows_risks(self):
        session = self._make_session([
            {
                "manager": "claude",
                "status": "done",
                "response_text": "### Risk Assessment\n- Margin at dangerous levels\n## End",
            },
            {
                "manager": "gemini",
                "status": "done",
                "response_text": "- Risk flag: API rate limit reached",
            },
        ])
        lines = _build_cross_agent_synthesis(session)
        text = "\n".join(lines)
        self.assertIn("RISK CONSENSUS", text)

    def test_synthesis_shows_failed_agents(self):
        session = self._make_session([
            {"manager": "claude", "status": "done", "response_text": "Analysis complete"},
            {"manager": "gemini", "status": "done", "response_text": "Another analysis"},
            {"manager": "codex", "status": "failed", "response_text": ""},
        ])
        lines = _build_cross_agent_synthesis(session)
        text = "\n".join(lines)
        self.assertIn("AGENTS DOWN", text)
        self.assertIn("CODEX", text)
        self.assertIn("REDUCED", text)


class BuildCombinedSummaryTests(unittest.TestCase):
    def test_basic_summary(self):
        session = HiveSession(
            prompt="Analyze trading bot performance",
            mode="full",
            routed_to=["claude", "gemini"],
            managers=[
                ManagerResult(
                    manager="claude",
                    role="Chief Operator",
                    status="done",
                    response_text="Bot is performing well.\nAll systems green.",
                    duration_s=3.5,
                ),
                ManagerResult(
                    manager="gemini",
                    role="Research Director",
                    status="done",
                    response_text="Market conditions favorable.",
                    duration_s=2.1,
                ),
            ],
            total_duration_s=5.6,
        )
        summary = build_combined_summary(session)
        self.assertIn("HIVE MIND DELIBERATION", summary)
        self.assertIn("CLAUDE", summary)
        self.assertIn("GEMINI", summary)
        self.assertIn("performing well", summary)

    def test_error_manager(self):
        session = HiveSession(
            prompt="Test",
            managers=[
                ManagerResult(
                    manager="codex",
                    role="Executor",
                    status="failed",
                    error="API timeout",
                ),
            ],
        )
        summary = build_combined_summary(session)
        self.assertIn("ERROR: API timeout", summary)

    def test_no_output_manager(self):
        session = HiveSession(
            prompt="Test",
            managers=[
                ManagerResult(manager="gemini", role="Research", status="pending"),
            ],
        )
        summary = build_combined_summary(session)
        self.assertIn("(no output)", summary)

    def test_long_response_truncated(self):
        long_text = "\n".join(f"Line {i}" for i in range(100))
        session = HiveSession(
            prompt="Test",
            managers=[
                ManagerResult(
                    manager="claude",
                    role="Chief",
                    status="done",
                    response_text=long_text,
                    duration_s=1.0,
                ),
            ],
        )
        summary = build_combined_summary(session)
        self.assertIn("more lines in war room", summary)


if __name__ == "__main__":
    unittest.main()
