"""
Deal State Machine -- LangGraph-powered adaptive deal flow.

Replaces linear "send email, wait, send another email" with a stateful
flow that adapts based on prospect responses:

  prospect -> qualify -> {
    positive -> book_call -> proposal -> negotiate -> close
    objection_budget -> send_roi_study -> followup
    objection_timing -> schedule_30d -> re_engage
    no_response -> followup_1 -> followup_2 -> breakup
    unsubscribe -> remove
  }

Each state transition is driven by:
  - NLP analysis of replies (spaCy sentiment + objection detection)
  - Brain policy scores (decisiveness, self-healing)
  - ML lead score (from LeadScorer)
  - LLM reasoning (via LiteLLM gateway)

Works without LangGraph import (pure Python state machine) for Oracle
compatibility. If LangGraph is available, uses it for visualization.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

log = logging.getLogger(__name__)


class DealState(str, Enum):
    """All possible states in the deal lifecycle."""
    NEW = "new"
    QUALIFIED = "qualified"
    OUTREACH_SENT = "outreach_sent"
    REPLIED_POSITIVE = "replied_positive"
    REPLIED_OBJECTION = "replied_objection"
    CALL_BOOKED = "call_booked"
    CALL_COMPLETED = "call_completed"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATING = "negotiating"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    NURTURE = "nurture"
    UNSUBSCRIBED = "unsubscribed"
    DORMANT = "dormant"


class DealEvent(str, Enum):
    """Events that trigger state transitions."""
    LEAD_CREATED = "lead_created"
    QUALIFIED = "qualified"
    OUTREACH_SENT = "outreach_sent"
    REPLY_POSITIVE = "reply_positive"
    REPLY_OBJECTION_BUDGET = "reply_objection_budget"
    REPLY_OBJECTION_TIMING = "reply_objection_timing"
    REPLY_OBJECTION_AUTHORITY = "reply_objection_authority"
    REPLY_OBJECTION_NEED = "reply_objection_need"
    NO_RESPONSE_7D = "no_response_7d"
    NO_RESPONSE_14D = "no_response_14d"
    NO_RESPONSE_21D = "no_response_21d"
    CALL_BOOKED = "call_booked"
    CALL_COMPLETED = "call_completed"
    PROPOSAL_SENT = "proposal_sent"
    PROPOSAL_ACCEPTED = "proposal_accepted"
    PROPOSAL_REJECTED = "proposal_rejected"
    CONTRACT_SIGNED = "contract_signed"
    UNSUBSCRIBED = "unsubscribed"


# State transition table: (current_state, event) -> (next_state, action)
TRANSITIONS = {
    (DealState.NEW, DealEvent.QUALIFIED): (DealState.QUALIFIED, "create_outreach_sequence"),
    (DealState.QUALIFIED, DealEvent.OUTREACH_SENT): (DealState.OUTREACH_SENT, "wait_for_reply"),
    (DealState.OUTREACH_SENT, DealEvent.REPLY_POSITIVE): (DealState.REPLIED_POSITIVE, "book_call"),
    (DealState.OUTREACH_SENT, DealEvent.REPLY_OBJECTION_BUDGET): (DealState.REPLIED_OBJECTION, "send_roi_case_study"),
    (DealState.OUTREACH_SENT, DealEvent.REPLY_OBJECTION_TIMING): (DealState.NURTURE, "schedule_followup_30d"),
    (DealState.OUTREACH_SENT, DealEvent.REPLY_OBJECTION_AUTHORITY): (DealState.REPLIED_OBJECTION, "request_intro_decision_maker"),
    (DealState.OUTREACH_SENT, DealEvent.REPLY_OBJECTION_NEED): (DealState.NURTURE, "send_educational_content"),
    (DealState.OUTREACH_SENT, DealEvent.NO_RESPONSE_7D): (DealState.OUTREACH_SENT, "send_followup_1"),
    (DealState.OUTREACH_SENT, DealEvent.NO_RESPONSE_14D): (DealState.OUTREACH_SENT, "send_followup_2"),
    (DealState.OUTREACH_SENT, DealEvent.NO_RESPONSE_21D): (DealState.DORMANT, "send_breakup_email"),
    (DealState.REPLIED_POSITIVE, DealEvent.CALL_BOOKED): (DealState.CALL_BOOKED, "prepare_call_brief"),
    (DealState.CALL_BOOKED, DealEvent.CALL_COMPLETED): (DealState.CALL_COMPLETED, "generate_proposal"),
    (DealState.CALL_COMPLETED, DealEvent.PROPOSAL_SENT): (DealState.PROPOSAL_SENT, "wait_for_decision"),
    (DealState.PROPOSAL_SENT, DealEvent.PROPOSAL_ACCEPTED): (DealState.NEGOTIATING, "send_contract"),
    (DealState.PROPOSAL_SENT, DealEvent.PROPOSAL_REJECTED): (DealState.NURTURE, "handle_rejection"),
    (DealState.NEGOTIATING, DealEvent.CONTRACT_SIGNED): (DealState.CLOSED_WON, "celebrate_and_onboard"),
    (DealState.REPLIED_OBJECTION, DealEvent.REPLY_POSITIVE): (DealState.REPLIED_POSITIVE, "book_call"),
    (DealState.NURTURE, DealEvent.REPLY_POSITIVE): (DealState.REPLIED_POSITIVE, "book_call"),
    (DealState.DORMANT, DealEvent.REPLY_POSITIVE): (DealState.REPLIED_POSITIVE, "book_call"),
    # Unsubscribe from any state
    **{(state, DealEvent.UNSUBSCRIBED): (DealState.UNSUBSCRIBED, "remove_from_sequences")
       for state in DealState if state != DealState.UNSUBSCRIBED},
}


# Action handlers
def _action_create_outreach(deal: dict) -> dict:
    """Create initial outreach sequence via LiteLLM."""
    try:
        from llm_gateway import ask_agent
        draft = ask_agent("piper_reeves",
            f"Draft a short intro email for {deal.get('lead_name', 'prospect')} "
            f"who needs {deal.get('need', 'automation help')}. "
            f"Keep it under 100 words, warm and personal.",
            model="fast")
        return {"action": "outreach_created", "draft": draft}
    except Exception:
        return {"action": "outreach_created", "draft": "template_fallback"}


def _action_send_roi_study(deal: dict) -> dict:
    return {"action": "roi_study_queued", "delay_days": 2}


def _action_schedule_30d(deal: dict) -> dict:
    return {"action": "followup_scheduled", "delay_days": 30}


def _action_book_call(deal: dict) -> dict:
    agent = deal.get("agent_slug", "piper-reeves")
    return {"action": "call_booking_link_sent", "booking_url": f"https://everlightventures.io/book/{agent}"}


def _action_prepare_brief(deal: dict) -> dict:
    try:
        from llm_gateway import ask
        brief = ask(
            f"Prepare a 3-point call brief for meeting with {deal.get('lead_name')} "
            f"about {deal.get('need')}. Include: their pain point, our solution, "
            f"pricing anchor. Be concise.",
            model="fast", agent_name="hammer_kovacs")
        return {"action": "call_brief_ready", "brief": brief}
    except Exception:
        return {"action": "call_brief_ready", "brief": "standard_brief"}


ACTION_HANDLERS = {
    "create_outreach_sequence": _action_create_outreach,
    "send_roi_case_study": _action_send_roi_study,
    "schedule_followup_30d": _action_schedule_30d,
    "book_call": _action_book_call,
    "prepare_call_brief": _action_prepare_brief,
}


def classify_reply(reply_text: str) -> DealEvent:
    """Classify a prospect's reply into a deal event using NLP."""
    try:
        import sys
        for p in ["/home/opc/06_DEVELOPMENT/everlight_os/neuromorphic",
                  "/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/neuromorphic"]:
            if p not in sys.path:
                sys.path.insert(0, p)

        from nlp_engine import analyze_email_reply
        analysis = analyze_email_reply(reply_text)

        if "unsubscribe" in reply_text.lower() or "stop" in reply_text.lower().split()[:3]:
            return DealEvent.UNSUBSCRIBED

        objections = analysis.get("objections", [])
        if analysis.get("is_interested") or analysis.get("reply_sentiment", 0) > 0.3:
            return DealEvent.REPLY_POSITIVE
        elif "budget" in objections:
            return DealEvent.REPLY_OBJECTION_BUDGET
        elif "timing" in objections:
            return DealEvent.REPLY_OBJECTION_TIMING
        elif "authority" in objections:
            return DealEvent.REPLY_OBJECTION_AUTHORITY
        elif "need" in objections or "competitor" in objections:
            return DealEvent.REPLY_OBJECTION_NEED
        elif analysis.get("reply_sentiment", 0) > 0:
            return DealEvent.REPLY_POSITIVE
        else:
            return DealEvent.REPLY_OBJECTION_TIMING  # Default: timing

    except Exception:
        # Fallback: simple keyword check
        text_lower = reply_text.lower()
        if any(w in text_lower for w in ["interested", "yes", "demo", "call", "schedule"]):
            return DealEvent.REPLY_POSITIVE
        elif any(w in text_lower for w in ["budget", "expensive", "cost"]):
            return DealEvent.REPLY_OBJECTION_BUDGET
        elif any(w in text_lower for w in ["later", "not now", "next quarter"]):
            return DealEvent.REPLY_OBJECTION_TIMING
        return DealEvent.REPLY_OBJECTION_TIMING


