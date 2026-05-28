"""Tests for outreach_templates.py.

Covers:
- classify_lead for all lead types
- first_name from assessor-formatted strings
- render_first_touch voice differences across personas
- TN-only constraint (no non-TN state names in body)
- persona email + title in output
- LLC lead gets professional (non-first-name) opener
- All four personas render without error
"""
from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import outreach_templates as ot

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_RITA_LEAD = {
    "owner_name": "TOWNSEND RITA M",
    "property_address": "836 N BELLEVUE BLVD",
    "address": "836 N BELLEVUE BLVD",
    "city": "Memphis",
    "state": "TN",
    "mailing_address": "836 N BELLEVUE BLVD MEMPHIS TN",  # same -> individual
}

_LLC_LEAD = {
    "owner_name": "MAGNOLIA HOLDINGS LLC",
    "property_address": "1200 UNION AVE",
    "city": "Memphis",
    "state": "TN",
    "mailing_address": "PO BOX 1000 CHICAGO IL 60601",  # different -> absentee, but LLC wins
}

_JOINT_LEAD = {
    "owner_name": "JOHNSON JAMES AND JOHNSON CAROL",
    "property_address": "500 SUMMER AVE",
    "city": "Memphis",
    "state": "TN",
}

_ABSENTEE_LEAD = {
    "owner_name": "WALKER DARNELL",
    "property_address": "210 POPLAR AVE MEMPHIS TN",
    "city": "Memphis",
    "state": "TN",
    "mailing_address": "9000 SUNSET BLVD LOS ANGELES CA 90028",
}

_PROBATE_LEAD = {
    "owner_name": "ESTATE OF HAROLD GREEN",
    "property_address": "77 JACKSON AVE",
    "city": "Memphis",
    "state": "TN",
}

_UNKNOWN_LEAD = {
    "owner_name": "",
    "property_address": "100 MAIN ST",
    "city": "Memphis",
    "state": "TN",
}

# Non-TN state names that must never appear in any rendered template
_BANNED_STATES = [
    "Atlanta", "Georgia", "Houston", "Texas", "Florida", "Arizona",
    "Missouri", "California", "Ohio", "Chicago", "Illinois",
    # Partial matches that would indicate cross-state drift
    " GA ", " TX ", " FL ", " AZ ", " MO ", " CA ", " OH ",
]


# ---------------------------------------------------------------------------
# classify_lead tests
# ---------------------------------------------------------------------------

class TestClassifyLead:

    def test_llc(self):
        assert ot.classify_lead(_LLC_LEAD) == "llc"

    def test_joint_couple(self):
        assert ot.classify_lead(_JOINT_LEAD) == "joint_couple"

    def test_absentee(self):
        assert ot.classify_lead(_ABSENTEE_LEAD) == "absentee"

    def test_probate(self):
        assert ot.classify_lead(_PROBATE_LEAD) == "probate"

    def test_individual(self):
        assert ot.classify_lead(_RITA_LEAD) == "individual"

    def test_unknown_blank_name(self):
        assert ot.classify_lead(_UNKNOWN_LEAD) == "unknown"

    def test_inc_classified_as_llc(self):
        lead = {"owner_name": "SUNBELT REAL ESTATE INC", "property_address": "123 Main"}
        assert ot.classify_lead(lead) == "llc"

    def test_trust_classified_as_llc(self):
        lead = {"owner_name": "HENDERSON FAMILY TRUST", "property_address": "456 Elm"}
        assert ot.classify_lead(lead) == "llc"


# ---------------------------------------------------------------------------
# first_name tests
# ---------------------------------------------------------------------------

class TestFirstName:

    def test_standard_last_first_middle(self):
        assert ot.first_name("TOWNSEND RITA M") == "Rita"

    def test_single_token(self):
        # Only one word -- fall back to that word
        result = ot.first_name("SMITHSON")
        assert result == "Smithson"

    def test_blank_name(self):
        assert ot.first_name("") == "There"

    def test_two_token(self):
        assert ot.first_name("JOHNSON JAMES") == "James"

    def test_title_cased(self):
        # Always returns title-cased
        assert ot.first_name("BROWN MARY ALICE") == "Mary"


# ---------------------------------------------------------------------------
# render_first_touch tests
# ---------------------------------------------------------------------------

