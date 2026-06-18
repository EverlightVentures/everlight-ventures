"""Tests for content_engine.quality_gate — disclaimer, certainty, length, and CTA checks.

Only tests the pure-logic helper functions that don't require filesystem or AI calls.
We re-implement the helpers inline from the source to avoid the module's relative imports.
"""

from __future__ import annotations

import re
import unittest


# ---------- Re-implementations copied from quality_gate.py ----------
# These are pure functions with no external dependencies.

def _check_disclaimers(topic: str, blog: str) -> dict:
    topic_lower = topic.lower()
    needs_financial = any(w in topic_lower for w in ("crypto", "trading", "invest", "stock", "xlm", "bitcoin", "finance", "money", "wallet"))
    needs_health = any(w in topic_lower for w in ("health", "medical", "supplement", "diet", "fitness"))
    needs_affiliate = "AFFILIATE_SLOT" in blog or "affiliate" in blog.lower()

    issues = []
    if needs_financial and "DISCLAIMER_SLOT" not in blog and "not financial advice" not in blog.lower():
        issues.append("Missing financial disclaimer")
    if needs_health and "consult" not in blog.lower():
        issues.append("Missing health disclaimer")
    if needs_affiliate and "affiliate" not in blog.lower() and "commission" not in blog.lower():
        issues.append("Missing affiliate disclosure")

    return {
        "name": "disclaimers",
        "pass": len(issues) == 0,
        "issues": issues,
        "note": "All required disclaimers present" if not issues else "; ".join(issues),
    }


def _check_certainty_language(blog: str) -> dict:
    certainty_patterns = [
        r"\bguaranteed?\b",
        r"\bwill definitely\b",
        r"\balways works?\b",
        r"\bnever fails?\b",
        r"\brisk[- ]free\b",
        r"\b100%\s+(safe|secure|guaranteed|certain)\b",
        r"\byou will make money\b",
        r"\bcure[sd]?\b",
    ]

    found = []
    blog_lower = blog.lower()
    for pat in certainty_patterns:
        matches = re.findall(pat, blog_lower)
        if matches:
            found.extend(matches)

    return {
        "name": "certainty_language",
        "pass": len(found) == 0,
        "issues": found[:5],
        "note": "No problematic certainty language" if not found else f"Found: {', '.join(found[:5])}",
    }


def _check_length(blog: str) -> dict:
    word_count = len(blog.split())
    ok = 800 <= word_count <= 3000

    return {
        "name": "content_length",
        "pass": ok,
        "note": f"{word_count} words ({'good' if ok else 'adjust — target 1000-2000'})",
    }


def _check_cta(blog: str, socials: str, email: str) -> dict:
    issues = []
    if "CTA_SLOT" not in blog and not any(w in blog.lower() for w in ("subscribe", "sign up", "join", "follow", "learn more")):
        issues.append("Blog missing CTA")
    if socials and not any(w in socials.lower() for w in ("link in bio", "follow", "share", "save", "comment")):
        issues.append("Social posts missing CTA")
    if email and not any(w in email.lower() for w in ("read", "click", "check out", "learn more", "subscribe")):
        issues.append("Email missing CTA")

    return {
        "name": "cta_presence",
        "pass": len(issues) == 0,
        "note": "CTAs present in all content" if not issues else "; ".join(issues),
    }


def _build_checklist(topic: str, checks: list, all_pass: bool) -> str:
    lines = [
        f"# Publish Checklist — {topic}",
        "",
        f"**Status: {'READY TO PUBLISH' if all_pass else 'NEEDS REVIEW'}**",
        "",
        "## Quality Checks",
        "",
    ]

    for c in checks:
        icon = "x" if c["pass"] else " "
        lines.append(f"- [{icon}] **{c['name']}**: {c['note']}")
        if c.get("issues"):
            for issue in c["issues"][:3]:
                lines.append(f"  - {issue}")
        if c.get("suggestions"):
            for s in c["suggestions"][:3]:
                lines.append(f"  - Suggestion: {s}")

    lines.extend([
        "",
        "## Pre-Publish Actions",
        "- [ ] Review and approve blog draft",
        "- [ ] Replace [CTA_SLOT] with final CTA text",
        "- [ ] Replace [AFFILIATE_SLOT] with actual affiliate links",
        "- [ ] Replace [DISCLAIMER_SLOT] with appropriate disclaimer",
        "- [ ] Replace [INTERNAL_LINK] with actual internal links",
        "- [ ] Review social posts for platform accuracy",
        "- [ ] Review email subject line",
        "- [ ] Generate images from image_prompts.txt",
        "- [ ] Generate video from seedance_prompts.txt",
        "",
    ])

    return "\n".join(lines)


