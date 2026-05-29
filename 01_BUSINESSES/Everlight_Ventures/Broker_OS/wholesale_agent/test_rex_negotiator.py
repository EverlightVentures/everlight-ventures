"""
Tests for rex_negotiator.py

Run: pytest test_rex_negotiator.py -v
"""

import importlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rex_negotiator as rn


# ---------------------------------------------------------------------------
# TASK 1: LLC / misrepresentation compliance
# ---------------------------------------------------------------------------

class TestNoLLCClaim:
    """No string in the module source may claim LLC or Logistics LLC status."""

    def _source(self):
        return Path(rn.__file__).read_text()

    def test_no_everlight_logistics_llc(self):
        assert "Everlight Logistics LLC" not in self._source(), (
            "COMPLIANCE FAIL: Everlight Logistics LLC found in rex_negotiator.py"
        )

    def test_no_registered_llc_claim(self):
        # The phrase "registered LLC" may legitimately appear inside the
        # system prompt's PROHIBITION (e.g. 'NEVER claim to be ... a
        # "registered LLC"'). What is forbidden is an AFFIRMATIVE claim.
        # Verify every occurrence is negated within the preceding context,
        # so the original bug ("We are a registered LLC (...)") still fails
        # while the protective guardrail language is allowed.
        src = self._source()
        for m in re.finditer(r"registered LLC", src):
            window = src[max(0, m.start() - 70):m.start()]
            assert re.search(r"NEVER|[Nn]ever|not |don't|cannot|can't", window), (
                "COMPLIANCE FAIL: affirmative 'registered LLC' claim near: "
                + src[max(0, m.start() - 70):m.start() + 30]
            )

    def test_no_bare_logistics_llc(self):
        assert "Logistics LLC" not in self._source(), (
            "COMPLIANCE FAIL: Logistics LLC found in rex_negotiator.py."
        )

    def test_suspicious_objection_no_llc(self):
        suspicious = rn.OBJECTION_PLAYBOOK["suspicious"]
        assert "LLC" not in suspicious, (
            "COMPLIANCE FAIL: suspicious objection still claims LLC: " + suspicious[:200]
        )

    def test_suspicious_objection_claims_sole_prop(self):
        suspicious = rn.OBJECTION_PLAYBOOK["suspicious"]
        assert "Richard Gee" in suspicious or "sole proprietor" in suspicious, (
            "suspicious must identify sole-prop operator (Richard Gee / sole proprietor)."
        )

    def test_want_more_info_no_llc(self):
        entry = rn.OBJECTION_PLAYBOOK["want_more_info"]
        assert "LLC" not in entry, (
            "COMPLIANCE FAIL: want_more_info objection claims LLC: " + entry[:200]
        )

    def test_want_more_info_sole_prop(self):
        entry = rn.OBJECTION_PLAYBOOK["want_more_info"]
        assert "Richard Gee" in entry or "sole proprietor" in entry, (
            "want_more_info must identify operator as sole proprietor."
        )


# ---------------------------------------------------------------------------
# TASK 2a: NEGOTIATION_SYSTEM_PROMPT quality checks
# ---------------------------------------------------------------------------

class TestSystemPrompt:

    def _p(self):
        return rn.NEGOTIATION_SYSTEM_PROMPT

    def test_uses_henry_persona(self):
        assert "Henry" in self._p(), (
            "System prompt must reference Henry -- old Rex persona must be replaced."
        )

    def test_discloses_assignment(self):
        assert "assign" in self._p().lower(), (
            "System prompt must instruct agent to disclose contract assignment intent."
        )

    def test_references_mao(self):
        assert "MAO" in self._p(), "System prompt must reference MAO pricing discipline."

    def test_anchor_replacement_references_listing(self):
        p = self._p().lower()
        assert "listing" in p or "commission" in p, (
            "System prompt must reference traditional listing path for anchor-replacement."
        )

    def test_anchor_replacement_references_net(self):
        assert "net" in self._p().lower(), (
            "System prompt must reference seller net for anchor-replacement framing."
        )

    def test_escalation_instruction_present(self):
        p = self._p().lower()
        has_escalate = "escalat" in p or "loop in" in p or "team lead" in p
        assert has_escalate, (
            "System prompt must contain an escalation instruction."
        )

    def test_no_llc_claim_in_system_prompt(self):
        p = self._p()
        if "LLC" in p:
            assert "NEVER" in p, (
                "System prompt contains LLC but not in a NEVER-claim context."
            )

    def test_sole_prop_in_system_prompt(self):
        assert "sole proprietor" in self._p().lower(), (
            "System prompt must state operator is sole proprietor."
        )

    def test_encourage_counsel(self):
        p = self._p().lower()
        assert "attorney" in p or "family" in p, (
            "System prompt must encourage sellers to consult family or attorney."
        )


