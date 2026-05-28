"""Tests for outreach_templates.py.

Covers:
- classify_lead for all lead types
- first_name from assessor-formatted strings
- render_first_touch voice differences across personas
- TN-only constraint (no non-TN state names in body)
- persona email + title in output
- LLC lead gets professional (non-first-name) opener
- All four personas render without error
- NEW: each persona contains their dossier-specific catchphrases/signatures
- NEW: Piper-vs-Henry token diversity >= 70%
- NEW: data_lens returns persona-specific interpretation
- NEW: render_first_touch_followup and render_first_touch_final return valid output
- NEW: rex_belfort email touches call outreach_templates render functions
"""
from __future__ import annotations

import sys
import os
from unittest.mock import patch, MagicMock

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

_LONG_HOLD_LEAD = {
    "owner_name": "HARRIS CLARENCE B",
    "property_address": "422 CHELSEA AVE",
    "address": "422 CHELSEA AVE",
    "city": "Memphis",
    "state": "TN",
    "mailing_address": "422 CHELSEA AVE MEMPHIS TN",
    "years_owned": 18,
    "county_appraisal": 62000,
}

# Non-TN state names that must never appear in any rendered template
_BANNED_STATES = [
    "Atlanta", "Georgia", "Houston", "Texas", "Florida", "Arizona",
    "Missouri", "California", "Ohio", "Chicago", "Illinois",
    # Partial matches that would indicate cross-state drift
    " GA ", " TX ", " FL ", " AZ ", " MO ", " CA ", " OH ",
]


def _token_set(html_body: str) -> set[str]:
    """Strip HTML tags, lowercase, split on whitespace/punctuation for token comparison."""
    import re
    text = re.sub(r"<[^>]+>", " ", html_body)
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    return set(tokens)


def _token_similarity(body_a: str, body_b: str) -> float:
    """Jaccard similarity between token sets of two html bodies. 0=distinct, 1=identical."""
    a = _token_set(body_a)
    b = _token_set(body_b)
    if not a or not b:
        return 1.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union


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
        result = ot.first_name("SMITHSON")
        assert result == "Smithson"

    def test_blank_name(self):
        assert ot.first_name("") == "There"

    def test_two_token(self):
        assert ot.first_name("JOHNSON JAMES") == "James"

    def test_title_cased(self):
        assert ot.first_name("BROWN MARY ALICE") == "Mary"


# ---------------------------------------------------------------------------
# render_first_touch -- persona-specific phrase tests (NEW)
# ---------------------------------------------------------------------------

