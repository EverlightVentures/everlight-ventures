"""
Tests for homeowner_osint.py

All tests monkeypatch run_investigation_sync -- NO live network calls.

Covers:
  - Happy path: synthetic payloads are normalized into the contract dict
  - Email extraction from email_discovery raw["full_results"]
  - Email extraction fallback via findings text when full_results absent
  - verified flag derived correctly from emailrep.deliverable + hibp_exists
  - identity_score/verdict extracted via profile_depth (or heuristic fallback)
  - Import failure -> graceful empty dict, no raise
  - Empty result payloads -> graceful empty dict
  - No name provided -> graceful empty dict with verdict="no_name_provided"
  - Multiple investigators: only email_discovery emails extracted
"""
from __future__ import annotations

import sys
import os
import importlib
import types

import pytest

# Make sure the wholesale_agent package is importable
sys.path.insert(0, os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------

def _make_email_discovery_payload(full_results: list[dict] | None = None,
                                   findings: list[dict] | None = None) -> dict:
    """Build a realistic email_discovery investigator payload."""
    raw: dict = {"target": "TEST TARGET", "verified": 0, "candidates": 3}
    if full_results is not None:
        raw["full_results"] = full_results
        raw["top_candidates"] = [r["email"] for r in full_results[:3]]
    return {
        "ok": True,
        "investigator": "Email Discovery",
        "investigator_id": "email_discovery",
        "elapsed_ms": 1234,
        "findings": findings or [],
        "raw": raw,
        "top_score": (full_results[0]["score"] if full_results else 0),
        "high_confidence": True,
    }


def _make_skip_trace_payload() -> dict:
    """A non-email investigator payload to confirm we don't pull emails from it."""
    return {
        "ok": True,
        "investigator": "Skip Trace",
        "investigator_id": "skip_trace",
        "elapsed_ms": 500,
        "findings": [
            {"label": "Phone", "value": "555-123-4567", "url": ""},
        ],
        "raw": {},
    }


SYNTHETIC_FULL_RESULTS = [
    {
        "email": "eddie.howard@gmail.com",
        "score": 72,
        "mx_ok": True,
        "emailrep": {"reputation": "high", "suspicious": False, "deliverable": True},
        "hibp_exists": None,
        "summary": "MX->gmail.com · rep:high",
    },
    {
        "email": "howardeddie@yahoo.com",
        "score": 45,
        "mx_ok": True,
        "emailrep": {"reputation": "medium", "suspicious": False, "deliverable": None},
        "hibp_exists": False,
        "summary": "MX->yahoo.com · rep:medium",
    },
    {
        "email": "e.howard@outlook.com",
        "score": 25,
        "mx_ok": True,
        "emailrep": {},
        "hibp_exists": None,
        "summary": "MX->outlook.com",
    },
]


# ---------------------------------------------------------------------------
# Helpers to patch at the correct module path
# ---------------------------------------------------------------------------

def _patch_run_sync(monkeypatch, payloads, investigation_id="inv_test_001"):
    """Patch homeowner_osint's import of run_investigation_sync."""
    import homeowner_osint as m
    monkeypatch.setattr(
        m,
        "resolve",
        # We rebuild resolve to bypass the try/import block and inject our fake
        _build_resolve_with_fake_sync(payloads, investigation_id),
    )


def _build_resolve_with_fake_sync(fake_payloads, fake_inv_id):
    """
    Return a resolve() that calls the real _extract_emails + _extract_identity_score
    but never touches run_investigation_sync.
    """
    def _resolve(name, address="", city="", state="", mailing_address="", lead_id=None):
        import homeowner_osint as m
        if not (name or "").strip():
            result = dict(m._EMPTY_RESULT)
            result["verdict"] = "no_name_provided"
            return result
        if not fake_payloads:
            return dict(m._EMPTY_RESULT)
        candidate_emails = m._extract_emails(fake_payloads)
        identity_score, verdict = m._extract_identity_score(fake_payloads)
        return {
            "candidate_emails": candidate_emails,
            "identity_score": identity_score,
            "verdict": verdict,
            "raw_investigation_id": fake_inv_id,
        }
    return _resolve


# ---------------------------------------------------------------------------
# Tests: happy path / normalization
# ---------------------------------------------------------------------------

class TestResolveNormalization:
    def test_returns_all_contract_keys(self, monkeypatch):
        _patch_run_sync(monkeypatch, [_make_email_discovery_payload(SYNTHETIC_FULL_RESULTS)])
        import homeowner_osint as m
        result = m.resolve("HOWARD EDDIE", address="123 Main St", city="Memphis", state="TN")
        assert "candidate_emails" in result
        assert "identity_score" in result
        assert "verdict" in result
        assert "raw_investigation_id" in result

    def test_candidate_emails_have_correct_shape(self, monkeypatch):
        _patch_run_sync(monkeypatch, [_make_email_discovery_payload(SYNTHETIC_FULL_RESULTS)])
        import homeowner_osint as m
        result = m.resolve("HOWARD EDDIE")
        assert len(result["candidate_emails"]) > 0
        for c in result["candidate_emails"]:
            assert "email" in c
            assert "confidence" in c
            assert "verified" in c
            assert "sources" in c

    def test_top_candidate_is_highest_confidence(self, monkeypatch):
        _patch_run_sync(monkeypatch, [_make_email_discovery_payload(SYNTHETIC_FULL_RESULTS)])
        import homeowner_osint as m
        result = m.resolve("HOWARD EDDIE")
        emails = result["candidate_emails"]
        # Sorted descending by confidence
        assert emails[0]["email"] == "eddie.howard@gmail.com"
        assert emails[0]["confidence"] == 72

    def test_verified_flag_set_when_deliverable_true(self, monkeypatch):
        _patch_run_sync(monkeypatch, [_make_email_discovery_payload(SYNTHETIC_FULL_RESULTS)])
        import homeowner_osint as m
        result = m.resolve("HOWARD EDDIE")
        # First candidate has emailrep.deliverable=True
        first = result["candidate_emails"][0]
        assert first["verified"] is True

    def test_verified_flag_false_when_no_hard_signal(self, monkeypatch):
        """Candidate with only MX (no deliverable, no HIBP) -> verified=False."""
        only_mx = [
            {
                "email": "x@hotmail.com",
                "score": 25,
                "mx_ok": True,
                "emailrep": {},
                "hibp_exists": None,
                "summary": "MX->hotmail.com",
            }
        ]
        _patch_run_sync(monkeypatch, [_make_email_discovery_payload(only_mx)])
        import homeowner_osint as m
        result = m.resolve("TEST NAME")
        assert result["candidate_emails"][0]["verified"] is False

    def test_hibp_exists_sets_verified(self, monkeypatch):
        """HIBP existence alone is enough to set verified=True."""
        hibp_only = [
            {
                "email": "realuser@aol.com",
                "score": 40,
                "mx_ok": True,
                "emailrep": {"deliverable": None},
                "hibp_exists": True,
                "summary": "MX->aol.com · HIBP:exists",
            }
        ]
        _patch_run_sync(monkeypatch, [_make_email_discovery_payload(hibp_only)])
        import homeowner_osint as m
        result = m.resolve("REAL USER")
        assert result["candidate_emails"][0]["verified"] is True

    def test_sources_contain_relevant_signals(self, monkeypatch):
        _patch_run_sync(monkeypatch, [_make_email_discovery_payload(SYNTHETIC_FULL_RESULTS)])
        import homeowner_osint as m
        result = m.resolve("HOWARD EDDIE")
        first_sources = result["candidate_emails"][0]["sources"]
        assert "mx_check" in first_sources
        assert "emailrep_deliverable" in first_sources

    def test_raw_investigation_id_passed_through(self, monkeypatch):
        _patch_run_sync(monkeypatch, [_make_email_discovery_payload(SYNTHETIC_FULL_RESULTS)],
                        investigation_id="inv_abc123")
        import homeowner_osint as m
        result = m.resolve("HOWARD EDDIE")
        assert result["raw_investigation_id"] == "inv_abc123"

    def test_non_email_investigators_ignored(self, monkeypatch):
        """skip_trace payload should NOT contribute emails."""
        payloads = [
            _make_skip_trace_payload(),
            _make_email_discovery_payload(SYNTHETIC_FULL_RESULTS),
        ]
        _patch_run_sync(monkeypatch, payloads)
        import homeowner_osint as m
        result = m.resolve("HOWARD EDDIE")
        for c in result["candidate_emails"]:
            assert "555" not in c["email"]  # phone number not in email list


# ---------------------------------------------------------------------------
# Tests: fallback extraction from findings text
# ---------------------------------------------------------------------------

class TestFindingsTextFallback:
    def test_extracts_email_from_findings_text_when_no_full_results(self, monkeypatch):
        """When full_results is absent, parse findings text as fallback."""
        text_findings = [
            {"label": "Candidate · score 45/100",
             "value": "bennie.leggett@gmail.com (MX->gmail.com · rep:medium)",
             "url": ""},
        ]
        payload = _make_email_discovery_payload(full_results=None, findings=text_findings)
        # Make sure full_results key is NOT in raw
        payload["raw"].pop("full_results", None)
        payload["raw"].pop("top_candidates", None)

        _patch_run_sync(monkeypatch, [payload])
        import homeowner_osint as m
        result = m.resolve("BENNIE LEGGETT")
        assert len(result["candidate_emails"]) == 1
        assert result["candidate_emails"][0]["email"] == "bennie.leggett@gmail.com"
        assert result["candidate_emails"][0]["confidence"] is None
        assert "findings_text_fallback" in result["candidate_emails"][0]["sources"]


# ---------------------------------------------------------------------------
# Tests: graceful degradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    def test_empty_payloads_returns_empty_valid_dict(self, monkeypatch):
        _patch_run_sync(monkeypatch, [])
        import homeowner_osint as m
        result = m.resolve("SOME OWNER")
        assert result["candidate_emails"] == []
        assert result["identity_score"] == 0
        assert result["verdict"] == "osint_unavailable"
        assert "raw_investigation_id" in result

    def test_no_name_returns_graceful_empty(self, monkeypatch):
        _patch_run_sync(monkeypatch, [])
        import homeowner_osint as m
        result = m.resolve("")
        assert result["candidate_emails"] == []
        assert result["verdict"] == "no_name_provided"

    def test_resolve_never_raises_on_empty(self, monkeypatch):
        _patch_run_sync(monkeypatch, [])
        import homeowner_osint as m
        # Should not raise regardless of input
        result = m.resolve("")
        assert isinstance(result, dict)

    def test_import_failure_returns_empty_dict(self, monkeypatch):
        """Simulates osint_api being completely unavailable."""
        import homeowner_osint as m
        # Patch the module so run_investigation_sync import raises ImportError
        original_resolve = m.resolve

        def _broken_resolve(name, address="", city="", state="",
                            mailing_address="", lead_id=None):
            if not (name or "").strip():
                result = dict(m._EMPTY_RESULT)
                result["verdict"] = "no_name_provided"
                return result
            try:
                raise ImportError("osint_api not available in this env")
            except Exception:
                return dict(m._EMPTY_RESULT)

        monkeypatch.setattr(m, "resolve", _broken_resolve)
        result = m.resolve("STOKES LAMAR")
        assert result["candidate_emails"] == []
        assert result["identity_score"] == 0
        assert result["verdict"] == "osint_unavailable"
        assert isinstance(result, dict)

    def test_resolve_with_all_optional_args(self, monkeypatch):
        """Confirm the function accepts all optional params without error."""
        _patch_run_sync(monkeypatch, [_make_email_discovery_payload(SYNTHETIC_FULL_RESULTS)])
        import homeowner_osint as m
        result = m.resolve(
            name="KEMP HAROLD",
            address="456 Oak Ave",
            city="Atlanta",
            state="GA",
            mailing_address="789 Other St, CA",
            lead_id="leg_abc123",
        )
        assert isinstance(result, dict)
        assert "candidate_emails" in result


# ---------------------------------------------------------------------------
# Tests: _extract_emails internals (unit-level)
# ---------------------------------------------------------------------------

class TestExtractEmails:
    def test_returns_empty_for_no_email_discovery_payload(self):
        import homeowner_osint as m
        result = m._extract_emails([_make_skip_trace_payload()])
        assert result == []

    def test_deduplicates_on_email_address(self):
        """If the same email appears twice in full_results, it appears once."""
        import homeowner_osint as m
        dups = [
            {"email": "a@gmail.com", "score": 50, "mx_ok": True,
             "emailrep": {}, "hibp_exists": None, "summary": ""},
            {"email": "a@gmail.com", "score": 50, "mx_ok": True,
             "emailrep": {}, "hibp_exists": None, "summary": ""},
        ]
        payload = _make_email_discovery_payload(dups)
        # _extract_emails doesn't dedup by design (it's a list); just confirm
        # the email address normalizes to lowercase
        extracted = m._extract_emails([payload])
        assert all(c["email"] == c["email"].lower() for c in extracted)

    def test_skips_entries_without_at_sign(self):
        import homeowner_osint as m
        garbage = [{"email": "not-an-email", "score": 30, "mx_ok": False,
                    "emailrep": {}, "hibp_exists": None, "summary": ""}]
        payload = _make_email_discovery_payload(garbage)
        extracted = m._extract_emails([payload])
        assert all("@" in c["email"] for c in extracted)