# ---------------------------------------------------------------------------
# TASK 2b: escalation_check function
# ---------------------------------------------------------------------------

class TestEscalationCheck:
    """escalation_check(seller_message, sentiment) -> (bool, str)"""

    # -- should trigger True --

    def test_hostile_sentiment_triggers(self):
        needs_human, reason = rn.escalation_check("What is your offer?", sentiment="hostile")
        assert needs_human is True
        assert reason

    def test_angry_sentiment_triggers(self):
        needs_human, _ = rn.escalation_check("Just give me a number", sentiment="angry")
        assert needs_human is True

    def test_legal_threat_lawyer(self):
        needs_human, reason = rn.escalation_check(
            "I am going to contact my lawyer about this.", sentiment="neutral"
        )
        assert needs_human is True
        assert "lawyer" in reason

    def test_legal_threat_attorney(self):
        needs_human, reason = rn.escalation_check(
            "My attorney reviewed your offer.", sentiment="neutral"
        )
        assert needs_human is True
        assert "attorney" in reason

    def test_legal_threat_sue(self):
        needs_human, _ = rn.escalation_check(
            "I will sue you if you do not stop.", sentiment="neutral"
        )
        assert needs_human is True

    def test_legal_threat_court(self):
        needs_human, _ = rn.escalation_check(
            "I am taking this to court.", sentiment="neutral"
        )
        assert needs_human is True

    def test_legal_threat_fraud(self):
        needs_human, _ = rn.escalation_check(
            "This looks like fraud to me.", sentiment="neutral"
        )
        assert needs_human is True

    def test_legal_threat_report_you(self):
        needs_human, _ = rn.escalation_check(
            "I am going to report you to the BBB.", sentiment="neutral"
        )
        assert needs_human is True

    def test_confusion_what_is_this(self):
        needs_human, _ = rn.escalation_check(
            "What is this? I dont understand what you want.", sentiment="neutral"
        )
        assert needs_human is True

    def test_confusion_scam_question(self):
        needs_human, _ = rn.escalation_check("Is this a scam?", sentiment="neutral")
        assert needs_human is True

    def test_vulnerability_passed_away(self):
        needs_human, _ = rn.escalation_check(
            "My husband passed away last month and I am still dealing with it.",
            sentiment="neutral"
        )
        assert needs_human is True

    def test_vulnerability_dying(self):
        needs_human, _ = rn.escalation_check(
            "I am dying and just need to settle this quickly.", sentiment="neutral"
        )
        assert needs_human is True

    def test_vulnerability_cant_afford(self):
        needs_human, _ = rn.escalation_check(
            "I cannot afford to keep it and I am desperate.", sentiment="neutral"
        )
        assert needs_human is True

    def test_vulnerability_eviction(self):
        needs_human, _ = rn.escalation_check(
            "We have an eviction notice and I do not know what to do.", sentiment="neutral"
        )
        assert needs_human is True

    def test_optout_stop(self):
        needs_human, _ = rn.escalation_check("Stop emailing me.", sentiment="neutral")
        assert needs_human is True

    def test_optout_remove_me(self):
        needs_human, _ = rn.escalation_check(
            "Please remove me from your list.", sentiment="neutral"
        )
        assert needs_human is True

    def test_hostile_language_scammer(self):
        needs_human, _ = rn.escalation_check(
            "You are a scammer, leave me alone.", sentiment="neutral"
        )
        assert needs_human is True

    # -- should return False (normal negotiation messages) --

    def test_normal_what_is_your_offer(self):
        needs_human, reason = rn.escalation_check(
            "What is your offer on the property?", sentiment="neutral"
        )
        assert needs_human is False
        assert reason == ""

    def test_normal_counter(self):
        needs_human, _ = rn.escalation_check(
            "I was thinking more like $65,000.", sentiment="neutral"
        )
        assert needs_human is False

    def test_normal_tell_me_more(self):
        needs_human, _ = rn.escalation_check(
            "Can you tell me more about the process?", sentiment="interested"
        )
        assert needs_human is False

    def test_normal_need_time(self):
        needs_human, _ = rn.escalation_check(
            "I need to think about it for a few days.", sentiment="neutral"
        )
        assert needs_human is False

    def test_normal_how_fast(self):
        needs_human, _ = rn.escalation_check(
            "How fast can you close?", sentiment="interested"
        )
        assert needs_human is False

    def test_return_type_is_tuple(self):
        result = rn.escalation_check("hello")
        assert isinstance(result, tuple) and len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


