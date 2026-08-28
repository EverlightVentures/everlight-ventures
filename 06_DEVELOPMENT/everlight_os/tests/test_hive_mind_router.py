"""Tests for everlight_os.hive_mind.router — prompt classification and manager routing."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hive_mind.router import classify, classify_lite, classify_all


SAMPLE_ROSTER = {
    "routing_rules": {
        "trading": {
            "keywords": ["trade", "trading", "xlm", "bot", "pnl", "margin"],
            "managers": ["claude", "gemini"],
        },
        "content": {
            "keywords": ["blog", "post", "content", "article", "seo"],
            "managers": ["claude", "codex"],
        },
        "ops": {
            "keywords": ["status", "deploy", "infra", "server"],
            "managers": ["gemini"],
        },
    },
    "lite_managers": ["claude", "perplexity"],
}


class ClassifyTests(unittest.TestCase):
    def test_trading_keywords(self):
        cat, managers = classify("Check XLM trading bot PnL", roster=SAMPLE_ROSTER)
        self.assertEqual(cat, "trading")
        self.assertIn("perplexity", managers)

    def test_content_keywords(self):
        cat, managers = classify("Write a blog post about SEO", roster=SAMPLE_ROSTER)
        self.assertEqual(cat, "content")
        self.assertIn("perplexity", managers)
        self.assertIn("claude", managers)

    def test_ops_keywords(self):
        cat, managers = classify("Check server status", roster=SAMPLE_ROSTER)
        self.assertEqual(cat, "ops")
        self.assertIn("perplexity", managers)
        self.assertIn("gemini", managers)

    def test_no_match_defaults_to_full(self):
        cat, managers = classify("Something completely unrelated", roster=SAMPLE_ROSTER)
        self.assertEqual(cat, "full")
        self.assertIn("perplexity", managers)

    def test_perplexity_always_included(self):
        cat, managers = classify("trading PnL", roster=SAMPLE_ROSTER)
        self.assertIn("perplexity", managers)

    def test_highest_score_wins(self):
        cat, managers = classify("trade trading bot margin XLM pnl blog", roster=SAMPLE_ROSTER)
        self.assertEqual(cat, "trading")

    def test_perplexity_not_duplicated(self):
        roster = {
            "routing_rules": {
                "test_cat": {
                    "keywords": ["magic"],
                    "managers": ["perplexity", "claude"],
                },
            },
        }
        cat, managers = classify("magic word", roster=roster)
        self.assertEqual(managers.count("perplexity"), 1)


class ClassifyLiteTests(unittest.TestCase):
    def test_returns_lite_managers(self):
        cat, managers = classify_lite(roster=SAMPLE_ROSTER)
        self.assertEqual(cat, "lite")
        self.assertEqual(managers, ["claude", "perplexity"])

    def test_default_roster_fallback(self):
        roster = {}
        cat, managers = classify_lite(roster=roster)
        self.assertEqual(cat, "lite")
        self.assertEqual(managers, ["claude", "perplexity"])


class ClassifyAllTests(unittest.TestCase):
    def test_returns_all(self):
        cat, managers = classify_all()
        self.assertEqual(cat, "all")
        self.assertIn("gemini", managers)
        self.assertIn("codex", managers)
        self.assertIn("perplexity", managers)


if __name__ == "__main__":
    unittest.main()
