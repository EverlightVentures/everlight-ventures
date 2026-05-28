"""Tests for comment_scan investigator.

All network calls are monkeypatched -- zero actual HTTP requests.
"""
from __future__ import annotations

import asyncio
import sys
import os
import types
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path wiring: make "from ._common import ..." work when pytest runs the
# investigators/ folder directly (i.e. without the full osint_api package
# installed).  We inject a minimal parent package shim so relative imports
# inside comment_scan.py resolve without touching the real live_log module.
# ---------------------------------------------------------------------------

_INVESTORS_DIR = os.path.dirname(__file__)
_OSINT_API_DIR = os.path.dirname(_INVESTORS_DIR)
_INTEL_CENTER_DIR = os.path.dirname(_OSINT_API_DIR)

# Build minimal package stubs so relative imports don't blow up
def _ensure_stubs():
    # osint_api package shim
    pkg_chain = [
        ("intel_center",           _INTEL_CENTER_DIR),
        ("intel_center.osint_api", _OSINT_API_DIR),
        ("intel_center.osint_api.investigators", _INVESTORS_DIR),
    ]
    for mod_name, path in pkg_chain:
        if mod_name not in sys.modules:
            mod = types.ModuleType(mod_name)
            mod.__path__ = [path]
            mod.__package__ = mod_name
            sys.modules[mod_name] = mod

    # Stub live_log so _common.py imports without the real module
    if "intel_center.osint_api.live_log" not in sys.modules:
        ll = types.ModuleType("intel_center.osint_api.live_log")
        ll.record = lambda *a, **kw: None
        sys.modules["intel_center.osint_api.live_log"] = ll
        sys.modules["osint_api.live_log"] = ll

    # Also expose as bare "live_log" in case _common tries that path
    if "live_log" not in sys.modules:
        ll2 = types.ModuleType("live_log")
        ll2.record = lambda *a, **kw: None
        sys.modules["live_log"] = ll2


_ensure_stubs()

# Now we can import
import importlib
comment_scan = importlib.import_module("intel_center.osint_api.investigators.comment_scan")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Minimal DDG HTML that contains one snippet with a known email
_FAKE_DDG_HTML_WITH_EMAIL = """
<html><body>
<div class="result">
  <a class="result__a" href="https://example-forum.com/t/contact-rita">Rita Townsend Memphis forum post</a>
  <a class="result__snippet">
    Rita Townsend, Memphis TN -- reach her at rita.townsend@gmail.com for more info.
    She lives in the Midtown area and owns several properties.
  </a>
</div>
</body></html>
"""

_FAKE_DDG_HTML_NO_EMAIL = """
<html><body>
<div class="result">
  <a class="result__a" href="https://some-site.com/page">Some Page Title</a>
  <a class="result__snippet">
    This snippet contains no email address at all, just text about Memphis.
  </a>
</div>
</body></html>
"""

_FAKE_DDG_HTML_JUNK_EMAIL = """
<html><body>
<div class="result">
  <a class="result__a" href="https://example.com/page">Page</a>
  <a class="result__snippet">
    Contact us at noreply@example.com or test@domain.com for details.
  </a>
</div>
</body></html>
"""


def _make_fetch_stub(status: int, text: str, error: str | None = None):
    """Return an async fetch stub that always returns the given (status, text, error)."""
    async def _stub(http, url, *, timeout=8, method="GET"):
        return (status, text, error)
    return _stub