class TestRenderFirstTouch:

    def test_piper_contains_memphis(self):
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"].lower()
        assert "memphis" in body, "Piper first-touch must mention Memphis"

    def test_piper_contains_persona_name(self):
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"].lower()
        assert "piper" in body, "Piper first-touch must contain Piper's name in signature"

    def test_henry_different_from_piper(self):
        piper = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        henry = ot.render_first_touch(_RITA_LEAD, persona_key="henry")
        assert piper["body_html"] != henry["body_html"], (
            "Piper and Henry must produce different body_html (distinct voices)"
        )

    def test_piper_voice_warm_opener(self):
        """Piper opens warmly -- 'Hey Rita' or similar, not corporate speak."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        # Should not start with "Greetings" or "Dear Sir"
        assert "Greetings" not in body
        assert "To Whom It May Concern" not in body

    def test_llc_lead_no_first_name_salutation(self):
        """LLC leads must not open with 'Hey [Name]' -- should use 'Hi,' or equivalent."""
        result = ot.render_first_touch(_LLC_LEAD, persona_key="piper")
        body = result["body_html"]
        # Should NOT contain "Hey Magnolia" or similar first-name-from-LLC
        assert "Hey Magnolia" not in body, (
            "LLC lead should not get a first-name salutation derived from company name"
        )
        # Should contain a professional opener
        assert any(opener in body for opener in ["Hi,", "Hi there,", "Good afternoon,"]), (
            f"LLC lead body_html should use a professional opener. Got: {body[:200]}"
        )

    def test_no_non_tn_state_names_piper(self):
        """Piper output must never contain non-TN state names."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        for banned in _BANNED_STATES:
            assert banned not in body, (
                f"Piper body_html contains banned state reference '{banned}'"
            )

    def test_no_non_tn_state_names_henry(self):
        result = ot.render_first_touch(_RITA_LEAD, persona_key="henry")
        body = result["body_html"]
        for banned in _BANNED_STATES:
            assert banned not in body, (
                f"Henry body_html contains banned state reference '{banned}'"
            )

    def test_no_non_tn_state_names_marvin(self):
        result = ot.render_first_touch(_RITA_LEAD, persona_key="marvin")
        body = result["body_html"]
        for banned in _BANNED_STATES:
            assert banned not in body, (
                f"Marvin body_html contains banned state reference '{banned}'"
            )

    def test_no_non_tn_state_names_vaughn(self):
        result = ot.render_first_touch(_RITA_LEAD, persona_key="vaughn")
        body = result["body_html"]
        for banned in _BANNED_STATES:
            assert banned not in body, (
                f"Vaughn body_html contains banned state reference '{banned}'"
            )

    def test_piper_persona_email_in_output(self):
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        assert result["persona"]["email"] == "piper@everlightventures.io"

    def test_henry_persona_title_in_output(self):
        result = ot.render_first_touch(_RITA_LEAD, persona_key="henry")
        assert "Negotiator" in result["persona"]["title"]

    def test_marvin_renders_without_error(self):
        result = ot.render_first_touch(_RITA_LEAD, persona_key="marvin")
        assert "body_html" in result
        assert len(result["body_html"]) > 50

    def test_vaughn_renders_without_error(self):
        result = ot.render_first_touch(_RITA_LEAD, persona_key="vaughn")
        assert "body_html" in result
        assert len(result["body_html"]) > 50

    def test_all_four_personas_return_required_keys(self):
        """Every persona returns {subject, body_html, persona} without error."""
        for key in ("piper", "henry", "marvin", "vaughn"):
            result = ot.render_first_touch(_RITA_LEAD, persona_key=key)
            assert "subject" in result, f"{key}: missing 'subject'"
            assert "body_html" in result, f"{key}: missing 'body_html'"
            assert "persona" in result, f"{key}: missing 'persona'"
            assert result["persona"]["email"].endswith("@everlightventures.io"), (
                f"{key}: persona email must be @everlightventures.io"
            )

    def test_invalid_persona_raises(self):
        with pytest.raises(ValueError, match="Unknown persona_key"):
            ot.render_first_touch(_RITA_LEAD, persona_key="nobody")

    def test_vaughn_uses_institutional_language(self):
        """Vaughn should sound senior / institutional -- no 'Hey' or casual openers."""
        result = ot.render_first_touch(_PROBATE_LEAD, persona_key="vaughn")
        body = result["body_html"]
        assert "Hey " not in body, "Vaughn should not use casual 'Hey' opener"
        # Should contain Vaughn-specific signals
        assert any(kw in body for kw in ["Sterling", "Senior Partner", "warm regards"]), (
            "Vaughn body_html should contain institutional signals"
        )

    def test_marvin_mentions_title_company(self):
        """Marvin's closing template should reference Mid-South Title."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="marvin")
        body = result["body_html"]
        assert "Mid-South" in body, "Marvin should reference Mid-South Title Company"