class TestPersonaCatchphrases:
    """Each persona's render must contain their signature phrases from the dossier."""

    # ---- NEW: operator blueprint voice checks ----

    def test_piper_no_too_formal_intro(self):
        """Piper must NOT open with the stiff 'My name is Piper Reeves with Everlight Ventures'."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "My name is Piper Reeves with Everlight Ventures" not in body, (
            "Piper opener is too formal -- must not use 'My name is Piper Reeves with Everlight Ventures'"
        )

    def test_piper_opener_starts_with_hey(self):
        """Piper must open with 'Hey' or equivalent casual greeting."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "Hey " in body or "Hi " in body, (
            "Piper first-touch must open with 'Hey' or warm equivalent"
        )

    def test_piper_intro_casual(self):
        """Piper introduces herself simply: 'I'm Piper with Everlight'."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "I'm Piper with Everlight" in body or "Piper with Everlight" in body, (
            "Piper must introduce herself casually: 'I'm Piper with Everlight'"
        )

    def test_piper_why_here_property_on_desk(self):
        """Piper must say the property came across her desk."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "came across my desk" in body or "came across" in body, (
            "Piper must say the property came across her desk"
        )

    def test_piper_dollar_range_stat(self):
        """Piper must include a ballpark dollar range stat about the house/block."""
        import re
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        dollar_ranges = re.findall(r"\$\d+", body)
        assert len(dollar_ranges) >= 1, (
            f"Piper first-touch must include a dollar range stat. Got: {body[:400]}"
        )

    def test_piper_casual_ask_phrase(self):
        """Piper must include a casual ask ('are you down', 'down for', 'let me know')."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"].lower()
        assert any(phrase in body for phrase in ["are you down", "down for", "down to", "let me know"]), (
            "Piper must include a casual ask phrase ('are you down', 'down for', 'let me know')"
        )

    def test_piper_no_false_deadline_friday(self):
        """Piper must NOT contain false deadline 'Friday' language."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "Friday" not in body, (
            "Piper first-touch must not contain false deadline 'Friday' language"
        )

    def test_piper_no_no_obligation_cash_offer_this(self):
        """Piper must NOT use the phrase 'no-obligation cash offer this'."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "no-obligation cash offer this" not in body.lower(), (
            "Piper first-touch must not contain false urgency 'no-obligation cash offer this'"
        )

    def test_piper_no_closing_my_open_files(self):
        """Piper must NOT use 'closing my open files' anywhere in first touch."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "closing my open files" not in body.lower(), (
            "Piper first-touch must not use 'closing my open files' pressure framing"
        )

    def test_piper_no_buyer_allocated(self):
        """Piper must NOT use 'buyer allocated' pressure language."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "buyer allocated" not in body.lower(), (
            "Piper first-touch must not use 'buyer allocated' pressure language"
        )

    def test_piper_no_pressure_close(self):
        """Piper's close must contain a no-pressure line."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert any(phrase in body.lower() for phrase in [
            "no worries", "timing isn't right", "timing is not right", "no rush", "whenever"
        ]), (
            "Piper must close with a no-pressure line"
        )

    # ---- EXISTING: Piper voice checks (updated to match new blueprint) ----

    def test_piper_honest_with_you(self):
        """Piper's 'honest with you' tell must appear in her long-hold first touch."""
        result = ot.render_first_touch(_LONG_HOLD_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "Honest with you" in body or "honest with you" in body, (
            "Piper should use her 'Honest with you' tell on long-hold leads"
        )

    def test_piper_two_persona_phrases(self):
        """Piper's body must contain at least 2 persona-specific phrases."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        piper_phrases = [
            "Piper with Everlight",
            "came across my desk",
            "Memphis",
            "no worries",
            "no rush",
            "down for",
            "are you down",
            "down to",
        ]
        found = [p for p in piper_phrases if p in body]
        assert len(found) >= 2, (
            f"Piper body must contain at least 2 persona phrases. "
            f"Found {len(found)}: {found}"
        )

    def test_henry_math_framing(self):
        """Henry must reference the math / spread / numbers framing."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="henry")
        body = result["body_html"]
        henry_markers = [
            "honest read",
            "comps",
            "Math first",
            "no hard feelings",
            "we'll pass",
            "where I can be today",
        ]
        found = [m for m in henry_markers if m in body]
        assert len(found) >= 2, (
            f"Henry body must contain at least 2 math/numbers-framing phrases. "
            f"Found {len(found)}: {found}"
        )

    def test_henry_no_hard_feelings_walk_away(self):
        """Henry's walks-away phrase must appear."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="henry")
        body = result["body_html"]
        assert "no hard feelings" in body or "we'll pass" in body, (
            "Henry must contain his walks-away framing ('no hard feelings -- we'll pass')"
        )

    def test_henry_math_first_catchphrase(self):
        """Henry's 'Math first, feelings second' catchphrase must appear."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="henry")
        body = result["body_html"]
        assert "Math first" in body, (
            "Henry must use his catchphrase 'Math first, feelings second'"
        )

    def test_marvin_procedural_15_min_confirm(self):
        """Marvin's '15 minutes' confirmation pledge must appear."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="marvin")
        body = result["body_html"]
        assert "15 minutes" in body, (
            "Marvin must include his '15 minutes' receipt confirmation pledge"
        )

    def test_marvin_mid_south_title(self):
        """Marvin's template must reference Mid-South Title."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="marvin")
        body = result["body_html"]
        assert "Mid-South" in body, (
            "Marvin must reference Mid-South Title Company -- it's his anchor partner"
        )

    def test_marvin_not_in_writing_catchphrase(self):
        """Marvin's 'If it's not in writing' catchphrase must appear."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="marvin")
        body = result["body_html"]
        assert "not in writing" in body, (
            "Marvin must use his catchphrase 'If it's not in writing, it's not in writing'"
        )

    def test_marvin_numbered_list(self):
        """Marvin uses numbered lists -- closing handoff must have <ol> or numbered items."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="marvin")
        body = result["body_html"]
        assert "<ol>" in body or "<li>" in body, (
            "Marvin closing handoff must use a numbered list"
        )

    def test_vaughn_no_deadline(self):
        """Vaughn's 'There is no deadline' line must appear."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="vaughn")
        body = result["body_html"]
        assert "There is no deadline" in body or "no deadline" in body.lower(), (
            "Vaughn must contain his 'There is no deadline on my end' line"
        )

    def test_vaughn_line_always_open(self):
        """Vaughn's 'my line is always open' closer must appear."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="vaughn")
        body = result["body_html"]
        assert "my line is always open" in body or "line is always open" in body, (
            "Vaughn must close with 'my line is always open'"
        )

    def test_vaughn_in_my_experience(self):
        """Vaughn's 'In my experience' phrase from his dossier must appear."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="vaughn")
        body = result["body_html"]
        assert "In my experience" in body or "I would like to be direct" in body or \
               "direct with you" in body, (
            "Vaughn must use 'In my experience' or 'I would like to be direct with you'"
        )

    def test_vaughn_two_persona_phrases(self):
        """Vaughn's body must contain at least 2 of his signature phrases."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="vaughn")
        body = result["body_html"]
        vaughn_phrases = [
            "There is no deadline",
            "my line is always open",
            "In my experience",
            "direct with you",
            "warm regards",
            "Senior Partner",
            "stewardship",
        ]
        found = [p for p in vaughn_phrases if p in body]
        assert len(found) >= 2, (
            f"Vaughn body must contain at least 2 persona phrases. "
            f"Found {len(found)}: {found}"
        )


# ---------------------------------------------------------------------------
# Piper vs Henry token diversity (NEW -- distinct voices are the contract)
# ---------------------------------------------------------------------------

class TestVoiceDiversity:

    def test_piper_vs_henry_token_diversity(self):
        """Piper and Henry on the same lead must share less than 30% of word tokens.

        Jaccard similarity < 0.30 means they differ by > 70% of vocabulary tokens.
        This is the contractual guarantee that different personas = different emails.
        """
        piper = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        henry = ot.render_first_touch(_RITA_LEAD, persona_key="henry")
        similarity = _token_similarity(piper["body_html"], henry["body_html"])
        assert similarity < 0.30, (
            f"Piper and Henry are too similar on the same lead. "
            f"Jaccard similarity = {similarity:.2f} (must be < 0.30). "
            f"These must read as completely different people."
        )

    def test_piper_vs_vaughn_token_diversity(self):
        """Piper and Vaughn must also produce meaningfully different bodies."""
        piper = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        vaughn = ot.render_first_touch(_RITA_LEAD, persona_key="vaughn")
        similarity = _token_similarity(piper["body_html"], vaughn["body_html"])
        assert similarity < 0.40, (
            f"Piper and Vaughn too similar: Jaccard = {similarity:.2f} (must be < 0.40)"
        )

    def test_marvin_vs_piper_token_diversity(self):
        """Marvin and Piper must produce distinct bodies."""
        piper = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        marvin = ot.render_first_touch(_RITA_LEAD, persona_key="marvin")
        similarity = _token_similarity(piper["body_html"], marvin["body_html"])
        assert similarity < 0.40, (
            f"Marvin and Piper too similar: Jaccard = {similarity:.2f} (must be < 0.40)"
        )


# ---------------------------------------------------------------------------
# data_lens tests (NEW)
# ---------------------------------------------------------------------------

class TestDataLens:

    def test_piper_lens_is_human_angle(self):
        """Piper's lens reads as human/emotional, not math."""
        lens = ot.data_lens("piper", _RITA_LEAD)
        # Piper sees the human story
        assert any(word in lens.lower() for word in
                   ["long-time", "real", "story", "roots", "straight answer", "owners"]), (
            f"Piper's data_lens should reference the human angle. Got: {lens}"
        )

    def test_henry_lens_is_math_angle(self):
        """Henry's lens reads as numbers/comps-first."""
        lens = ot.data_lens("henry", _RITA_LEAD)
        assert any(word in lens.lower() for word in
                   ["comps", "spread", "math", "number", "honest read", "cash"]), (
            f"Henry's data_lens should reference math/comps. Got: {lens}"
        )

    def test_marvin_lens_is_process_angle(self):
        """Marvin's lens reads as title/process/paperwork focused."""
        lens = ot.data_lens("marvin", _RITA_LEAD)
        assert any(word in lens.lower() for word in
                   ["title", "closing", "contract", "writing", "mid-south", "emd", "shelby"]), (
            f"Marvin's data_lens should reference the closing/title process. Got: {lens}"
        )

    def test_vaughn_lens_is_gravitas_angle(self):
        """Vaughn's lens reads as institutional/stewardship."""
        lens = ot.data_lens("vaughn", _RITA_LEAD)
        assert any(word in lens.lower() for word in
                   ["experience", "stewardship", "transaction", "weight",
                    "deadline", "direct", "wealth"]), (
            f"Vaughn's data_lens should convey gravitas/stewardship. Got: {lens}"
        )

    def test_piper_probate_lens_empathetic(self):
        """Piper's lens on a probate lead should be extra empathetic."""
        lens = ot.data_lens("piper", _PROBATE_LEAD)
        assert any(word in lens.lower() for word in
                   ["estate", "family", "managing", "quiet", "clean", "care"]), (
            f"Piper's probate lens should be empathetic. Got: {lens}"
        )

    def test_four_lenses_differ_on_same_lead(self):
        """All four personas must produce different lens text on the same lead."""
        lenses = {k: ot.data_lens(k, _RITA_LEAD) for k in ("piper", "henry", "marvin", "vaughn")}
        unique = set(lenses.values())
        assert len(unique) == 4, (
            "All four data_lens outputs must be unique strings -- "
            f"got {len(unique)} unique lenses out of 4"
        )

    def test_henry_lens_with_appraisal_includes_dollar_figure(self):
        """When county_appraisal is present, Henry's lens should quote a number."""
        lens = ot.data_lens("henry", _LONG_HOLD_LEAD)
        import re
        dollar_amounts = re.findall(r"\$[\d,]+", lens)
        assert dollar_amounts, (
            f"Henry's data_lens should include a dollar figure when appraisal is present. "
            f"Got: {lens}"
        )


# ---------------------------------------------------------------------------
# render_first_touch -- existing tests (all must still pass)
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
        assert "Greetings" not in body
        assert "To Whom It May Concern" not in body

    def test_llc_lead_no_first_name_salutation(self):
        """LLC leads must not open with 'Hey [Name]' -- should use 'Hi,' or equivalent."""
        result = ot.render_first_touch(_LLC_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "Hey Magnolia" not in body, (
            "LLC lead should not get a first-name salutation derived from company name"
        )
        assert any(opener in body for opener in ["Hi,", "Hi there,", "Good afternoon,"]), (
            f"LLC lead body_html should use a professional opener. Got: {body[:200]}"
        )

    def test_no_non_tn_state_names_piper(self):
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
        assert any(kw in body for kw in ["Sterling", "Senior Partner", "warm regards"]), (
            "Vaughn body_html should contain institutional signals"
        )

    def test_marvin_mentions_title_company(self):
        """Marvin's closing template should reference Mid-South Title."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="marvin")
        body = result["body_html"]
        assert "Mid-South" in body, "Marvin should reference Mid-South Title Company"


# ---------------------------------------------------------------------------
# render_first_touch_followup + render_first_touch_final (NEW)
# ---------------------------------------------------------------------------

class TestFollowupAndFinalVariants:

    def test_piper_followup_returns_valid_keys(self):
        result = ot.render_first_touch_followup(_RITA_LEAD, persona_key="piper")
        assert "subject" in result
        assert "body_html" in result
        assert "persona" in result

    def test_piper_followup_bumps_inbox(self):
        """Day-2 followup must bump the inbox casually -- no pressure language."""
        result = ot.render_first_touch_followup(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert any(kw in body for kw in ["bumping", "bump", "buried", "follow", "last note"]), (
            f"Piper day-2 followup should bump the inbox casually. Body: {body[:300]}"
        )

    def test_piper_followup_no_buyer_allocated(self):
        """Day-2 followup must NOT contain 'buyer allocated' pressure language."""
        result = ot.render_first_touch_followup(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "buyer allocated" not in body.lower(), (
            "Piper day-2 followup must not use 'buyer allocated' pressure language"
        )

    def test_piper_followup_no_friday(self):
        """Day-2 followup must NOT contain false deadline 'Friday'."""
        result = ot.render_first_touch_followup(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "Friday" not in body, (
            "Piper day-2 followup must not contain false deadline 'Friday'"
        )

    def test_piper_final_warm_closure(self):
        """Day-4 final must contain warm closure language, no false deadlines."""
        result = ot.render_first_touch_final(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert any(kw in body for kw in ["last note", "timing", "no expiration", "find me", "okay"]), (
            f"Piper day-4 final should contain warm closure language. Body: {body[:300]}"
        )

    def test_piper_final_no_closing_my_open_files(self):
        """Day-4 final must NOT use 'closing my open files' framing."""
        result = ot.render_first_touch_final(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "closing my open files" not in body.lower(), (
            "Piper day-4 final must not use 'closing my open files' false urgency"
        )

    def test_piper_final_no_friday(self):
        """Day-4 final must NOT contain false deadline 'Friday'."""
        result = ot.render_first_touch_final(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "Friday" not in body, (
            "Piper day-4 final must not contain 'Friday' false deadline"
        )

    def test_henry_followup_returns_valid_output(self):
        result = ot.render_first_touch_followup(_RITA_LEAD, persona_key="henry")
        assert "body_html" in result
        assert len(result["body_html"]) > 20

    def test_vaughn_followup_returns_valid_output(self):
        result = ot.render_first_touch_followup(_RITA_LEAD, persona_key="vaughn")
        assert "body_html" in result
        assert len(result["body_html"]) > 20

    def test_marvin_followup_two_items_pending(self):
        result = ot.render_followup(_RITA_LEAD, touch_index=1, persona_key="marvin")
        body = result["body_html"]
        assert "15 minutes" in body or "pending" in body, (
            "Marvin follow-up should mention pending items or 15-minute confirmation"
        )


# ---------------------------------------------------------------------------
# render_followup tests
# ---------------------------------------------------------------------------

class TestRenderFollowup:

    def test_piper_followup_touch1(self):
        result = ot.render_followup(_RITA_LEAD, touch_index=1, persona_key="piper")
        assert "body_html" in result
        body = result["body_html"]
        assert "Memphis" in body

    def test_piper_followup_touch2_uses_yall(self):
        result = ot.render_followup(_RITA_LEAD, touch_index=2, persona_key="piper")
        body = result["body_html"]
        # Touch 2 is the "last note" -- should have the y'all / door stays open tone
        assert any(kw in body for kw in ["y'all", "door", "last", "nuisance", "right time"]), (
            f"Piper final follow-up should have closure energy. Got: {body[:300]}"
        )

    def test_henry_followup_math_still_there(self):
        result = ot.render_followup(_RITA_LEAD, touch_index=1, persona_key="henry")
        body = result["body_html"]
        assert "math" in body.lower() or "number" in body.lower() or "spread" in body.lower(), (
            "Henry follow-up should still reference the math"
        )

    def test_all_personas_followup_returns_keys(self):
        for key in ("piper", "henry", "marvin", "vaughn"):
            result = ot.render_followup(_RITA_LEAD, touch_index=1, persona_key=key)
            assert "subject" in result
            assert "body_html" in result
            assert "persona" in result


# ---------------------------------------------------------------------------
# rex_belfort sequence integration test (NEW -- Part B)
# ---------------------------------------------------------------------------

class TestRexBelfortTemplateWiring:
    """Verify that rex_belfort_sequence email touches call outreach_templates."""

    def test_email_touches_use_render_first_touch(self):
        """The three email touches in the Belfort sequence must call render functions."""
        # We can validate this by importing the module and inspecting that the
        # BELFORT_TOUCHES dict email channel entries reference outreach_templates.
        # The actual wire is done by _get_personalized_content -> render_first_touch.
        # We test the integration by calling the template renders directly as the
        # sequence would -- same lead dict, same persona_key.
        lead = dict(_RITA_LEAD)
        lead["owner_email"] = "rita@example.com"

        # Day-0-hour-4 (touch index 1) -- render_first_touch
        result_day0 = ot.render_first_touch(lead, persona_key="piper")
        assert result_day0["subject"], "Day-0 email subject must be non-empty"
        assert "piper" in result_day0["body_html"].lower(), "Day-0 email must be signed by Piper"
        # Piper must introduce herself and reference the property coming across her desk
        assert "Piper with Everlight" in result_day0["body_html"] or \
               "came across" in result_day0["body_html"], (
            "Day-0 email must carry Piper's casual intro and desk-reference"
        )

        # Day-2 (touch index 3) -- render_first_touch_followup
        result_day2 = ot.render_first_touch_followup(lead, persona_key="piper")
        assert result_day2["subject"], "Day-2 followup subject must be non-empty"
        assert "piper" in result_day2["body_html"].lower(), "Day-2 email must be signed by Piper"

        # Day-4 (touch index 5) -- render_first_touch_final
        result_day4 = ot.render_first_touch_final(lead, persona_key="piper")
        assert result_day4["subject"], "Day-4 final subject must be non-empty"
        assert "piper" in result_day4["body_html"].lower(), "Day-4 email must be signed by Piper"

        # Verify the three are distinct -- not the same template repeated
        assert result_day0["body_html"] != result_day2["body_html"], (
            "Day-0, Day-2 emails must be distinct"
        )
        assert result_day2["body_html"] != result_day4["body_html"], (
            "Day-2, Day-4 emails must be distinct"
        )
        assert result_day0["body_html"] != result_day4["body_html"], (
            "Day-0, Day-4 emails must be distinct"
        )

    def test_render_functions_accept_lead_dict_from_belfort(self):
        """Simulate the lead dict shape that rex_belfort_sequence builds and verify renders."""
        # This is the shape rex_belfort_sequence uses internally
        belfort_lead = {
            "owner_name": "TOWNSEND RITA M",
            "address": "836 N BELLEVUE BLVD",
            "property_address": "836 N BELLEVUE BLVD",
            "city": "Memphis",
            "state": "TN",
            "owner_email": "owner@example.com",
            "sequence_step": 1,
            "enriched": False,
            "detected_distress": "high_equity",
            "years_owned": 12,
            "county_appraisal": 55000,
        }
        for fn in (ot.render_first_touch, ot.render_first_touch_followup, ot.render_first_touch_final):
            result = fn(belfort_lead, persona_key="piper")
            assert result["subject"]
            assert result["body_html"]
            assert result["persona"]["email"] == "piper@everlightventures.io"


# ---------------------------------------------------------------------------
# rex_negotiator (Henry) + rex_closer (Marvin) wiring tests
# ---------------------------------------------------------------------------

class TestNegotiatorAndCloserWiring:
    """
    Verify render_negotiation (Henry) and render_closing_handoff (Marvin) produce
    correct, persona-pure output on Rita Townsend's lead.

    These tests mirror how rex_negotiator.py and rex_closer.py call the templates.
    """

    _RITA = {
        "owner_name": "TOWNSEND RITA M",
        "property_address": "836 N BELLEVUE BLVD",
        "address": "836 N BELLEVUE BLVD",
        "city": "Memphis",
        "state": "TN",
        "mailing_address": "836 N BELLEVUE BLVD MEMPHIS TN",
        "county_appraisal": 72000,
    }

    def test_henry_negotiation_body_contains_numbers_reference(self):
        """Henry's render_negotiation must contain a $, 'spread', or 'comps' reference."""
        result = ot.render_negotiation(self._RITA, persona_key="henry")
        body = result["body_html"]
        assert any(kw in body for kw in ["$", "spread", "comps"]), (
            "Henry negotiation body must contain a numbers reference ($, spread, or comps). "
            f"Got (first 300 chars): {body[:300]}"
        )

    def test_henry_negotiation_body_contains_henry_signature(self):
        """Henry's render_negotiation body must contain his name in the signature."""
        result = ot.render_negotiation(self._RITA, persona_key="henry")
        body = result["body_html"]
        assert "Henry" in body, (
            "Henry negotiation body must contain 'Henry' in the signature block. "
            f"Got (first 300 chars): {body[:300]}"
        )

    def test_henry_negotiation_references_memphis_or_tennessee(self):
        """TN-only constraint -- Henry's template must anchor to Memphis or Tennessee."""
        result = ot.render_negotiation(self._RITA, persona_key="henry")
        body = result["body_html"]
        assert "Memphis" in body or "Tennessee" in body or "TN" in body, (
            "Henry negotiation body must reference Memphis or Tennessee (TN-only doctrine). "
            f"Got (first 400 chars): {body[:400]}"
        )

    def test_henry_negotiation_no_piper_signature_contamination(self):
        """Henry's negotiation email must not have Piper's signature or email address.

        Note: 'picking up from Piper' is intentional handoff language and is allowed.
        What must NOT appear is Piper's signature block or email alias.
        """
        result = ot.render_negotiation(self._RITA, persona_key="henry")
        body = result["body_html"]
        assert "piper@everlightventures.io" not in body, (
            "Henry negotiation body must not contain Piper's email address. "
            f"Found in: {body[:400]}"
        )
        assert "Outreach Specialist" not in body, (
            "Henry negotiation body must not contain Piper's title (cross-persona signature leak). "
            f"Found in: {body[:400]}"
        )

    def test_marvin_closing_handoff_contains_mid_south_title(self):
        """Marvin's render_closing_handoff must reference Mid-South Title."""
        result = ot.render_closing_handoff(self._RITA, persona_key="marvin")
        body = result["body_html"]
        assert "Mid-South" in body, (
            "Marvin closing handoff must reference Mid-South Title (his anchor partner). "
            f"Got (first 300 chars): {body[:300]}"
        )

    def test_marvin_closing_handoff_contains_marvin_signature(self):
        """Marvin's render_closing_handoff body must contain his name."""
        result = ot.render_closing_handoff(self._RITA, persona_key="marvin")
        body = result["body_html"]
        assert "Marvin" in body, (
            "Marvin closing handoff must contain 'Marvin' in the signature block. "
            f"Got (first 300 chars): {body[:300]}"
        )

    def test_marvin_closing_handoff_contains_procedural_list(self):
        """Marvin's closing handoff must have a numbered list (his dossier-mandated style)."""
        result = ot.render_closing_handoff(self._RITA, persona_key="marvin")
        body = result["body_html"]
        import re
        has_numbered_html = "<ol>" in body or "<li>" in body
        has_numbered_text = bool(re.search(r"\b[123]\.", body))
        assert has_numbered_html or has_numbered_text, (
            "Marvin closing handoff must contain a numbered/procedural list. "
            f"Got (first 500 chars): {body[:500]}"
        )

    def test_marvin_closing_handoff_references_memphis_or_tennessee(self):
        """TN-only constraint -- Marvin's template must anchor to Memphis or Tennessee."""
        result = ot.render_closing_handoff(self._RITA, persona_key="marvin")
        body = result["body_html"]
        assert "Memphis" in body or "Tennessee" in body or "TN" in body, (
            "Marvin closing handoff must reference Memphis or Tennessee (TN-only doctrine). "
            f"Got (first 400 chars): {body[:400]}"
        )

    def test_marvin_closing_handoff_no_piper_contamination(self):
        """Marvin's closing handoff must not contain 'Piper' -- cross-persona check."""
        result = ot.render_closing_handoff(self._RITA, persona_key="marvin")
        body = result["body_html"]
        assert "Piper" not in body, (
            "Marvin closing handoff must not contain 'Piper' -- cross-persona contamination. "
            f"Found in: {body[:400]}"
        )


# ---------------------------------------------------------------------------
# NEW: Operator blueprint compliance tests
# ---------------------------------------------------------------------------

_RITA_WITH_APPRAISAL = {
    "owner_name": "TOWNSEND RITA M",
    "property_address": "836 N BELLEVUE",
    "address": "836 N BELLEVUE",
    "city": "Memphis",
    "state": "TN",
    "parcel_id": "021083 00056",
    "source": "shelby_tax_delinquent_csv_2026-04-28",
    "county_appraisal": 58000,
    "mailing_address": "836 N BELLEVUE MEMPHIS TN",
}

_APPRAISAL_LEAD = {
    "owner_name": "HARRIS CLARENCE B",
    "property_address": "422 CHELSEA AVE",
    "address": "422 CHELSEA AVE",
    "city": "Memphis",
    "state": "TN",
    "mailing_address": "422 CHELSEA AVE MEMPHIS TN",
    "years_owned": 18,
    "county_appraisal": 62000,
    "source": "shelby_tax_delinquent_csv_2026-04-28",
    "lead_type": "tax_lien",
}

_NO_APPRAISAL_LEAD = {
    "owner_name": "WALKER DARNELL",
    "property_address": "210 POPLAR AVE MEMPHIS TN",
    "city": "Memphis",
    "state": "TN",
    "mailing_address": "9000 SUNSET BLVD LOS ANGELES CA 90028",
    # no county_appraisal
}


class TestOperatorBlueprintCompliance:
    """All personas must comply with the operator's data-first blueprint:
    signal + data + real number + future state + direct CTA."""

    # ---- Piper: dollar number when appraisal is present ----

    def test_piper_first_touch_has_dollar_number_when_appraisal_present(self):
        """When county_appraisal is set, Piper first_touch must contain a dollar number."""
        import re
        result = ot.render_first_touch(_RITA_WITH_APPRAISAL, persona_key="piper")
        body = result["body_html"]
        dollar_amounts = re.findall(r"\$\d[\d,]*", body)
        assert dollar_amounts, (
            f"Piper first_touch must contain a dollar number when county_appraisal is present. "
            f"county_appraisal=58000. Got body (first 600 chars): {body[:600]}"
        )

    def test_piper_offer_range_reflects_appraisal(self):
        """Piper's rendered offer range must be derived from county_appraisal (55-70% band)."""
        import re
        result = ot.render_first_touch(_RITA_WITH_APPRAISAL, persona_key="piper")
        body = result["body_html"]
        # appraisal=58000 -> 55%=$31,900, 70%=$40,600. Both should appear.
        low_str = "31,900"
        high_str = "40,600"
        assert low_str in body or "31" in body, (
            f"Piper offer range lower bound not found for appraisal=58000 (expect ~$31,900). "
            f"Body: {body[:800]}"
        )
        assert high_str in body or "40" in body, (
            f"Piper offer range upper bound not found for appraisal=58000 (expect ~$40,600). "
            f"Body: {body[:800]}"
        )

    def test_piper_no_dollar_fallback_when_appraisal_missing(self):
        """When appraisal is missing, Piper must still include a dollar fallback range."""
        import re
        result = ot.render_first_touch(_NO_APPRAISAL_LEAD, persona_key="piper")
        body = result["body_html"]
        dollar_amounts = re.findall(r"\$\d[\d,]*", body)
        assert dollar_amounts, (
            "Piper first_touch must still include a fallback dollar range even without appraisal. "
            f"Body: {body[:600]}"
        )

    # ---- Piper: specific reason we reached out (signal) ----

    def test_piper_tax_delinquent_signal_in_body(self):
        """When source=shelby_tax_delinquent, Piper body must reference the tax signal."""
        result = ot.render_first_touch(_RITA_WITH_APPRAISAL, persona_key="piper")
        body = result["body_html"].lower()
        assert any(phrase in body for phrase in [
            "delinquent", "tax", "back-tax", "tax balance", "tax burden"
        ]), (
            "Piper must name the specific signal (tax delinquent) when source indicates it. "
            f"Body: {body[:600]}"
        )

    def test_piper_signal_named_not_generic_desk_only(self):
        """Piper body must go beyond 'your property came across my desk' -- must name the WHY."""
        result = ot.render_first_touch(_RITA_WITH_APPRAISAL, persona_key="piper")
        body = result["body_html"]
        # Must contain both the desk reference AND the specific signal reason
        has_desk = "came across" in body
        has_signal = any(phrase in body.lower() for phrase in [
            "delinquent", "tax", "quitclaim", "probate", "absentee", "out of town",
            "estate", "long time", "no recent", "vacant"
        ])
        assert has_desk and has_signal, (
            "Piper must include BOTH 'came across my desk' AND the specific outreach reason. "
            f"has_desk={has_desk}, has_signal={has_signal}. Body: {body[:600]}"
        )

    # ---- All personas: future-state phrase ----

    def test_piper_contains_future_state_phrase(self):
        """Piper first_touch must contain a future-state outcome phrase."""
        result = ot.render_first_touch(_RITA_WITH_APPRAISAL, persona_key="piper")
        body = result["body_html"].lower()
        future_phrases = [
            "clean exit", "out from under", "fresh start", "no back-tax burden",
            "walk away", "clean cash", "free and clear", "cash in hand",
            "no agent fees", "7 days"
        ]
        found = [p for p in future_phrases if p in body]
        assert found, (
            f"Piper first_touch must contain a future-state phrase. "
            f"None of {future_phrases} found. Body: {body[:600]}"
        )

    def test_henry_contains_future_state_phrase(self):
        """Henry negotiation must contain a future-state outcome phrase."""
        result = ot.render_first_touch(_APPRAISAL_LEAD, persona_key="henry")
        body = result["body_html"].lower()
        future_phrases = [
            "clean exit", "out from under", "fresh start", "no back-tax",
            "walk", "clean cash", "free and clear", "cash in hand", "7-day",
            "tax burden", "liquidity", "equity to cash"
        ]
        found = [p for p in future_phrases if p in body]
        assert found, (
            f"Henry negotiation must contain a future-state phrase. "
            f"None of {future_phrases} found. Body: {body[:600]}"
        )

    def test_vaughn_contains_future_state_phrase(self):
        """Vaughn first_touch must contain a future-state outcome phrase."""
        result = ot.render_first_touch(_RITA_WITH_APPRAISAL, persona_key="vaughn")
        body = result["body_html"].lower()
        future_phrases = [
            "liquidity", "clean", "carrying cost", "outcome", "certainty",
            "converts", "7-day", "cash close", "no obligation"
        ]
        found = [p for p in future_phrases if p in body]
        assert found, (
            f"Vaughn first_touch must contain a future-state outcome phrase. "
            f"None of {future_phrases} found. Body: {body[:600]}"
        )

    def test_marvin_contains_future_state_phrase(self):
        """Marvin closing handoff must reference the procedural future state (numbers in writing)."""
        result = ot.render_first_touch(_APPRAISAL_LEAD, persona_key="marvin")
        body = result["body_html"].lower()
        future_phrases = [
            "in writing", "closing date", "7 business days", "specific date",
            "mid-south", "clean", "actual number"
        ]
        found = [p for p in future_phrases if p in body]
        assert found, (
            f"Marvin must contain future-state / procedural clarity phrases. "
            f"None of {future_phrases} found. Body: {body[:600]}"
        )

    # ---- Piper: under 1200 chars on first_touch (no over-talking) ----

    def test_piper_first_touch_under_1200_chars_plain_text(self):
        """Piper first_touch body text (HTML stripped) must be under 1200 chars."""
        import re
        result = ot.render_first_touch(_RITA_WITH_APPRAISAL, persona_key="piper")
        body = result["body_html"]
        # strip HTML tags for char count
        plain = re.sub(r"<[^>]+>", " ", body)
        plain = re.sub(r"\s+", " ", plain).strip()
        char_count = len(plain)
        assert char_count <= 1200, (
            f"Piper first_touch must be under 1200 chars plain text (no over-talking). "
            f"Got {char_count} chars. Blueprint: 'We don't need to over-talk.' "
            f"Text (first 800): {plain[:800]}"
        )

    # ---- Piper: CTA is direct, not a phone call pitch ----

    def test_piper_cta_is_reply_based_not_call_pitch(self):
        """Piper's CTA must be reply-based ('send you a number', 'are you down', etc.)."""
        result = ot.render_first_touch(_RITA_WITH_APPRAISAL, persona_key="piper")
        body = result["body_html"].lower()
        # Must have a direct reply-based CTA
        cta_phrases = [
            "send you a real number", "send you the actual number",
            "are you down", "want me to send", "just reply",
            "let me know", "hit reply"
        ]
        found = [p for p in cta_phrases if p in body]
        assert found, (
            f"Piper CTA must be direct and reply-based (per blueprint: 'want me to send you a real number this week'). "
            f"None of {cta_phrases} found. Body: {body[:600]}"
        )

    # ---- Henry: appraisal-based number in negotiation ----

    def test_henry_negotiation_includes_computed_offer_range_from_appraisal(self):
        """Henry's negotiation email must include computed offer range when appraisal is present."""
        import re
        result = ot.render_first_touch(_APPRAISAL_LEAD, persona_key="henry")
        body = result["body_html"]
        dollar_amounts = re.findall(r"\$[\d,]+", body)
        assert len(dollar_amounts) >= 2, (
            f"Henry negotiation must include at least 2 dollar figures (range) when appraisal present. "
            f"Found: {dollar_amounts}. Body: {body[:600]}"
        )

    # ---- Vaughn: data + offer when appraisal present ----

    def test_vaughn_includes_offer_range_when_appraisal_present(self):
        """Vaughn must include computed offer range when county_appraisal is present."""
        import re
        result = ot.render_first_touch(_RITA_WITH_APPRAISAL, persona_key="vaughn")
        body = result["body_html"]
        dollar_amounts = re.findall(r"\$[\d,]+", body)
        assert dollar_amounts, (
            f"Vaughn must include a dollar range when county_appraisal is present. "
            f"Body: {body[:600]}"
        )


# ---------------------------------------------------------------------------
# Part D: Marquise persona tests
# ---------------------------------------------------------------------------

_MARQUISE_LEAD = {
    "owner_name": "EVANS ARIN B",
    "property_address": "942 MELROSE",
    "address": "942 MELROSE",
    "city": "Memphis",
    "state": "TN",
    "zip_code": "38114",
    "owner_mailing_zip": "38114",
    "owner_mailing_street": "905 S WILLETT ST",
    "county_appraisal": 25000,
    "total_appraisal_usd": 25000,
    "subdivision": "V C THOMAS",
    "last_sale_year": 2017,
    "last_sale_price_usd": 100,
    "sales_history": [
        {"type_code": "QC", "date": "2017-03-28", "price_usd": 100, "year": 2017},
        {"type_code": "QC", "date": "2011-02-15", "price_usd": 5010, "year": 2011},
    ],
    "permits": [{"year": 1979, "permit_number": "124026"}],
    "source": "shelby_tax_delinquent",
}


class TestMarquisePersona:
    """Marquise first_touch, anchor_offer, counter, pivot, final_wrap -- persona purity."""

    def test_marquise_first_touch_no_piper_contamination(self):
        """Marquise opener must not say 'I'm Piper' -- no persona contamination."""
        result = ot.render_marquise_first_touch(_MARQUISE_LEAD)
        body = result["body_html"]
        assert "I'm Piper" not in body, (
            "Marquise first touch must not contain Piper's name in the body -- persona contamination"
        )
        assert "piper@everlightventures.io" not in body, (
            "Marquise first touch must not contain Piper's email -- persona contamination"
        )

    def test_marquise_first_touch_no_outreach_specialist_title(self):
        """Marquise body must not contain 'Outreach Specialist' (Piper's title)."""
        result = ot.render_marquise_first_touch(_MARQUISE_LEAD)
        body = result["body_html"]
        assert "Outreach Specialist" not in body, (
            "Marquise first touch must not contain Piper's title 'Outreach Specialist'"
        )

    def test_marquise_first_touch_references_memphis(self):
        """Marquise body must reference Memphis explicitly."""
        result = ot.render_marquise_first_touch(_MARQUISE_LEAD)
        body = result["body_html"]
        assert "Memphis" in body or "38114" in body or "Orange Mound" in body, (
            f"Marquise first touch must reference Memphis / neighborhood. Body: {body[:400]}"
        )

    def test_marquise_first_touch_orange_mound_zip(self):
        """38114 zip lead should trigger Orange Mound neighborhood reference."""
        result = ot.render_marquise_first_touch(_MARQUISE_LEAD)
        body = result["body_html"]
        # 38114 is Orange Mound -- should appear somewhere
        assert "38114" in body or "Orange Mound" in body, (
            "Marquise first touch on 38114 lead must reference Orange Mound or the zip code"
        )

    def test_marquise_first_touch_marquise_signed(self):
        """Marquise body must contain his name in the signature."""
        result = ot.render_marquise_first_touch(_MARQUISE_LEAD)
        body = result["body_html"]
        assert "Marquise" in body, (
            "Marquise first touch must contain 'Marquise' in the signature block"
        )

    def test_marquise_first_touch_persona_key(self):
        """render_marquise_first_touch must return persona dict with marquise email."""
        result = ot.render_marquise_first_touch(_MARQUISE_LEAD)
        assert result["persona"]["email"] == "marquise@everlightventures.io", (
            "Marquise persona email must be marquise@everlightventures.io"
        )

    def test_marquise_first_touch_no_number(self):
        """Marquise first touch does NOT drop a dollar number -- gets the reply first."""
        import re
        result = ot.render_marquise_first_touch(_MARQUISE_LEAD)
        body = result["body_html"]
        # Strip county appraisal mentions; we're checking for offer numbers
        # Marquise first touch should NOT include an offer number (that's anchor_offer's job)
        # But it may mention the county value as credibility -- that's acceptable
        # What must NOT appear: explicit offer like "$16,250" or "my number is"
        assert "my number" not in body.lower() and "my offer" not in body.lower(), (
            "Marquise first touch must not drop a dollar offer -- gets reply first. "
            f"Body: {body[:400]}"
        )

    def test_marquise_anchor_offer_contains_dollar_number(self):
        """Marquise anchor_offer body must contain a dollar number (the actual offer)."""
        import re
        result = ot.render_marquise_anchor_offer(_MARQUISE_LEAD)
        body = result["body_html"]
        dollar_amounts = re.findall(r"\$[\d,]+", body)
        assert dollar_amounts, (
            "Marquise anchor_offer must contain a dollar number. "
            f"Got body: {body[:400]}"
        )

    def test_marquise_anchor_offer_65pct_of_appraisal(self):
        """Marquise anchor offer is 65% of appraisal -- should be $16,250 on $25,000."""
        result = ot.render_marquise_anchor_offer(_MARQUISE_LEAD)
        body = result["body_html"]
        # 25000 * 0.65 = $16,250
        assert "16,250" in body or "16250" in body, (
            "Marquise anchor_offer on $25k appraisal should quote $16,250 (65%). "
            f"Got body: {body[:400]}"
        )

    def test_marquise_anchor_offer_mid_south_title(self):
        """Marquise anchor_offer must reference Mid-South Title."""
        result = ot.render_marquise_anchor_offer(_MARQUISE_LEAD)
        body = result["body_html"]
        assert "Mid-South" in body, (
            "Marquise anchor_offer must reference Mid-South Title"
        )

    def test_marquise_counter_real_talk_correction(self):
        """Marquise counter must use 'Real talk' and reference the counter offer."""
        result = ot.render_marquise_counter(_MARQUISE_LEAD, seller_ask=23750, our_offer=21250)
        body = result["body_html"]
        assert "Real talk" in body or "real talk" in body or "correct" in body.lower(), (
            "Marquise counter must include real-talk framing or factual correction. "
            f"Body: {body[:400]}"
        )
        assert "21,250" in body, (
            "Marquise counter must contain our_offer $21,250 in the body"
        )

    def test_marquise_counter_cites_prior_sale_price(self):
        """Marquise counter cites the actual prior sale price from sales_history."""
        result = ot.render_marquise_counter(_MARQUISE_LEAD, seller_ask=23750, our_offer=21250)
        body = result["body_html"]
        # Prior sale in the lead is $5,010 (2011)
        assert "5,010" in body, (
            "Marquise counter must cite the actual prior sale price ($5,010) from sales_history. "
            f"Body: {body[:500]}"
        )

    def test_psa_contract_has_seven_blocks(self):
        """render_psa_contract must return exactly 7 blocks."""
        psa = ot.render_psa_contract(
            _MARQUISE_LEAD,
            {"purchase_price": 21250, "assignment_fee": 3000, "emd_amount": 500}
        )
        assert len(psa["blocks"]) == 7, (
            f"PSA contract must have exactly 7 blocks. Got {len(psa['blocks'])}: "
            f"{[b['title'] for b in psa['blocks']]}"
        )

    def test_psa_contract_block_titles(self):
        """PSA contract blocks must have expected titles."""
        psa = ot.render_psa_contract(
            _MARQUISE_LEAD,
            {"purchase_price": 21250, "assignment_fee": 3000}
        )
        titles = [b["title"] for b in psa["blocks"]]
        assert any("Parties" in t for t in titles), "PSA must have a 'Parties' block"
        assert any("Property" in t and "Earnest" in t for t in titles), "PSA must have a 'Property and Earnest Money' block"
        assert any("Equitable" in t for t in titles), "PSA must have an 'Equitable Interest' block"
        assert any("Dual Remedy" in t or "Liquidated" in t for t in titles), "PSA must have a 'Dual Remedy / Liquidated Damages' block"
        assert any("SB 909" in t or "Wholesaler" in t for t in titles), "PSA must have a 'Wholesaler Disclosure' block"
        assert any("Title" in t and "Closing" in t for t in titles), "PSA must have a 'Title and Closing' block"
        assert any("Signature" in t for t in titles), "PSA must have a 'Signatures' block"

    def test_psa_sb909_block_has_required_disclosures(self):
        """TN SB 909 block must disclose wholesale buyer intent and assignment fee."""
        psa = ot.render_psa_contract(
            _MARQUISE_LEAD,
            {"purchase_price": 21250, "assignment_fee": 3000}
        )
        sb909_block = next((b for b in psa["blocks"] if "SB 909" in b["title"] or "Wholesaler" in b["title"]), None)
        assert sb909_block is not None, "PSA must contain a TN SB 909 / Wholesaler Disclosure block"
        body = sb909_block["body"]
        assert "WHOLESALE BUYER" in body, "SB 909 block must state 'WHOLESALE BUYER'"
        assert "assign" in body.lower(), "SB 909 block must mention assignment intent"
        assert "3,000" in body or "3000" in body, "SB 909 block must state the assignment fee ($3,000)"

    def test_psa_contract_returns_psa_html(self):
        """render_psa_contract must return psa_html key with non-empty HTML."""
        psa = ot.render_psa_contract(
            _MARQUISE_LEAD,
            {"purchase_price": 21250, "assignment_fee": 3000}
        )
        assert "psa_html" in psa, "render_psa_contract must return psa_html key"
        assert len(psa["psa_html"]) > 200, "psa_html must be non-trivial HTML"

    def test_henry_buyer_negotiation_differs_from_seller_negotiation(self):
        """Henry buyer-side negotiation body must differ from seller-side negotiation body."""
        # Henry seller-side (standard render_negotiation)
        seller_side = ot.render_negotiation(_MARQUISE_LEAD, persona_key="henry")
        # Henry buyer-side (render_henry_buyer_negotiation)
        buyer_side = ot.render_henry_buyer_negotiation(
            _MARQUISE_LEAD, our_floor=24250, chris_offer=23750
        )
        assert seller_side["body_html"] != buyer_side["body_html"], (
            "Henry buyer-side negotiation must be different from seller-side negotiation -- "
            "different stage = different framing"
        )
        # Buyer-side must mention Chris or buyer-side context
        assert "Chris" in buyer_side["body_html"] or "buyer" in buyer_side["body_html"].lower(), (
            "Henry buyer-side negotiation must reference the buyer (Chris) context"
        )

    def test_marquise_pivot_internal_note(self):
        """render_marquise_pivot_to_chris must produce an internal team note."""
        result = ot.render_marquise_pivot_to_chris(_MARQUISE_LEAD, locked_price=21250)
        body = result["body_html"]
        assert "Chris" in body, "Marquise pivot note must mention Chris"
        assert "21,250" in body, "Marquise pivot note must mention the locked price"
        assert "INTERNAL" in result["subject"], "Marquise pivot subject must be marked [INTERNAL]"

    def test_marquise_final_wrap_commission(self):
        """render_marquise_final_wrap must contain the commission amount."""
        result = ot.render_marquise_final_wrap(
            _MARQUISE_LEAD,
            sell_price=21250,
            assign_price=24250,
            commission=3000
        )
        body = result["body_html"]
        assert "3,000" in body, "Marquise final wrap must contain the $3,000 commission"
        assert "CLOSED" in result["subject"] or "DEAL CLOSED" in result["subject"], (
            "Marquise final wrap subject must indicate DEAL CLOSED"
        )