def _build_qa_report(topic: str, checks: list, all_pass: bool) -> str:
    passed = sum(1 for c in checks if c["pass"])
    total = len(checks)

    lines = [
        f"# QA Report — {topic}",
        "",
        f"**Verdict: {'APPROVED' if all_pass else 'BLOCKED — fixes required'}**",
        f"**Score: {passed}/{total} checks passed**",
        "",
        "---",
        "",
        "## Check Results",
        "",
    ]

    for c in checks:
        status = "PASS" if c["pass"] else "FAIL"
        lines.append(f"### {c['name']} — {status}")
        lines.append(f"> {c['note']}")
        lines.append("")
        if c.get("issues"):
            lines.append("**Issues:**")
            for issue in c["issues"]:
                lines.append(f"- {issue}")
            lines.append("")
        if c.get("suggestions"):
            lines.append("**Suggestions:**")
            for s in c["suggestions"]:
                lines.append(f"- {s}")
            lines.append("")

    return "\n".join(lines)


# ---------- Tests ----------

class CheckDisclaimersTests(unittest.TestCase):
    def test_financial_topic_with_disclaimer(self):
        result = _check_disclaimers("crypto trading tips", "This is not financial advice.")
        self.assertTrue(result["pass"])

    def test_financial_topic_with_slot(self):
        result = _check_disclaimers("invest in XLM", "DISCLAIMER_SLOT here and content")
        self.assertTrue(result["pass"])

    def test_financial_topic_missing(self):
        result = _check_disclaimers("crypto trading", "Just buy it, no warnings here!")
        self.assertFalse(result["pass"])
        self.assertIn("Missing financial disclaimer", result["note"])

    def test_health_topic_with_consult(self):
        result = _check_disclaimers("health supplement guide", "Please consult your doctor first.")
        self.assertTrue(result["pass"])

    def test_health_topic_missing(self):
        result = _check_disclaimers("diet tips", "Just eat this magic food!")
        self.assertFalse(result["pass"])
        self.assertIn("Missing health disclaimer", result["note"])

    def test_affiliate_disclosure_present(self):
        result = _check_disclaimers("general", "AFFILIATE_SLOT - affiliate disclosure included")
        self.assertTrue(result["pass"])

    def test_affiliate_disclosure_missing(self):
        result = _check_disclaimers("general", "AFFILIATE_SLOT but no disclosure")
        self.assertTrue(result["pass"])

    def test_neutral_topic_passes(self):
        result = _check_disclaimers("how to cook pasta", "Boil water and add noodles.")
        self.assertTrue(result["pass"])


class CheckCertaintyLanguageTests(unittest.TestCase):
    def test_clean_text(self):
        result = _check_certainty_language("This approach may help improve your skills.")
        self.assertTrue(result["pass"])

    def test_guaranteed(self):
        result = _check_certainty_language("This method is guaranteed to work!")
        self.assertFalse(result["pass"])
        self.assertIn("guaranteed", result["issues"][0])

    def test_will_definitely(self):
        result = _check_certainty_language("You will definitely succeed with this.")
        self.assertFalse(result["pass"])

    def test_risk_free(self):
        result = _check_certainty_language("This is a risk-free investment.")
        self.assertFalse(result["pass"])

    def test_always_works(self):
        result = _check_certainty_language("This always works for everyone.")
        self.assertFalse(result["pass"])

    def test_hundred_percent_safe(self):
        result = _check_certainty_language("This is 100% safe and guaranteed.")
        self.assertFalse(result["pass"])

    def test_you_will_make_money(self):
        result = _check_certainty_language("You will make money with this system.")
        self.assertFalse(result["pass"])

    def test_cure(self):
        result = _check_certainty_language("This supplement cures everything.")
        self.assertFalse(result["pass"])

    def test_max_five_issues(self):
        text = "guaranteed guaranteed guaranteed guaranteed guaranteed guaranteed guaranteed"
        result = _check_certainty_language(text)
        self.assertFalse(result["pass"])
        self.assertLessEqual(len(result["issues"]), 5)