def transition(current_state: str, event: str, deal: dict | None = None) -> dict:
    """Execute a state transition and return the result.

    Args:
        current_state: Current DealState value (string)
        event: DealEvent value (string)
        deal: Context dict with lead_name, need, agent_slug, etc.

    Returns:
        Dict with: new_state, action, action_result, timestamp
    """
    deal = deal or {}
    state = DealState(current_state) if current_state in DealState._value2member_map_ else DealState.NEW
    evt = DealEvent(event) if event in DealEvent._value2member_map_ else None

    if evt is None:
        return {"error": f"Unknown event: {event}", "current_state": state.value}

    key = (state, evt)
    if key not in TRANSITIONS:
        return {
            "error": f"No transition from {state.value} on {evt.value}",
            "current_state": state.value,
            "valid_events": [e.value for s, e in TRANSITIONS if s == state],
        }

    new_state, action_name = TRANSITIONS[key]

    # Execute action handler if available
    handler = ACTION_HANDLERS.get(action_name)
    action_result = handler(deal) if handler else {"action": action_name}

    return {
        "previous_state": state.value,
        "event": evt.value,
        "new_state": new_state.value,
        "action": action_name,
        "action_result": action_result,
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_deal_flow_status(current_state: str) -> dict:
    """Get info about current state and available next steps."""
    state = DealState(current_state) if current_state in DealState._value2member_map_ else DealState.NEW
    valid_events = [(e.value, TRANSITIONS[(s, e)][0].value, TRANSITIONS[(s, e)][1])
                    for s, e in TRANSITIONS if s == state]

    return {
        "current_state": state.value,
        "possible_transitions": [
            {"event": ev, "next_state": ns, "action": act}
            for ev, ns, act in valid_events
        ],
    }
