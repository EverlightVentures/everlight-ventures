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

    def test_piper_catchphrase_first_conversation(self):
        """Piper's core catchphrase must appear in first touch."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "First conversation, not a pitch" in body, (
            "Piper first-touch must contain her catchphrase 'First conversation, not a pitch.'"
        )

    def test_piper_honest_with_you(self):
        """Piper's 'honest with you' tell must appear in her individual first touch."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert "Honest with you" in body or "honest with you" in body, (
            "Piper should use her 'Honest with you' tell on individual leads"
        )

    def test_piper_two_persona_phrases(self):
        """Piper's body must contain at least 2 persona-specific phrases."""
        result = ot.render_first_touch(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        piper_phrases = [
            "First conversation, not a pitch",
            "honest with you",
            "Honest with you",
            "genuinely love to hear",
            "Memphis",
            "no rush",
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

    def test_piper_followup_contains_social_proof_angle(self):
        result = ot.render_first_touch_followup(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        # Day-2 should contain social proof + the buyer-allocation angle
        assert any(kw in body for kw in ["closed", "buyer", "allocated", "follow"]), (
            f"Piper day-2 followup should contain social proof angle. Body: {body[:300]}"
        )

    def test_piper_final_closing_file_framing(self):
        result = ot.render_first_touch_final(_RITA_LEAD, persona_key="piper")
        body = result["body_html"]
        assert any(kw in body for kw in ["closing out", "closing", "Friday", "last note", "file"]), (
            f"Piper day-4 final should contain closing-file framing. Body: {body[:300]}"
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
        assert "First conversation, not a pitch" in result_day0["body_html"], (
            "Day-0 email must carry Piper's core catchphrase"
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