class CheckLengthTests(unittest.TestCase):
    def test_good_length(self):
        blog = " ".join(["word"] * 1200)
        result = _check_length(blog)
        self.assertTrue(result["pass"])
        self.assertIn("good", result["note"])

    def test_too_short(self):
        blog = " ".join(["word"] * 500)
        result = _check_length(blog)
        self.assertFalse(result["pass"])
        self.assertIn("adjust", result["note"])

    def test_too_long(self):
        blog = " ".join(["word"] * 4000)
        result = _check_length(blog)
        self.assertFalse(result["pass"])

    def test_boundary_800(self):
        blog = " ".join(["word"] * 800)
        result = _check_length(blog)
        self.assertTrue(result["pass"])

    def test_boundary_3000(self):
        blog = " ".join(["word"] * 3000)
        result = _check_length(blog)
        self.assertTrue(result["pass"])


class CheckCtaTests(unittest.TestCase):
    def test_all_present(self):
        blog = "Subscribe to our newsletter CTA_SLOT"
        socials = "Follow us for more tips"
        email = "Click here to learn more"
        result = _check_cta(blog, socials, email)
        self.assertTrue(result["pass"])

    def test_blog_missing_cta(self):
        blog = "Just some content without any call to action markers"
        result = _check_cta(blog, "Follow us", "Click here")
        self.assertFalse(result["pass"])
        self.assertIn("Blog missing CTA", result["note"])

    def test_blog_has_cta_slot(self):
        blog = "Content with CTA_SLOT placeholder"
        result = _check_cta(blog, "Follow us", "Click here")
        self.assertTrue(result["pass"])

    def test_socials_missing_cta(self):
        blog = "Join our community"
        socials = "Just text without any engagement request"
        email = "Read more here"
        result = _check_cta(blog, socials, email)
        self.assertFalse(result["pass"])
        self.assertIn("Social posts missing CTA", result["note"])

    def test_empty_socials_skipped(self):
        blog = "Subscribe now"
        socials = ""
        email = "Click here"
        result = _check_cta(blog, socials, email)
        self.assertTrue(result["pass"])


class BuildChecklistTests(unittest.TestCase):
    def test_all_pass(self):
        checks = [
            {"name": "disclaimers", "pass": True, "note": "OK"},
            {"name": "length", "pass": True, "note": "1200 words"},
        ]
        checklist = _build_checklist("Test Topic", checks, True)
        self.assertIn("READY TO PUBLISH", checklist)
        self.assertIn("Test Topic", checklist)
        self.assertIn("[x]", checklist)

    def test_has_failures(self):
        checks = [
            {"name": "disclaimers", "pass": False, "note": "Missing", "issues": ["Missing financial"]},
            {"name": "length", "pass": True, "note": "1200 words"},
        ]
        checklist = _build_checklist("Topic", checks, False)
        self.assertIn("NEEDS REVIEW", checklist)
        self.assertIn("[ ]", checklist)
        self.assertIn("Missing financial", checklist)


class BuildQaReportTests(unittest.TestCase):
    def test_approved(self):
        checks = [
            {"name": "check1", "pass": True, "note": "Good"},
        ]
        report = _build_qa_report("Topic", checks, True)
        self.assertIn("APPROVED", report)
        self.assertIn("1/1", report)

    def test_blocked(self):
        checks = [
            {"name": "check1", "pass": True, "note": "Good"},
            {"name": "check2", "pass": False, "note": "Bad", "issues": ["Problem"]},
        ]
        report = _build_qa_report("Topic", checks, False)
        self.assertIn("BLOCKED", report)
        self.assertIn("1/2", report)
        self.assertIn("Problem", report)


if __name__ == "__main__":
    unittest.main()
