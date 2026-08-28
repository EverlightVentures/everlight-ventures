"""Tests for everlight_os.hive_mind.telemetry — specialist performance parsing."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hive_mind.telemetry import _extract_specialist_reports


class ExtractSpecialistReportsTests(unittest.TestCase):
    def test_active_specialist(self):
        text = (
            "**data_analyst** | STATUS: ACTIVE\n"
            "- Finding 1: Trading volume increased 15%\n"
            "- Finding 2: Win rate stable at 62%\n"
            "- Recommendation: Increase position sizes\n"
        )
        reports = _extract_specialist_reports(text, ["data_analyst"])
        self.assertEqual(reports["data_analyst"]["status"], "ACTIVE")
        self.assertEqual(reports["data_analyst"]["findings_count"], 2)
        self.assertTrue(reports["data_analyst"]["has_recommendation"])
        self.assertFalse(reports["data_analyst"]["has_risk_flag"])

    def test_standby_specialist(self):
        text = "**risk_monitor** | STATUS: STANDBY\n"
        reports = _extract_specialist_reports(text, ["risk_monitor"])
        self.assertEqual(reports["risk_monitor"]["status"], "STANDBY")
        self.assertEqual(reports["risk_monitor"]["findings_count"], 0)

    def test_not_found(self):
        text = "Some text without specialist markers"
        reports = _extract_specialist_reports(text, ["unknown_specialist"])
        self.assertEqual(reports["unknown_specialist"]["status"], "NOT_FOUND")
        self.assertEqual(reports["unknown_specialist"]["findings_count"], 0)
        self.assertFalse(reports["unknown_specialist"]["has_recommendation"])

    def test_multiple_specialists(self):
        text = (
            "**analyst** | STATUS: ACTIVE\n"
            "- Finding 1: Volume spike detected\n"
            "- Recommendation: Pause trading\n"
            "- Risk flag: High volatility environment\n"
            "**architect** | STATUS: ACTIVE\n"
            "- Finding 1: Pipeline latency within bounds\n"
        )
        reports = _extract_specialist_reports(text, ["analyst", "architect"])
        self.assertEqual(reports["analyst"]["status"], "ACTIVE")
        self.assertEqual(reports["analyst"]["findings_count"], 1)
        self.assertTrue(reports["analyst"]["has_recommendation"])
        self.assertTrue(reports["analyst"]["has_risk_flag"])
        self.assertEqual(reports["architect"]["status"], "ACTIVE")
        self.assertEqual(reports["architect"]["findings_count"], 1)
        self.assertFalse(reports["architect"]["has_risk_flag"])

    def test_empty_text(self):
        reports = _extract_specialist_reports("", ["analyst"])
        self.assertEqual(reports["analyst"]["status"], "NOT_FOUND")

    def test_none_text(self):
        reports = _extract_specialist_reports(None, ["analyst"])
        self.assertEqual(reports["analyst"]["status"], "NOT_FOUND")

    def test_case_insensitive_status(self):
        text = "**bot_monitor** | STATUS: active\n"
        reports = _extract_specialist_reports(text, ["bot_monitor"])
        self.assertEqual(reports["bot_monitor"]["status"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