# ---------------------------------------------------------------------------
# Draft gate: queue_for_human_review + AUTOSEND flag
# ---------------------------------------------------------------------------

class TestDraftGateWired:

    def test_queue_function_exists(self):
        assert callable(rn.queue_for_human_review)

    def test_human_review_queue_path_defined(self):
        assert hasattr(rn, "HUMAN_REVIEW_QUEUE")
        p = str(rn.HUMAN_REVIEW_QUEUE)
        assert "negotiation" in p and p.endswith(".jsonl")

    def test_autosend_default_off(self):
        import os
        autosend_env = os.environ.get("WHOLESALE_NEGOTIATE_AUTOSEND", "0")
        assert autosend_env.strip() in ("0", ""), (
            "WHOLESALE_NEGOTIATE_AUTOSEND must default to 0 (draft mode). "
            "Current env value: " + autosend_env
        )

    def test_queue_writes_jsonl(self, tmp_path, monkeypatch):
        test_queue = tmp_path / "test_queue.jsonl"
        monkeypatch.setattr(rn, "HUMAN_REVIEW_QUEUE", test_queue)
        monkeypatch.setattr(rn, "SLACK_TOKEN", "")

        deal = rn.DealState("123 Test St", "Memphis", "TN")
        deal.owner_name = "John Doe"
        deal.owner_email = "john@example.com"
        deal.our_offer = 45000
        deal.our_mao = 50000

        rn.queue_for_human_review(
            deal, "I need to think about it.", "Here is our offer...", "test_reason"
        )

        assert test_queue.exists(), "Queue file was not created."
        lines = test_queue.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["deal_id"] == deal.id
        assert entry["escalation_reason"] == "test_reason"
        assert "seller_message" in entry
        assert "drafted_response" in entry
        assert "action_required" in entry


# ---------------------------------------------------------------------------
# Smoke: module imports and syntax
# ---------------------------------------------------------------------------

class TestModuleIntegrity:
    def test_module_imports_cleanly(self):
        importlib.reload(rn)

    def test_objection_playbook_keys_present(self):
        expected_keys = {
            "too_low", "other_offers", "not_motivated",
            "want_more_info", "suspicious", "needs_time", "counter_offer"
        }
        assert expected_keys.issubset(set(rn.OBJECTION_PLAYBOOK.keys()))

    def test_deal_state_instantiation(self):
        d = rn.DealState("456 Elm St", "Memphis", "TN")
        assert d.status == "outreach_sent"
        assert d.city == "Memphis"

    def test_system_prompt_is_string(self):
        assert isinstance(rn.NEGOTIATION_SYSTEM_PROMPT, str)
        assert len(rn.NEGOTIATION_SYSTEM_PROMPT) > 200

    def test_no_em_dash_in_file(self):
        """Repo hook blocks U+2014 em-dash. File must use '--' instead."""
        source = Path(rn.__file__).read_text()
        em_dash = chr(0x2014)
        em_dash_count = source.count(em_dash)
        assert em_dash_count == 0, (
            str(em_dash_count) + " em-dash character(s) found in rex_negotiator.py. "
            "Replace all with --."
        )


