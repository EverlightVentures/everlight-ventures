"""Tests for everlight_os.hive_mind.contracts — Hive Mind data contracts."""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hive_mind.contracts import ManagerResult, HiveSession


class ManagerResultTests(unittest.TestCase):
    def test_defaults(self):
        mr = ManagerResult()
        self.assertEqual(mr.manager, "")
        self.assertEqual(mr.role, "")
        self.assertEqual(mr.status, "pending")
        self.assertEqual(mr.response_text, "")
        self.assertEqual(mr.duration_s, 0.0)
        self.assertIsInstance(mr.employees_consulted, list)

    def test_to_dict(self):
        mr = ManagerResult(
            manager="claude",
            role="Chief Operator",
            status="done",
            response_text="Analysis complete",
            duration_s=5.2,
            employees_consulted=["automation_architect", "data_analyst"],
        )
        d = mr.to_dict()
        self.assertEqual(d["manager"], "claude")
        self.assertEqual(d["status"], "done")
        self.assertEqual(len(d["employees_consulted"]), 2)
        self.assertAlmostEqual(d["duration_s"], 5.2)

    def test_error_field(self):
        mr = ManagerResult(manager="gemini", status="failed", error="API timeout")
        self.assertEqual(mr.error, "API timeout")
        self.assertEqual(mr.status, "failed")


class HiveSessionTests(unittest.TestCase):
    def test_defaults(self):
        hs = HiveSession()
        self.assertTrue(len(hs.id) > 0)
        self.assertEqual(hs.prompt, "")
        self.assertEqual(hs.mode, "full")
        self.assertEqual(hs.status, "pending")
        self.assertIsInstance(hs.routed_to, list)
        self.assertIsInstance(hs.managers, list)
        self.assertTrue(hs.created)

    def test_to_dict(self):
        hs = HiveSession(
            prompt="Analyze trading performance",
            mode="lite",
            status="done",
            routed_to=["claude", "perplexity"],
            total_duration_s=12.5,
        )
        d = hs.to_dict()
        self.assertEqual(d["prompt"], "Analyze trading performance")
        self.assertEqual(d["mode"], "lite")
        self.assertEqual(d["routed_to"], ["claude", "perplexity"])
        self.assertAlmostEqual(d["total_duration_s"], 12.5)

    def test_to_json(self):
        hs = HiveSession(prompt="Test prompt", mode="full")
        j = hs.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["prompt"], "Test prompt")
        self.assertEqual(parsed["mode"], "full")

    def test_from_dict(self):
        d = {
            "id": "abc123",
            "prompt": "Check bot status",
            "mode": "lite",
            "status": "done",
            "routed_to": ["claude"],
            "total_duration_s": 8.0,
        }
        hs = HiveSession.from_dict(d)
        self.assertEqual(hs.id, "abc123")
        self.assertEqual(hs.prompt, "Check bot status")
        self.assertEqual(hs.mode, "lite")

    def test_from_dict_ignores_extra_keys(self):
        d = {
            "id": "test1",
            "prompt": "test",
            "unexpected_key": "should_be_ignored",
        }
        hs = HiveSession.from_dict(d)
        self.assertEqual(hs.id, "test1")

    def test_to_json_roundtrip(self):
        hs = HiveSession(
            prompt="Full roundtrip test",
            mode="all",
            routed_to=["claude", "gemini", "codex"],
        )
        j = hs.to_json()
        parsed = json.loads(j)
        hs2 = HiveSession.from_dict(parsed)
        self.assertEqual(hs2.prompt, hs.prompt)
        self.assertEqual(hs2.mode, hs.mode)
        self.assertEqual(hs2.routed_to, hs.routed_to)


if __name__ == "__main__":
    unittest.main()