def _run(coro):
    """Run an async coroutine in the test process."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCommentScan:

    def test_email_extracted_from_snippet(self):
        """When DDG returns a snippet containing an email, it appears in findings."""
        stub = _make_fetch_stub(200, _FAKE_DDG_HTML_WITH_EMAIL)
        with patch.object(comment_scan, "fetch", stub):
            result = _run(comment_scan.run("Rita Townsend, Memphis", http=None))

        emails = [f["email"] for f in result["findings"]]
        assert "rita.townsend@gmail.com" in emails, (
            f"Expected rita.townsend@gmail.com in findings, got: {emails}"
        )

    def test_score_nonzero_when_email_found(self):
        """top_score > 0 when at least one plausible email is extracted."""
        stub = _make_fetch_stub(200, _FAKE_DDG_HTML_WITH_EMAIL)
        with patch.object(comment_scan, "fetch", stub):
            result = _run(comment_scan.run("Rita Townsend, Memphis", http=None))

        assert result["top_score"] > 0, (
            f"Expected non-zero top_score, got: {result['top_score']}"
        )

    def test_name_city_match_boosts_score(self):
        """Email whose local-part matches the name + city in snippet scores higher than average."""
        stub = _make_fetch_stub(200, _FAKE_DDG_HTML_WITH_EMAIL)
        with patch.object(comment_scan, "fetch", stub):
            result = _run(comment_scan.run("Rita Townsend, Memphis", http=None))

        # rita.townsend@gmail.com should have a name match + city match -> score >= 50
        hit = next(
            (f for f in result["findings"] if f["email"] == "rita.townsend@gmail.com"),
            None
        )
        assert hit is not None, "rita.townsend@gmail.com finding not present"
        assert hit["score"] >= 50, (
            f"Expected score >= 50 for strong name+city match, got: {hit['score']}"
        )

    def test_empty_findings_when_no_email_in_snippet(self):
        """Returns empty findings (not an error) when snippet has no emails."""
        stub = _make_fetch_stub(200, _FAKE_DDG_HTML_NO_EMAIL)
        with patch.object(comment_scan, "fetch", stub):
            result = _run(comment_scan.run("Rita Townsend, Memphis", http=None))

        assert result["findings"] == [], (
            f"Expected empty findings for no-email HTML, got: {result['findings']}"
        )
        assert result["top_score"] == 0
        assert result["high_confidence"] is False

    def test_junk_emails_filtered_out(self):
        """noreply@ and example.com / domain.com addresses are discarded."""
        stub = _make_fetch_stub(200, _FAKE_DDG_HTML_JUNK_EMAIL)
        with patch.object(comment_scan, "fetch", stub):
            result = _run(comment_scan.run("Rita Townsend, Memphis", http=None))

        emails = [f["email"] for f in result["findings"]]
        assert "noreply@example.com" not in emails, "noreply@ should be filtered"
        assert "test@domain.com" not in emails, "test@domain.com should be filtered"

    def test_never_raises_on_network_error(self):
        """fetch returning error string must not bubble up as an exception."""
        stub = _make_fetch_stub(0, "", "timeout")
        with patch.object(comment_scan, "fetch", stub):
            # Should complete without raising
            result = _run(comment_scan.run("Rita Townsend, Memphis", http=None))

        assert isinstance(result, dict), "run() must return a dict even on network error"
        assert "findings" in result
        assert result["findings"] == []

    def test_structure_keys_always_present(self):
        """Result dict always has the required investigator keys."""
        stub = _make_fetch_stub(200, _FAKE_DDG_HTML_NO_EMAIL)
        with patch.object(comment_scan, "fetch", stub):
            result = _run(comment_scan.run("Nobody Here, Nowhere", http=None))

        required_keys = {"ok", "findings", "raw", "top_score", "high_confidence",
                         "elapsed_ms", "investigator", "investigator_id"}
        missing = required_keys - set(result.keys())
        assert not missing, f"Missing keys in result: {missing}"

    def test_for_target_includes_comment_scan(self):
        """comment_scan module declares WHEN=['person'] so for_target selects it."""
        # Verify the WHEN attribute directly on the module -- this is what the
        # real investigators.__init__.for_target() loop checks.
        assert hasattr(comment_scan, "WHEN"), "comment_scan must export WHEN"
        when = comment_scan.WHEN
        assert "person" in when or "*" in when, (
            f"comment_scan.WHEN must include 'person' or '*', got: {when}"
        )

        # Also verify the module is listed in the real ALL registry.
        # We load __init__.py as a spec-based module to avoid full package
        # import machinery (which would need the live Oracle infra stubs).
        init_path = os.path.join(_INVESTORS_DIR, "__init__.py")
        init_src = open(init_path).read()
        assert "comment_scan" in init_src, (
            "comment_scan not found in investigators/__init__.py ALL registry"
        )