# ---------------------------------------------------------------------------
# SHARED DECIDER -- compose_negotiation_reply (sim == live guarantee)
# ---------------------------------------------------------------------------

class TestComposeNegotiationReply:
    """The ONE function live + sim both call, so they cannot diverge."""

    def _deal(self):
        d = rn.DealState("100 Test Ave", "Memphis", "TN")
        d.owner_name = "Jane Doe"
        d.owner_email = "jane@example.com"
        d.arv = 100000
        d.our_offer = 48000
        d.our_mao = 54000
        d.repair_estimate = 22000
        d.status = "negotiating"
        return d

    def test_reply_shape(self):
        reply = rn.compose_negotiation_reply(self._deal(), "tell me more", is_first_touch=True)
        for k in ("subject", "body_html", "persona", "engine", "is_first_touch", "reasoned_text"):
            assert k in reply, "missing key: " + k

    def test_first_touch_uses_anchor_template(self):
        reply = rn.compose_negotiation_reply(self._deal(), "tell me more", is_first_touch=True)
        assert reply["engine"] == "template:first-touch-anchor"
        assert reply["is_first_touch"] is True
        assert len(reply["body_html"]) > 100  # branded anchor table

    def test_rounds_2plus_reasoned(self, monkeypatch):
        d = self._deal()

        def fake_gen(deal, msg, force_template=False):
            rn.LAST_RESPONSE_ENGINE = "llm:claude-sonnet-4-6"
            return "I hear you. The math works at 54k, not 60k."

        monkeypatch.setattr(rn, "generate_negotiation_response", fake_gen)
        reply = rn.compose_negotiation_reply(d, "I want 60k", is_first_touch=False)
        assert reply["engine"] == "llm:claude-sonnet-4-6"
        assert reply["reasoned_text"].startswith("I hear you")
        assert "54k" in reply["body_html"]
        assert reply["is_first_touch"] is False

    def test_rounds_2plus_reasoned_text_is_branded(self, monkeypatch):
        d = self._deal()

        def fake_gen(deal, msg, force_template=False):
            rn.LAST_RESPONSE_ENGINE = "template:keyword-fallback"
            return "Here is where I can be today."

        monkeypatch.setattr(rn, "generate_negotiation_response", fake_gen)
        reply = rn.compose_negotiation_reply(d, "too low", is_first_touch=False)
        # branded shell carries Henry's signature so reasoned == templated in inbox
        assert "Henry Hammond" in reply["body_html"]
        assert reply["engine"] == "template:keyword-fallback"


class TestRenderFreeform:
    """Branded wrap for reasoned (non-templated) replies."""

    def test_branded_wrap_paragraphs(self):
        import outreach_templates as ot
        out = ot.render_freeform("henry", "First para.\n\nSecond para.", "Re: 100 Test Ave")
        assert out["subject"] == "Re: 100 Test Ave"
        assert "<p>First para.</p>" in out["body_html"]
        assert "<p>Second para.</p>" in out["body_html"]
        assert "Henry Hammond" in out["body_html"]

    def test_escapes_html(self):
        import outreach_templates as ot
        out = ot.render_freeform("henry", "5 < 6 & 7 > 2", "subj")
        assert "&lt;" in out["body_html"]
        assert "&amp;" in out["body_html"]

    def test_unknown_persona_falls_back_to_henry(self):
        import outreach_templates as ot
        out = ot.render_freeform("nobody", "hi", "subj")
        assert out["persona"]["name"] == "Henry Hammond"
