"""Tests for everlight_os.core.router — request classification and step planning."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.router import (
    _match_any,
    _detect_content_subtype,
    _trading_steps,
    _content_steps,
    _saas_steps,
    _books_steps,
    classify,
    TRADING_PATTERNS,
    BOOKS_PATTERNS,
    SAAS_PATTERNS,
    STATUS_PATTERNS,
)


class MatchAnyTests(unittest.TestCase):
    def test_matches_trading_keyword(self):
        self.assertTrue(_match_any("Show me today's trading report", TRADING_PATTERNS))

    def test_no_match(self):
        self.assertFalse(_match_any("Hello world", TRADING_PATTERNS))

    def test_case_insensitive(self):
        self.assertTrue(_match_any("XLM Price Check", TRADING_PATTERNS))

    def test_books_patterns(self):
        self.assertTrue(_match_any("Write a new book about Sam", BOOKS_PATTERNS))

    def test_saas_patterns(self):
        self.assertTrue(_match_any("Build SaaS product for scheduling", SAAS_PATTERNS))

    def test_status_patterns(self):
        self.assertTrue(_match_any("Everlight status", STATUS_PATTERNS))
        self.assertTrue(_match_any("System status", STATUS_PATTERNS))
        self.assertTrue(_match_any("status report", STATUS_PATTERNS))


class DetectContentSubtypeTests(unittest.TestCase):
    def test_howto(self):
        self.assertEqual(_detect_content_subtype("How to build a website"), "howto")

    def test_comparison(self):
        self.assertEqual(_detect_content_subtype("React vs Angular"), "comparison")

    def test_news(self):
        self.assertEqual(_detect_content_subtype("Latest news on AI"), "news")

    def test_listicle(self):
        self.assertEqual(_detect_content_subtype("5 best ways to save energy"), "listicle")

    def test_explainer(self):
        self.assertEqual(_detect_content_subtype("What is machine learning"), "explainer")

    def test_default_is_explainer(self):
        self.assertEqual(_detect_content_subtype("Random text without keywords"), "explainer")

    def test_tutorial(self):
        self.assertEqual(_detect_content_subtype("Step-by-step guide to cooking"), "howto")

    def test_buyers_guide(self):
        self.assertEqual(_detect_content_subtype("Best laptop for gaming"), "comparison")


class TradingStepsTests(unittest.TestCase):
    def test_daily_report_steps(self):
        steps = _trading_steps("daily_report")
        self.assertTrue(len(steps) > 0)
        names = [s.name for s in steps]
        self.assertIn("parse_logs", names)
        self.assertIn("generate_report", names)
        self.assertIn("post_to_slack", names)

    def test_report_alias(self):
        steps = _trading_steps("report")
        self.assertTrue(len(steps) > 0)

    def test_status_steps(self):
        steps = _trading_steps("status")
        names = [s.name for s in steps]
        self.assertIn("read_state", names)
        self.assertIn("post_to_slack", names)

    def test_unknown_intent_empty(self):
        steps = _trading_steps("unknown_thing")
        self.assertEqual(steps, [])


class ContentStepsTests(unittest.TestCase):
    def test_content_step_names(self):
        steps = _content_steps("howto")
        names = [s.name for s in steps]
        self.assertIn("research", names)
        self.assertIn("outline", names)
        self.assertIn("draft", names)
        self.assertIn("seo", names)
        self.assertIn("monetize", names)
        self.assertIn("quality_gate", names)
        self.assertIn("post_to_slack", names)


class SaasStepsTests(unittest.TestCase):
    def test_full_build_has_all_phases(self):
        steps = _saas_steps("full_build")
        names = [s.name for s in steps]
        self.assertIn("scope_idea", names)
        self.assertIn("pick_stack", names)
        self.assertIn("write_spec", names)
        self.assertIn("scaffold_repo", names)
        self.assertIn("write_launch", names)
        self.assertIn("write_ops", names)

    def test_spec_only_default(self):
        steps = _saas_steps("spec_only")
        names = [s.name for s in steps]
        self.assertIn("scope_idea", names)
        self.assertIn("write_spec", names)
        self.assertNotIn("scaffold_repo", names)


class BooksStepsTests(unittest.TestCase):
    def test_book_steps(self):
        steps = _books_steps("new_book")
        names = [s.name for s in steps]
        self.assertIn("series_bible", names)
        self.assertIn("manuscript", names)
        self.assertIn("illustrations", names)
        self.assertIn("kdp_metadata", names)


class ClassifyTests(unittest.TestCase):
    def test_trading_report(self):
        result = classify("Give me today's trading report")
        self.assertEqual(result.engine, "trading")
        self.assertEqual(result.intent, "daily_report")
        self.assertGreater(result.confidence, 0)

    def test_trading_status(self):
        result = classify("Check trading status")
        self.assertEqual(result.engine, "trading")
        self.assertEqual(result.intent, "status")

    def test_content_prefix(self):
        result = classify("Post about the best SEO tools")
        self.assertEqual(result.engine, "content")

    def test_books_prefix(self):
        result = classify("Book: Sam learns about space")
        self.assertEqual(result.engine, "books")
        self.assertEqual(result.intent, "new_book")

    def test_saas_prefix(self):
        result = classify("Build SaaS: scheduling tool")
        self.assertEqual(result.engine, "saas")

    def test_saas_full_build(self):
        result = classify("build saas full build scheduling tool")
        self.assertEqual(result.engine, "saas")
        self.assertEqual(result.intent, "full_build")

    def test_status_check(self):
        result = classify("Everlight status")
        self.assertEqual(result.engine, "status")
        self.assertEqual(result.intent, "full_status")
        self.assertGreater(result.confidence, 0.9)
        self.assertEqual(result.steps, [])

    def test_default_to_content(self):
        result = classify("Tell me something interesting about cooking")
        self.assertEqual(result.engine, "content")

    def test_mode_hint_override(self):
        result = classify("Something random", mode_hint="trading")
        self.assertEqual(result.engine, "trading")

    def test_url_in_metadata(self):
        result = classify("Post about AI", url="https://example.com")
        self.assertEqual(result.metadata["url"], "https://example.com")

    def test_no_url_empty_metadata(self):
        result = classify("Post about AI")
        self.assertEqual(result.metadata, {})

    def test_pattern_match_xlm(self):
        result = classify("Check XLM price movement")
        self.assertEqual(result.engine, "trading")

    def test_pattern_match_kindle(self):
        result = classify("Publish my book on Kindle ebook")
        self.assertEqual(result.engine, "books")

    def test_content_subtype_howto(self):
        result = classify("How to build a website from scratch")
        self.assertEqual(result.engine, "content")
        self.assertEqual(result.intent, "howto")


if __name__ == "__main__":
    unittest.main()
